#!/usr/bin/env python3
"""Play N matches between two (or more) bots and report each bot's win rate, on the
same table code and blind structure as the tournament. Matches run in parallel, one
per CPU core by default.

  play_multi 500 my_bots/mybot bots/caller                 # 500 heads-up freezeouts
  play_multi 500 my_bots/mybot bots/caller --seed 7        # matches use seeds 7, 8, 9, ...
  play_multi 500 my_bots/mybot bots/caller -j 4            # at most 4 matches at a time
  play_multi 500 my_bots/mybot bots/caller --log-dir logs  # one JSON-lines log per match

Seats rotate every match so no bot keeps the same position. Each match's line shows
its seed and seat order: to replay one, pass the bots to play.py in that order with
--seed. Every match has its own seed, so results don't depend on how many run at once.
Ctrl-C stops early and still prints the results so far.

A bot is a folder with bot.py (and optionally data/), a bot.py file, or a .zip.
"""

import argparse
import json
import math
import os
import sys
import time
from collections import Counter
from concurrent.futures import ProcessPoolExecutor, as_completed
from dataclasses import dataclass
from pathlib import Path

from pokercore import core_hash, structures
from pokercore.seats import BotSeat
from pokercore.seeds import derive_seed, new_seed
from pokercore.table import MODES, MatchConfig, play_match

RESULT_KEYS = ("bot", "place", "delta", "timeouts", "errors", "restarts", "avg_think_ms")


@dataclass
class Bot:
    name: str
    path: str
    hash: str = None
    source: str = "local"


class Log:
    """Collects a match's events; optionally prints hands or writes JSON lines."""

    def __init__(self, show=False, out=None):
        self.n = 0
        self.show = show
        self.out = open(out, "w", buffering=1 << 16) if out else None

    def emit(self, event_type, **data):
        event = {"i": self.n, "type": event_type, **data}
        self.n += 1
        if self.out:
            self.out.write(json.dumps(event, default=str) + "\n")
        if self.show:
            _print_event(event)
        return event

    def close(self):
        if self.out:
            self.out.close()


def _print_event(e):
    t = e["type"]
    if t == "level":
        print(f"-- level {e['level']}: blinds {e['sb']}/{e['bb']}" + (f", ante {e['ante']}" if e["ante"] else ""))
    elif t == "hand_start":
        stacks = ", ".join(f"{n} {s:,}" for n, s in e.get("stacks", {}).items())
        print(f"\nHand {e['hand'] + 1}  ({stacks})")
    elif t == "decision":
        a = e["applied"]
        cards = " ".join(e["state"].get("your_cards") or [])
        amount = f" {a['amount']:,}" if a.get("amount") else ""
        problem = f"  [{e['reply'].get('error')}]" if e.get("reply", {}).get("error") else ""
        print(f"  {e['street']:<7} {e['bot']} [{cards}] {a['action']}{amount}{problem}")
    elif t == "deal":
        print(f"  board   {' '.join(e['board'])}")
    elif t == "showdown":
        print("  showdown: " + ", ".join(f"{n} {' '.join(c)}" for n, c in (e.get("reveal") or {}).items()))
    elif t == "award":
        print(f"  {e['bot']} wins {e['amount']:,}")
    elif t == "elimination":
        print(f"** {e['bot']} is out (place {e['place']})")


def load_bots(paths):
    bots, names = [], set()
    for path in paths:
        bp = Path(path)
        if bp.name == "bot.py":
            base = bp.resolve().parent.name
        elif bp.suffix in (".py", ".zip"):
            base = bp.stem
        else:
            base = bp.resolve().name
        name, k = base, 2
        while name in names:
            name, k = f"{base}_{k}", k + 1
        names.add(name)
        bots.append(Bot(name, path))
    return bots


def run_match(i, seed, order, cfg, log_path=None):
    """Play one match (usually in a worker process) and return plain, picklable data."""
    names = [name for name, _ in order]
    try:
        config = MatchConfig(mode=cfg["mode"], hands=cfg["hands"], starting_stack=cfg["stack"],
                             structure=structures.parse(cfg["blinds"], cfg["stack"]), seed=seed,
                             time_limit_ms=cfg["time_limit_ms"])
        seats = [BotSeat(Bot(name, path), seed=derive_seed(seed, "bot", name),
                         time_limit_ms=cfg["time_limit_ms"], use_docker=False) for name, path in order]
        log = Log(show=cfg["show"], out=log_path)
        try:
            result = play_match(seats, config, "local", log)
        finally:
            log.close()
        return {
            "i": i, "seed": seed, "order": names,
            "hands": result["hands"],
            "stopped": str(result.get("stopped") or "").replace("_", " "),
            "results": [{k: r.get(k) for k in RESULT_KEYS} for r in result["results"]],
            "problems": {s.name: [str(e) for e in (s.summary().get("errors_list") or [])] for s in seats},
        }
    except Exception as e:      # one broken match shouldn't sink the whole run
        return {"i": i, "seed": seed, "order": names, "error": f"{type(e).__name__}: {e}"}


def winner_of(results):
    """The match winner's name, or None for a tie. Freezeouts have a place 1; fixed and
    cash matches may not, so those fall back to the biggest chip gain."""
    firsts = [r["bot"] for r in results if r.get("place") == 1]
    if firsts:
        return firsts[0] if len(firsts) == 1 else None
    best = max(r.get("delta") or 0 for r in results)
    top = [r["bot"] for r in results if (r.get("delta") or 0) == best]
    return top[0] if len(top) == 1 else None


def wilson(k, n, z=1.96):
    """95% Wilson score interval for k wins in n matches."""
    if n == 0:
        return 0.0, 0.0
    p = k / n
    d = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / d
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return max(0.0, centre - half), min(1.0, centre + half)


def _duration(seconds):
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h:
        return f"{h}h {m:02d}m"
    if m:
        return f"{m}m {s:02d}s"
    return f"{seconds:.1f}s"


def _new_stats():
    return {"wins": 0, "delta": 0, "timeouts": 0, "errors": 0, "restarts": 0, "think_total": 0.0, "think_n": 0}


class Tally:
    """Running totals across matches, plus the per-match line and the final summary."""

    def __init__(self, bots, games, quiet):
        self.n_bots = len(bots)
        self.games = games
        self.quiet = quiet
        self.width = len(str(games))
        self.stats = {b.name: _new_stats() for b in bots}
        self.problems = {b.name: Counter() for b in bots}
        self.played = self.ties = self.failed = self.hands = 0

    def add(self, m):
        head = f"match {m['i'] + 1:>{self.width}}/{self.games}  seed {m['seed']}  {' vs '.join(m['order'])}"
        if "error" in m:
            self.failed += 1
            print(f"{head}  FAILED: {m['error']}")
            return
        self.played += 1
        self.hands += m["hands"]
        for r in m["results"]:
            s = self.stats.setdefault(r["bot"], _new_stats())
            s["delta"] += r.get("delta") or 0
            for k in ("timeouts", "errors", "restarts"):
                s[k] += r.get(k) or 0
            if r.get("avg_think_ms") is not None:
                s["think_total"] += r["avg_think_ms"]
                s["think_n"] += 1
        for name, errs in m["problems"].items():
            self.problems.setdefault(name, Counter()).update(errs)
        winner = winner_of(m["results"])
        if winner:
            self.stats[winner]["wins"] += 1
        else:
            self.ties += 1
        if not self.quiet:
            tally = ", ".join(f"{n} {s['wins']}" for n, s in self.stats.items())
            print(f"{head}  -> {winner or 'tie'}  ({m['hands']} hands{', ' + m['stopped'] if m['stopped'] else ''})"
                  f"   [{tally}]")

    def summary(self, elapsed, jobs):
        """Print the results table; return True if any bot or match had problems."""
        rate = f", {self.played / elapsed:.1f} matches/s" if elapsed > 0 and self.played else ""
        print(f"\n{self.played} matches in {_duration(elapsed)}{rate}, {jobs} at a time"
              + (f", avg {self.hands / self.played:,.0f} hands per match" if self.played else ""))
        if not self.played:
            return True
        played = self.played
        rows = sorted(self.stats.items(), key=lambda kv: (-kv[1]["wins"], -kv[1]["delta"]))
        name_w = max(10, max(len(n) for n in self.stats))
        print(f"  {'bot':<{name_w}}  {'wins':>5}  {'win rate':>8}  {'95% CI':>13}  {'avg chips':>10}  {'avg think':>9}")
        for name, s in rows:
            lo, hi = wilson(s["wins"], played)
            ci = f"{lo:.1%}-{hi:.1%}"
            think = s["think_total"] / s["think_n"] if s["think_n"] else 0
            flags = [f"{s[k]} {k}" for k in ("timeouts", "errors", "restarts") if s[k]]
            print(f"  {name:<{name_w}}  {s['wins']:>5}  {s['wins'] / played:>8.1%}  {ci:>13}  "
                  f"{s['delta'] / played:>+10,.0f}  {think:>6.0f} ms" + (f"  {', '.join(flags)}" if flags else ""))
        extras = [x for x in (f"{self.ties} tied" if self.ties else "",
                              f"{self.failed} failed" if self.failed else "") if x]
        if extras:
            print(f"  ({', '.join(extras)}; win rate counts these as not won)")

        fair = 1 / self.n_bots
        leader, s = rows[0]
        lo, _ = wilson(s["wins"], played)
        if lo > fair:
            print(f"\n{leader} wins more than its fair share ({fair:.0%}) by more than chance explains (95% CI).")
        else:
            print(f"\nToo close to call: {leader}'s 95% CI still includes {fair:.0%}. More matches would narrow it.")

        any_problems = self.failed > 0
        for name, errs in self.problems.items():
            if errs:
                any_problems = True
                items = ", ".join(f"{e} (x{c})" if c > 1 else e for e, c in errs.most_common(5))
                print(f"\n{name} had problems: {items}" + (" ..." if len(errs) > 5 else ""))
        return any_problems


def _cpu_count():
    return (getattr(os, "process_cpu_count", None) or os.cpu_count)() or 1


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("games", type=int, help="number of matches to play")
    p.add_argument("bots", nargs="+", help="2-9 bot folders, bot.py files or .zip archives")
    p.add_argument("-j", "--jobs", type=int, default=None,
                   help=f"matches to run at once (default: one per CPU core, {_cpu_count()} here)")
    p.add_argument("--mode", choices=MODES, default="freezeout",
                   help="freezeout (default): until one bot has every chip; fixed: N hands, stacks carry "
                        "over; cash: N hands, every hand from the starting stack")
    p.add_argument("--hands", type=int, default=2000, help="hands per match (fixed/cash) or safety cap (freezeout)")
    p.add_argument("--blinds", default="standard",
                   help="turbo, standard (default) or slow (rising), or flat blinds like 50/100")
    p.add_argument("--stack", type=int, default=10_000, help="starting stack (default 10,000)")
    p.add_argument("--seed", type=int,
                   help="seed of the first match (default: random); match i uses seed + i - 1")
    p.add_argument("--time-limit-ms", type=int, default=None, help="per decision (default 2000)")
    p.add_argument("--no-rotate", action="store_true", help="keep the seat order as given in every match")
    p.add_argument("--quiet", action="store_true", help="print only the final summary, not a line per match")
    p.add_argument("--show", action="store_true", help="print every hand of every match (runs one at a time)")
    p.add_argument("--log-dir", metavar="DIR",
                   help="write each match's events, including what each bot saw, as DIR/match_N.jsonl")
    args = p.parse_args(argv)

    if not 2 <= len(args.bots) <= 9:
        p.error("a table needs 2-9 bots")
    if args.games < 1:
        p.error("the number of matches must be at least 1")
    if args.jobs is not None and args.jobs < 1:
        p.error("--jobs must be at least 1")
    bots = load_bots(args.bots)
    log_dir = Path(args.log_dir) if args.log_dir else None
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
    # --show prints hands as they happen, which only reads sensibly one match at a time
    jobs = 1 if args.show else min(args.jobs or _cpu_count(), args.games)

    base_seed = args.seed if args.seed is not None else new_seed()
    print(f"{' vs '.join(b.name for b in bots)}: {args.games} matches, {args.mode}, blinds {args.blinds}, "
          f"stack {args.stack:,}, seeds {base_seed}-{base_seed + args.games - 1}, {jobs} at a time"
          f"  (core {core_hash()})\n")

    cfg = {"mode": args.mode, "hands": args.hands, "stack": args.stack, "blinds": args.blinds,
           "time_limit_ms": args.time_limit_ms, "show": args.show}
    width = len(str(args.games))
    tasks = []
    for i in range(args.games):
        shift = 0 if args.no_rotate else i % len(bots)
        order = [(b.name, b.path) for b in bots[shift:] + bots[:shift]]
        log_path = str(log_dir / f"match_{i + 1:0{width}d}.jsonl") if log_dir else None
        tasks.append((i, base_seed + i, order, cfg, log_path))

    tally = Tally(bots, args.games, args.quiet)
    interrupted = False
    start = time.monotonic()
    try:
        if jobs == 1:
            for t in tasks:
                tally.add(run_match(*t))
        else:
            pool = ProcessPoolExecutor(max_workers=jobs)
            try:
                futures = {pool.submit(run_match, *t): t for t in tasks}
                for f in as_completed(futures):
                    try:
                        tally.add(f.result())
                    except Exception as e:      # e.g. a worker process died
                        i, seed, order = futures[f][:3]
                        tally.add({"i": i, "seed": seed, "order": [n for n, _ in order],
                                   "error": f"{type(e).__name__}: {e}"})
            finally:
                pool.shutdown(wait=False, cancel_futures=True)
    except KeyboardInterrupt:
        interrupted = True
        print("\nstopped")

    any_problems = tally.summary(time.monotonic() - start, jobs)
    if interrupted:
        return 130
    return 1 if any_problems else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:            # e.g. piped into head: stop quietly
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(0)
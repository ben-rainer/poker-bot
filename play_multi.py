#!/usr/bin/env python3
"""Play N matches between two (or more) bots and report each bot's win rate, on the
same table code, blind structure and sandbox as the tournament.

  play_multi 500 my_bots/mybot bots/caller                 # 500 heads-up freezeouts
  play_multi 500 my_bots/mybot bots/caller --seed 7        # matches use seeds 7, 8, 9, ...
  play_multi 500 my_bots/mybot bots/caller --docker        # inside the tournament's Docker sandbox
  play_multi 500 my_bots/mybot bots/caller --log-dir logs  # one JSON-lines log per match

Seats rotate every match so no bot keeps the same position. Each match's line shows
its seed and seat order: to replay one, pass the bots to play.py in that order with
--seed. Ctrl-C stops early and still prints the results so far.

A bot is a folder with bot.py (and optionally data/), a bot.py file, or a .zip.
"""

import argparse
import json
import math
import sys
import time
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from pokercore import core_hash, structures
from pokercore.seats import BotSeat
from pokercore.seeds import derive_seed, new_seed
from pokercore.table import MODES, MatchConfig, play_match


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
        self.out = open(out, "w") if out else None

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


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("games", type=int, help="number of matches to play")
    p.add_argument("bots", nargs="+", help="2-9 bot folders, bot.py files or .zip archives")
    p.add_argument("--mode", choices=MODES, default="freezeout",
                   help="freezeout (default): until one bot has every chip; fixed: N hands, stacks carry "
                        "over; cash: N hands, every hand from the starting stack")
    p.add_argument("--hands", type=int, default=2000, help="hands per match (fixed/cash) or safety cap (freezeout)")
    p.add_argument("--blinds", default="standard",
                   help="turbo, standard (default) or slow (rising), or flat blinds like 50/100")
    p.add_argument("--stack", type=int, default=10_000, help="starting stack (default 10,000)")
    p.add_argument("--seed", type=int,
                   help="seed of the first match (default: random); match i uses seed + i - 1")
    p.add_argument("--docker", action="store_true", help="run bots in the Docker sandbox (make sandbox first)")
    p.add_argument("--time-limit-ms", type=int, default=None, help="per decision (default 2000)")
    p.add_argument("--no-rotate", action="store_true", help="keep the seat order as given in every match")
    p.add_argument("--quiet", action="store_true", help="print only the final summary, not a line per match")
    p.add_argument("--show", action="store_true", help="print every hand of every match")
    p.add_argument("--log-dir", metavar="DIR",
                   help="write each match's events, including what each bot saw, as DIR/match_N.jsonl")
    args = p.parse_args(argv)

    if not 2 <= len(args.bots) <= 9:
        p.error("a table needs 2-9 bots")
    if args.games < 1:
        p.error("the number of matches must be at least 1")
    bots = load_bots(args.bots)
    log_dir = Path(args.log_dir) if args.log_dir else None
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)

    base_seed = args.seed if args.seed is not None else new_seed()
    width = len(str(args.games))
    print(f"{' vs '.join(b.name for b in bots)}: {args.games} matches, {args.mode}, blinds {args.blinds}, "
          f"stack {args.stack:,}, seeds {base_seed}-{base_seed + args.games - 1}"
          + (", Docker sandbox" if args.docker else "") + f"  (core {core_hash()})\n")

    stats = {b.name: _new_stats() for b in bots}
    problems = {b.name: Counter() for b in bots}
    played = ties = failed = total_hands = 0
    interrupted = False
    start = time.monotonic()

    try:
        for i in range(args.games):
            seed = base_seed + i
            shift = 0 if args.no_rotate else i % len(bots)
            order = bots[shift:] + bots[:shift]
            config = MatchConfig(mode=args.mode, hands=args.hands, starting_stack=args.stack,
                                 structure=structures.parse(args.blinds, args.stack), seed=seed,
                                 time_limit_ms=args.time_limit_ms)
            seats = [BotSeat(b, seed=derive_seed(seed, "bot", b.name), time_limit_ms=args.time_limit_ms,
                             use_docker=args.docker) for b in order]
            log = Log(show=args.show, out=log_dir / f"match_{i + 1:0{width}d}.jsonl" if log_dir else None)
            try:
                result = play_match(seats, config, "local", log)
            except Exception as e:      # one broken match shouldn't sink the whole run
                failed += 1
                print(f"match {i + 1:>{width}}/{args.games}  seed {seed}  FAILED: {type(e).__name__}: {e}")
                continue
            finally:
                log.close()

            played += 1
            total_hands += result["hands"]
            for r in result["results"]:
                s = stats.setdefault(r["bot"], _new_stats())
                s["delta"] += r.get("delta") or 0
                for k in ("timeouts", "errors", "restarts"):
                    s[k] += r.get(k) or 0
                if r.get("avg_think_ms") is not None:
                    s["think_total"] += r["avg_think_ms"]
                    s["think_n"] += 1
            for seat in seats:
                for err in seat.summary().get("errors_list") or []:
                    problems.setdefault(seat.name, Counter())[str(err)] += 1

            winner = winner_of(result["results"])
            if winner:
                stats[winner]["wins"] += 1
            else:
                ties += 1

            if not args.quiet:
                tally = ", ".join(f"{n} {s['wins']}" for n, s in stats.items())
                stopped = str(result.get("stopped") or "").replace("_", " ")
                print(f"match {i + 1:>{width}}/{args.games}  seed {seed}  {' vs '.join(b.name for b in order)}"
                      f"  -> {winner or 'tie'}  ({result['hands']} hands{', ' + stopped if stopped else ''})"
                      f"   [{tally}]")
    except KeyboardInterrupt:
        interrupted = True
        print("\nstopped")

    elapsed = time.monotonic() - start
    print(f"\n{played} matches in {_duration(elapsed)}"
          + (f", avg {total_hands / played:,.0f} hands per match" if played else ""))
    if not played:
        return 130 if interrupted else 1

    rows = sorted(stats.items(), key=lambda kv: (-kv[1]["wins"], -kv[1]["delta"]))
    name_w = max(10, max(len(n) for n in stats))
    print(f"  {'bot':<{name_w}}  {'wins':>5}  {'win rate':>8}  {'95% CI':>13}  {'avg chips':>10}  {'avg think':>9}")
    for name, s in rows:
        lo, hi = wilson(s["wins"], played)
        ci = f"{lo:.1%}-{hi:.1%}"
        think = s["think_total"] / s["think_n"] if s["think_n"] else 0
        flags = [f"{s[k]} {k}" for k in ("timeouts", "errors", "restarts") if s[k]]
        print(f"  {name:<{name_w}}  {s['wins']:>5}  {s['wins'] / played:>8.1%}  {ci:>13}  "
              f"{s['delta'] / played:>+10,.0f}  {think:>6.0f} ms" + (f"  {', '.join(flags)}" if flags else ""))
    extras = [x for x in (f"{ties} tied" if ties else "", f"{failed} failed" if failed else "") if x]
    if extras:
        print(f"  ({', '.join(extras)}; win rate counts these as not won)")

    fair = 1 / len(bots)
    leader, s = rows[0]
    lo, _ = wilson(s["wins"], played)
    if lo > fair:
        print(f"\n{leader} wins more than its fair share ({fair:.0%}) by more than chance explains (95% CI).")
    else:
        print(f"\nToo close to call: {leader}'s 95% CI still includes {fair:.0%}. More matches would narrow it.")

    any_problems = failed > 0
    for name, errs in problems.items():
        if errs:
            any_problems = True
            items = ", ".join(f"{e} (x{c})" if c > 1 else e for e, c in errs.most_common(5))
            print(f"\n{name} had problems: {items}" + (" ..." if len(errs) > 5 else ""))

    if interrupted:
        return 130
    return 1 if any_problems else 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except BrokenPipeError:            # e.g. piped into head: stop quietly
        import os
        os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        sys.exit(0)
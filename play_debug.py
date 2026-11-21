#!/usr/bin/env python3
"""Debug version of play.py: stops the match at the first sign of trouble and shows it.

  python3 play_debug.py my_bots/mybot bots/caller              # crash on the first bot problem
  python3 play_debug.py my_bots/mybot bots/caller --seed 7     # replay the seed a crash printed
  python3 play_debug.py my_bots/mybot bots/caller --show       # print every hand on the way there

The table normally catches a bot's exceptions, timeouts and bad replies, substitutes an
action and carries on, so problems only show up in the summary at the end. Here the first
one stops everything: you get the hand so far, the exact state the bot saw, its reply, the
error, and a traceback. Exceptions in the table code itself are never caught either.

A bot is a folder with bot.py (and optionally data/), a bot.py file, or a .zip.
"""

import argparse
import faulthandler
import json
import sys
from dataclasses import dataclass
from pathlib import Path

from pokercore import core_hash, structures
from pokercore.seats import BotSeat
from pokercore.seeds import derive_seed, new_seed
from pokercore.table import MODES, MatchConfig, play_match

# event types that mean something went wrong, even when the event carries no "error" field
PROBLEM_WORDS = ("error", "exception", "crash", "timeout", "restart", "invalid")
# routine event types that play.py's printer doesn't show either
QUIET_EVENTS = {"match_start", "post", "hand_end", "match_end"}


class BotProblem(BaseException):
    """A bot raised, timed out or sent a bad reply. A BaseException, not an Exception, so
    no `except Exception` inside the table code can swallow it on its way out."""


@dataclass
class Bot:
    name: str
    path: str
    hash: str = None
    source: str = "local"


def _problem_in(event):
    """(bot, error text) if this event reports a problem, else None."""
    bot = event.get("bot") or "?"
    reply = event.get("reply")
    if isinstance(reply, dict) and reply.get("error"):
        return bot, str(reply["error"])
    if event.get("error"):
        return bot, str(event["error"])
    for seat in event.get("seats") or []:     # match_start: did every bot load?
        warmup = seat.get("warmup") if isinstance(seat, dict) else None
        if isinstance(warmup, dict) and (warmup.get("ok") is False or warmup.get("error")):
            text = f"failed to load: {warmup.get('error')}"
            if warmup.get("logs"):
                text += f"\n\nwhat it printed while loading:\n{warmup['logs']}"
            return seat.get("name", "?"), text
    if any(w in str(event.get("type", "")).lower() for w in PROBLEM_WORDS):
        return bot, str(event["type"])
    return None


def _dump(obj):
    return json.dumps(obj, indent=2, default=str)


class Log:
    """Collects a match's events, prints or writes them like play.py, and crashes on the
    first event that reports a problem."""

    def __init__(self, seed, show=False, out=None):
        self.n = 0
        self.seed = seed
        self.show = show
        self.out = open(out, "w") if out else None
        self.hand_no = None
        self.hand = []          # events of the current hand, printed if something goes wrong

    def emit(self, event_type, **data):
        event = {"i": self.n, "type": event_type, **data}
        self.n += 1
        if self.out:
            self.out.write(json.dumps(event, default=str) + "\n")
            self.out.flush()    # so the log is complete up to the crash
        if self.show:
            _print_event(event)
        if event_type == "hand_start":
            self.hand_no = event.get("hand")
            self.hand = []
        self.hand.append(event)
        problem = _problem_in(event)
        if problem:
            self.crash(event, *problem)
        return event

    def crash(self, event, bot, problem):
        hand =f"hand {self.hand_no + 1}" if isinstance(self.hand_no, int) else "before the first hand"
        street = f", {event['street']}" if event.get("street") else ""
        print(f"\n{'=' * 70}\nBOT PROBLEM: {bot}, {hand}{street}  (seed {self.seed}, event {event['i']})\n{'=' * 70}")
        if not self.show and self.hand_no is not None:
            print("\nthis hand so far:")
            for e in self.hand:
                _print_event(e)
        print(f"\nerror:\n{problem}")
        if "state" in event:
            print(f"\nwhat {bot} saw:\n{_dump(event['state'])}")
        if "reply" in event:
            print(f"\nwhat {bot} replied:\n{_dump(event['reply'])}")
        if "applied" in event:
            print(f"\nwhat the table applied instead:\n{_dump(event['applied'])}")
        others = {k: v for k, v in event.items() if k not in ("i", "type", "bot", "street", "state", "reply", "applied")}
        if others:
            print(f"\nrest of the event:\n{_dump(others)}")
        print(flush=True)
        raise BotProblem(f"{bot}: {problem.splitlines()[-1] if problem.strip() else problem}")

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
    elif t not in QUIET_EVENTS:     # anything new is worth seeing while debugging
        print(f"  [{t}] {json.dumps({k: v for k, v in e.items() if k not in ('i', 'type')}, default=str)}")


def main(argv=None):
    faulthandler.enable()   # tracebacks even for hard crashes (segfaults) in native code
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("bots", nargs="+", help="2-9 bot folders, bot.py files or .zip archives")
    p.add_argument("--mode", choices=MODES, default="freezeout",
                   help="freezeout (default): until one bot has every chip; fixed: N hands, stacks carry "
                        "over; cash: N hands, every hand from the starting stack")
    p.add_argument("--hands", type=int, default=2000, help="hands to play (fixed/cash) or safety cap (freezeout)")
    p.add_argument("--blinds", default="standard",
                   help="turbo, standard (default) or slow (rising), or flat blinds like 50/100")
    p.add_argument("--stack", type=int, default=10_000, help="starting stack (default 10,000)")
    p.add_argument("--seed", type=int, help="match seed (default: random); the same seed deals the same cards")
    p.add_argument("--docker", action="store_true", help="run bots in the Docker sandbox (make sandbox first)")
    p.add_argument("--time-limit-ms", type=int, default=None,
                   help="per decision (default 2000); raise it if you're pausing in a debugger")
    p.add_argument("--show", action="store_true", help="print every hand")
    p.add_argument("--log", metavar="FILE", help="write every event, including what each bot saw, as JSON lines")
    args = p.parse_args(argv)

    if not 2 <= len(args.bots) <= 9:
        p.error("a table needs 2-9 bots")
    bots, names = [], set()
    for path in args.bots:
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

    seed = args.seed if args.seed is not None else new_seed()
    config = MatchConfig(mode=args.mode, hands=args.hands, starting_stack=args.stack,
                         structure=structures.parse(args.blinds, args.stack), seed=seed,
                         time_limit_ms=args.time_limit_ms)
    seats = [BotSeat(b, seed=derive_seed(seed, "bot", b.name), time_limit_ms=args.time_limit_ms,
                     use_docker=args.docker) for b in bots]

    print(f"{' vs '.join(b.name for b in bots)}: {args.mode}, blinds {args.blinds}, "
          f"stack {args.stack:,}, seed {seed}" + (", Docker sandbox" if args.docker else "")
          + f"  (core {core_hash()})  [debug: stops on the first problem]")
    log = Log(seed, show=args.show, out=args.log)
    try:
        result = play_match(seats, config, "local", log)
    finally:
        log.close()

    print(f"\n{result['hands']} hands ({result['stopped'].replace('_', ' ')})")
    for r in result["results"]:
        flags = [f"{r[k]} {k}" for k in ("timeouts", "errors", "restarts") if r.get(k)]
        print(f"  {r['place'] or '-'}. {r['bot']:<20} {r['final_stack']:>9,}  ({r['delta']:+,})"
              f"  avg think {r.get('avg_think_ms') or 0:.0f} ms" + (f"  {', '.join(flags)}" if flags else ""))

    # backstop: anything the table counted as a problem but never reported in an event
    missed = []
    for r in result["results"]:
        missed += [f"{r['bot']}: {r[k]} {k}" for k in ("timeouts", "errors", "restarts") if r.get(k)]
        if r.get("disabled"):
            missed.append(f"{r['bot']}: disabled by the table")
    for s in seats:
        missed += [f"{s.name}: {e}" for e in (s.summary().get("errors_list") or [])]
    if missed:
        raise BotProblem("problems the table recorded without reporting them as they happened:\n  "
                         + "\n  ".join(missed))
    print("\nno problems")
    return 0


if __name__ == "__main__":
    sys.exit(main())
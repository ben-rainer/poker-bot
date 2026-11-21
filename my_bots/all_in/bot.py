import random
from collections import Counter

RANKS = "23456789TJQKA"
DECK = [r + s for r in RANKS for s in "cdhs"]


def _straight(rs):
    s = set(rs) | ({-1} if 12 in rs else set())  # ace also plays low
    return next((h for h in range(12, 2, -1) if all(h - i in s for i in range(5))), 0)


def _strength(cards):
    rs = sorted((RANKS.index(c[0]) for c in cards), reverse=True)
    cnt = Counter(rs)
    g = sorted(cnt, key=lambda r: (cnt[r], r), reverse=True)  # ranks by count, then rank
    a, b = cnt[g[0]], cnt[g[1]]
    suit, n = Counter(c[1] for c in cards).most_common(1)[0]
    fl = sorted((RANKS.index(c[0]) for c in cards if c[1] == suit), reverse=True) if n >= 5 else []
    if fl and (h := _straight(fl)): return 8, h
    if a == 4: return 7, g[0], max(r for r in rs if r != g[0])
    if a == 3 and b >= 2: return 6, g[0], g[1]
    if fl: return 5, *fl[:5]
    if h := _straight(rs): return 4, h
    if a == 3: return 3, *g[:3]
    if a == b == 2: return 2, g[0], g[1], max(r for r in rs if r not in g[:2])
    return (1, *g[:4]) if a == 2 else (0, *g[:5])


def simulate_win_odds(game_state: dict, number_of_games: int) -> float:
    mine, board = game_state["your_cards"], game_state["community_cards"]
    deck = [c for c in DECK if c not in mine + board]
    wins = 0
    for _ in range(number_of_games):
        draw = random.sample(deck, 7 - len(board))  # 2 opponent cards + rest of the board
        river = board + draw[2:]
        wins += _strength(mine + river) > _strength(draw[:2] + river)
    return wins / number_of_games



# ===========================#
# ========== MAIN ========== #
# ===========================#



def decide(game_state: dict) -> dict:

    if game_state.get("can_check"): return {"action": "check"}

    if simulate_win_odds(game_state, 1000) > 0.5: return {"action": "all_in"}

    return {"action": "fold"}

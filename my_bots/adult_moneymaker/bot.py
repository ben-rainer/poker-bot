
import random
from collections import Counter

LAG = 1000

# ========== Winner ========== #

_RANK_VALUE = {r: v for v, r in enumerate("23456789TJQKA", start=2)}  # 2..14


def _parse_card(card: str) -> tuple[int, str]:
    card = card.strip()
    rank, suit = card[:-1].upper(), card[-1].lower()
    if rank == "10":
        rank = "T"
    return _RANK_VALUE[rank], suit


def _straight_high(ranks: set[int]) -> int:
    """Top card of the best straight in `ranks` (5 for the wheel A-2-3-4-5), or 0."""
    if 14 in ranks:
        ranks = ranks | {1}                     # the ace also plays low
    run = 0
    for r in range(14, 0, -1):
        if r in ranks:
            run += 1
            if run == 5:
                return r + 4
        else:
            run = 0
    return 0


def _hand_strength(cards: list[str]) -> tuple:
    """Strength of the best 5-card hand in 5-7 cards. Bigger tuple = better hand.

    (8, high)                    straight flush
    (7, quad, kicker)            four of a kind
    (6, trips, pair)             full house
    (5, c1, c2, c3, c4, c5)      flush
    (4, high)                    straight
    (3, trips, k1, k2)           three of a kind
    (2, high_pair, low_pair, k)  two pair
    (1, pair, k1, k2, k3)        one pair
    (0, c1, c2, c3, c4, c5)      high card
    """
    parsed = [_parse_card(c) for c in cards]
    ranks = [r for r, _ in parsed]

    by_suit: dict[str, list[int]] = {}
    for r, s in parsed:
        by_suit.setdefault(s, []).append(r)
    flush = next((rs for rs in by_suit.values() if len(rs) >= 5), None)

    if flush:
        sf = _straight_high(set(flush))
        if sf:
            return (8, sf)

    # (rank, count) sorted by count, then rank, highest first
    groups = sorted(Counter(ranks).items(), key=lambda rc: (rc[1], rc[0]), reverse=True)
    trips = [r for r, c in groups if c == 3]
    pairs = [r for r, c in groups if c == 2]

    if groups[0][1] == 4:
        quad = groups[0][0]
        return (7, quad, max(r for r in ranks if r != quad))
    if trips and (len(trips) > 1 or pairs):
        return (6, trips[0], max(trips[1:] + pairs))
    if flush:
        return (5, *sorted(flush, reverse=True)[:5])
    st = _straight_high(set(ranks))
    if st:
        return (4, st)
    if trips:
        t = trips[0]
        return (3, t, *sorted((r for r in ranks if r != t), reverse=True)[:2])
    if len(pairs) >= 2:
        hi, lo = pairs[0], pairs[1]
        return (2, hi, lo, max(r for r in ranks if r not in (hi, lo)))
    if pairs:
        p = pairs[0]
        return (1, p, *sorted((r for r in ranks if r != p), reverse=True)[:3])
    return (0, *sorted(ranks, reverse=True)[:5])


def is_winner(hand_one: list[str], hand_two: list[str], river: list[str]) -> bool | None:
    """True if hand_one beats hand_two on this board, False if it loses, None on a tie.

    hand_one / hand_two: exactly 2 hole cards each.
    river: the community cards, 3, 4 or 5 of them.
    """
    one = _hand_strength(list(hand_one) + list(river))
    two = _hand_strength(list(hand_two) + list(river))
    if one == two:
        return None
    return one > two


# ========== Score ========== #

def random_card() -> str:

    RANKS = ["2", "3", "4", "5", "6", "7", "8", "9", "T", "J", "Q", "K", "A"]
    SUITS = ["c", "d", "h", "s"]

    rank = random.choice(RANKS)
    suit = random.choice(SUITS)

    return(rank+suit)


def generate_opponent_hand(game_state: dict) -> list[str]:

    cards = []

    for i in range(2):
        while True:

            card = random_card()

            if not card in (game_state.get("your_cards") + game_state.get("community_cards") + cards):
                cards.append(card)
                break

    return cards


def complete_river(game_state: dict, opponent_hand: list[str]) -> list[str]:

    river = list(game_state.get("community_cards"))

    while len(river) < 5:

        card = random_card()

        if not card in (game_state.get("your_cards") + river + opponent_hand):
            river.append(card)

    return river


def simulate_win_odds(game_state: dict, number_of_games: int) -> float:

    wins = 0
    losses = 0

    for i in range(number_of_games):

        opponent_hand = generate_opponent_hand(game_state)
        river = complete_river(game_state, opponent_hand)

        winner = is_winner(game_state.get("your_cards"), opponent_hand, river)

        if winner == True: wins += 1
        if winner == False: losses += 1

    return wins / number_of_games



# ========== Main ========== #



def decide(game_state: dict) -> dict:


    """
    game_state (the most useful keys):
      your_cards        ["Ah", "Kh"]
      community_cards   [] preflop, then 3, 4, 5 cards
      street            "preflop" | "flop" | "turn" | "river"
      pot, current_bet, min_raise_to, amount_owed, can_check
      your_stack, your_bet_this_street, your_bot_id
      blinds            {"sb", "bb", "ante"} for this hand (they rise every 20 hands)
      hand_num          hand number in this match, from 0
      button_seat, sb_seat, bb_seat, seat_to_act
      players           public info per seat: seat, bot_id, stack, state, bet_this_street, ...
      action_log        every action this hand: {"seat", "bot_id", "action", "amount", "street"}
      match_action_log  the last 200 actions across the match, with "hand_num", plus
                        {"action": "show", "cards": [...]} for each player at a showdown

    Debugging: anything you print() is saved with the decision, and you can add
    a JSON-serialisable "debug" value to what you return, e.g.
    {"action": "call", "debug": {"equity": 0.4}}. Run with: python3 play.py --show
    """


    if game_state.get("type") == "warmup":     # one call before hand 1; load things here if you like
        return {"action": "check"}

    # ── Your strategy goes here. This example is deliberately simple. ──────────


    cards = game_state["your_cards"]
    pot = game_state["pot"]
    owed = game_state["amount_owed"]

    ranks = [c[0] for c in cards]


    if ranks[0] == ranks[1] and ranks[0] in "AKQJ":           # big pocket pair: raise


        raise_to = max(game_state["min_raise_to"], game_state["current_bet"] + pot)
        return {"action": "raise", "amount": raise_to}


    if game_state["can_check"]:

        return {"action": "check"}

    if owed <= pot * 0.25:    
                                         # cheap to continue: call
        return {"action": "call"}
        
    return {"action": "fold"}




# ========== Odds Calculation ========== #
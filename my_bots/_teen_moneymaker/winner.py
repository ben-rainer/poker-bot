
"""Showdown comparison for Texas Hold'em. Standard library only.

Cards are strings like "Ah", "Td", "9c" (rank then suit, as the engine sends
them); "10h" is also accepted. Each player's best five of their 7 (or 6, or 5)
cards is compared, so kickers beyond the best five never count.
"""

from collections import Counter

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
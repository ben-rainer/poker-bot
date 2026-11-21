

# Suits

# Clubs     _c
# Diamonds  _d 
# Hearts    _h 
# Spades    _s


# Ranks

# Two   2_
# Three 3_
# Four  4_
# Five  5_
# Six   6_
# Seven 7_
# Eight 8_
# Nine  9_
# Ten   T_
# Jack  J_
# Queen Q_
# King  K_
# Ace   A_  



def compare_high_card(hand_one: list[str], hand_two: list[str]) -> bool | None:

    RANK_INDEX = "234567889TJQKA"

    for card_index in range(5):

        card_one_index = RANK_INDEX.index(hand_one[card_index][0])
        card_two_index = RANK_INDEX.index(hand_two[card_index][0])

        if card_one_index > card_two_index:
            return True
        if card_one_index < card_two_index:
            return False

    return None



def rank_groups(hand: list[str]) -> list[int]:

    rank_count = {"2":0,"3":0,"4":0,"5":0,"6":0,"7":0,"8":0,"9":0,"T":0,"J":0,"Q":0,"K":0,"A":0}

    for card in hand:
        rank_count[card[0]] += 1
    
    rank_groups = []

    for value in rank_count.values():
        if value > 1:
            rank_groups.append(value)
    
    return rank_groups



def is_flush(hand: list[str]) -> bool:
    
    return hand[0][1] == hand[1][1] == hand[2][1] == hand[3][1] == hand[4][1]



def is_straight(hand: list[str]) -> bool:

    RANK_INDEX = "234567889TJQKA"

    rank_list = []

    for card in hand:
        rank_list.append(RANK_INDEX.index(card[0]))
    
    rank_list.sort()

    for i in range(4):
        if rank_list[i]+1 != rank_list[i+1]:
            return False

    return True

    
def get_hand_rank(hand: list[str]) -> int:

    groups = rank_groups(hand)
    
    # 9 Royal flush
    # TS never happening dawg

    # 8 Straight flush
    if is_straight(hand) and is_flush(hand): return 8

    # 7 Four of a kind
    if 4 in groups: return 7

    # 6 Full house
    if 3 in groups and 2 in groups: return 6

    # 5 Flush
    if is_flush(hand): return 5

    # 4 Straight
    if is_straight(hand): return 4

    # 3 Three of a kind
    if 3 in groups: return 3

    # 2 Two pair
    if groups.count(2)==2: return 2

    # 1 One pair
    if 2 in groups: return 1

    # 0 High card
    return 0



def compare_hands(hand_one: list[str], hand_two: list[str]) -> bool | None:
    
    hand_one_rank = get_hand_rank(hand_one)
    hand_two_rank = get_hand_rank(hand_two)

    if hand_one_rank > hand_two_rank:
        return True
    if hand_one_rank < hand_two_rank:
        return False
    
    


if __name__ == "__main__":

    print("Yo bruh")

    HAND_ONE = ["2s", "3s", "4s", "5s", "6s"]
    HAND_TWO = ["5s", "Td", "2h", "Kc", "5d"]

    print(compare_high_card(HAND_ONE, HAND_TWO))
    print(rank_groups(HAND_ONE))
    print(get_hand_rank(HAND_ONE))














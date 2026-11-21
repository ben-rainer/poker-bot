

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



def get_hand_rank(hand: list[str]) -> int:
    



def compare_hands(hand_one: list[str], hand_two: list[str]) -> bool | None:
    pass



if __name__ == "__main__":

    print("Yo bruh")

    HAND_ONE = ["5s", "Td", "2h", "Kc", "Ad"]
    HAND_TWO = ["5s", "Td", "2h", "Kc", "5d"]

    print(compare_high_card(HAND_ONE, HAND_TWO))














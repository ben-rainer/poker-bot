
import random

from winner import is_winner



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



if __name__ == "__main__":

    game_state_flop = {'type': 'action_request', 'your_cards': ['3s', '7c'], 'community_cards': ['Qd', '3h', '5h'], 'street': 'flop', 'pot': 800, 'your_stack': 9750, 'your_bet_this_street': 0, 'amount_owed': 300, 'can_check': False, 'current_bet': 300, 'min_raise_to': 600, 'your_bot_id': 'my_bot', 'seat_to_act': 1, 'button_seat': 0, 'sb_seat': 0, 'bb_seat': 1, 'hand_num': 0, 'hand_id': 'demo_flop_h0000', 'blinds': {'sb': 50, 'bb': 100, 'ante': 0}, 'players': [{'seat': 0, 'bot_id': 'opponent', 'stack': 9450, 'state': 'active', 'is_folded': False, 'is_all_in': False, 'bet_this_street': 300, 'hole_cards': None}, {'seat': 1, 'bot_id': 'my_bot', 'stack': 9750, 'state': 'active', 'is_folded': False, 'is_all_in': False, 'bet_this_street': 0, 'hole_cards': None}], 'action_log': [{'seat': 0, 'bot_id': 'opponent', 'action': 'small_blind', 'amount': 50, 'street': 'preflop'}, {'seat': 1, 'bot_id': 'my_bot', 'action': 'big_blind', 'amount': 100, 'street': 'preflop'}, {'seat': 0, 'bot_id': 'opponent', 'action': 'raise', 'amount': 250, 'street': 'preflop'}, {'seat': 1, 'bot_id': 'my_bot', 'action': 'call', 'amount': 150, 'street': 'preflop'}, {'seat': 1, 'bot_id': 'my_bot', 'action': 'check', 'amount': 0, 'street': 'flop'}, {'seat': 0, 'bot_id': 'opponent', 'action': 'raise', 'amount': 300, 'street': 'flop'}], 'match_action_log': [{'hand_num': 0, 'seat': 0, 'bot_id': 'opponent', 'action': 'small_blind', 'amount': 50, 'street': 'preflop'}, {'hand_num': 0, 'seat': 1, 'bot_id': 'my_bot', 'action': 'big_blind', 'amount': 100, 'street': 'preflop'}, {'hand_num': 0, 'seat': 0, 'bot_id': 'opponent', 'action': 'raise', 'amount': 250, 'street': 'preflop'}, {'hand_num': 0, 'seat': 1, 'bot_id': 'my_bot', 'action': 'call', 'amount': 150, 'street': 'preflop'}, {'hand_num': 0, 'seat': 1, 'bot_id': 'my_bot', 'action': 'check', 'amount': 0, 'street': 'flop'}, {'hand_num': 0, 'seat': 0, 'bot_id': 'opponent', 'action': 'raise', 'amount': 300, 'street': 'flop'}], 'time_limit_ms': 2000}
    game_state_turn = {'type': 'action_request', 'your_cards': ['Kh', '7d'], 'community_cards': ['Th', '6h', 'As', '9d'], 'street': 'turn', 'pot': 1150, 'your_stack': 9650, 'your_bet_this_street': 0, 'amount_owed': 450, 'can_check': False, 'current_bet': 450, 'min_raise_to': 900, 'your_bot_id': 'my_bot', 'seat_to_act': 0, 'button_seat': 0, 'sb_seat': 0, 'bb_seat': 1, 'hand_num': 0, 'hand_id': 'demo_turn_h0000', 'blinds': {'sb': 50, 'bb': 100, 'ante': 0}, 'players': [{'seat': 0, 'bot_id': 'my_bot', 'stack': 9650, 'state': 'active', 'is_folded': False, 'is_all_in': False, 'bet_this_street': 0, 'hole_cards': None}, {'seat': 1, 'bot_id': 'opponent', 'stack': 9200, 'state': 'active', 'is_folded': False, 'is_all_in': False, 'bet_this_street': 450, 'hole_cards': None}], 'action_log': [{'seat': 0, 'bot_id': 'my_bot', 'action': 'small_blind', 'amount': 50, 'street': 'preflop'}, {'seat': 1, 'bot_id': 'opponent', 'action': 'big_blind', 'amount': 100, 'street': 'preflop'}, {'seat': 0, 'bot_id': 'my_bot', 'action': 'raise', 'amount': 200, 'street': 'preflop'}, {'seat': 1, 'bot_id': 'opponent', 'action': 'call', 'amount': 100, 'street': 'preflop'}, {'seat': 1, 'bot_id': 'opponent', 'action': 'check', 'amount': 0, 'street': 'flop'}, {'seat': 0, 'bot_id': 'my_bot', 'action': 'raise', 'amount': 150, 'street': 'flop'}, {'seat': 1, 'bot_id': 'opponent', 'action': 'call', 'amount': 150, 'street': 'flop'}, {'seat': 1, 'bot_id': 'opponent', 'action': 'raise', 'amount': 450, 'street': 'turn'}], 'match_action_log': [{'hand_num': 0, 'seat': 0, 'bot_id': 'my_bot', 'action': 'small_blind', 'amount': 50, 'street': 'preflop'}, {'hand_num': 0, 'seat': 1, 'bot_id': 'opponent', 'action': 'big_blind', 'amount': 100, 'street': 'preflop'}, {'hand_num': 0, 'seat': 0, 'bot_id': 'my_bot', 'action': 'raise', 'amount': 200, 'street': 'preflop'}, {'hand_num': 0, 'seat': 1, 'bot_id': 'opponent', 'action': 'call', 'amount': 100, 'street': 'preflop'}, {'hand_num': 0, 'seat': 1, 'bot_id': 'opponent', 'action': 'check', 'amount': 0, 'street': 'flop'}, {'hand_num': 0, 'seat': 0, 'bot_id': 'my_bot', 'action': 'raise', 'amount': 150, 'street': 'flop'}, {'hand_num': 0, 'seat': 1, 'bot_id': 'opponent', 'action': 'call', 'amount': 150, 'street': 'flop'}, {'hand_num': 0, 'seat': 1, 'bot_id': 'opponent', 'action': 'raise', 'amount': 450, 'street': 'turn'}], 'time_limit_ms': 2000}
    game_state_river = {'type': 'action_request', 'your_cards': ['4d', 'Qd'], 'community_cards': ['Jc', '6s', '2d', '7s', 'Kc'], 'street': 'river', 'pot': 1500, 'your_stack': 9550, 'your_bet_this_street': 0, 'amount_owed': 600, 'can_check': False, 'current_bet': 600, 'min_raise_to': 1200, 'your_bot_id': 'my_bot', 'seat_to_act': 1, 'button_seat': 0, 'sb_seat': 0, 'bb_seat': 1, 'hand_num': 0, 'hand_id': 'demo_river_h0000', 'blinds': {'sb': 50, 'bb': 100, 'ante': 0}, 'players': [{'seat': 0, 'bot_id': 'opponent', 'stack': 8950, 'state': 'active', 'is_folded': False, 'is_all_in': False, 'bet_this_street': 600, 'hole_cards': None}, {'seat': 1, 'bot_id': 'my_bot', 'stack': 9550, 'state': 'active', 'is_folded': False, 'is_all_in': False, 'bet_this_street': 0, 'hole_cards': None}], 'action_log': [{'seat': 0, 'bot_id': 'opponent', 'action': 'small_blind', 'amount': 50, 'street': 'preflop'}, {'seat': 1, 'bot_id': 'my_bot', 'action': 'big_blind', 'amount': 100, 'street': 'preflop'}, {'seat': 0, 'bot_id': 'opponent', 'action': 'raise', 'amount': 250, 'street': 'preflop'}, {'seat': 1, 'bot_id': 'my_bot', 'action': 'call', 'amount': 150, 'street': 'preflop'}, {'seat': 1, 'bot_id': 'my_bot', 'action': 'check', 'amount': 0, 'street': 'flop'}, {'seat': 0, 'bot_id': 'opponent', 'action': 'raise', 'amount': 200, 'street': 'flop'}, {'seat': 1, 'bot_id': 'my_bot', 'action': 'call', 'amount': 200, 'street': 'flop'}, {'seat': 1, 'bot_id': 'my_bot', 'action': 'check', 'amount': 0, 'street': 'turn'}, {'seat': 0, 'bot_id': 'opponent', 'action': 'check', 'amount': 0, 'street': 'turn'}, {'seat': 1, 'bot_id': 'my_bot', 'action': 'check', 'amount': 0, 'street': 'river'}, {'seat': 0, 'bot_id': 'opponent', 'action': 'raise', 'amount': 600, 'street': 'river'}], 'match_action_log': [{'hand_num': 0, 'seat': 0, 'bot_id': 'opponent', 'action': 'small_blind', 'amount': 50, 'street': 'preflop'}, {'hand_num': 0, 'seat': 1, 'bot_id': 'my_bot', 'action': 'big_blind', 'amount': 100, 'street': 'preflop'}, {'hand_num': 0, 'seat': 0, 'bot_id': 'opponent', 'action': 'raise', 'amount': 250, 'street': 'preflop'}, {'hand_num': 0, 'seat': 1, 'bot_id': 'my_bot', 'action': 'call', 'amount': 150, 'street': 'preflop'}, {'hand_num': 0, 'seat': 1, 'bot_id': 'my_bot', 'action': 'check', 'amount': 0, 'street': 'flop'}, {'hand_num': 0, 'seat': 0, 'bot_id': 'opponent', 'action': 'raise', 'amount': 200, 'street': 'flop'}, {'hand_num': 0, 'seat': 1, 'bot_id': 'my_bot', 'action': 'call', 'amount': 200, 'street': 'flop'}, {'hand_num': 0, 'seat': 1, 'bot_id': 'my_bot', 'action': 'check', 'amount': 0, 'street': 'turn'}, {'hand_num': 0, 'seat': 0, 'bot_id': 'opponent', 'action': 'check', 'amount': 0, 'street': 'turn'}, {'hand_num': 0, 'seat': 1, 'bot_id': 'my_bot', 'action': 'check', 'amount': 0, 'street': 'river'}, {'hand_num': 0, 'seat': 0, 'bot_id': 'opponent', 'action': 'raise', 'amount': 600, 'street': 'river'}], 'time_limit_ms': 2000}

    print(simulate_win_odds(game_state_river, 10000))
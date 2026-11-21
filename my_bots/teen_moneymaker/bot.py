"""
The next generation Moneymaker model

by Ben Rainer and Nico Couton
"""

"""
  - Check your bot before submitting:  make validate BOT=my_bots/<your_team>
"""

import random  # noqa: F401  (seeded per match, so a seeded match replays exactly)
from score import simulate_win_odds

# Helper methods
def hand_score(game_state:dict) -> float:
    '''Determine how good a hand is.'''
    
    return simulate_win_odds(game_state, 10000)
    
    # Kid Moneymaker does it randomly
    #return random.randrange(1, 100) / 100

def calculate_raise_amount(current_bet: int, ante: int) -> int:
    '''Calculate the amount we can bet during a raise action.'''
    
    # Kid Moneymaker will raise linearly
    return current_bet + max(10, (ante / 2))

def calculate_bluff_amount(current_bet: int, score: float, ante: int):
    '''Calculate the amount we can bet during a bluff action.'''
    
    # Kid Moneymaker will bluff linearly
    return current_bet + max(10, ante, (1 - score) * current_bet)

def wildcard() -> bool:
    '''1% chance to return true'''
    return random.random() < 0.01

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
    current_bet = game_state.get("current_bet") or 10
    
    # determine if blind
    seat = game_state.get("seat_to_act")
    sb_seat = game_state.get("sb_seat")
    bb_seat = game_state.get("bb_seat")
    button_seat = game_state.get("button_seat")
    blinds = game_state.get("blinds") or {}
    
    is_small_blind = (seat == sb_seat)
    is_big_blind = (seat == bb_seat)
    is_button = (seat == button_seat)
    
    ante = blinds.get("ante") or 0
    
    if game_state.get("type") == "warmup":     # one call before hand 1; load things here if you like
        return {"action": "check"}

    elif game_state.get("street") == "preflop":
        # Must call, raise or check
        
        if(not is_small_blind and not is_big_blind):
            score: float = hand_score(game_state)
            raiseby = calculate_raise_amount(current_bet, ante)
            
            # Fold if we have a very bad hand
            if(score >= 0.75):
                return {"action": "call"}
            if(score < 0.5):
                return {"action": "check"}
        
        raiseby = calculate_raise_amount(current_bet, ante)
        if(is_small_blind):
            raiseby = blinds.get("sb") + ante
        elif(is_big_blind):
            raiseby = blinds.get("bb") + ante
        
        return {"action": "raise", "amount": raiseby}

    else:
        score: float = hand_score(game_state)
        raiseby = calculate_raise_amount(current_bet, ante)
        
        # Wildcard
        if(wildcard()): return {"action": "all_in"}
        
        # Fold if we have a very bad hand
        # if(score < 0.1):
        #     return {"action": "fold"}
        
        if(score > 0.94):
            # We have an exceptionally good hand, go all in 
            return {"action": "all_in"}
        elif(score > 0.5 and score < 0.75):
            # We have a very good hand, raise it a bit more than the current bet.
            return {"action": "raise", "amount": raiseby}
        elif(score >= 0.75):
            # We have a decent hand, call the current bet.
            return {"action": "call"}
        
        # Otherwise, check
        if(game_state.get("can_check")):
            return {"action": "check"}

    # Fold in all other cases
    return {"action": "fold"}
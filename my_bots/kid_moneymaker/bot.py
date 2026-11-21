"""
A very basic poker bot, blindly figuring out life

The most whimsy to date of any Moneymaker model

by Ben Rainer and Nico Couton
"""

"""
Bot template. Copy this folder to my_bots/<your_team>/ and write decide().

  - decide() is called once per decision and has 2 seconds to return, or your
    bot folds. Crashes and invalid actions also fold; your bot stays in the game.
  - You may use the Python 3.10 standard library, eval7, numpy, scipy, treys
    and scikit-learn. Nothing else is installed in the sandbox.
  - No network, no file writes, no subprocesses, no eval/exec. You may read
    your own data/ folder, at import time only.
  - Check your bot before submitting:  make validate BOT=my_bots/<your_team>

The full list of what decide() receives is in the README ("What your bot
sees"); the most useful keys are summarised below.

RETURN FORMAT:
  {"action": "fold"}
  {"action": "check"}                       # only when can_check is True
  {"action": "call"}
  {"action": "raise", "amount": 1200}       # amount = your TOTAL bet this street
  {"action": "all_in"}

CARDS are strings like "As" (ace of spades) or "Td" (ten of diamonds).
"""

import random  # noqa: F401  (seeded per match, so a seeded match replays exactly)


# Helper methods
def hand_score(hand: list) -> float:
    '''Determine how good a hand is.'''
    
    # Kid Moneymaker does it randomly
    return random.randrange(1, 100) / 100

def calculate_raise_amount(current_bet: int, ante: int) -> int:
    '''Calculate the amount we can bet during a raise action.'''
    
    # Kid Moneymaker will only raise 10 each time, regardless
    return min(current_bet + 10, ante)

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
        # Must call, raise or fold
        
        raiseby = calculate_raise_amount(current_bet, ante)
        # If blind, bet the minimum
        if(is_small_blind):
            raiseby = blinds.get("sb")
        elif(is_big_blind):
            raiseby = blinds.get("bb")
        
        return {"action": "raise", "amount": raiseby}

    else:
        score: float = hand_score(game_state.get("your_cards"))
        raiseby = calculate_raise_amount(current_bet, ante)
        
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
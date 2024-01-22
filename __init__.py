from typing import Sequence

from anki.cards import Card
from anki.notes import Note
from aqt import gui_hooks, mw
from aqt.browser import Browser
from aqt.qt import *
from aqt.utils import tooltip

# Read config
config = mw.addonManager.getConfig(__name__)

# Load config values
enableLearn = config['enable-learn']
learnConsecutive = config['learn-consecutive']
enableLearnTag = config['enable-learn-tag']
learnTag = config['learn-tag']
enableLearnSuspend = config['enable-learn-suspend']

enableForget = config['enable-forget']
forgetConsecutive = config['forget-consecutive']
enableForgetTag = config['enable-forget-tag']
forgetTag = config['forget-tag']
enableForgetSuspend = config['enable-forget-suspend']

ignoreSuspendedCards = config['ignore-suspended-cards']

# Constant for the action name
ACTION_NAME = "Rule of 3s"

# Function to check the "Rule of 3s" for a card
def checkCard(*args):
    if len(args) == 1:
        card = args[0]
        ease = None
    elif len(args) == 3:
        _, card, ease = args
    else:
        raise ValueError("Invalid number of arguments")

    if ignoreSuspendedCards:
        if card.queue == -1: # if card is suspended
            return 0

    # Retrieve the list of reviews for the card from the database
    review_list = mw.col.db.all(f"SELECT ease, type FROM revlog WHERE cid = '{card.id}' ORDER BY id ASC ")

    n = len(review_list)

    # Check for wrong answers
    if enableForget:
        if n >= forgetConsecutive:  # Check if a card has more than n previous reviews
            # Extract ease (rating) values from the last n reviews
            last_n_reviews = [review[0] for review in review_list[-forgetConsecutive:]]

            # Check if all the last n reviews are ratings 1 or 2
            if all(rating in (1, 2) for rating in last_n_reviews):
                # Set the card properties and add a tag
                if enableForgetSuspend:
                    card.queue = -1
                    card.flush()
                if enableForgetTag:
                    card.note().tags.append(forgetTag)
                    card.note().flush()
                if ease != None:
                    tooltip(f"Card marked: {forgetConsecutive} consecutive wrongs.")
                return 1

    # Check for correct answers
    if enableLearn:
        review_count = 0
        consecutive_corrects = 0
        for review in review_list:
            rating = review[0]
            revType = review[1]

            if rating in (3, 4):
                consecutive_corrects += 1
                if revType != 0: # if the card is out of its learning stage
                    review_count += 1
            else:
                consecutive_corrects = 0
                review_count = 0

            if consecutive_corrects >= learnConsecutive and review_count >= learnConsecutive/2:
                # Set the card properties
                if enableLearnSuspend:
                    card.queue = -1
                    card.flush()
                if enableLearnTag:
                    card.note().tags.append(learnTag)
                    card.note().flush()
                if ease != None:
                    tooltip(f"Card marked: {learnConsecutive} consecutive corrects.")
                return 2

    return 0

# Function to perform the "Rule of 3s" check on selected cards in bulk
def bulk_check_rule_of_3(nids: Sequence):
    mw.checkpoint(ACTION_NAME)
    mw.progress.start()

    answers = [0, 0, 0]


    for nid in nids:
        card = mw.col.get_card(nid)
        answers[checkCard(card)] += 1

    tooltip(f"Checked {answers[0]+answers[1]+answers[2]} notes.\nMarked {answers[1]} new forgotten cards and {answers[2]} new learnt cards.")

    mw.progress.finish()
    mw.reset()

# Function to set up the menu entry in the browser window
def setup_browser_menu(browser: Browser):
    action = QAction(ACTION_NAME, browser)
    qconnect(action.triggered, lambda: bulk_check_rule_of_3(browser.selected_cards()))
    browser.form.menuEdit.addAction(action)

# Add hooks
gui_hooks.reviewer_did_answer_card.append(checkCard)
gui_hooks.browser_menus_did_init.append(setup_browser_menu)

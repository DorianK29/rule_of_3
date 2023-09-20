from typing import Sequence

from anki.cards import Card
from anki.notes import Note
from aqt import gui_hooks, mw
from aqt.browser import Browser
from aqt.qt import *
from aqt.utils import tooltip

# Constant for the action name
ACTION_NAME = "Rule of 3's"

# Function to check the "Rule of 3's" for a card
def checkCard(*args):
    if len(args) == 1:
        card = args[0]
        ease = None
    elif len(args) == 3:
        _, card, ease = args
    else:
        raise ValueError("Invalid number of arguments")

    # Retrieve the list of reviews for the card from the database
    review_list = mw.col.db.all(f"SELECT ease, type FROM revlog WHERE cid = '{card.id}' ORDER BY id ASC ")

    n = len(review_list)

    review_count = 0
    consecutive_corrects = 0

    if n >= 3:  # Check if a card has more than 3 previous reviews
        # Extract ease (rating) values from the last 3 reviews
        last_three_reviews = [review[0] for review in review_list[-3:]]

        # Check if all the last 3 reviews are ratings 1 or 2
        if all(rating in (1, 2) for rating in last_three_reviews):
            # Set the card properties and add a tag
            card.queue = -1
            card.flush()
            card.note().tags.append("Relearn")
            card.note().flush()
            if ease != None:
                tooltip("Card suspended: 3 consecutive forgottens.")
            return

    for review in review_list:
        rating = review[0]
        revType = review[1]

        if rating in (3, 4):
            consecutive_corrects += 1
            if revType != 0:
                review_count += 1
        else:
            consecutive_corrects = 0
            review_count = 0

        if consecutive_corrects >= 3 and review_count >= 2:
            # Set the card properties
            card.queue = -1
            card.flush()
            if ease != None:
                tooltip("Card suspended: 3 consecutive corrects.")
            return

# Function to perform the "Rule of 3's" check on selected cards in bulk
def bulk_check_rule_of_3(nids: Sequence):
    mw.checkpoint(ACTION_NAME)
    mw.progress.start()

    for nid in nids:
        card = mw.col.get_card(nid)
        checkCard(card)

    tooltip(f"Checked {len(nids)} notes.")

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

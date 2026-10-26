"""
Unit Tests for SuperMemo SM-2 Algorithm & Deck Scheduler
"""

import pytest
from datetime import datetime
from src.sm2_scheduler import SM2Card, SM2DeckScheduler
from src.config import SM2_DEFAULT_EF, SM2_MIN_EF


def test_sm2_initial_state():
    card = SM2Card(card_id="c1", front="What is 2+2?", back="4")
    assert card.card_id == "c1"
    assert card.repetition == 0
    assert card.interval == 0
    assert card.easiness_factor == SM2_DEFAULT_EF
    assert card.mastery_tier == "New"
    assert card.is_due is True


def test_sm2_first_successful_review():
    card = SM2Card(card_id="c2", front="Q", back="A")
    # Review with quality 4 (Good)
    res = card.review(quality=4)
    assert res["new_repetition"] == 1
    assert res["new_interval"] == 1
    assert card.mastery_tier == "Learning"
    assert card.lapses == 0


def test_sm2_second_successful_review():
    card = SM2Card(card_id="c3", front="Q", back="A", repetition=1, interval=1)
    res = card.review(quality=4)
    assert res["new_repetition"] == 2
    assert res["new_interval"] == 6
    assert card.mastery_tier == "Consolidating"


def test_sm2_third_successful_review_scaling():
    card = SM2Card(card_id="c4", front="Q", back="A", repetition=2, interval=6, easiness_factor=2.5)
    res = card.review(quality=5)  # Perfect recall
    assert res["new_repetition"] == 3
    # Interval = round(6 * EF')
    assert res["new_interval"] >= 15
    assert card.easiness_factor >= 2.5


def test_sm2_failure_lapse():
    card = SM2Card(card_id="c5", front="Q", back="A", repetition=3, interval=15, easiness_factor=2.5)
    # Failed recall (quality 1 = Again)
    res = card.review(quality=1)
    assert res["new_repetition"] == 0
    assert res["new_interval"] == 1
    assert card.lapses == 1
    assert card.mastery_tier == "Learning"


def test_sm2_ef_lower_bound():
    card = SM2Card(card_id="c6", front="Q", back="A", easiness_factor=1.3)
    # Repeatedly review with 0 (blackout)
    for _ in range(5):
        card.review(quality=0)
    assert card.easiness_factor == SM2_MIN_EF  # Must not drop below 1.3


def test_sm2_retention_calculation():
    card = SM2Card(card_id="c7", front="Q", back="A", interval=10, last_reviewed=datetime.utcnow().strftime("%Y-%m-%d"))
    retention_now = card.calculate_retention(days_elapsed=0)
    assert retention_now == 1.0
    retention_future = card.calculate_retention(days_elapsed=15)
    assert 0.0 < retention_future < 1.0


def test_sm2_deck_analytics():
    cards = [
        SM2Card(card_id="1", front="A", back="1", repetition=0),
        SM2Card(card_id="2", front="B", back="2", repetition=1),
        SM2Card(card_id="3", front="C", back="3", repetition=5, interval=25),
    ]
    scheduler = SM2DeckScheduler(cards)
    analytics = scheduler.get_deck_analytics()
    assert analytics["total_cards"] == 3
    assert analytics["mastered_count"] == 1
    assert analytics["learning_count"] == 1
    assert analytics["new_count"] == 1
    assert 0 <= analytics["mastery_percentage"] <= 100

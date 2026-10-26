"""
SuperMemo SM-2 Spaced Repetition Engine
Implements the classic SM-2 algorithm with continuous easiness factor adjustment,
interval scheduling, retention modeling, and mastery tier categorization.
"""

from __future__ import annotations

import math
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
from src.config import SM2_DEFAULT_EF, SM2_MIN_EF, SM2_INITIAL_INTERVAL_1, SM2_INITIAL_INTERVAL_2


class SM2Card:
    """Represents a single flashcard with its SM-2 spaced repetition state."""

    def __init__(
        self,
        card_id: str,
        front: str,
        back: str,
        hint: str = "",
        category: str = "General",
        repetition: int = 0,
        interval: int = 0,
        easiness_factor: float = SM2_DEFAULT_EF,
        last_reviewed: Optional[str] = None,
        next_review_due: Optional[str] = None,
        review_count: int = 0,
        lapses: int = 0,
    ):
        self.card_id = card_id
        self.front = front
        self.back = back
        self.hint = hint
        self.category = category
        self.repetition = repetition
        self.interval = interval
        self.easiness_factor = max(SM2_MIN_EF, easiness_factor)
        self.last_reviewed = last_reviewed
        self.next_review_due = next_review_due or datetime.utcnow().strftime("%Y-%m-%d")
        self.review_count = review_count if review_count > 0 else repetition
        self.lapses = lapses

    @property
    def is_due(self) -> bool:
        """Determines if the card is due for review today or overdue."""
        if not self.next_review_due:
            return True
        today = datetime.utcnow().strftime("%Y-%m-%d")
        return self.next_review_due <= today

    @property
    def mastery_tier(self) -> str:
        """
        Categorizes card recall strength:
        - New: never reviewed
        - Learning: repetition 1
        - Consolidating: repetition 2 or 3
        - Mastered: repetition >= 4 and interval >= 14
        """
        if self.review_count == 0:
            return "New"
        if self.repetition <= 1:
            return "Learning"
        if self.repetition < 4:
            return "Consolidating"
        return "Mastered"

    def calculate_retention(self, days_elapsed: Optional[float] = None) -> float:
        """
        Calculates theoretical memory retention R(t) using Ebbinghaus exponential decay:
        R(t) = exp(-t / (S * 1.5)) where S is interval days.
        """
        if self.interval <= 0:
            return 0.5
        if days_elapsed is None:
            if not self.last_reviewed:
                return 0.5
            last_date = datetime.strptime(self.last_reviewed, "%Y-%m-%d")
            days_elapsed = max(0, (datetime.utcnow() - last_date).total_days())
        
        stability = max(1.0, float(self.interval))
        retention = math.exp(-days_elapsed / (stability * 1.5))
        return min(1.0, max(0.0, retention))

    def review(self, quality: int, review_date: Optional[datetime] = None) -> Dict[str, Any]:
        """
        Updates the card state based on a user recall quality grade:
        Quality Grade Scale:
        - 0: Complete blackout
        - 1: Incorrect response; card needs restart
        - 2: Incorrect response; but upon seeing correct answer it seemed easy
        - 3: Correct response with serious difficulty / hesitation
        - 4: Correct response after hesitation
        - 5: Perfect recall with zero hesitation

        Standard 4-button mappings:
        - Again = 1
        - Hard = 3
        - Good = 4
        - Easy = 5
        """
        quality = max(0, min(5, quality))
        now = review_date or datetime.utcnow()
        self.last_reviewed = now.strftime("%Y-%m-%d")
        self.review_count += 1

        # Calculate new Easiness Factor (EF')
        # EF' = EF + (0.1 - (5 - q) * (0.08 + (5 - q) * 0.02))
        q_diff = 5 - quality
        delta_ef = 0.1 - q_diff * (0.08 + q_diff * 0.02)
        new_ef = self.easiness_factor + delta_ef
        self.easiness_factor = max(SM2_MIN_EF, round(new_ef, 3))

        # Check success threshold (quality >= 3 is a pass)
        if quality < 3:
            # Failed recall -> Reset repetition counter, lapse recorded
            self.repetition = 0
            self.interval = 1
            self.lapses += 1
        else:
            # Successful recall -> Increment repetition and scale interval
            if self.repetition == 0:
                self.interval = SM2_INITIAL_INTERVAL_1
            elif self.repetition == 1:
                self.interval = SM2_INITIAL_INTERVAL_2
            else:
                self.interval = int(round(self.interval * self.easiness_factor))
            self.repetition += 1

        # Schedule next due date
        next_due = now + timedelta(days=self.interval)
        self.next_review_due = next_due.strftime("%Y-%m-%d")

        return {
            "card_id": self.card_id,
            "quality": quality,
            "new_repetition": self.repetition,
            "new_interval": self.interval,
            "new_ef": self.easiness_factor,
            "next_due": self.next_review_due,
            "mastery_tier": self.mastery_tier,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serializes card to dictionary."""
        return {
            "card_id": self.card_id,
            "front": self.front,
            "back": self.back,
            "hint": self.hint,
            "category": self.category,
            "repetition": self.repetition,
            "interval": self.interval,
            "easiness_factor": self.easiness_factor,
            "last_reviewed": self.last_reviewed,
            "next_review_due": self.next_review_due,
            "review_count": self.review_count,
            "lapses": self.lapses,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> SM2Card:
        """Instantiates card from dictionary."""
        return cls(
            card_id=str(data.get("card_id", "")),
            front=data.get("front", ""),
            back=data.get("back", ""),
            hint=data.get("hint", ""),
            category=data.get("category", "General"),
            repetition=int(data.get("repetition", 0)),
            interval=int(data.get("interval", 0)),
            easiness_factor=float(data.get("easiness_factor", SM2_DEFAULT_EF)),
            last_reviewed=data.get("last_reviewed"),
            next_review_due=data.get("next_review_due"),
            review_count=int(data.get("review_count", 0)),
            lapses=int(data.get("lapses", 0)),
        )


class SM2DeckScheduler:
    """Manages an entire deck of cards, filtering due cards and computing analytics."""

    def __init__(self, cards: Optional[List[SM2Card]] = None):
        self.cards: List[SM2Card] = cards or []

    def add_card(self, card: SM2Card) -> None:
        self.cards.append(card)

    def get_due_cards(self) -> List[SM2Card]:
        return [c for c in self.cards if c.is_due]

    def get_deck_analytics(self) -> Dict[str, Any]:
        """Computes summary statistics for the deck."""
        total = len(self.cards)
        if total == 0:
            return {
                "total_cards": 0,
                "due_today": 0,
                "mastered_count": 0,
                "learning_count": 0,
                "new_count": 0,
                "mastery_percentage": 0.0,
                "average_ef": SM2_DEFAULT_EF,
                "average_retention": 100.0,
            }

        due = sum(1 for c in self.cards if c.is_due)
        mastered = sum(1 for c in self.cards if c.mastery_tier == "Mastered")
        consolidating = sum(1 for c in self.cards if c.mastery_tier == "Consolidating")
        learning = sum(1 for c in self.cards if c.mastery_tier == "Learning")
        new = sum(1 for c in self.cards if c.mastery_tier == "New")

        avg_ef = sum(c.easiness_factor for c in self.cards) / total
        avg_retention = sum(c.calculate_retention() for c in self.cards) / total * 100

        return {
            "total_cards": total,
            "due_today": due,
            "mastered_count": mastered,
            "consolidating_count": consolidating,
            "learning_count": learning,
            "new_count": new,
            "mastery_percentage": round((mastered / total) * 100, 1),
            "average_ef": round(avg_ef, 2),
            "average_retention": round(avg_retention, 1),
        }

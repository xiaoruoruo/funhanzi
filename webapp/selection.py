"""
Module for character selection using a fluent API.

This module provides the Selection class which allows for flexible character selection
using a fluent (chainable) API. It supports various sources (lessons, FSRS cards) and
filtering operations.
"""

import random
from datetime import date, timedelta, datetime, timezone
from typing import List, Optional

from . import fsrs_logic
from . import words


class Selection:
    """
    A fluent API for selecting characters based on various criteria.
    
    Usage:
        s = Selection(conn)
        selected_chars = s.from_lesson_range("1-10") \
            .remove_recent_records(days=3, types=['read', 'write']) \
            .remove_score_greater("write", 5) \
            .random(10)
    """

    def __init__(self, conn):
        """
        Initialize the Selection with a database connection.

        Args:
            conn: Database connection object
        """
        self.conn = conn
        self.characters: List[str] = []
        self.fsrs_cards: List[dict] = []  # List of card data dictionaries
        self.is_fsrs_mode = False

    def from_lesson_range(self, lessons_str: str) -> "Selection":
        """
        Populate the selection with all unique characters from the specified lessons.

        Args:
            lessons_str (str): String representing lesson ranges, e.g. "1-5,8,10-12"

        Returns:
            Selection: Self for method chaining
        """
        self.fsrs_cards = []
        lesson_numbers = words.parse_lesson_ranges(lessons_str)
        char_pool = []
        for num in lesson_numbers:
            lesson_chars = words.get_lesson(num)
            if lesson_chars:
                char_pool.extend(list(lesson_chars))

        self.characters = list(set(char_pool))
        self.is_fsrs_mode = False
        return self

    def from_fsrs(self, card_type: str, due_only: bool = False) -> "Selection":
        """
        Populate the selection with FSRS cards of a specific type.
        If due_only=True, only include cards that are currently due for review.

        Args:
            card_type (str): Type of card ('read' or 'write')
            due_only (bool): If True, only include cards due for review

        Returns:
            Selection: Self for method chaining
        """
        self.characters = []
        cards_list = []

        today = datetime.now(timezone.utc)
        for (char, card_type_), card in fsrs_logic.cards.items():
            if card_type_ == card_type:
                retrievability = None
                if card_type == "read":
                    retrievability = fsrs_logic.read_scheduler.get_card_retrievability(
                        card, today
                    )
                elif card_type == "write":
                    retrievability = fsrs_logic.write_scheduler.get_card_retrievability(
                        card, today
                    )

                if retrievability is not None:
                    card_data = {
                        "char": char,
                        "retrievability": float(retrievability),
                        "card": card,
                    }

                    # Check if the card is due if due_only is True
                    if due_only:
                        # Card is due if the due date is today or earlier (based on due date, not retrievability)
                        if card.due and card.due <= today:
                            cards_list.append(card_data)
                    else:
                        cards_list.append(card_data)

        self.fsrs_cards = cards_list
        self.is_fsrs_mode = True
        return self

    def from_failed_records(
        self, record_type: str, cutoff_date: str, threshold: int
    ) -> "Selection":
        """
        Populate the selection with characters that have failed recent exams.
        A "failure" is defined as having the most recent score below the threshold.
        Uses SQL ROW_NUMBER() to get the most recent score for each character.

        Args:
            record_type (str): The record type to check ('read', 'write', etc.)
            cutoff_date (str): Date string in ISO format ('YYYY-MM-DD') to check records from
            threshold (int): Score threshold below which a record is considered a failure

        Returns:
            Selection: Self for method chaining
        """
        self.fsrs_cards = []
        cursor = self.conn.cursor()
        query = """
            WITH RankedRecords AS (
                SELECT
                    character,
                    score,
                    ROW_NUMBER() OVER (PARTITION BY character ORDER BY date DESC, id DESC) as rn
                FROM records
                WHERE date >= ? AND type = ?
            )
            SELECT character
            FROM RankedRecords
            WHERE rn = 1 AND score < ?
        """
        cursor.execute(query, (cutoff_date, record_type, threshold))

        failed_chars = [row["character"] for row in cursor.fetchall()]

        self.characters = failed_chars
        self.is_fsrs_mode = False
        return self

    def remove_any_recent_records(self, days: int) -> "Selection":
        """
        Filter out characters that have any record within the last days.

        Args:
            days (int): Number of recent days to check

        Returns:
            Selection: Self for method chaining
        """
        return self._remove_records(days)

    def remove_recent_records_by_type(self, days: int, types: List[str]) -> "Selection":
        """
        Filter out characters that have a record of the specified types within the last days.

        Args:
            days (int): Number of recent days to check
            types (list): List of record types to check, e.g. ['read', 'write']

        Returns:
            Selection: Self for method chaining
        """
        if not types:
            raise ValueError(
                "types list cannot be empty when calling remove_recent_records_by_type"
            )
        return self._remove_records(days, types)

    def _remove_records(
        self, days: int, types: Optional[List[str]] = None
    ) -> "Selection":
        """
        Private helper to filter out characters based on recent records.
        """
        if types is None:
            types = []

        # Get recent characters from records
        cursor = self.conn.cursor()
        cutoff_date = (date.today() - timedelta(days=days)).isoformat()

        if types:
            type_placeholders = ",".join(["?" for _ in types])
            query = f"SELECT DISTINCT character FROM records WHERE date >= ? AND type IN ({type_placeholders})"
            cursor.execute(query, [cutoff_date] + types)
        else:
            cursor.execute(
                "SELECT DISTINCT character FROM records WHERE date >= ?", (cutoff_date,)
            )

        recent_chars = {row["character"] for row in cursor.fetchall()}

        if self.is_fsrs_mode:
            # Filter the FSRS cards
            self.fsrs_cards = [
                card for card in self.fsrs_cards if card["char"] not in recent_chars
            ]
        else:
            # Filter the character list
            self.characters = [
                char for char in self.characters if char not in recent_chars
            ]

        return self

    def remove_score_greater(self, record_type: str, score: float) -> "Selection":
        """
        Filter out characters whose latest score for a given record type is greater than score.

        Args:
            record_type (str): The record type ('read', 'write', etc.)
            score (int/float): The score threshold

        Returns:
            Selection: Self for method chaining
        """
        scores = self._get_latest_scores(record_type)

        if self.is_fsrs_mode:
            # Filter FSRS cards based on their character's score
            self.fsrs_cards = [
                card for card in self.fsrs_cards if scores.get(card["char"], 0) <= score
            ]
        else:
            # Filter character list based on scores
            self.characters = [
                char for char in self.characters if scores.get(char, 0) <= score
            ]

        return self

    def lowest_retrievability(self) -> "Selection":
        """
        Sort the FSRS cards by their retrievability score in ascending order (lowest first).
        This method requires from_fsrs() to be called first.

        Returns:
            Selection: Self for method chaining
        """
        if not self.is_fsrs_mode:
            raise ValueError(
                "lowest_retrievability() can only be called after from_fsrs()"
            )

        # Sort the cards by retrievability score (ascending)
        self.fsrs_cards.sort(key=lambda x: x["retrievability"])
        return self

    def retrievability(self, min_val: float = -1, max_val: float = 1) -> "Selection":
        """
        Filter the FSRS cards by their retrievability score within the given range [min_val, max_val].
        This method requires from_fsrs() to be called first.

        Args:
            min_val (float): Minimum retrievability value (inclusive), default -1
            max_val (float): Maximum retrievability value (inclusive), default 1

        Returns:
            Selection: Self for method chaining
        """
        if not self.is_fsrs_mode:
            raise ValueError("retrievability() can only be called after from_fsrs()")

        # Filter the cards by retrievability score within the specified range
        self.fsrs_cards = [
            card
            for card in self.fsrs_cards
            if min_val <= card["retrievability"] <= max_val
        ]
        return self

    def random(self, n: int) -> List[str]:
        """
        Return a list of n random characters from the current selection.

        Args:
            n (int): Number of characters to select randomly

        Returns:
            list: List of randomly selected characters
        """
        if self.is_fsrs_mode:
            chars = [card["char"] for card in self.fsrs_cards]
        else:
            chars = self.characters

        if len(chars) <= n:
            return chars
        else:
            return random.sample(chars, k=n)

    def take(self, n: int) -> List[str]:
        """
        Return a list of the first n characters. This is typically used after a sorting method.

        Args:
            n (int): Number of characters to take

        Returns:
            list: List of first n characters
        """
        if self.is_fsrs_mode:
            chars = [card["char"] for card in self.fsrs_cards]
        else:
            chars = self.characters

        return chars[:n]

    def get_all(self) -> List[str]:
        """
        Return all characters in the current selection.

        Returns:
            list: List of all characters in selection
        """
        if self.is_fsrs_mode:
            return [card["char"] for card in self.fsrs_cards]
        else:
            return self.characters

    def _get_latest_scores(self, exam_type):
        """
        Get the latest scores for all characters of a specific exam type.

        Args:
            exam_type (str): The exam type to get scores for

        Returns:
            dict: Dictionary mapping character to latest score
        """
        scores = {}
        cursor = self.conn.cursor()
        cursor.execute(
            """
            SELECT character, score
            FROM records
            WHERE id IN (
                SELECT MAX(id)
                FROM records
                WHERE type = ?
                GROUP BY character
            )
        """,
            (exam_type,),
        )
        for row in cursor.fetchall():
            scores[row["character"]] = row["score"]
        return scores

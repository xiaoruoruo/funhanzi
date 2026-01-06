"""
Module for character selection using a fluent API.

This module provides the Selection class which allows for flexible character selection
using a fluent (chainable) API. It supports various sources (lessons, FSRS cards) and
filtering operations adapted to work with Django models.
"""

import random
import sys
from datetime import date, timedelta, datetime, timezone
from typing import List, Optional

from studies.models import Word, StudyLog, Lesson
from . import fsrs
from django.db.models import Window, F
from django.db.models.functions import RowNumber


class Selection:
    """
    A fluent API for selecting characters based on various criteria.
    
    Usage:
        s = Selection()  # Single-user system, no user needed
        selected_chars = s.from_learned_lessons() \
            .remove_recent_records(days=3, types=['read', 'write']) \
            .remove_score_greater("write", 5) \
            .random(10)
    """

    def __init__(self):
        """
        Initialize the Selection for a single-user system.
        """
        self.words: List[Word] = []
        self.study_logs: List[StudyLog] = []  # List of StudyLog objects
        self.is_fsrs_mode = False

    def from_learned_lessons(self, book_id: Optional[int] = None, lesson_id: Optional[int] = None, lesson_ids: Optional[List[int]] = None) -> "Selection":
        """
        Populate the selection with all unique characters from lessons marked as learned.
        Optionally filter by book_id, lesson_id, or a list of lesson_ids.

        Args:
            book_id (int, optional): ID of the book to filter by.
            lesson_id (int, optional): ID of the lesson to filter by.
            lesson_ids (List[int], optional): List of lesson IDs to filter by.

        Returns:
            Selection: Self for method chaining
        """
        self.study_logs = []
        
        lessons = Lesson.objects.filter(is_learned=True)
        
        if book_id:
            lessons = lessons.filter(book_id=book_id)
        if lesson_id:
            lessons = lessons.filter(id=lesson_id)
        if lesson_ids:
            lessons = lessons.filter(id__in=lesson_ids)
            
        # Extract characters from all learned lessons
        # Robustly handle comma-separated or continuous strings
        all_chars = set()
        for lesson in lessons:
            if lesson.characters:
                # Remove commas and whitespace, treat everything else as potential characters
                cleaned = lesson.characters.replace(',', '').replace(' ', '').replace('\t', '').replace('\n', '')
                all_chars.update(list(cleaned))
        
        # Query words matching these characters
        if all_chars:
            self.words = list(Word.objects.filter(hanzi__in=list(all_chars)))
        else:
            self.words = []
            
        self.is_fsrs_mode = False
        return self

    def from_fsrs(self, card_type: str, due_only: bool = False, book_id: Optional[int] = None, lesson_id: Optional[int] = None, lesson_ids: Optional[List[int]] = None) -> "Selection":
        """
        Populate the selection with FSRS cards of a specific type, filtered by learned lessons.
        If due_only=True, only include cards that are currently due for review.
        Optionally filter by book_id, lesson_id, or a list of lesson_ids.

        Args:
            card_type (str): Type of card ('read' or 'write')
            due_only (bool): If True, only include cards due for review
            book_id (int, optional): ID of the book to filter by.
            lesson_id (int, optional): ID of the lesson to filter by.
            lesson_ids (List[int], optional): List of lesson IDs to filter by.

        Returns:
            Selection: Self for method chaining
        """
        self.words = []
        study_logs_list = []

        # First, get the set of characters from learned lessons
        lessons = Lesson.objects.filter(is_learned=True)
        
        if book_id:
            lessons = lessons.filter(book_id=book_id)
        if lesson_id:
            lessons = lessons.filter(id=lesson_id)
        if lesson_ids:
            lessons = lessons.filter(id__in=lesson_ids)
            
        # Extract characters from all learned lessons
        all_chars = set()
        for lesson in lessons:
            if lesson.characters:
                # Remove commas and whitespace, treat everything else as potential characters
                cleaned = lesson.characters.replace(',', '').replace(' ', '').replace('\t', '').replace('\n', '')
                all_chars.update(list(cleaned))

        learned_chars = all_chars

        # Get all study logs for characters in learned lessons
        all_study_logs = StudyLog.objects.filter(word__hanzi__in=learned_chars).select_related('word')
        
        # Build FSRS cards from the filtered logs to calculate retrievability
        fsrs_cards = fsrs.build_cards_from_logs(list(all_study_logs))
        
        # Iterate through all fsrs_cards and filter by card_type
        today = datetime.now(timezone.utc)
        
        for (char, card_card_type), card in fsrs_cards.items():
            # Only consider cards of the specified type
            if card_card_type == card_type:
                # Check if the card is due if due_only is True
                is_due = False
                if due_only:
                    # Card is due if the due date is today or earlier
                    if hasattr(card, 'due') and card.due and card.due <= today:
                        is_due = True
                else:
                    is_due = True  # If not checking due only, include all cards of this type

                if is_due:
                    # Find a representative study log for this character to use in the data structure
                    representative_log = next(
                        (log for log in all_study_logs if log.word.hanzi == char), 
                        None
                    )
                    
                    if representative_log:
                        # Calculate retrievability for display purposes
                        retrievability = None
                        if card_type == "read":
                            retrievability = fsrs.read_scheduler.get_card_retrievability(
                                card, today
                            )
                        elif card_type == "write":
                            retrievability = fsrs.write_scheduler.get_card_retrievability(
                                card, today
                            )

                        if retrievability is not None:
                            study_log_data = {
                                "study_log": representative_log,
                                "retrievability": float(retrievability),
                                "word": representative_log.word,
                            }
                            study_logs_list.append(study_log_data)
                        # If retrievability is None, skip this card to match old behavior

        self.study_logs = study_logs_list
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
        self.study_logs = []
        
        # Get the most recent score for each word that is below the threshold
        # This requires finding the latest StudyLog for each word
        from django.db.models import Max
        
        # Filter study logs by cutoff date and type
        study_logs_queryset = StudyLog.objects.filter(
            study_date__gte=cutoff_date,
            type=record_type  # Filter by the specified record type
        ).values('word').annotate(latest_id=Max('id')).values_list('latest_id', flat=True)
        
        # Get the actual study logs
        latest_study_logs = StudyLog.objects.filter(id__in=study_logs_queryset).filter(score__lt=threshold)
        
        # Get the words for these logs
        failed_words = list(Word.objects.filter(study_logs__in=latest_study_logs).distinct())

        self.words = failed_words
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

        cutoff_date = (date.today() - timedelta(days=days)).isoformat()

        # Get recent words from study logs
        if types:
            # If specific types are provided, filter by those types
            recent_study_logs = StudyLog.objects.filter(
                study_date__gte=cutoff_date,
                type__in=types
            ).values_list('word__hanzi', flat=True)
        else:
            recent_study_logs = StudyLog.objects.filter(
                study_date__gte=cutoff_date
            ).values_list('word__hanzi', flat=True)

        recent_chars = set(recent_study_logs)

        if self.is_fsrs_mode:
            # Filter the FSRS records
            self.study_logs = [
                log for log in self.study_logs if log["word"].hanzi not in recent_chars
            ]
        else:
            # Filter the word list
            self.words = [
                word for word in self.words if word.hanzi not in recent_chars
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
            # Filter FSRS records based on their character's score
            self.study_logs = [
                log for log in self.study_logs if scores.get(log["word"].hanzi, 0) <= score
            ]
        else:
            # Filter word list based on scores
            self.words = [
                word for word in self.words if scores.get(word.hanzi, 0) <= score
            ]

        return self

    def lowest_retrievability(self) -> "Selection":
        """
        Sort the FSRS records by their retrievability score in ascending order (lowest first).
        This method requires from_fsrs() to be called first.

        Returns:
            Selection: Self for method chaining
        """
        if not self.is_fsrs_mode:
            raise ValueError(
                "lowest_retrievability() can only be called after from_fsrs()"
            )

        # Sort the records by retrievability score (ascending)
        self.study_logs.sort(key=lambda x: x["retrievability"])
        return self

    def retrievability(self, min_val: float = -1, max_val: float = 1) -> "Selection":
        """
        Filter the FSRS records by their retrievability score within the given range [min_val, max_val].
        This method requires from_fsrs() to be called first.

        Args:
            min_val (float): Minimum retrievability value (inclusive), default -1
            max_val (float): Maximum retrievability value (inclusive), default 1

        Returns:
            Selection: Self for method chaining
        """
        if not self.is_fsrs_mode:
            raise ValueError("retrievability() can only be called after from_fsrs()")

        # Filter the records by retrievability score within the specified range
        self.study_logs = [
            log
            for log in self.study_logs
            if min_val <= log["retrievability"] <= max_val
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
            chars = [log["word"].hanzi for log in self.study_logs]
        else:
            chars = [word.hanzi for word in self.words]

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
            chars = [log["word"].hanzi for log in self.study_logs]
        else:
            chars = [word.hanzi for word in self.words]

        return chars[:n]

    def get_all(self) -> List[str]:
        """
        Return all characters in the current selection.

        Returns:
            list: List of all characters in selection
        """
        if self.is_fsrs_mode:
            return [log["word"].hanzi for log in self.study_logs]
        else:
            return [word.hanzi for word in self.words]

    def get_hard_mode_words(self, record_type: str) -> List[Word]:
        """
        Identify words that are in "Hard Mode" (2 consecutive failures with score <= 1).
        
        Args:
            record_type (str): The record type to check ('read' or 'write')
            
        Returns:
            List[Word]: List of Word objects in hard mode
        """
        # We need to look at the last 2 records for each word
        # Using a subquery approach to get the recent logs efficiently
        
        # 1. Fetch all relevant logs for the type, ordered by date desc
        logs = StudyLog.objects.filter(type=record_type).order_by('word_id', '-study_date', '-id')
        
        # In memory processing (simpler than complex window functions in SQLite/Django)
        # Assuming database size is manageable. If large, need raw SQL or window functions.
        # Given personal use app, in-memory is fine.
        
        hard_mode_word_ids = set()
        from collections import defaultdict
        
        # We only need the last 2 records per word
        # Optimization: distinct words first, then fetch last 2
        # Or just iterate since we're ordering by word
        
        current_word_id = None
        consecutive_fails = 0
        skip_current_word = False
        
        # Iterate through logs. Logs are ordered by word, then date desc.
        for log in logs:
            if log.word_id != current_word_id:
                # New word
                current_word_id = log.word_id
                consecutive_fails = 0
                skip_current_word = False
                
            if skip_current_word:
                continue
                
            # Check if this log is a failure
            if log.score is not None and log.score <= 1:
                consecutive_fails += 1
            else:
                # Sequence broken by a pass (or score > 1)
                # Since we look at newest first, a pass means the current streak is broken/non-existent.
                skip_current_word = True
                continue
                
            if consecutive_fails >= 2:
                hard_mode_word_ids.add(current_word_id)
                skip_current_word = True # Found status, stop checking this word
                 
        return list(Word.objects.filter(id__in=hard_mode_word_ids))

    def remove_hard_mode_words(self, record_type: str) -> "Selection":
        """
        Filter out words that are in Hard Mode for the specified record type.
        
        Args:
            record_type (str): 'read' or 'write'
            
        Returns:
            Selection: Self for method chaining
        """
        hard_mode_words = self.get_hard_mode_words(record_type)
        hard_mode_ids = {w.id for w in hard_mode_words}
        
        if self.is_fsrs_mode:
            self.study_logs = [
                log for log in self.study_logs 
                if log["word"].id not in hard_mode_ids
            ]
        else:
            self.words = [
                word for word in self.words 
                if word.id not in hard_mode_ids
            ]
            
        return self

    def from_hard_mode(self, record_type: str) -> "Selection":
        """
        Populate selection with words currently in Hard Mode.
        
        Args:
            record_type (str): 'read' or 'write'
            
        Returns:
            Selection: Self for method chaining
        """
        self.words = self.get_hard_mode_words(record_type)
        self.study_logs = []
        self.is_fsrs_mode = False
        return self

    def _get_latest_scores(self, exam_type):
        """
        Get the latest scores for all characters of a specific exam type.

        Args:
            exam_type (str): The exam type to get scores for

        Returns:
            dict: Dictionary mapping character to latest score
        """
        scores = {}
        
        # Get the latest score for each word
        from django.db.models import Max
        
        # Get the IDs of the latest study logs for each word
        latest_logs = StudyLog.objects.filter(
            type=exam_type
        ).values('word').annotate(
            latest_id=Max('id')
        ).values_list('latest_id', flat=True)
        
        # Get the actual latest study logs
        latest_study_logs = StudyLog.objects.filter(id__in=latest_logs)
        
        for log in latest_study_logs:
            scores[log.word.hanzi] = log.score
            
        return scores
"""
Module for generating words for exams based on character lists and FSRS scores.
"""

from typing import List
import logging

from . import fsrs_logic
from .words_db import get_words_for_char


log = logging.getLogger(__name__)


def generate_exam_words(conn, characters: List[str]) -> List[str]:
    """
    Generate a list of words for a write exam based on the given characters,
    using words from the database. The characters from the generated words must only include characters provided in the input argument.

    Args:
        conn: Database connection.
        characters: List of Chinese characters to generate words for.
    Returns:
        List of words that contain the given characters.
    """
    remaining_chars = set(characters)
    final_word_list = []
    for char in characters:
        if char not in remaining_chars:
            continue

        words_with_scores = get_words_for_char(conn, char)
        best_word = char

        # Score for a single character is notionally 0, any multi-char word is better
        best_word_score = -1 
        # How many of the *remaining* characters are covered
        best_word_covered_count = 1

        # Find the best word that can be formed from the remaining characters
        for word, score in words_with_scores:
            word_chars = set(word)
            if word_chars.issubset(remaining_chars):
                # Prioritize words that cover more characters, then by score
                if len(word_chars) > best_word_covered_count:
                    best_word_covered_count = len(word_chars)
                    best_word = word
                    best_word_score = score
                elif len(word_chars) == best_word_covered_count:
                    if score > best_word_score:
                        best_word = word
                        best_word_score = score

        final_word_list.append(best_word)
        remaining_chars -= set(best_word)
    return final_word_list


def generate_words_max_score(conn, characters: List[str]) -> List[str]:
    """
    Generate words that maximize a score based on FSRS retrievability.
    
    For each character, use words_db to get a list of candidate words that contain that character.
    For each character in all the candidate words, obtain the fsrs retrievability score (type "read").
    Compute the score of the candidate as: SUM(character_score - 80 for each character's score). Here 80 is a threshold where a character is considered good enough.
    Select the candidate word with the max score.
    Continue with the next character to generate. It's not necessary to prevent having overlap characters in words.
    
    Args:
        conn: Database connection.
        characters: List of Chinese characters to generate words for.
    Returns:
        List of words with the highest calculated scores.
    """
    from datetime import datetime, timezone
    
    # Don't use remaining_chars since overlapping characters in words is allowed
    final_word_list = []
    
    for char in characters:
        # Get candidate words for this character
        candidate_words = get_words_for_char(conn, char)
        
        best_word = char
        best_score = -float('inf')  # Initialize to negative infinity
        
        for word, word_db_score in candidate_words:
            # Calculate the total score for this word based on character scores
            total_score = 0
            word_chars = set(word)
            
            for word_char in word_chars:
                # Get FSRS retrievability score for the character (type "read")
                retrievability = None
                if (word_char, 'read') in fsrs_logic.cards:
                    card = fsrs_logic.cards[(word_char, 'read')]
                    today = datetime.now(timezone.utc)
                    retrievability = fsrs_logic.read_scheduler.get_card_retrievability(card, today)
                
                # Use 0 as default if no retrievability score exists
                char_score = retrievability if retrievability is not None else 0
                # Add (character_score - 80) to the total score
                total_score += (char_score - 80)
            
            # Update best word if this one has higher score
            if total_score > best_score:
                best_score = total_score
                best_word = word
        
        final_word_list.append(best_word)
    
    return final_word_list
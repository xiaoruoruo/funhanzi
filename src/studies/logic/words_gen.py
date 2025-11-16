"""
Module for generating words for study sheets based on character lists and FSRS scores,
replicating the logic from the legacy webapp.
"""
from typing import List
from datetime import datetime, timezone

from studies.models import WordEntry, StudyLog
from . import fsrs

def generate_words_max_score(characters: List[str]) -> List[str]:
    """
    Generate words that are good enough based on FSRS retrievability.
    For each character, use words_db to get a list of candidate words that contain that character.
    For each character in all the candidate words, obtain the fsrs retrievability score (type "read").
    Compute the score of the candidate as: COUNT(character_score > 80%) - COUNT(character_score < 80%). Here 80 is a
 threshold where a character is considered good enough.
    Select the candidate words that is good enough.
    Continue with the next character to generate. It's not necessary to prevent having overlap characters in words.

    Args:
        characters: List of Chinese characters to generate words for.
    Returns:
        List of words. Each character may have multiple words.
    """
    # Build FSRS cards once to avoid repeated database queries
    all_logs = list(StudyLog.objects.filter(type__in=['read', 'write']).select_related('word'))
    fsrs_cards = fsrs.build_cards_from_logs(all_logs)
    
    final_word_list = []

    for char in characters:
        # Get candidate words for this character with a score >= 0.8
        candidate_words = WordEntry.objects.filter(word__contains=char, score__gte=0.8)

        for entry in candidate_words:
            word = entry.word
            total_score = 0
            
            for word_char in set(word):
                # Get FSRS retrievability score for the character (type "read")
                retrievability = 0.0  # Default to 0 if no card or score exists
                card_key = (word_char, "read")
                
                if card_key in fsrs_cards:
                    card = fsrs_cards[card_key]
                    today = datetime.now(timezone.utc)
                    r_val = fsrs.read_scheduler.get_card_retrievability(card, today)
                    if r_val is not None:
                        retrievability = float(r_val)

                if retrievability > 0.8:
                    total_score += 1
                else:
                    total_score -= 4

            if total_score >= 2:
                final_word_list.append(word)

    return final_word_list

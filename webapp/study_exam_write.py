from typing import List
import random
from . import words_db

def generate_content(conn, characters: List[str], lesson_chars: List[str]) -> List[str]:
    """
    Generate a list of words for a write exam based on the given characters,
    using words from the database.
    
    Args:
        conn: Database connection.
        characters: List of Chinese characters to generate words for.
        lesson_chars: List of all characters available in the lessons.
        
    Returns:
        List of words that contain the given characters.
    """
    remaining_chars = set(characters)
    final_word_list = []
    lesson_chars_set = set(lesson_chars)
    
    char_list = list(remaining_chars)
    random.shuffle(char_list)

    for char in char_list:
        if char not in remaining_chars:
            continue

        words_with_scores = words_db.get_words_for_char(conn, char)
        
        best_word = char
        # Score for a single character is notionally 0, any multi-char word is better
        best_word_score = -1 
        # How many of the *remaining* characters are covered
        best_word_covered_count = 1

        # Find the best word that can be formed from the remaining characters
        for word, score in words_with_scores:
            word_chars = set(word)
            if not word_chars.issubset(lesson_chars_set):
                continue

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

    random.shuffle(final_word_list)
    return final_word_list

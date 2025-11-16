"""
Module for generating character/word study content as JSON-serializable data structures.
"""
import random
from collections import defaultdict
from dataclasses import dataclass
from typing import List
from . import ai
from studies.models import WordEntry


from . import words_gen


@dataclass
class CharWordEntry:
    char: str
    pinyin: str
    word: str


def _get_pinyin_for_words(words: List[str]) -> dict:
    """
    Uses the AI model to get pinyin for a list of words.
    """
    if not words:
        return {}

    model = ai.get_gemini_model()
    
    # Create a single prompt for all words to minimize API calls
    prompt = "请为以下词语提供拼音，每个词语一行，格式为：词语, pīn yīn\n"
    prompt += "\n".join(words)

    response = ai.generate_content(model, prompt)
    pinyin_map = {}
    if response and response.text:
        try:
            lines = response.text.strip().split("\n")
            for line in lines:
                parts = line.split(",", 1) # Split only on the first comma
                if len(parts) == 2:
                    word = parts[0].strip()
                    pinyin = parts[1].strip()
                    pinyin_map[word] = pinyin
        except Exception as e:
            print(f"Error parsing AI response for pinyin: {e}")
            
    return pinyin_map


def generate_content(characters: List[str]) -> List[dict]:
    """
    Generate character-word entries with pinyin and words for the given characters,
    replicating the legacy app's logic using the Django ORM.

    Args:
        characters: List of Chinese characters to generate content for

    Returns:
        List of dictionaries, where each dictionary represents a character study entry.
    """
    if not characters:
        return []

    # 1. Find the best example word for each character using the correct algorithm
    all_generated_words = words_gen.generate_words_max_score(characters)

    # Build a map from character to a list of words containing it.
    char_to_words_map = defaultdict(list)
    for word in all_generated_words:
        for char in characters:
            if char in word:
                char_to_words_map[char].append(word)

    # Select one word randomly for each character.
    generated_words = []
    for char in characters:
        words_for_char = char_to_words_map.get(char)
        if words_for_char:
            generated_words.append(random.choice(words_for_char))
        else:
            generated_words.append("N/A")  # Fallback if no word is found

    # 2. Get pinyin for all unique words
    unique_words = sorted(list(set(w for w in generated_words if w != "N/A")))
    pinyin_map = _get_pinyin_for_words(unique_words)

    # 3. Assemble the final data structure
    characters_data = []
    for i, char in enumerate(characters):
        word = generated_words[i]
        pinyin = pinyin_map.get(word, "N/A")
        entry = CharWordEntry(char=char, pinyin=pinyin, word=word)
        characters_data.append({
            'char': entry.char,
            'pinyin': entry.pinyin,
            'word': entry.word
        })

    return characters_data

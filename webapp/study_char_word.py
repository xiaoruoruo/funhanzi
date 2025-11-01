from dataclasses import dataclass
from typing import List
from . import ai
from . import words_gen
from . import db


@dataclass
class CharWordEntry:
    char: str
    pinyin: str
    word: str


def generate_content(characters: List[str]) -> List[CharWordEntry]:
    """
    Generate character-word entries with pinyin and words for the given characters.

    Args:
        characters: List of Chinese characters to generate content for

    Returns:
        List of CharWordEntry objects containing character, pinyin, and word
    """
    conn = db.get_db_connection()
    generated_words = words_gen.generate_words_max_score(conn, characters)
    conn.close()

    model = ai.get_gemini_model()

    # Create a single prompt for all words
    prompt = "请为以下词语提供拼音，每个词语一行，格式为：词语, pīn yīn\n"
    for word in generated_words:
        prompt += f"{word}\n"

    response = ai.generate_content(model, prompt)
    pinyin_map = {}
    if response:
        try:
            lines = response.text.strip().split("\n")
            for line in lines:
                parts = line.split(",")
                if len(parts) == 2:
                    word = parts[0].strip()
                    pinyin = parts[1].strip()
                    pinyin_map[word] = pinyin
        except Exception as e:
            print(f"Error parsing Gemini response: {e}")

    characters_data = []
    for i, char in enumerate(characters):
        word = generated_words[i] if i < len(generated_words) else char
        pinyin = pinyin_map.get(word, "N/A")
        characters_data.append(CharWordEntry(char=char, pinyin=pinyin, word=word))

    return characters_data

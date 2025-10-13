from dataclasses import dataclass
from typing import List
import random
from . import ai


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
    # Generate pinyin and words using Gemini
    model = ai.get_gemini_model()
    
    characters_data = []
    for char in characters:
        prompt = f"请为“{char}”这个字，提供它的拼音，以及一个最常见的、由两个字组成的词语。请用这个格式返回：拼音，词语。例如：pīn yīn, 词语"
        response = ai.generate_content(model, prompt)
        try:
            if response is not None:
                pinyin, word = response.text.strip().split(",", 1)
                characters_data.append(CharWordEntry(
                    char=char,
                    pinyin=pinyin.strip(),
                    word=word.strip()
                ))
            else:
                characters_data.append(CharWordEntry(
                    char=char,
                    pinyin="N/A",
                    word="N/A"
                ))
        except ValueError:
            characters_data.append(CharWordEntry(
                char=char,
                pinyin="N/A",
                word="N/A"
            ))

    return characters_data
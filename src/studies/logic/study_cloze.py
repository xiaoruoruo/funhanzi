from dataclasses import dataclass
from typing import List
import random
import logging

from . import words_gen, sentence_gen


@dataclass
class ClozeEntry:
    word: str
    cloze_sentence: str

    def to_dict(self):
        return {"word": self.word, "cloze_sentence": self.cloze_sentence}


def generate_content(characters: List[str]) -> List[dict]:
    """
    Generate cloze test entries with words and sentences containing blanks.

    Args:
        characters: List of Chinese characters to generate content for.

    Returns:
        List of dictionaries representing ClozeEntry objects.
    """
    logging.info(f"Generating cloze using: {characters}")
    words = words_gen.generate_words_max_score(characters)
    random.shuffle(words)
    words = words[:8]
    logging.info(f"Selected words for cloze: {words}")

    best_sentences = sentence_gen.generate_best_sentences(words)

    pairs = []
    for word in words:
        if word in best_sentences:
            cloze_sentence = best_sentences[word].replace(word, "（ ）", 1)
            entry = ClozeEntry(word=word, cloze_sentence=cloze_sentence)
            pairs.append(entry.to_dict())
        else:
            # If no sentences were generated for this word, create a fallback entry
            entry = ClozeEntry(word=word, cloze_sentence=f"无法为 {word} 生成句子")
            pairs.append(entry.to_dict())

    return pairs

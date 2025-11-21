from dataclasses import dataclass, field
from typing import List
import random
import logging

from google import genai
from pydantic import BaseModel

from . import words_gen


class TranslationPair(BaseModel):
    chinese_word: str
    english_translation: str


class TranslationsResponse(BaseModel):
    translations: List[TranslationPair]


@dataclass
class ChEnMatchingEntry:
    chinese_word: str
    correct_translation: str
    options: List[str] = field(default_factory=list)

    def __post_init__(self):
        # Add the correct translation to the options and shuffle them
        if self.correct_translation not in self.options:
            self.options.append(self.correct_translation)
        random.shuffle(self.options)

    def to_dict(self):
        return {
            "chinese_word": self.chinese_word,
            "correct_translation": self.correct_translation,
            "options": self.options,
        }


def generate_content(characters: List[str]) -> List[dict]:
    """
    Generate Chinese-English matching entries.
    """
    words = words_gen.generate_words_max_score(characters)
    random.shuffle(words)
    words = words[:8]

    words_str = ", ".join(words)

    client = genai.Client()
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"Translate the following Chinese words to English: '{words_str}'.",
            config={
                "response_mime_type": "application/json",
                "response_schema": TranslationsResponse,
            },
        )

        response_data: TranslationsResponse = response.parsed

        # Create a dictionary to quickly look up translations
        translations: dict[str, str] = {
            item.chinese_word: item.english_translation
            for item in response_data.translations
        }

        all_english_translations = list(translations.values())

        # If we don't have enough translations to create distractors, return an error
        if len(all_english_translations) < 4:
            logging.error("Not enough translations to generate a matching study.")
            return [
                ChEnMatchingEntry(
                    chinese_word="错误",
                    correct_translation="Error",
                    options=["Not enough translations to generate a study."]
                ).to_dict()
            ]

        entries = []
        for word in words:
            if word in translations:
                correct_translation = translations[word]

                # Select three incorrect options from the other translations
                distractors = random.sample(
                    [t for t in all_english_translations if t != correct_translation], 3
                )

                entry = ChEnMatchingEntry(
                    chinese_word=word,
                    correct_translation=correct_translation,
                    options=distractors,
                )
                entries.append(entry.to_dict())

        return entries

    except Exception as e:
        logging.error(f"Could not generate translations: {e}")
        return [
            ChEnMatchingEntry(
                chinese_word="错误",
                correct_translation="Error",
                options=["Could not generate translations."]
            ).to_dict()
        ]

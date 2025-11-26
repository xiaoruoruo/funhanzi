from dataclasses import dataclass, field
from typing import List
import random
import logging

from google import genai
from pydantic import BaseModel

from . import words_gen, sentence_gen


class TranslationPair(BaseModel):
    chinese_word: str
    english_translation: str


class TranslationsResponse(BaseModel):
    translations: List[TranslationPair]


class SentenceMatchingItem(BaseModel):
    original_chinese: str
    english_translation: str
    wrong_options: List[str]


class SentenceMatchingResponse(BaseModel):
    items: List[SentenceMatchingItem]


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
    entries = []

    # 1. Generate Word Matching Questions
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

    except Exception as e:
        logging.error(f"Could not generate translations: {e}")
        return [
            ChEnMatchingEntry(
                chinese_word="错误",
                correct_translation="Error",
                options=["Could not generate translations."]
            ).to_dict()
        ]

    # 2. Generate Sentence Matching Questions
    # Select 2 words to generate sentences for
    sentence_words = words[:2]
    best_sentences = sentence_gen.generate_best_sentences(sentence_words)

    if best_sentences:
        sentences_to_process = list(best_sentences.values())
        sentences_str = "\n".join(sentences_to_process)
        
        try:
            response_sentences = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=f"For each of the following Chinese sentences, provide the English translation and 3 incorrect Chinese sentences created by swapping word order. The incorrect sentences must use the same characters but have different meaning or be grammatically incorrect.\nSentences:\n{sentences_str}",
                config={
                    "response_mime_type": "application/json",
                    "response_schema": SentenceMatchingResponse,
                },
            )
            
            sentence_data: SentenceMatchingResponse = response_sentences.parsed
            
            for item in sentence_data.items:
                # For sentence matching:
                # Question (chinese_word field) = English Sentence
                # Answer (correct_translation field) = Chinese Sentence
                # Options = [Correct Chinese, Wrong1, Wrong2, Wrong3]
                
                entry = ChEnMatchingEntry(
                    chinese_word=item.english_translation,
                    correct_translation=item.original_chinese,
                    options=item.wrong_options
                )
                entries.append(entry.to_dict())
                
        except Exception as e:
            logging.error(f"Could not generate sentence matching questions: {e}")
            # We don't fail the whole study if sentence generation fails, just skip these questions.

    return entries

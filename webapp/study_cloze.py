from dataclasses import dataclass
from typing import List
import random
import logging
from datetime import datetime, timezone

from . import words_gen, fsrs_logic

from google import genai
from pydantic import BaseModel

class SentencePair(BaseModel):
    word: str
    sentence: str

@dataclass
class ClozeEntry:
    word: str
    cloze_sentence: str


def calculate_sentence_score(sentence: str) -> float:
    """
    Calculate the score for a sentence based on character FSRS retrievability scores.
    For each character in the sentence, get the FSRS retrievability score (type "read").
    Calculate the score as: SUM(character_score - 90% for each character's score).
    Here 90% is a threshold where a character is considered good enough.
    """
    total_score = 0
    sentence_chars = set(sentence)
    
    for char in sentence_chars:
        retrievability = None
        if (char, 'read') in fsrs_logic.cards:
            card = fsrs_logic.cards[(char, 'read')]
            today = datetime.now(timezone.utc)
            retrievability = fsrs_logic.read_scheduler.get_card_retrievability(card, today)
        
        char_score = retrievability if retrievability is not None else 0
        total_score += (char_score - 0.9)
    
    return total_score


def generate_content(conn, characters: List[str]) -> List[ClozeEntry]:
    """
    Generate cloze test entries with words and sentences containing blanks.
    
    Args:
        conn: Database connection.
        characters: List of Chinese characters to generate content for.
        
    Returns:
        List of ClozeEntry objects containing word and cloze sentence
    """
    logging.info(f"Generating cloze using: {characters}")
    words = words_gen.generate_words_max_score(conn, characters)
    random.shuffle(words)
    words = words[:5]
    logging.info(f"Selected words for cloze: {words}")

    words_str = ", ".join(words)

    client = genai.Client()
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"""我在给2年级的孩子准备中文生字复习，请根据以下词语：'{words_str}'，为每个词语各生成至少5个包含该词语的简单句子。""",
            config={
                "response_mime_type": "application/json",
                "response_schema": list[SentencePair],
            },
        )
            
        print(response.text)
        pairs_data: list[SentencePair] = response.parsed

        # Group sentences by word and select the one with the highest score for each word
        word_to_sentences = {}
        for item in pairs_data:
            word = item.word
            sentence = item.sentence
            if word not in word_to_sentences:
                word_to_sentences[word] = []
            word_to_sentences[word].append(sentence)

        pairs = []
        for word in words:
            if word in word_to_sentences:
                sentences = word_to_sentences[word]
                # Calculate score for each sentence and select the one with the highest score
                best_sentence = sentences[0]
                best_score = calculate_sentence_score(sentences[0])
                
                for sentence in sentences[1:]:
                    score = calculate_sentence_score(sentence)
                    if score > best_score:
                        best_score = score
                        best_sentence = sentence
                
                cloze_sentence = best_sentence.replace(word, '（ ）', 1)
                pairs.append(ClozeEntry(
                    word=word,
                    cloze_sentence=cloze_sentence
                ))
            else:
                # If no sentences were generated for this word, create a fallback entry
                pairs.append(ClozeEntry(
                    word=word,
                    cloze_sentence=f"无法为 {word} 生成句子"
                ))
    except Exception as e:
        print(f"无法生成句子: {e}")
        pairs = [ClozeEntry(word="错误", cloze_sentence="无法生成句子")] * 5

    return pairs
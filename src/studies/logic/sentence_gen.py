from typing import List, Dict, Optional
import logging
from datetime import datetime, timezone
from google import genai
from pydantic import BaseModel

from . import fsrs
from studies.models import StudyLog

class SentencePair(BaseModel):
    word: str
    sentence: str

def calculate_sentence_score(sentence: str, fsrs_cards: dict) -> float:
    """
    Calculate the score for a sentence based on character FSRS retrievability scores.
    For each character in the sentence, get the FSRS retrievability score (type "read").
    Calculate the score as: COUNTIF(character_score > 90%) for each character's score.
    Here 90% is a threshold where a character is considered good enough.
    """
    total_score = 0
    sentence_chars = set(sentence)
    today = datetime.now(timezone.utc)

    for char in sentence_chars:
        if char in ['，','。', '？', '！', '：', '“', '”']:
            continue
        retrievability = None
        if (char, "read") in fsrs_cards:
            card = fsrs_cards[(char, "read")]
            retrievability = fsrs.read_scheduler.get_card_retrievability(
                card, today
            )

        char_score = retrievability if retrievability is not None else 0
        if char_score > 0.9:
            total_score += 1
        else:
            total_score -= 4

    return total_score

def generate_best_sentences(words: List[str], min_score: int = 4) -> Dict[str, str]:
    """
    Generate sentences for the given words using Gemini, and select the best one
    based on the user's FSRS scores.
    
    Returns:
        A dictionary mapping word -> best_sentence.
        Only includes words for which a sentence with score >= min_score was found.
    """
    if not words:
        return {}

    words_str = ", ".join(words)

    # Build FSRS cards once to pass to the scoring function
    all_logs = list(StudyLog.objects.filter(type__in=['read', 'write']).select_related('word'))
    fsrs_cards = fsrs.build_cards_from_logs(all_logs)

    client = genai.Client()
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"""我在给2年级的孩子准备中文生字复习，请根据以下词语：'{words_str}'，为每个词语各生成至少8个包含该词语的简单句子。""",
            config={
                "response_mime_type": "application/json",
                "response_schema": list[SentencePair],
            },
        )

        pairs_data: list[SentencePair] = response.parsed

        # Group sentences by word
        word_to_sentences = {}
        for item in pairs_data:
            word = item.word
            sentence = item.sentence
            if word not in word_to_sentences:
                word_to_sentences[word] = []
            word_to_sentences[word].append(sentence)

        best_sentences = {}
        for word in words:
            if word in word_to_sentences:
                sentences = word_to_sentences[word]
                # Calculate score for each sentence and select the one with the highest score
                best_sentence = sentences[0]
                best_score = calculate_sentence_score(sentences[0], fsrs_cards)

                for sentence in sentences[1:]:
                    score = calculate_sentence_score(sentence, fsrs_cards)
                    if score > best_score:
                        best_score = score
                        best_sentence = sentence

                # Only accept the sentence if it is good enough.
                if best_score >= min_score:
                    best_sentences[word] = best_sentence
                else:
                    logging.info(f"Best sentence for {word} had score {best_score} < {min_score}: {best_sentence}")

        return best_sentences

    except Exception as e:
        logging.error(f"无法生成句子: {e}")
        return {}

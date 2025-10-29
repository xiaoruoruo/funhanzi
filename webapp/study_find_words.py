from dataclasses import dataclass
from typing import List
import random
import sys
from google import genai
from pydantic import BaseModel

from . import words_db
from . import db
from . import selection

class SentencesResponse(BaseModel):
    sentences: List[str]

@dataclass
class FindWordsContent:
    words: List[str]
    sentence: str


def get_learned_chars(conn):
    """Fetches all unique characters with FSRS retrievability > 0.9."""
    return set(selection.Selection(conn).from_fsrs('read', due_only=False).retrievability(min_val=0.9).get_all())


def generate_content(characters: List[str]) -> FindWordsContent:
    """
    Generate find-words puzzle content with words and a sentence containing those words.
    
    Args:
        characters: List of Chinese characters to generate content for
        
    Returns:
        FindWordsContent object containing words and sentence
    """
    # Get words from the database
    words_with_scores = []
    with words_db.get_conn() as conn:
        for char in characters:
            words_with_scores.extend(words_db.get_words_for_char(conn, char))

    conn = db.get_db_connection()
    learned_chars = get_learned_chars(conn)
    conn.close()
    allowed_chars = set(characters).union(learned_chars)

    # Filter for 2-character words, unique, and select 8 with score >= 0.8
    two_char_words_filtered = []
    seen_words = set()
    for w, score in words_with_scores:
        if len(w) == 2 and score >= 0.8 and w not in seen_words:
            # Check if any character in the word is from the 'characters' list
            # and all characters in the word are either 'characters' or 'learned_chars'
            if any(c in characters for c in w) and all(c in allowed_chars for c in w):
                two_char_words_filtered.append(w)
                seen_words.add(w)

    random.shuffle(two_char_words_filtered)
    selected_words = two_char_words_filtered[:8]

    print(f"汉字: {characters} 词语: {selected_words}")

    if not selected_words:
        print("Error: Could not find enough words to generate the puzzle.", file=sys.stderr)
        # Fallback values
        return FindWordsContent(
            words=["错误"] * 8,
            sentence="无法生成句子"
        )

    allowed_chars_set = set(characters).union(learned_chars).union(set("，。"))
    characters_set = set(characters)
    
    words_str = ", ".join(selected_words)

    client = genai.Client()
    best_sentence = "无法生成句子"
    best_score = -float('inf')

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"""
你是一个小学语文老师。请根据以下词语：
- 词语列表: '{words_str}'

请生成5个包含部分词语的句子。
每个句子必须满足以下条件：
   - 长度在10到18个汉字。
""",
            config={
                "response_mime_type": "application/json",
                "response_schema": SentencesResponse,
            },
        )
        
        response_data: SentencesResponse = response.parsed
        candidate_sentences = response_data.sentences

        for sentence in candidate_sentences:
            if len(sentence) > 18:
                continue

            score = 0
            # Rule 1: +1 for each character in `characters`
            for char in sentence:
                if char in characters_set:
                    score += 1
            
            # Rule 2: +4 for each word in `selected_words`
            for word in selected_words:
                if word in sentence:
                    score += 4
            
            # Rule 3: -4 for each character not in `allowed_chars`
            for char in sentence:
                if char not in allowed_chars_set:
                    score -= 4
            
            print(f"{score} points: {sentence}")
            if score > best_score:
                best_score = score
                best_sentence = sentence

    except Exception as e:
        print(f"Could not generate or parse sentences: {e}", file=sys.stderr)
        # Fallback is handled after this block

    if best_score < 6:
        raise Exception("No great sentence generated")

    return FindWordsContent(
        words=selected_words,
        sentence=best_sentence
    )
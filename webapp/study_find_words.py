from dataclasses import dataclass
from typing import List, Tuple
import random
import sys
import os
import sqlite3
from . import ai
from . import words_db
import json


@dataclass
class FindWordsContent:
    words: List[str]
    sentence: str


def get_learned_chars(conn):
    """Fetches all unique characters that have a 'read' or 'write' record."""
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT DISTINCT character FROM records WHERE type IN ('read', 'write')")
        return {row['character'] for row in cursor.fetchall()}
    except sqlite3.OperationalError:
        return set()


def generate_content(characters: List[str]) -> FindWordsContent:
    """
    Generate find-words puzzle content with words and a sentence containing those words.
    
    Args:
        characters: List of Chinese characters to generate content for
        
    Returns:
        FindWordsContent object containing words and sentence
    """
    # Add cli to the path to import words_db
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

    model = ai.get_gemini_model()

    # Get words from the database
    words = []
    with words_db.get_conn() as conn:
        for char in characters:
            words.extend(words_db.get_words_for_char(conn, char))

    # Import here to avoid circular dependencies
    from . import db
    conn = db.get_db_connection()
    learned_chars = get_learned_chars(conn)
    conn.close()
    allowed_chars = set(characters).union(learned_chars)

    # Filter for 2-character words, unique, and select 8
    two_char_words = []
    for w in list(set(w for w in words if len(w) == 2)):
        if any(c in characters for c in w) and all(c in allowed_chars for c in w):
            two_char_words.append(w)

    random.shuffle(two_char_words)
    selected_words = two_char_words[:8]

    if not selected_words:
        print("Error: Could not find enough words to generate the puzzle.", file=sys.stderr)
        # Fallback values
        return FindWordsContent(
            words=["错误"] * 8,
            sentence="无法生成句子"
        )

    allowed_chars = set(characters).union(learned_chars).union(set("，。"))
    characters_str = "".join(characters)
    learned_chars_str = "".join(learned_chars)
    words_str = ", ".join(selected_words)

    prompt = f"""
你是一个小学语文老师。请根据以下汉字和词语：
- 学习汉字: '{characters_str}'
- 已学汉字: '{learned_chars_str}'
- 词语列表: '{words_str}'

生成一个包含部分词语的简单句子。这个句子必须满足以下条件：
   - 长度不能超过18个汉字。
   - 只能包含学习汉字和已学汉字列表中的汉字。

请以JSON格式返回，不要包含任何其他说明文字或代码块标记。结构如下：
{{
  "sentence": "一个句子。"
}}
"""

    MAX_RETRIES = 5
    for attempt in range(MAX_RETRIES):
        response = ai.generate_content(model, prompt)
        try:
            if response is not None:
                cleaned_text = response.text.strip()
                if cleaned_text.startswith("```json"):
                    cleaned_text = cleaned_text[7:]
                if cleaned_text.endswith("```"):
                    cleaned_text = cleaned_text[:-3]
                data = json.loads(cleaned_text)
                sentence = data["sentence"]

                if len(sentence) <= 18 and all(c in allowed_chars for c in sentence):
                    return FindWordsContent(
                        words=selected_words,
                        sentence=sentence
                    )

            else:
                print(f"Failed to generate content for puzzle, attempt {attempt + 1}")
                continue

        except (json.JSONDecodeError, KeyError) as e:
            print(f"无法生成句子: {e}")
            continue

    # Fallback values
    return FindWordsContent(
        words=["错误"] * 8,
        sentence="无法生成句子"
    )
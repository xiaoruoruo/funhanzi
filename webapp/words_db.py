"""
## Words database

Maintain a chinese words table in the database. 

Schema
- word: string. This is a word with 2 or more characters.
- score: integer. A score between 0 to 1.

Process 1: seeding new words for a given character
- Given a character, if there are less than desired number of words with that character
- Use Gemini to generate a batch of 2-character words (e.g. 20) containing that character
- Use Gemini to generate a batch of 3-character words (e.g. 5) containing that character
- Use Gemini to generate a batch of 4-character words (e.g. 5) containing that character
- Post process all the generated words, unique them, filter out words that's already in the database
- For the remaining words, use Gemini to generate the word scoring. 
- Insert those words into the database
- Output a logging message after this process is done, with some simple statistics

Process 2: seed a set of characters
- Given a lesson of characters in the lesson (see words.py), go through process 1 for each of the character
- Use threading to process each character in parallel
"""

import sqlite3
from pathlib import Path
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed

from . import ai, words

DB_FILE = Path(__file__).parent.parent / "webapp" / "database.db"
log = logging.getLogger(__name__)


def get_conn():
    conn = sqlite3.connect(DB_FILE, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS words (
                word TEXT PRIMARY KEY,
                score REAL
            )
            """
        )
        conn.commit()


def get_words_for_char(conn, char, desired_words=10):
    words_with_scores = [
        (row["word"], row["score"]) for row in conn.execute("SELECT word, score FROM words WHERE word LIKE ?", (f"%{char}%",))
    ]
    if len(words_with_scores) < desired_words:
        seed_words_for_char(char, desired_words)
        words_with_scores = [
            (row["word"], row["score"]) for row in conn.execute("SELECT word, score FROM words WHERE word LIKE ?", (f"%{char}%",))
        ]
    return words_with_scores


def seed_words_for_char(char, desired_words=10):
    with get_conn() as conn:
        existing_words = [
            row["word"] for row in conn.execute("SELECT word FROM words WHERE word LIKE ?", (f"%{char}%",))
        ]

    log.info(f"Generating words for {char}")
    model = ai.get_gemini_model()

    def generate_words(length, count):
        prompt = f"Generate {length}-character Chinese words containing the character '{char}', generate {count} words. Output the words separated by space, no quotes please."
        response = model.generate_content(prompt)
        return response.text.split()

    new_words = []
    new_words.extend(generate_words(2, 20))
    new_words.extend(generate_words(3, 5))
    new_words.extend(generate_words(4, 5))

    new_words = sorted(list(set(w for w in new_words if char in w)))
    new_words = [w for w in new_words if w not in existing_words]

    if not new_words:
        log.info(f"No new words generated for {char}.")
        return

    def score_words(words_to_score):
        prompt = f"""
        你是一位经验丰富的小学语文老师。请为以下中文词语打分，分数范围为0到1。评分标准请严格按照常用度以及小学生是否容易理解来判断。
        1分：小学生日常学习生活中常用，意思简单明了。
        0.5分：常用词，但小学生可能不常用或不易理解其确切含义。
        0分：生僻词、专业术语或无意义的组合。

        举例，包含“日”字的词：
        - 1分：日本, 日期, 日子
        - 0.5分：日企
        - 0分：日星

        待评分的词语:
        {', '.join(words_to_score)}

        请严格按照“词语:分数”的格式返回，并用英文逗号分隔，不要包含任何其他说明。
        """
        response = model.generate_content(prompt)
        return response.text.strip().split(",")

    scores_text = score_words(new_words)
    scored_words = []
    for item in scores_text:
        try:
            word, score_str = item.split(":")
            word = word.replace('\'','')
            scored_words.append((word.strip(), float(score_str.strip())))
        except ValueError:
            log.warning(f"Could not parse score for '{item}'")

    with get_conn() as conn:
        for word, score in scored_words:
            conn.execute("INSERT OR IGNORE INTO words (word, score) VALUES (?, ?)", (word, score))
        conn.commit()

    log.debug(' '.join(s[0] + ':' + str(s[1]) for s in scored_words))
    log.info(f"Added {len(scored_words)} new words for character '{char}'.")

def seed_words_for_lesson(lesson_number):
    lesson_chars = words.get_lesson(lesson_number)
    if not lesson_chars:
        log.error(f"Lesson {lesson_number} not found.")
        return

    with ThreadPoolExecutor() as executor:
        futures = {executor.submit(seed_words_for_char, char): char for char in lesson_chars}
        for future in as_completed(futures):
            char = futures[future]
            try:
                future.result()
            except Exception as e:
                log.exception(f"An error occurred while processing character '{char}': {e}")

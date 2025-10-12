import os
import random
import sqlite3
import sys
from datetime import date, timedelta, datetime, timezone
import google.generativeai as genai
from dotenv import load_dotenv

from . import fsrs_logic
from . import words
from . import formatter

DB_FILE = "webapp/database.db"

# --- Database filtering logic from exam_record.py ---

def get_db_connection():
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def get_latest_scores(conn, exam_type):
    scores = {}
    cursor = conn.cursor()
    cursor.execute("""
        SELECT character, score
        FROM records
        WHERE id IN (
            SELECT MAX(id)
            FROM records
            WHERE type = ?
            GROUP BY character
        )
    """, (exam_type,))
    for row in cursor.fetchall():
        scores[row['character']] = row['score']
    return scores

def filter_chars_by_score(char_list, exam_type, score_filter):
    conn = get_db_connection()
    scores = get_latest_scores(conn, exam_type)
    conn.close()
    return [char for char in char_list if scores.get(char, 0) < score_filter]

def filter_chars_by_days(char_list, days_filter):
    conn = get_db_connection()
    cursor = conn.cursor()
    cutoff_date = (date.today() - timedelta(days=days_filter)).isoformat()
    cursor.execute("SELECT DISTINCT character FROM records WHERE date >= ?", (cutoff_date,))
    recent_chars = {row['character'] for row in cursor.fetchall()}
    conn.close()
    return [char for char in char_list if char not in recent_chars]

# --- Exam generation logic ---

def generate_read_exam(num_chars, lessons, output_filename, score_filter=None, days_filter=None, character_list=None, title=None, header_text=None):
    selected_chars = []
    if character_list is not None:
        selected_chars = character_list
    else:
        lesson_numbers = words.parse_lesson_ranges(lessons)
        char_pool = []
        for num in lesson_numbers:
            lesson_chars = words.get_lesson(num)
            if lesson_chars:
                char_pool.extend(list(lesson_chars))
        
        unique_chars = list(set(char_pool))
        if score_filter is not None:
            unique_chars = filter_chars_by_score(unique_chars, "read", score_filter)
        if days_filter is not None:
            unique_chars = filter_chars_by_days(unique_chars, days_filter)

        num_to_select = min(num_chars, len(unique_chars))
        selected_chars = random.sample(unique_chars, k=num_to_select)

    final_title = title if title is not None else "Reading Test"
    final_header_text = header_text if header_text is not None else f"Lessons: {lessons}. Test date: ____. Circle the forgotten ones."
    formatter.generate_exam_html(
        items=selected_chars,
        output_filename=output_filename,
        title=final_title,
        header_text=final_header_text,
        items_per_row=6,
        font_size=36
    )
    return output_filename

def generate_write_exam(num_chars, lessons, output_filename, score_filter=None, days_filter=None, character_list=None):
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in .env file")
    genai.configure(api_key=api_key)

    if character_list is not None:
        char_pool = character_list
    else:
        lesson_numbers = words.parse_lesson_ranges(lessons)
        char_pool = []
        for num in lesson_numbers:
            lesson_chars = words.get_lesson(num)
            if lesson_chars:
                char_pool.extend(list(lesson_chars))

    unique_chars = list(set(char_pool))
    if score_filter is not None:
        unique_chars = filter_chars_by_score(unique_chars, "write", score_filter)
    if days_filter is not None:
        unique_chars = filter_chars_by_days(unique_chars, days_filter)

    num_to_select = min(num_chars, len(unique_chars))
    selected_chars = random.sample(unique_chars, k=num_to_select)

    model = genai.GenerativeModel('models/gemini-2.5-flash')
    
    remaining_chars = set(selected_chars)
    final_word_list = []
    tries = 4
    
    while len(remaining_chars) > 1 and tries > 0:
        print("Remaining chars ", remaining_chars)
        tries -= 1
        chunk_size = 30
        current_char_list = list(remaining_chars)
        chunk = random.sample(current_char_list, k=min(chunk_size, len(current_char_list)))
        char_list_str = "".join(chunk)
        prompt = (
            f"给定以下中文字: {char_list_str}\n"
            "请根据这些中文字组词，尽可能的只使用给定的字。如果实在有个字不能组词，可以用给定的字以外的字来为它组词，但一定要是简单的字。"
            "给定的字每个字都要有组词。"
            "输出词语，每个词语之间用空格分割，不要输出任何其他的内容。"
        )

        try:
            response = model.generate_content(prompt)
            text_response = response.text.strip().replace('`', '')
        except ValueError:
            print(f"ValueError when generating words for prompt: {prompt}, continuing...")
            continue
        generated_words = text_response.split()
        print("Generated Words", generated_words)
        
        random.shuffle(generated_words)
        
        for word in generated_words:
            final_word_list.append(word)
            remaining_chars -= set(word)
    
    unused_chars = list(remaining_chars)
    final_word_list.extend(unused_chars)
    random.shuffle(final_word_list)

    title = "Writing Test"
    header_text = f"Lessons: {lessons}. Test date: ____. Write down the characters."
    formatter.generate_exam_html(
        items=final_word_list,
        output_filename=output_filename,
        title=title,
        header_text=header_text,
        items_per_row=4,
        font_size=30
    )
    return output_filename

# --- Study material generation logic ---

def _generate_study_sheet_from_chars(selected_chars, output_filename):
    # Generate pinyin and words using Gemini
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in .env file")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")
    
    characters_data = []
    for char in selected_chars:
        prompt = f"请为“{char}”这个字，提供它的拼音，以及一个最常见的、由两个字组成的词语。请用这个格式返回：拼音，词语。例如：pīn yīn, 词语"
        response = model.generate_content(prompt)
        try:
            pinyin, word = response.text.strip().split(",", 1)
            characters_data.append((char, pinyin.strip(), word.strip()))
        except ValueError:
            characters_data.append((char, "N/A", "N/A"))

    formatter.format_study_sheet_html(characters_data, output_filename)
    return output_filename

def generate_review_study_sheet(num_chars, output_filename, days_filter=None):
    
    
    # Get all 'write' cards and calculate retrievability
    write_cards = []
    for (char, card_type), card in fsrs_logic.cards.items():
        if card_type == 'write':
            retrievability = fsrs_logic.write_scheduler.get_card_retrievability(card, datetime.now(timezone.utc))
            if retrievability is not None and retrievability > 0:
                write_cards.append({'char': char, 'retrievability': float(retrievability)})
    
    # Sort by retrievability (lowest first)
    write_cards.sort(key=lambda x: x['retrievability'])
    
    # Get the characters
    char_pool = [card['char'] for card in write_cards]

    # Filter out recently studied characters
    if days_filter is not None:
        conn = get_db_connection()
        cursor = conn.cursor()
        cutoff_date = (date.today() - timedelta(days=days_filter)).isoformat()
        cursor.execute("SELECT DISTINCT character FROM records WHERE date >= ? AND type IN ('readstudy', 'writestudy')", (cutoff_date,))
        recent_chars = {row['character'] for row in cursor.fetchall()}
        conn.close()
        char_pool = [char for char in char_pool if char not in recent_chars]

    # Select the top `num_chars`
    selected_chars = char_pool[:num_chars]
    
    return _generate_study_sheet_from_chars(selected_chars, output_filename)

def generate_study_chars_sheet(num_chars, lessons, output_filename, score_filter=None, days_filter=None, character_list=None):
    if character_list is not None:
        char_pool = character_list
    else:
        lesson_numbers = words.parse_lesson_ranges(lessons)
        char_pool = []
        for num in lesson_numbers:
            lesson_chars = words.get_lesson(num)
            if lesson_chars:
                char_pool.extend(list(lesson_chars))

    unique_chars = list(set(char_pool))
    if score_filter is not None:
        unique_chars = filter_chars_by_score(unique_chars, "read", score_filter)
    if days_filter is not None:
        unique_chars = filter_chars_by_days(unique_chars, days_filter)

    num_to_select = min(num_chars, len(unique_chars))
    selected_chars = random.sample(unique_chars, k=num_to_select) if character_list is None else unique_chars[:num_to_select]

    return _generate_study_sheet_from_chars(selected_chars, output_filename)

def generate_grid(sentence, words, filler_chars):
    GRID_SIZE = 8
    grid = [[None for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
    start_row = random.randint(0, GRID_SIZE - 1)
    r, c = start_row, 0
    for char in sentence:
        grid[r][c] = char
        possible_moves = []
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0: continue
                if dc < 1 and random.random() < 0.4: continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < GRID_SIZE and 0 <= nc < GRID_SIZE and grid[nr][nc] is None:
                    possible_moves.append((nr, nc))
        if possible_moves:
            r, c = random.choice(possible_moves)
        else:
            break
    empty_cells = []
    for r_ in range(GRID_SIZE):
        for c_ in range(GRID_SIZE):
            if grid[r_][c_] is None:
                empty_cells.append((r_, c_))
    random.shuffle(empty_cells)
    for word in words:
        is_filled = False
        while empty_cells:
            r_, c_ = empty_cells.pop()
            if grid[r_][c_] is None and c_ + 1 < GRID_SIZE and grid[r_][c_+1] is None:
                grid[r_][c_] = word[0]
                grid[r_][c_+1] = word[1]
                is_filled = True
                break
    empty_cells = [(r_, c_) for r_ in range(GRID_SIZE) for c_ in range(GRID_SIZE) if grid[r_][c_] is None]
    for r_, c_ in empty_cells:
        if filler_chars:
            grid[r_][c_] = random.choice(filler_chars)
    return grid, start_row

def generate_cloze_test(num_chars, lessons, output_filename, score_filter=None, days_filter=None, study_source=None):
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in .env file")
    genai.configure(api_key=api_key)

    if study_source == 'review':
        
        read_cards = []
        for (char, card_type), card in fsrs_logic.cards.items():
            if card_type == 'read':
                retrievability = fsrs_logic.read_scheduler.get_card_retrievability(card, datetime.now(timezone.utc))
                if retrievability is not None and retrievability > 0:
                    read_cards.append({'char': char, 'retrievability': float(retrievability)})
        read_cards.sort(key=lambda x: x['retrievability'])
        char_pool = [card['char'] for card in read_cards]

        if days_filter is not None:
            conn = get_db_connection()
            cursor = conn.cursor()
            cutoff_date = (date.today() - timedelta(days=days_filter)).isoformat()
            cursor.execute("SELECT DISTINCT character FROM records WHERE date >= ? AND type IN ('readstudy')", (cutoff_date,))
            recent_chars = {row['character'] for row in cursor.fetchall()}
            conn.close()
            char_pool = [char for char in char_pool if char not in recent_chars]

        selected_chars = char_pool[:num_chars]
    else:
        lesson_numbers = words.parse_lesson_ranges(lessons)
        char_pool = []
        for num in lesson_numbers:
            lesson_chars = words.get_lesson(num)
            if lesson_chars:
                char_pool.extend(list(lesson_chars))

        unique_chars = list(set(char_pool))
        if score_filter is not None:
            unique_chars = filter_chars_by_score(unique_chars, "read", score_filter)
        if days_filter is not None:
            unique_chars = filter_chars_by_days(unique_chars, days_filter)

        num_to_select = min(num_chars, len(unique_chars))
        selected_chars = random.sample(unique_chars, k=num_to_select)

    model = genai.GenerativeModel("gemini-2.5-flash")
    characters_str = "".join(selected_chars)
    prompt = f"""
    我在给2年级的孩子准备中文生字复习，请根据以下汉字：'{characters_str}'
    1. 生成5个双字词语。这些词语要使用到列表中的汉字，每个汉字只能用一次。
    2. 为每个词语生成一个包含该词语的简单句子。

    请以JSON格式返回，不要包含任何其他说明文字或代码块标记。结构如下：
    {{
      "pairs": [
        {{"word": "词语1", "sentence": "包含词语1的句子。"}},
        {{"word": "词语2", "sentence": "包含词语2的句子。"}},
        {{"word": "词语3", "sentence": "包含词语3的句子。"}},
        {{"word": "词语4", "sentence": "包含词语4的句子。"}},
        {{"word": "词语5", "sentence": "包含词语5的句子。"}}
      ]
    }}
    """
    response = model.generate_content(prompt)
    import json
    try:
        cleaned_text = response.text.strip()
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[7:]
        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3]
        data = json.loads(cleaned_text)
        pairs = []
        for item in data['pairs']:
            word = item['word']
            sentence = item['sentence']
            cloze_sentence = sentence.replace(word, '（ ）', 1)
            pairs.append((word, cloze_sentence))
    except (json.JSONDecodeError, KeyError) as e:
        print(f"无法生成句子: {e}")
        pairs = [("错误", "无法生成句子")] * 5

    formatter.format_cloze_test_html(pairs, output_filename)
    return output_filename

def get_learned_chars(conn):
    """Fetches all unique characters that have a 'read' or 'write' record."""
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT DISTINCT character FROM records WHERE type IN ('read', 'write')")
        return {row['character'] for row in cursor.fetchall()}
    except sqlite3.OperationalError:
        return set()

def generate_find_words_puzzle(num_chars, lessons, output_filename, score_filter=None, days_filter=None, study_source=None):
    # Add cli to the path to import words_db
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from . import words_db

    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in .env file")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")

    if study_source == 'review':

        read_cards = []
        for (char, card_type), card in fsrs_logic.cards.items():
            if card_type == 'read':
                retrievability = fsrs_logic.read_scheduler.get_card_retrievability(card, datetime.now(timezone.utc))
                if retrievability is not None and retrievability > 0:
                    read_cards.append({'char': char, 'retrievability': float(retrievability)})
        read_cards.sort(key=lambda x: x['retrievability'])
        char_pool = [card['char'] for card in read_cards]

        if days_filter is not None:
            conn = get_db_connection()
            cursor = conn.cursor()
            cutoff_date = (date.today() - timedelta(days=days_filter)).isoformat()
            cursor.execute("SELECT DISTINCT character FROM records WHERE date >= ? AND type IN ('readstudy')", (cutoff_date,))
            recent_chars = {row['character'] for row in cursor.fetchall()}
            conn.close()
            char_pool = [char for char in char_pool if char not in recent_chars]

        selected_chars = char_pool[:num_chars]
    else:
        lesson_numbers = words.parse_lesson_ranges(lessons)
        char_pool = []
        for num in lesson_numbers:
            lesson_chars = words.get_lesson(num)
            if lesson_chars:
                char_pool.extend(list(lesson_chars))

        unique_chars = list(set(char_pool))
        if score_filter is not None:
            unique_chars = filter_chars_by_score(unique_chars, "read", score_filter)
        if days_filter is not None:
            unique_chars = filter_chars_by_days(unique_chars, days_filter)

        num_to_select = min(num_chars, len(unique_chars))
        selected_chars = random.sample(unique_chars, k=num_to_select)

    # Get words from the database
    words = []
    with words_db.get_conn() as conn:
        for char in selected_chars:
            words.extend(words_db.get_words_for_char(conn, char))

    conn = get_db_connection()
    learned_chars = get_learned_chars(conn)
    conn.close()
    allowed_chars = set(selected_chars).union(learned_chars)

    # Filter for 2-character words, unique, and select 8
    two_char_words = []
    for w in list(set(w for w in words if len(w) == 2)):
        if any(c in selected_chars for c in w) and all(c in allowed_chars for c in w):
            two_char_words.append(w)

    random.shuffle(two_char_words)
    selected_words = two_char_words[:8]

    if not selected_words:
        print("Error: Could not find enough words to generate the puzzle.", file=sys.stderr)
        # Fallback or error handling
        words = ["错误"]*8
        sentence = "无法生成句子"
        grid, start_row = generate_grid(sentence, words, selected_chars)
        formatter.format_find_words_html(words, sentence, grid, start_row, output_filename)
        return output_filename

    allowed_chars = set(selected_chars).union(learned_chars).union(set("，。"))
    characters_str = "".join(selected_chars)
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
    
    print(prompt)
    MAX_RETRIES = 5
    for attempt in range(MAX_RETRIES):
        response = model.generate_content(prompt)
        import json
        try:
            cleaned_text = response.text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            data = json.loads(cleaned_text)
            sentence = data["sentence"]

            if len(sentence) > 18:
                continue

            if not all(c in allowed_chars for c in sentence):
                continue

            grid, start_row = generate_grid(sentence, selected_words, selected_chars)
            formatter.format_find_words_html(selected_words, sentence, grid, start_row, output_filename)
            return output_filename

        except (json.JSONDecodeError, KeyError) as e:
            print(f"无法生成句子: {e}")
            continue

    # Fallback or error handling
    words = ["错误"]*8
    sentence = "无法生成句子"
    grid, start_row = generate_grid(sentence, words, selected_chars)
    formatter.format_find_words_html(words, sentence, grid, start_row, output_filename)
    return output_filename

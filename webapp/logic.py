import os
import random
import sqlite3
import sys
from datetime import date, timedelta, datetime, timezone
import google.generativeai as genai
from dotenv import load_dotenv

DB_FILE = "webapp/database.db"

# --- Word loading logic from words.py ---

_lessons = []
words_txt_path = os.path.join(os.path.dirname(__file__), '..', 'words.txt')
with open(words_txt_path, 'r', encoding='utf-8') as f:
    for line in f:
        cleaned_line = ''.join(line.split())
        if cleaned_line:
            _lessons.append(cleaned_line)

def get_lesson(lesson_number):
    index = lesson_number - 1
    if 0 <= index < len(_lessons):
        return _lessons[index]
    return None

def parse_lesson_ranges(lesson_str):
    lessons = set()
    parts = lesson_str.split(',')
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if '-' in part:
            start, end = map(int, part.split('-'))
            lessons.update(range(start, end + 1))
        else:
            lessons.add(int(part))
    return sorted(list(lessons))

# --- HTML generation logic from exam_formatter.py ---

def generate_exam_html(items, output_filename, title, header_text, items_per_row, font_size):
    html_content = [
        "<!DOCTYPE html>", "<html>", "<head>", "<meta charset='UTF-8'>",
        f"<title>{title}</title>", "<style>",
        "  @page { size: letter; margin: 1in; }",
        "  body { font-family: 'Songti SC', 'STSong', serif; }",
        "  h1 { text-align: center; }",
        "  .items-grid { display: grid;",
        f"   grid-template-columns: repeat({items_per_row}, 1fr);",
        "    gap: 1em 0;", "  }",
        "  .item {", f"   font-size: {font_size}pt;",
        "    display: flex;", "    align-items: center;", "    justify-content: center;", "  }",
        "  .header { font-size: 10pt; text-align: right; padding-bottom: 20px; page-break-inside: avoid; }",
        "</style>", "</head>", "<body>", f"<h1>{title}</h1>"
    ]
    html_content.append("<div class='header'>")
    html_content.append(f"<p>{header_text}</p>")
    html_content.append("</div>")
    if items:
        html_content.append("<div class='items-grid'>")
        for item in items:
            html_content.append(f"<div class='item'>{item}</div>")
        html_content.append("</div>")
    html_content.extend(["</body>", "</html>"])
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write("\n".join(html_content))

def generate_failed_study_sheet(failed_read_chars, failed_write_chars, output_filename, header_text):
    html_content = [
        "<!DOCTYPE html>", "<html>", "<head>", "<meta charset='UTF-8'>",
        f"<title>Character Review</title>", "<style>",
        "  @page { size: letter; margin: 1in; }",
        "  body { font-family: 'Songti SC', 'STSong', serif; }",
        "  h1, h2 { text-align: center; }",
        "  .items-grid { display: grid;",
        f"   grid-template-columns: repeat(6, 1fr);",
        "    gap: 1em 0;", "  }",
        "  .item {", f"   font-size: 36pt;",
        "    display: flex;", "    align-items: center;", "    justify-content: center;", "  }",
        "  .header { font-size: 10pt; text-align: right; padding-bottom: 20px; page-break-inside: avoid; }",
        "  .section { margin-bottom: 40px; }",
        "</style>", "</head>", "<body>", f"<h1>Character Review</h1>"
    ]
    html_content.append("<div class='header'>")
    html_content.append(f"<p>{header_text}</p>")
    html_content.append("</div>")

    if failed_read_chars:
        html_content.append("<div class='section'>")
        html_content.append("<h2>Reading Practice</h2>")
        html_content.append("<div class='items-grid'>")
        for item in failed_read_chars:
            html_content.append(f"<div class='item'>{item}</div>")
        html_content.append("</div></div>")

    if failed_write_chars:
        html_content.append("<div class='section'>")
        html_content.append("<h2>Writing Practice</h2>")
        html_content.append("<div class='items-grid'>")
        for item in failed_write_chars:
            html_content.append(f"<div class='item'>{item}</div>")
        html_content.append("</div></div>")

    html_content.extend(["</body>", "</html>"])
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write("\n".join(html_content))


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
        lesson_numbers = parse_lesson_ranges(lessons)
        char_pool = []
        for num in lesson_numbers:
            lesson_chars = get_lesson(num)
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
    generate_exam_html(
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
        lesson_numbers = parse_lesson_ranges(lessons)
        char_pool = []
        for num in lesson_numbers:
            lesson_chars = get_lesson(num)
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
    generate_exam_html(
        items=final_word_list,
        output_filename=output_filename,
        title=title,
        header_text=header_text,
        items_per_row=4,
        font_size=30
    )
    return output_filename

# --- Study material generation logic ---

def format_study_sheet_html(characters_data, output_filename):
    html = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>汉字学习</title>
    <style>
        @page { size: letter; margin: 0.75in; }
        body { font-family: 'Songti SC', 'STSong', serif; font-size: 18pt; }
        h1 { text-align: center; margin-bottom: 20px; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border: 1px solid #000; padding: 15px; text-align: center; height: 60px; }
        th { background-color: #f2f2f2; font-weight: bold; }
        .character-col { width: 10%; }
        .pinyin-col { width: 15%; }
        .word-col { width: 20%; }
        .empty-col { width: 11%; }
    </style>
</head>
<body>
    <h1>汉字学习</h1>
    <table>
        <thead>
            <tr>
                <th class="character-col">汉字</th>
                <th class="pinyin-col">拼音</th>
                <th class="word-col">词语</th>
                <th class="empty-col"></th><th class="empty-col"></th><th class="empty-col"></th>
                <th class="empty-col"></th><th class="empty-col"></th>
            </tr>
        </thead>
        <tbody>
"""
    for char, pinyin, word in characters_data:
        html += f"""
            <tr>
                <td>{char}</td><td>{pinyin}</td><td>{word}</td>
                <td></td><td></td><td></td><td></td><td></td>
            </tr>
"""
    html += "</tbody></table></body></html>"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(html)

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

    format_study_sheet_html(characters_data, output_filename)
    return output_filename

def generate_review_study_sheet(num_chars, output_filename, days_filter=None):
    import fsrs_logic
    
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
        lesson_numbers = parse_lesson_ranges(lessons)
        char_pool = []
        for num in lesson_numbers:
            lesson_chars = get_lesson(num)
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

def format_find_words_html(words, sentence, grid, start_row, output_filename, title="找朋友"):
    start_marker_top = f"calc((100% / 16) + (100% / 8) * {start_row})"
    html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        @page {{ size: letter; margin: 1in; }}
        body {{ font-family: 'Songti SC', 'STSong', serif; font-size: 16pt; display: flex; flex-direction: column; align-items: center; }}
        .container {{ width: 80%; }}
        h1 {{ text-align: center; margin-bottom: 20px; }}
        .word-list {{ display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; margin-bottom: 20px; padding: 0; list-style: none; }}
        .word-item {{ border: 2px solid #ccc; border-radius: 25px; padding: 5px 15px; }}
        .instructions {{ text-align: center; margin-bottom: 20px; }}
        .sentence-box {{ border: 2px dotted #999; padding: 15px; margin-bottom: 20px; text-align: center; font-size: 18pt; }}
        .grid-container {{ position: relative; width: 100%; margin: 0 auto; }}
        .char-grid {{ display: grid; grid-template-columns: repeat(8, 1fr); border-top: 2px solid black; border-left: 2px solid black; }}
        .grid-cell {{ border-right: 2px solid black; border-bottom: 2px solid black; aspect-ratio: 1 / 1; display: flex; align-items: center; justify-content: center; font-size: 24pt; }}
        .start-marker {{ position: absolute; left: -30px; top: {start_marker_top}; transform: translateY(-50%); color: orange; font-size: 20pt; }}
    </style>
</head>
<body>
    <h1>{title}</h1>
    <div class="container">
        <ul class="word-list">{''.join(f'<li class="word-item">{word}</li>' for word in words)}</ul>
        <p class="instructions">逐一读出词组，并将词组在下方方格中圈出。将下方的句子连起来。</p>
        <div class="sentence-box">{sentence}</div>
        <div class="grid-container">
            <div class="char-grid">{''.join(f'<div class="grid-cell">{char if char is not None else ""}</div>' for row in grid for char in row)}</div>
            <div class="start-marker">▶</div>
        </div>
    </div>
</body>
</html>
"""
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(html_content)

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

def format_cloze_test_html(pairs, output_filename, title="句子填空"):
    # Randomize the order of words and sentences independently
    words = [p[0] for p in pairs]
    sentences = [p[1] for p in pairs]
    random.shuffle(words)
    random.shuffle(sentences)

    html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        @page {{ size: letter; margin: 1in; }}
        body {{ font-family: 'Songti SC', 'STSong', serif; font-size: 16pt; }}
        .container {{ width: 90%; margin: auto; }}
        h1 {{ text-align: center; margin-bottom: 20px; }}
        .instructions {{ text-align: center; margin-bottom: 30px; }}
        .cloze-table {{ width: 100%; border-collapse: collapse; }}
        .cloze-table td {{ padding: 15px 5px; vertical-align: middle; }}
        .word-cell {{ width: 25%; text-align: center; }}
        .sentence-cell {{ width: 75%; }}
        .word-box {{ border: 2px solid #ccc; border-radius: 15px; padding: 10px 20px; display: inline-block; }}
        .bullet {{ font-size: 20px; margin-right: 10px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <p class="instructions">找出句子中正确的词组，将它们连起来。</p>
        <table class="cloze-table">
"""
    for i in range(len(words)):
        html_content += f"""
            <tr>
                <td class="word-cell"><div class="word-box">{words[i]}</div></td>
                <td class="sentence-cell"><span class="bullet">&bull;</span>{sentences[i]}</td>
            </tr>
"""
    html_content += """
        </table>
    </div>
</body>
</html>
"""
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(html_content)

def generate_cloze_test(num_chars, lessons, output_filename, score_filter=None, days_filter=None, study_source=None):
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in .env file")
    genai.configure(api_key=api_key)

    if study_source == 'review':
        import fsrs_logic
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
        lesson_numbers = parse_lesson_ranges(lessons)
        char_pool = []
        for num in lesson_numbers:
            lesson_chars = get_lesson(num)
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

    format_cloze_test_html(pairs, output_filename)
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
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not found in .env file")
    genai.configure(api_key=api_key)
    model = genai.GenerativeModel("gemini-2.5-flash")

    if study_source == 'review':
        import fsrs_logic
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
        lesson_numbers = parse_lesson_ranges(lessons)
        char_pool = []
        for num in lesson_numbers:
            lesson_chars = get_lesson(num)
            if lesson_chars:
                char_pool.extend(list(lesson_chars))

        unique_chars = list(set(char_pool))
        if score_filter is not None:
            unique_chars = filter_chars_by_score(unique_chars, "read", score_filter)
        if days_filter is not None:
            unique_chars = filter_chars_by_days(unique_chars, days_filter)

        num_to_select = min(num_chars, len(unique_chars))
        selected_chars = random.sample(unique_chars, k=num_to_select)

    conn = get_db_connection()
    learned_chars = get_learned_chars(conn)
    conn.close()

    allowed_chars = set(selected_chars).union(learned_chars).union(set("，。"))
    characters_str = "".join(selected_chars)
    learned_chars_str = "".join(learned_chars)

    prompt = f"""
请根据以下汉字：
- 学习汉字: '{characters_str}'
- 已学汉字: '{learned_chars_str}'

1. 生成8个双字词语。这些词语应该尽可能使用学习汉字列表中的汉字。
2. 生成一个包含部分词语的简单句子。这个句子必须满足以下条件：
   - 长度不能超过18个汉字。
   - 只能包含学习汉字和已学汉字列表中的汉字。

请以JSON格式返回，不要包含任何其他说明文字或代码块标记。结构如下：
{{
  "words": ["词语1", "词语2", "词语3", "词语4", "词语5", "词语6", "词语7", "词语8"],
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
            words = data["words"]
            sentence = data["sentence"]

            print(data)

            if len(sentence) > 18:
                continue

            if not all(c in allowed_chars for c in sentence):
                continue

            grid, start_row = generate_grid(sentence, words, selected_chars)
            format_find_words_html(words, sentence, grid, start_row, output_filename)
            return output_filename

        except (json.JSONDecodeError, KeyError) as e:
            print(f"无法生成句子: {e}")
            continue

    # Fallback or error handling
    words = ["错误"]*8
    sentence = "无法生成句子"
    grid, start_row = generate_grid(sentence, words, selected_chars)
    format_find_words_html(words, sentence, grid, start_row, output_filename)
    return output_filename



from flask import Flask, render_template, request, redirect, url_for
import db
import logic
import datetime
import json
from bs4 import BeautifulSoup
import fsrs_logic

app = Flask(__name__)


@app.route('/')
def index():
    return redirect(url_for('exam'))

@app.route('/exam')
def exam():
    conn = db.get_db_connection()
    exams = conn.execute('SELECT * FROM exams ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('exam.html', exams=exams)

@app.route('/exam/generate/<exam_type>')
def generate_exam(exam_type):
    conn = db.get_db_connection()
    settings = conn.execute('SELECT * FROM settings').fetchall()
    conn.close()
    settings_dict = {s['key']: s['value'] for s in settings}
    
    if exam_type == 'read':
        num_chars = int(settings_dict.get('read_exam_chars', 100))
    else:
        num_chars = int(settings_dict.get('write_exam_chars', 50))
    lesson_range = settings_dict.get('lesson_range', '1-10')
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    output_filename = f"webapp/static/exams/{exam_type}_{timestamp}.html"

    if exam_type == 'read':
        logic.generate_read_exam(num_chars, lesson_range, output_filename)
    elif exam_type == 'write':
        logic.generate_write_exam(num_chars, lesson_range, output_filename)
    else:
        return "Invalid exam type", 400

    conn = db.get_db_connection()
    conn.execute("INSERT INTO exams (type, filename) VALUES (?, ?)",
                 (exam_type, output_filename.replace('webapp/', '')))
    conn.commit()
    conn.close()
    
    return redirect(url_for('exam'))

@app.route('/exam/generate_review/<exam_type>')
def generate_review_exam(exam_type):
    conn = db.get_db_connection()
    settings = conn.execute('SELECT * FROM settings').fetchall()
    conn.close()
    settings_dict = {s['key']: s['value'] for s in settings}

    # Get due characters
    due_chars = []
    today = datetime.datetime.now(datetime.timezone.utc)
    for (char, card_type), card in fsrs_logic.cards.items():
        if card_type == exam_type and card.due <= today:
            due_chars.append(char)

    if not due_chars:
        # Handle case with no due characters, maybe flash a message
        return redirect(url_for('exam'))

    if exam_type == 'read':
        num_chars = int(settings_dict.get('read_exam_chars', 100))
    else:
        num_chars = int(settings_dict.get('write_exam_chars', 50))
    lesson_range = settings_dict.get('lesson_range', '1-10') # Keep for header text

    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    output_filename = f"webapp/static/exams/{exam_type}_review_{timestamp}.html"

    if exam_type == 'read':
        logic.generate_read_exam(num_chars, lesson_range, output_filename, character_list=due_chars)
    elif exam_type == 'write':
        logic.generate_write_exam(num_chars, lesson_range, output_filename, character_list=due_chars)
    else:
        return "Invalid exam type", 400

    conn = db.get_db_connection()
    conn.execute("INSERT INTO exams (type, filename) VALUES (?, ?)",
                 (f"{exam_type}", output_filename.replace('webapp/', '')))
    conn.commit()
    conn.close()

    return redirect(url_for('exam'))


def parse_characters_from_exam(html_file):
    characters = []
    with open(html_file, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
        items = soup.find_all('div', class_='item')
        for item in items:
            # For write exams, the item might be a word, so we take all characters
            for char in item.text.strip():
                characters.append(char)
    return sorted(list(set(characters)))

def parse_characters_from_study_sheet(html_file):
    read_chars = []
    write_chars = []
    with open(html_file, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
        
        # Find the h2 tag for Reading Practice
        read_header = soup.find('h2', string='Reading Practice')
        if read_header:
            read_grid = read_header.find_next_sibling('div', class_='items-grid')
            if read_grid:
                items = read_grid.find_all('div', class_='item')
                for item in items:
                    read_chars.append(item.text.strip())

        # Find the h2 tag for Writing Practice
        write_header = soup.find('h2', string='Writing Practice')
        if write_header:
            write_grid = write_header.find_next_sibling('div', class_='items-grid')
            if write_grid:
                items = write_grid.find_all('div', class_='item')
                for item in items:
                    write_chars.append(item.text.strip())
                    
    return read_chars, write_chars

@app.route('/exam/record/<int:exam_id>', methods=['GET', 'POST'])
def record_exam(exam_id):
    conn = db.get_db_connection()
    exam = conn.execute('SELECT * FROM exams WHERE id = ?', (exam_id,)).fetchone()
    
    if request.method == 'POST':
        today_str = datetime.date.today().strftime('%Y-%m-%d')
        for char, score in request.form.items():
            if char.startswith('score_'):
                character = char.split('_', 1)[1]
                conn.execute(
                    "INSERT INTO records (character, type, score, date) VALUES (?, ?, ?, ?)",
                    (character, exam['type'], int(score), today_str)
                )
        
        conn.execute("UPDATE exams SET recorded = TRUE WHERE id = ?", (exam_id,))
        
        # Rebuild cards to reflect the new scores
        fsrs_logic.rebuild_cards_from_records(conn)
        
        conn.commit()
        conn.close()
        
        return redirect(url_for('exam'))

    # GET request
    exam_filepath = f"webapp/{exam['filename']}"
    characters = parse_characters_from_exam(exam_filepath)
    conn.close()
    
    return render_template('record_exam.html', exam=exam, characters=characters)


@app.route('/study')
def study():
    conn = db.get_db_connection()
    studies = conn.execute('SELECT * FROM studies ORDER BY created_at DESC').fetchall()
    conn.close()
    return render_template('study.html', studies=studies)

def parse_characters_from_standard_study_sheet(html_file):
    characters = []
    with open(html_file, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
        # Find all table rows, skip the header row
        rows = soup.find_all('tr')[1:]
        for row in rows:
            # The character is in the first cell of each row
            char_cell = row.find('td')
            if char_cell:
                characters.append(char_cell.text.strip())
    return characters

def parse_characters_from_find_words_puzzle(html_file):
    characters = set()
    with open(html_file, 'r', encoding='utf-8') as f:
        soup = BeautifulSoup(f, 'html.parser')
        sentence_box = soup.find('div', class_='sentence-box')
        if sentence_box:
            sentence = sentence_box.text.strip()
            for char in sentence:
                # Add any character that is a Chinese character
                if '\u4e00' <= char <= '\u9fff':
                    characters.add(char)
    return sorted(list(characters))

@app.route('/study/mark_done/<int:study_id>')
def mark_study_done(study_id):
    conn = db.get_db_connection()
    study = conn.execute('SELECT * FROM studies WHERE id = ?', (study_id,)).fetchone()

    if study:
        study_filepath = f"webapp/{study['filename']}"
        today_str = datetime.date.today().strftime('%Y-%m-%d')

        if study['type'] == 'failed':
            read_chars, write_chars = parse_characters_from_study_sheet(study_filepath)
            
            for char in read_chars:
                conn.execute(
                    "INSERT INTO records (character, type, score, date) VALUES (?, ?, ?, ?)",
                    (char, 'read', 8, today_str)
                )
            
            for char in write_chars:
                conn.execute(
                    "INSERT INTO records (character, type, score, date) VALUES (?, ?, ?, ?)",
                    (char, 'write', 8, today_str)
                )
            
            fsrs_logic.rebuild_cards_from_records(conn)

        elif study['type'] == 'words':
            chars = parse_characters_from_find_words_puzzle(study_filepath)
            for char in chars:
                conn.execute(
                    "INSERT INTO records (character, type, score, date) VALUES (?, ?, ?, ?)",
                    (char, 'readstudy', 10, today_str)
                )

        elif study['type'] == 'chars':
            chars = parse_characters_from_standard_study_sheet(study_filepath)
            for char in chars:
                conn.execute(
                    "INSERT INTO records (character, type, score, date) VALUES (?, ?, ?, ?)",
                    (char, 'readstudy', 10, today_str)
                )

    conn.execute("UPDATE studies SET done = TRUE WHERE id = ?", (study_id,))
    conn.commit()
    conn.close()
    return redirect(url_for('study'))

@app.route('/study/generate/<study_type>')
def generate_study(study_type):
    conn = db.get_db_connection()
    settings = conn.execute('SELECT * FROM settings').fetchall()
    conn.close()
    settings_dict = {s['key']: s['value'] for s in settings}
    
    num_chars = int(settings_dict.get('study_chars', 20))
    lesson_range = settings_dict.get('lesson_range', '1-10')
    
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    output_filename = f"webapp/static/studies/{study_type}_{timestamp}.html"

    if study_type == 'chars':
        study_source = settings_dict.get('study_source', 'basic')
        if study_source == 'review':
            days_filter = int(settings_dict.get('failed_recency_days', 8))
            logic.generate_review_study_sheet(num_chars, output_filename, days_filter=days_filter)
        else:
            logic.generate_study_chars_sheet(num_chars, lesson_range, output_filename)
    elif study_type == 'failed':
        failed_threshold = int(settings_dict.get('failed_threshold', 5))
        failed_recency_days = int(settings_dict.get('failed_recency_days', 8))
        
        conn = db.get_db_connection()
        cutoff_date = (datetime.date.today() - datetime.timedelta(days=failed_recency_days)).strftime('%Y-%m-%d')
        
        # Get characters where the most recent score for 'read' is below the threshold
        read_query = '''
            WITH RankedRecords AS (
                SELECT
                    character,
                    score,
                    ROW_NUMBER() OVER (PARTITION BY character ORDER BY date DESC, id DESC) as rn
                FROM records
                WHERE date >= ? AND type = 'read'
            )
            SELECT character
            FROM RankedRecords
            WHERE rn = 1 AND score < ?
        '''
        read_records = conn.execute(read_query, (cutoff_date, failed_threshold)).fetchall()
        
        # Get characters where the most recent score for 'write' is below the threshold
        write_query = '''
            WITH RankedRecords AS (
                SELECT
                    character,
                    score,
                    ROW_NUMBER() OVER (PARTITION BY character ORDER BY date DESC, id DESC) as rn
                FROM records
                WHERE date >= ? AND type = 'write'
            )
            SELECT character
            FROM RankedRecords
            WHERE rn = 1 AND score < ?
        '''
        write_records = conn.execute(write_query, (cutoff_date, failed_threshold)).fetchall()
        conn.close()
        
        failed_read_chars = sorted(list(set([record['character'] for record in read_records])))
        failed_write_chars = sorted(list(set([record['character'] for record in write_records])))
        
        # Limit the number of characters if necessary
        if len(failed_read_chars) + len(failed_write_chars) > num_chars:
            # This is a simple way to limit, might need a more sophisticated approach
            # if you want to prioritize or balance the lists.
            total_chars = len(failed_read_chars) + len(failed_write_chars)
            while total_chars > num_chars:
                if len(failed_read_chars) > len(failed_write_chars):
                    failed_read_chars.pop()
                else:
                    failed_write_chars.pop()
                total_chars -= 1

        if not failed_read_chars and not failed_write_chars:
            # Handle case with no failed characters, maybe flash a message
            return redirect(url_for('study'))

        logic.generate_failed_study_sheet(
            failed_read_chars=failed_read_chars,
            failed_write_chars=failed_write_chars,
            output_filename=output_filename,
            header_text=f"Characters needing review from the last {failed_recency_days} days"
        )

    elif study_type == 'words':
        study_source = settings_dict.get('study_source', 'basic')
        days_filter = int(settings_dict.get('failed_recency_days', 8))
        logic.generate_find_words_puzzle(num_chars, lesson_range, output_filename, study_source=study_source, days_filter=days_filter)

    else:
        return "Invalid study type", 400

    conn = db.get_db_connection()
    conn.execute("INSERT INTO studies (type, filename) VALUES (?, ?)",
                 (study_type, output_filename.replace('webapp/', '')))
    conn.commit()
    conn.close()
    
    return redirect(url_for('study'))

@app.route('/progress')
def progress():
    conn = db.get_db_connection()
    records = conn.execute('''
        SELECT character, type, score, date
        FROM (
            SELECT
                character,
                type,
                score,
                date,
                ROW_NUMBER() OVER (PARTITION BY character, type ORDER BY date DESC) as rn
            FROM records
            WHERE type IN ('read', 'write')
        )
        WHERE rn <= 3
        ORDER BY character, type, date ASC
    ''').fetchall()
    conn.close()

    progress_data = {}
    for record in records:
        char = record['character']
        if char not in progress_data:
            progress_data[char] = {
                'read': {'records': [], 'retrievability': 'N/A', 'due_in_days': 'N/A'},
                'write': {'records': [], 'retrievability': 'N/A', 'due_in_days': 'N/A'}
            }
        
        record_type = record['type']
        
        # Calculate days ago
        record_date = datetime.datetime.strptime(record['date'], '%Y-%m-%d')
        days_ago = (datetime.datetime.now() - record_date).days
        
        # Determine color
        score = record['score']
        rating = fsrs_logic.score_to_rating(score)
        color = fsrs_logic.RATING_TO_COLOR.get(rating, '')

        progress_data[char][record_type]['records'].append({
            'days_ago': days_ago,
            'color': color
        })

    # Get retrievability and due date for all characters
    for char in progress_data:
        for record_type in ['read', 'write']:
            card_key = (char, record_type)
            if card_key in fsrs_logic.cards:
                card = fsrs_logic.cards[card_key]
                
                scheduler = fsrs_logic.read_scheduler if record_type == 'read' else fsrs_logic.write_scheduler
                
                # Retrievability
                retrievability_val = scheduler.get_card_retrievability(card, datetime.datetime.now(datetime.timezone.utc))
                if retrievability_val is not None:
                    progress_data[char][record_type]['retrievability'] = f"{float(retrievability_val)*100:.2f}%"
                
                # Due date
                due_date = card.due
                if due_date:
                    due_in_days = (due_date - datetime.datetime.now(datetime.timezone.utc)).days
                    progress_data[char][record_type]['due_in_days'] = due_in_days

    return render_template('progress.html', progress_data=progress_data)

@app.route('/admin', methods=['GET', 'POST'])
def admin():
    if request.method == 'POST':
        conn = db.get_db_connection()
        conn.execute("UPDATE settings SET value = ? WHERE key = 'lesson_range'",
                     (request.form['lesson_range'],))
        conn.execute("UPDATE settings SET value = ? WHERE key = 'read_exam_chars'",
                     (request.form['read_exam_chars'],))
        conn.execute("UPDATE settings SET value = ? WHERE key = 'write_exam_chars'",
                     (request.form['write_exam_chars'],))
        conn.execute("UPDATE settings SET value = ? WHERE key = 'study_chars'",
                     (request.form['study_chars'],))
        conn.execute("UPDATE settings SET value = ? WHERE key = 'study_source'",
                        (request.form['study_source'],))
        conn.execute("UPDATE settings SET value = ? WHERE key = 'failed_threshold'",
                        (request.form['failed_threshold'],))
        conn.execute("UPDATE settings SET value = ? WHERE key = 'failed_recency_days'",
                        (request.form['failed_recency_days'],))
        conn.commit()
        conn.close()
        return redirect(url_for('admin'))

    conn = db.get_db_connection()
    settings = conn.execute('SELECT * FROM settings').fetchall()
    conn.close()
    settings_dict = {s['key']: s['value'] for s in settings}
    return render_template('admin.html', settings=settings_dict)

if __name__ == '__main__':
    db.create_tables()
    conn = db.get_db_connection()
    fsrs_logic.rebuild_cards_from_records(conn)
    conn.commit()
    conn.close()
    app.run(debug=True)

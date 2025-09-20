
import sqlite3

def get_db_connection():
    conn = sqlite3.connect('webapp/database.db')
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    conn = get_db_connection()
    c = conn.cursor()

    # settings table
    c.execute('''
        CREATE TABLE IF NOT EXISTS settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')

    # exams table
    c.execute('''
        CREATE TABLE IF NOT EXISTS exams (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            filename TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            recorded BOOLEAN DEFAULT FALSE
        )
    ''')

    # studies table
    c.execute('''
        CREATE TABLE IF NOT EXISTS studies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            filename TEXT NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            done BOOLEAN DEFAULT FALSE
        )
    ''')

    # cards table for FSRS
    c.execute('''
        CREATE TABLE IF NOT EXISTS cards (
            character TEXT NOT NULL,
            type TEXT NOT NULL,
            card_data TEXT NOT NULL,
            PRIMARY KEY (character, type)
        )
    ''')

    # Set default settings
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('lesson_range', '1-10')")
    
    # Migration for num_chars to read_exam_chars and write_exam_chars
    c.execute("SELECT value FROM settings WHERE key = 'num_chars'")
    row = c.fetchone()
    if row:
        num_chars_val = row['value']
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('read_exam_chars', ?)", (num_chars_val,))
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('write_exam_chars', ?)", (num_chars_val,))
        c.execute("DELETE FROM settings WHERE key = 'num_chars'")
    else:
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('read_exam_chars', '100')")
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('write_exam_chars', '50')")
    
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('study_chars', '20')")
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('failed_threshold', '5')")
    c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('failed_recency_days', '8')")


    conn.commit()
    conn.close()

if __name__ == '__main__':
    create_tables()
    print("Database tables created successfully.")

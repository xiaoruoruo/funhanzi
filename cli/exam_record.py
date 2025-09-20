import argparse
import os
import sqlite3
import sys
from datetime import date, timedelta

DB_FILE = "record.db"

def get_db_connection():
    """Establishes a connection to the SQLite database."""
    conn = sqlite3.connect(DB_FILE)
    return conn

# --- Database Migration Framework ---

# List of migration functions. Each function migrates the schema to the next version.
# MIGRATIONS[0] brings schema to version 1.
# MIGRATIONS[1] brings schema to version 2.
# etc.
MIGRATIONS = []

def migration_v1(cursor):
    """Schema version 1: initial creation."""
    # This migration creates the initial 'records' table.
    # It reflects the schema *before* the 'readstudy' and 'writestudy' types were added.
    # Columns:
    #- date: the date of the exam
    #- character: the character being tested
    #- type: "read" if it's reading exam or "write" for writing exam
    #- score: A score between 0 to 10
    cursor.execute("""
        CREATE TABLE records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            character TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('read', 'write')),
            score INTEGER NOT NULL CHECK(score >= 0 AND score <= 10)
        )
    """)
MIGRATIONS.append(migration_v1)

def migration_v2(cursor):
    """Schema version 2: add 'readstudy' and 'writestudy' types."""
    # SQLite doesn't support ALTER TABLE to modify a CHECK constraint directly.
    # The workaround is to rename the table, create a new one with the new schema,
    # copy the data, and drop the old table.
    cursor.execute("ALTER TABLE records RENAME TO _records_old")
    cursor.execute("""
        CREATE TABLE records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT NOT NULL,
            character TEXT NOT NULL,
            type TEXT NOT NULL CHECK(type IN ('read', 'write', 'readstudy', 'writestudy')),
            score INTEGER NOT NULL CHECK(score >= 0 AND score <= 10)
        )
    """)
    cursor.execute("INSERT INTO records (id, date, character, type, score) SELECT id, date, character, type, score FROM _records_old")
    cursor.execute("DROP TABLE _records_old")
MIGRATIONS.append(migration_v2)

def get_db_version(cursor):
    """Gets the schema version from the database using PRAGMA user_version."""
    return cursor.execute("PRAGMA user_version").fetchone()[0]

def set_db_version(cursor, version):
    """Sets the schema version in the database using PRAGMA user_version."""
    cursor.execute(f"PRAGMA user_version = {version}")

def migrate_db(conn):
    """Applies all necessary database migrations."""
    cursor = conn.cursor()
    current_version = get_db_version(cursor)
    
    if current_version == 0:
        # Check if this is a fresh DB or an old, unversioned one.
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='records'")
        if cursor.fetchone() is not None:
            print("Found existing unversioned database. Setting schema version to 1.", file=sys.stderr)
            current_version = 1
            set_db_version(cursor, 1)
            conn.commit()

    latest_version = len(MIGRATIONS)
    print(f"Current DB version: {current_version}. Latest version: {latest_version}.", file=sys.stderr)

    for i in range(current_version, latest_version):
        version = i + 1
        print(f"Applying migration to version {version}...", file=sys.stderr)
        MIGRATIONS[i](cursor)
        set_db_version(cursor, version)
        conn.commit()
        print(f"Successfully migrated to version {version}.", file=sys.stderr)

# --- End of Migration Framework ---

def insert_record(conn, record_date, character, exam_type, score):
    """Inserts a new exam record into the database."""
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO records (date, character, type, score) VALUES (?, ?, ?, ?)",
        (record_date, character, exam_type, score)
    )
    conn.commit()


def get_latest_scores(conn, exam_type):
    """Fetches the latest score for each character for a given exam type."""
    scores = {}
    cursor = conn.cursor()
    try:
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
            scores[row[0]] = row[1]
    except sqlite3.OperationalError:
        # Table might not exist yet, which is fine.
        pass
    return scores

def filter_chars_by_score(char_list, exam_type, score_filter):
    """Filters a list of characters based on their latest score."""
    if not os.path.exists(DB_FILE):
        print(f"Warning: Database file '{DB_FILE}' not found. Cannot filter by score.", file=sys.stderr)
        return char_list

    conn = get_db_connection()
    scores = get_latest_scores(conn, exam_type)
    conn.close()

    filtered_chars = []
    for char in char_list:
        score = scores.get(char, 0)  # Default score is 0 if not found
        if score < score_filter:
            filtered_chars.append(char)

    print(f"Filtered {len(char_list) - len(filtered_chars)} characters based on score >= {score_filter}.", file=sys.stderr)
    return filtered_chars

def filter_chars_by_days(char_list, days_filter):
    """Filters out characters that have been tested recently."""
    if not os.path.exists(DB_FILE):
        print(f"Warning: Database file '{DB_FILE}' not found. Cannot filter by days.", file=sys.stderr)
        return char_list

    conn = get_db_connection()
    cursor = conn.cursor()

    cutoff_date = (date.today() - timedelta(days=days_filter)).isoformat()

    recent_chars = set()
    try:
        cursor.execute("SELECT DISTINCT character FROM records WHERE date >= ?", (cutoff_date,))
        recent_chars = {row[0] for row in cursor.fetchall()}
    except sqlite3.OperationalError:
        pass  # Table might not exist, which is fine.
    finally:
        conn.close()

    original_char_count = len(char_list)
    filtered_chars = [char for char in char_list if char not in recent_chars]
    filtered_count = original_char_count - len(filtered_chars)

    print(f"Filtered {filtered_count} characters tested in the last {days_filter} days.", file=sys.stderr)
    return filtered_chars


def get_recent_low_score_chars(conn, days_filter, score_filter):
    """
    Find characters that have been tested in the last `days_filter` days,
    and whose latest score is <= `score_filter`.
    """
    cursor = conn.cursor()

    # This query gets the latest record for each character.
    cursor.execute("""
        SELECT character, score, date
        FROM records r1
        WHERE r1.id = (
            SELECT id
            FROM records r2
            WHERE r2.character = r1.character
            ORDER BY r2.date DESC, r2.id DESC
            LIMIT 1
        )
    """)

    recent_low_score_chars = []
    cutoff_date = date.today() - timedelta(days=days_filter)

    for row in cursor.fetchall():
        char, score, record_date_str = row
        record_date = date.fromisoformat(record_date_str)

        if score <= score_filter and record_date >= cutoff_date:
            recent_low_score_chars.append(char)

    return recent_low_score_chars


def main():
    """
    Main function to parse command-line arguments and insert an exam record.
    """
    parser = argparse.ArgumentParser(description="Record an exam result.")
    parser.add_argument("--character", type=str, help="The character(s) being tested. Can be a string of multiple characters.")
    parser.add_argument("--type", type=str, choices=['read', 'write', 'readstudy', 'writestudy'], help="The type of exam ('read', 'write', 'readstudy', or 'writestudy').")
    parser.add_argument("--score", type=int, help="The score from 0 to 10.")
    parser.add_argument("--date", type=str, default=date.today().isoformat(), help="The date of the exam in YYYY-MM-DD format (default: today).")
    args = parser.parse_args()

    if not (0 <= args.score <= 10):
        print("Error: Score must be between 0 and 10.", file=sys.stderr)
        sys.exit(1)

    try:
        conn = get_db_connection()
        migrate_db(conn)
        
        for char in args.character:
            insert_record(conn, args.date, char, args.type, args.score)
        
        print(f"Successfully recorded results for {len(args.character)} character(s) with Type='{args.type}', Score={args.score}")
    
    except sqlite3.Error as e:
        print(f"Database error: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    main()

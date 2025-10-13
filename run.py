import os
from webapp.app import app
from webapp import db, fsrs_logic

# Ensure static directories exist
os.makedirs("webapp/static/exams", exist_ok=True)
os.makedirs("webapp/static/studies", exist_ok=True)

# Initialize database and FSRS cards before running the app
db.create_tables()
with db.get_db_connection() as conn:
    fsrs_logic.rebuild_cards_from_records(conn)

if __name__ == "__main__":
    app.run(debug=True)

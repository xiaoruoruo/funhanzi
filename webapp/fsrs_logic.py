import datetime
import json
from fsrs import Scheduler, Card, Rating

from . import words

# FSRS Schedulers
read_scheduler = Scheduler(desired_retention=0.9)
write_scheduler = Scheduler(desired_retention=0.6)
cards = {}  # In-memory store for cards: (character, type) -> Card

RATING_TO_COLOR = {
    Rating.Again: "text-danger",
    Rating.Hard: "text-warning",
    Rating.Good: "text-info",
    Rating.Easy: "text-success",
}


def score_to_rating(score):
    if score <= 1:
        return Rating.Again
    elif score <= 4:
        return Rating.Hard
    elif score <= 8:
        return Rating.Good
    else:
        return Rating.Easy


def build_cards(unique_characters, all_records):
    # Group records by card (character, type), adding implied read records
    records_by_card = {}
    for record in all_records:
        char = record["character"]
        record_type = record["type"]
        score = record["score"]

        # Add the original record
        key = (char, record_type)
        if key not in records_by_card:
            records_by_card[key] = []
        records_by_card[key].append(dict(record))

        # If it's a write record, add an implied read record
        if record_type == "write":
            read_key = (char, "read")
            if read_key not in records_by_card:
                records_by_card[read_key] = []

            implied_read_record = {
                "character": char,
                "type": "read",
                "score": min(score + 3, 10),
                "date": record["date"],
            }
            records_by_card[read_key].append(implied_read_record)

    built_cards = {}
    # Build cards
    for char in unique_characters:
        for card_type in ["read", "write"]:
            card_key = (char, card_type)
            card_records = records_by_card.get(card_key, [])

            # Sort records by date before replaying
            card_records.sort(key=lambda r: r["date"])

            scheduler = read_scheduler if card_type == "read" else write_scheduler

            card = Card()
            if card_records:
                for record in card_records:
                    rating = score_to_rating(record["score"])
                    review_time = datetime.datetime.strptime(
                        record["date"], "%Y-%m-%d"
                    ).replace(tzinfo=datetime.timezone.utc)
                    card, _ = scheduler.review_card(card, rating, review_time)

            built_cards[card_key] = card
    return built_cards


def rebuild_cards_from_records(conn):
    # Get lesson range from settings
    settings = conn.execute("SELECT * FROM settings").fetchall()
    settings_dict = {s["key"]: s["value"] for s in settings}
    lesson_range_str = settings_dict.get("lesson_range", "1-10")

    # Get all characters from the specified lessons
    lesson_numbers = words.parse_lesson_ranges(lesson_range_str)
    characters = []
    for num in lesson_numbers:
        lesson_chars = words.get_lesson(num)
        if lesson_chars:
            characters.extend(list(lesson_chars))
    unique_characters = sorted(list(set(characters)))

    if not unique_characters:
        print("No characters found for the specified lesson range.")
        return

    # Fetch all records.
    query = "SELECT * FROM records ORDER BY date"
    all_records = conn.execute(query).fetchall()

    built_cards = build_cards(unique_characters, all_records)
    cards.clear()
    cards.update(built_cards)

    for (char, card_type), card in cards.items():
        # Persist the final card state
        conn.execute(
            "INSERT OR REPLACE INTO cards (character, type, card_data) VALUES (?, ?, ?)",
            (char, card_type, json.dumps(card.to_dict())),
        )

    print("FSRS cards rebuilt from records.")

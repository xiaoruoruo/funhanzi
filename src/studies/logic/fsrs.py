import datetime
from fsrs import Scheduler, Card, Rating

read_scheduler = Scheduler(desired_retention=0.9)
write_scheduler = Scheduler(desired_retention=0.6)


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


def build_cards_from_logs(all_study_logs):
    """
    Build FSRS cards from study logs in a single-user system.
    This function takes simple StudyLog records and calculates the current FSRS state in memory.
    
    Args:
        all_study_logs: List of StudyLog records to use for building cards
    
    Returns:
        Dictionary mapping (character, type) tuples to Card objects
    """
    # Get unique characters from the study logs
    unique_characters = sorted(list(set(log.word.hanzi for log in all_study_logs)))
    
    # Group study logs by card (character, type), adding implied read records
    records_by_card = {}
    for log in all_study_logs:
        char = log.word.hanzi
        record_type = log.type
        score = log.score

        # Add the original record
        key = (char, record_type)
        if key not in records_by_card:
            records_by_card[key] = []
        records_by_card[key].append({
            'character': char,
            'type': record_type,
            'score': score,
            'date': log.study_date
        })

        # If it's a write record, add an implied read record
        if record_type == "write":
            read_key = (char, "read")
            if read_key not in records_by_card:
                records_by_card[read_key] = []

            implied_read_record = {
                "character": char,
                "type": "read",
                "score": min(score + 3, 10),  # Limit to 10
                "date": log.study_date,
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
                    review_time = datetime.datetime.combine(
                        record["date"], 
                        datetime.datetime.min.time()
                    ).replace(tzinfo=datetime.timezone.utc)
                    card, _ = scheduler.review_card(card, rating, review_time)

            built_cards[card_key] = card
    return built_cards

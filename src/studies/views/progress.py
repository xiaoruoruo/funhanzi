import logging
from django.shortcuts import render
from studies.models import StudyLog
from django.db.models import Window
from django.db.models.functions import RowNumber
from django.utils import timezone
from ..logic import fsrs
import pytz
from datetime import timedelta, date, datetime
from collections import defaultdict

# Get an instance of a logger
logger = logging.getLogger(__name__)

def progress_view(request):
    """
    View function for the progress page, replicating the logic from the original Flask app.
    """
    # Use Django ORM with window functions to get the last 3 records per character-type
    ranked_study_logs = StudyLog.objects.filter(
        type__in=['read', 'write']
    ).select_related('word').annotate(
        rn=Window(
            expression=RowNumber(),
            partition_by=['word__hanzi', 'type'],
            order_by=['-study_date']
        )
    ).filter(rn__lte=3).order_by('word__hanzi', 'type', 'study_date')

    logger.info(f"Found {ranked_study_logs.count()} ranked study logs.")
    for log in ranked_study_logs[:5]:
        logger.info(f"  - Char: {log.word.hanzi}, Type: {log.type}, Score: {log.score}, Date: {log.study_date}")

    progress_data = {}
    
    # Pre-populate structure for logs
    for log in ranked_study_logs:
        char = log.word.hanzi
        if char not in progress_data:
            progress_data[char] = {
                "read": {"records": [], "retrievability": "N/A", "due_in_days": "N/A"},
                "write": {"records": [], "retrievability": "N/A", "due_in_days": "N/A"},
            }

        record_type = log.type
        local_tz = pytz.timezone('America/Los_Angeles')
        local_now = timezone.now().astimezone(local_tz)
        days_ago = (local_now.date() - log.study_date).days

        score = log.score
        rating = fsrs.score_to_rating(score if score is not None else 0)
        color = fsrs.RATING_TO_COLOR.get(rating, "")

        progress_data[char][record_type]["records"].append(
            {"days_ago": days_ago, "color": color}
        )

    try:
        from ..logic import stats
        study_logs = StudyLog.objects.filter(
            type__in=['read', 'write']
        ).select_related('word')
        fsrs_cards = fsrs.build_cards_from_logs(list(study_logs))
        
        # Calculate stats using shared logic
        char_stats = stats.calculate_character_stats(fsrs_cards, local_now)

        # Merge stats into progress_data
        for char, data in char_stats.items():
            if char in progress_data:
                if data["read"]["retrievability_str"] != "N/A":
                    progress_data[char]["read"]["retrievability"] = data["read"]["retrievability_str"]
                if data["read"]["due_in_days_str"] != "N/A":
                    progress_data[char]["read"]["due_in_days"] = data["read"]["due_in_days_str"]
                
                if data["write"]["retrievability_str"] != "N/A":
                    progress_data[char]["write"]["retrievability"] = data["write"]["retrievability_str"]
                if data["write"]["due_in_days_str"] != "N/A":
                    progress_data[char]["write"]["due_in_days"] = data["write"]["due_in_days_str"]

    except Exception as e:
        logger.error(f"Error in FSRS processing: {e}")
        pass
    
    return render(request, 'studies/progress.html', {'progress_data': progress_data})


def stats_view(request):
    
    # Fetch all records ordered by date (no user filter)
    all_study_logs = StudyLog.objects.order_by('study_date')
    
    if not all_study_logs:
        return render(request, 'studies/stats.html', {'stats': []})

    # Group all records by month to identify months to process
    records_by_month = defaultdict(list)
    all_chars_in_records = set()
    
    # Convert StudyLog objects to dictionaries similar to the original format
    all_records = []
    for log in all_study_logs:
        record_dict = {
            'character': log.word.hanzi,
            'type': log.type,
            'score': log.score,
            'date': log.study_date.strftime('%Y-%m-%d')
        }
        all_records.append(record_dict)
        month_str = log.study_date.strftime('%Y-%m')  # Format like '2025-10'
        records_by_month[month_str].append(record_dict)
        all_chars_in_records.add(log.word.hanzi)

    all_chars_in_records = sorted(list(all_chars_in_records))

    # Identify the date range from first record to last record
    first_date = all_study_logs.first().study_date
    last_date = all_study_logs.last().study_date

    # Generate all months between first and last date
    current_date = date(first_date.year, first_date.month, 1)
    end_date = date(last_date.year, last_date.month, 1)
    months_to_process = []

    while current_date <= end_date:
        months_to_process.append(current_date.strftime('%Y-%m'))
        # Move to next month
        if current_date.month == 12:
            current_date = date(current_date.year + 1, 1, 1)
        else:
            current_date = date(current_date.year, current_date.month + 1, 1)

    # Initialize FSRS schedulers
    read_scheduler = fsrs.read_scheduler
    write_scheduler = fsrs.write_scheduler

    monthly_stats = []
    cumulative_chars = set()

    for month in months_to_process:
        year = int(month[:4])
        month_num = int(month[5:7])
        
        # Calculate the last day of the current month
        if month_num == 12:
            next_month_first_day = date(year + 1, 1, 1)
        else:
            next_month_first_day = date(year, month_num + 1, 1)
        last_day_of_month = next_month_first_day - timedelta(days=1)
        month_end_date_str = last_day_of_month.strftime('%Y-%m-%d')

        # Filter records up to the end of the current month
        historical_records = [r for r in all_records if r['date'] <= month_end_date_str]

        # Build cards using the historical records up to month end
        # Create a temporary function to build cards from historical records similar to the original
        fsrs_cards = build_fsrs_cards_from_records(historical_records, all_chars_in_records)

        # Update cumulative unique characters
        for record in historical_records:
            cumulative_chars.add(record['character'])

        # Calculate retrievability and categorize at the end of the month
        read_mastered, read_learning, read_lapsing = 0, 0, 0
        write_mastered, write_learning, write_lapsing = 0, 0, 0

        # Calculate FSRS retrievability as of the end of the month
        calculation_time = datetime.combine(
            last_day_of_month, datetime.max.time()
        ).replace(tzinfo=pytz.UTC)

        for char in cumulative_chars:
            # Read card
            read_card = fsrs_cards.get((char, "read"))
            if read_card:
                r = read_scheduler.get_card_retrievability(read_card, calculation_time)
                if r is not None:
                    r = float(r)
                    if r > 0.9:
                        read_mastered += 1
                    elif r >= 0.6:
                        read_learning += 1
                    else:
                        read_lapsing += 1

            # Write card
            write_card = fsrs_cards.get((char, "write"))
            if write_card:
                r = write_scheduler.get_card_retrievability(write_card, calculation_time)
                if r is not None:
                    r = float(r)
                    if r > 0.9:
                        write_mastered += 1
                    elif r >= 0.6:
                        write_learning += 1
                    else:
                        write_lapsing += 1

        # Count reviews and studies specifically for the current month
        month_records = records_by_month.get(month, [])
        reviews_this_month = sum(1 for r in month_records if r['type'] in ['read', 'write'])
        studies_this_month = sum(1 for r in month_records if r['type'] in ['readstudy', 'writestudy'])

        stats = {
            'month': month,  # Keep in YYYY-MM format to match Flask
            'total_reviews': reviews_this_month,
            'total_studies': studies_this_month,
            'cumulative_unique_chars': len(cumulative_chars),
            'read_mastered': read_mastered,
            'read_learning': read_learning,
            'read_lapsing': read_lapsing,
            'write_mastered': write_mastered,
            'write_learning': write_learning,
            'write_lapsing': write_lapsing,
        }
        monthly_stats.append(stats)

    # Return sorted in reverse order (newest first), like in Flask
    return render(request, 'studies/stats.html', {'stats': sorted(monthly_stats, key=lambda x: x["month"], reverse=True)})


def build_fsrs_cards_from_records(historical_records, all_chars_in_records):
    """
    Build FSRS cards from historical records, replicating the logic from the original Flask app
    """
    from ..logic.fsrs import read_scheduler, write_scheduler, score_to_rating
    from fsrs import Card
    
    # Group records by (character, type)
    records_by_card = {}
    for record in historical_records:
        char = record['character']
        record_type = record['type']
        score = record['score']

        # Add the original record
        key = (char, record_type)
        if key not in records_by_card:
            records_by_card[key] = []
        records_by_card[key].append({
            'character': char,
            'type': record_type,
            'score': score,
            'date': record['date']
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
                "date": record['date'],
            }
            records_by_card[read_key].append(implied_read_record)

    built_cards = {}
    # Build cards
    for char in all_chars_in_records:
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
                    review_date = datetime.strptime(record["date"], "%Y-%m-%d")
                    review_time = datetime.combine(
                        review_date.date(), 
                        datetime.min.time()
                    ).replace(tzinfo=datetime.timezone.utc)
                    card, _ = scheduler.review_card(card, rating, review_time)

            built_cards[card_key] = card
    return built_cards

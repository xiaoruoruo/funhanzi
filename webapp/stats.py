"""Provide a historical overview of learning progress, with data aggregated by month.
-   **Month:** The year and month (e.g., 2025-10, 2025-09).
-   **Total Reviews This Month:** The number of `read` or `write` reviews logged *during* that specific month. This shows exam activity for the period.
-   **Total Studies This Month:** The number of `readstudy` or `writestudy` records logged *during* that specific month. This shows study sheet activity for the period.
-   **Cumulative Unique Chars:** The total count of unique characters ever studied up to the end of that month.
-   **Read - Mastered (>90%):** The number of characters with a `read` retrievability over 90% at the end of that month.
-   **Read - Learning (60-90%):** The number of characters with a `read` retrievability between 60% and 90% at the end of that month.
-   **Read - Lapsing (<60%):** The number of characters with a `read` retrievability below 60% at the end of that month.
-   **Write - Mastered (>90%):** The number of characters with a `write` retrievability over 90% at the end of that month.
-   **Write - Learning (60-90%):** The number of characters with a `write` retrievability between 60% and 90% at the end of that month.
-   **Write - Lapsing (<60%):** The number of characters with a `write` retrievability below 60% at the end of that month.
"""

import datetime
from collections import defaultdict
from fsrs import Scheduler

from . import db
from . import fsrs_logic


def calculate_monthly_stats():
    conn = db.get_db_connection()

    # 1. Fetch All Records
    all_records = conn.execute("SELECT * FROM records ORDER BY date").fetchall()
    if not all_records:
        return []

    # Get all unique characters from the records
    all_chars_in_records = sorted(list(set(r["character"] for r in all_records)))

    # 2. Group Records by Month
    records_by_month = defaultdict(list)
    for record in all_records:
        month_str = record["date"][:7]  # YYYY-MM
        records_by_month[month_str].append(record)

    # 3. Iterate Chronologically
    start_date = datetime.datetime.strptime(all_records[0]["date"], "%Y-%m-%d")
    end_date = datetime.datetime.strptime(all_records[-1]["date"], "%Y-%m-%d")

    current_date = start_date
    months_to_process = []
    while current_date <= end_date:
        months_to_process.append(current_date.strftime("%Y-%m"))
        # Move to the first day of the next month
        if current_date.month == 12:
            current_date = current_date.replace(
                year=current_date.year + 1, month=1, day=1
            )
        else:
            current_date = current_date.replace(month=current_date.month + 1, day=1)

    monthly_stats = []
    cumulative_chars = set()

    for month in sorted(months_to_process):
        year = int(month[:4])
        month_num = int(month[5:7])
        if month_num == 12:
            next_month_first_day = datetime.date(year + 1, 1, 1)
        else:
            next_month_first_day = datetime.date(year, month_num + 1, 1)
        last_day_of_month = next_month_first_day - datetime.timedelta(days=1)
        month_end_date_str = last_day_of_month.strftime("%Y-%m-%d")

        # Filter records up to the end of the current month
        historical_records = [r for r in all_records if r["date"] <= month_end_date_str]

        # 4a. Initialize fresh FSRS schedulers
        read_scheduler = Scheduler(desired_retention=0.9)
        write_scheduler = Scheduler(desired_retention=0.6)

        # 4b. Process historical records
        cards = fsrs_logic.build_cards(all_chars_in_records, historical_records)

        # Update cumulative unique characters
        for record in historical_records:
            cumulative_chars.add(record["character"])

        # Calculate retrievability and categorize
        read_mastered, read_learning, read_lapsing = 0, 0, 0
        write_mastered, write_learning, write_lapsing = 0, 0, 0

        calculation_time = datetime.datetime.combine(
            last_day_of_month, datetime.datetime.max.time()
        ).replace(tzinfo=datetime.timezone.utc)

        for char in cumulative_chars:
            # Read card
            read_card = cards.get((char, "read"))
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
            write_card = cards.get((char, "write"))
            if write_card:
                r = write_scheduler.get_card_retrievability(
                    write_card, calculation_time
                )
                if r is not None:
                    r = float(r)
                    if r > 0.9:
                        write_mastered += 1
                    elif r >= 0.6:
                        write_learning += 1
                    else:
                        write_lapsing += 1

        # Count reviews and studies for the current month
        reviews_this_month = 0
        studies_this_month = 0
        month_records = records_by_month.get(month, [])
        for record in month_records:
            if record["type"] in ["read", "write"]:
                reviews_this_month += 1
            elif record["type"] in ["readstudy", "writestudy"]:
                studies_this_month += 1

        stats = {
            "month": month,
            "total_reviews": reviews_this_month,
            "total_studies": studies_this_month,
            "cumulative_unique_chars": len(cumulative_chars),
            "read_mastered": read_mastered,
            "read_learning": read_learning,
            "read_lapsing": read_lapsing,
            "write_mastered": write_mastered,
            "write_learning": write_learning,
            "write_lapsing": write_lapsing,
        }
        monthly_stats.append(stats)

    conn.close()
    return sorted(monthly_stats, key=lambda x: x["month"], reverse=True)

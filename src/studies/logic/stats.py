from . import fsrs
from . import selection
import logging

logger = logging.getLogger(__name__)

def calculate_character_stats(fsrs_cards, local_now):
    """
    Calculate detailed stats for each character based on FSRS cards.
    """
    stats_data = {}

    # Get hard mode words for read and write
    s = selection.Selection()
    read_hard_words = {w.hanzi for w in s.get_hard_mode_words('read')}
    write_hard_words = {w.hanzi for w in s.get_hard_mode_words('write')}

    for (char, card_type), card in fsrs_cards.items():
        if char not in stats_data:
            stats_data[char] = {
                "read": {"retrievability": None, "due_in_days": None, "retrievability_str": "N/A", "due_in_days_str": "N/A", "is_hard_mode": False},
                "write": {"retrievability": None, "due_in_days": None, "retrievability_str": "N/A", "due_in_days_str": "N/A", "is_hard_mode": False},
            }
        
        is_hard = False
        if card_type == "read" and char in read_hard_words:
            is_hard = True
        elif card_type == "write" and char in write_hard_words:
            is_hard = True

        stats_data[char][card_type]["is_hard_mode"] = is_hard

        try:
            scheduler = fsrs.read_scheduler if card_type == "read" else fsrs.write_scheduler
            retrievability_val = scheduler.get_card_retrievability(card, local_now)
            
            if retrievability_val is not None:
                stats_data[char][card_type]["retrievability"] = float(retrievability_val)
                if not is_hard:
                    stats_data[char][card_type]["retrievability_str"] = f"{float(retrievability_val) * 100:.2f}%"
                else:
                    stats_data[char][card_type]["retrievability_str"] = "Hard"
            
            if hasattr(card, 'due') and card.due:
                due_in_days = (card.due - local_now).days
                due_in_days = (card.due - local_now).days
                stats_data[char][card_type]["due_in_days"] = due_in_days
                
                if is_hard:
                    stats_data[char][card_type]["retrievability_str"] = "Hard"
                    stats_data[char][card_type]["due_in_days_str"] = "Hard"
                else:
                    stats_data[char][card_type]["retrievability_str"] = f"{float(retrievability_val) * 100:.2f}%"
                    stats_data[char][card_type]["due_in_days_str"] = due_in_days

                
        except Exception as e:
            logger.error(f"Error processing FSRS card for {char} ({card_type}): {e}")
            pass
            
    return stats_data

def aggregate_lesson_stats(character_stats, lesson_chars):
    """
    Aggregate stats for a list of characters (e.g. from a lesson).
    Returns counts for Mastered, Learning, Lapsing.
    """
    aggregated = {
        "read": {"mastered": 0, "learning": 0, "lapsing": 0, "hard": 0, "total": 0},
        "write": {"mastered": 0, "learning": 0, "lapsing": 0, "hard": 0, "total": 0}
    }
    
    for char in lesson_chars:
        if char not in character_stats:
            continue
            
        for card_type in ["read", "write"]:
            r = character_stats[char][card_type]["retrievability"]
            is_hard = character_stats[char][card_type].get("is_hard_mode", False)
            
            if r is not None:
                aggregated[card_type]["total"] += 1
                
                if is_hard:
                    aggregated[card_type]["hard"] += 1
                elif r > 0.9:
                    aggregated[card_type]["mastered"] += 1
                elif r >= 0.6:
                    aggregated[card_type]["learning"] += 1
                else:
                    aggregated[card_type]["lapsing"] += 1
                    
    return aggregated


def calculate_recent_history(all_study_logs, local_now):
    """
    Calculate recent study history (last 3 reviews) for each character.
    Returns: dict[char][type] -> list of {days_ago, color}
    """
    history_data = {}
    
    # Process logs in memory. Assuming all_study_logs is a list or QuerySet.
    # We need them sorted by date desc for "recent". 
    # Can't assume input is sorted.
    
    # Group by (char, type)
    from collections import defaultdict
    logs_by_key = defaultdict(list)
    
    for log in all_study_logs:
        logs_by_key[(log.word.hanzi, log.type)].append(log)
        
    for (char, record_type), logs in logs_by_key.items():
        if char not in history_data:
            history_data[char] = {
                "read": [],
                "write": []
            }
        
        # Sort logs by date descending and take top 3
        logs.sort(key=lambda x: x.study_date, reverse=True)
        recent_logs = logs[:3]
        
        records_list = []
        for log in recent_logs:
            days_ago = (local_now.date() - log.study_date).days
            rating = fsrs.score_to_rating(log.score if log.score is not None else 0)
            color = fsrs.RATING_TO_COLOR.get(rating, "")
            records_list.append({"days_ago": days_ago, "color": color})
            
        # User wants chronological order (Oldest -> Newest) for the display
        # We fetched newest first (to get top 3), so we reverse now.
        records_list.reverse()
        history_data[char][record_type] = records_list
            
    return history_data

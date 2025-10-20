#!/usr/bin/env python3
"""
Test script to verify the Selection class functionality, including the new from_failed_records method.
"""
import sys
import os

# Add the parent directory to the path so we can import webapp modules
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from webapp.selection import Selection
from webapp import fsrs_logic
from webapp.db import get_db_connection

def test_selection_api():
    """Test the Selection API with various scenarios."""
    print("Testing Selection API...")
    
    # Initialize FSRS cards first (required for FSRS operations)
    print("Initializing FSRS cards...")
    conn = get_db_connection()
    fsrs_logic.rebuild_cards_from_records(conn)
    
    # Test 1: Basic lesson range selection
    print("\n1. Testing from_lesson_range...")
    s = Selection(conn)
    chars = s.from_lesson_range("1-10").get_all()
    print(f"Characters from lessons 1-10: {chars[:10]}... (showing first 10)")
    
    # Test 2: Lesson range with random selection
    print("\n2. Testing from_lesson_range with random(5)...")
    s2 = Selection(conn)
    random_chars = s2.from_lesson_range("1-5").random(5)
    print(f"Random 5 characters from lessons 1-5: {random_chars}")
    
    # Test 3: FSRS selection (read cards)
    print("\n3. Testing from_fsrs for read cards...")
    s3 = Selection(conn)
    fsrs_chars = s3.from_fsrs("read").take(5)
    print(f"First 5 read FSRS cards: {fsrs_chars}")
    
    # Test 4: FSRS selection due only
    print("\n4. Testing from_fsrs for write cards due only...")
    s4 = Selection(conn)
    due_chars = s4.from_fsrs("write", due_only=True).get_all()
    print(f"Due write cards: {due_chars}")
    
    # Test 5: Chain with filters (example from docs)
    print("\n5. Testing chained operations (Write Exam example)...")
    try:
        s5 = Selection(conn)
        selected_chars = s5.from_lesson_range("1-10") \
            .remove_recent_records_by_type(3, ['read', 'write']) \
            .remove_score_greater("write", 5) \
            .random(10)
        print(f"Filtered characters (Write Exam example): {selected_chars}")
    except Exception as e:
        print(f"Error in chained operations: {e}")
    
    # Test 6: Chain with FSRS and lowest retrievability (Study Sheet review)
    print("\n6. Testing FSRS with lowest retrievability (Study Sheet review example)...")
    try:
        s6 = Selection(conn)
        review_chars = s6.from_fsrs("write") \
            .lowest_retrievability() \
            .remove_recent_records_by_type(1, ['readstudy', 'writestudy']) \
            .take(5)
        print(f"Review characters (lowest retrievability): {review_chars}")
    except Exception as e:
        print(f"Error in FSRS with retrievability: {e}")
    
    # Test 7: New from_failed_records method
    print("\n7. Testing from_failed_records...")
    try:
        from datetime import date, timedelta
        cutoff_date = (date.today() - timedelta(days=30)).isoformat()  # Last 30 days
        s7 = Selection(conn)
        failed_chars = s7.from_failed_records("write", cutoff_date, threshold=5).get_all()
        print(f"Characters with write score < 5 in the last 30 days: {failed_chars}")
    except Exception as e:
        print(f"Error in from_failed_records: {e}")
    
    conn.close()
    print("\nAll tests completed!")

if __name__ == "__main__":
    test_selection_api()
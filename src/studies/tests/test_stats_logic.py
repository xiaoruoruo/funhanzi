from django.test import TestCase
from django.utils import timezone
import datetime
from studies.logic import stats, fsrs
from fsrs import Card

class StatsLogicTest(TestCase):

    def test_calculate_character_stats(self):
        # Setup mock data
        local_now = timezone.now()
        
        # Mock FSRS cards
        test_card = Card()
        test_card.due = local_now + datetime.timedelta(days=2) # Due below
        
        # We need to simulate retrievability. 
        # Since we can't easily mock the FSRS internal calculation without a lot of setup,
        # we will rely on the fact that a new card has some retrievability or use a known state.
        # But simpler: we just test that the function handles the card object and returns the structured data.
        
        fsrs_cards = {
            ("你", "read"): test_card,
            ("你", "write"): test_card,
        }
        
        # Calculate stats
        result = stats.calculate_character_stats(fsrs_cards, local_now)
        
        # Assertions
        self.assertIn("你", result)
        self.assertIn("read", result["你"])
        self.assertIn("write", result["你"])
        
        # Check due days
        self.assertEqual(result["你"]["read"]["due_in_days"], 2)
        self.assertEqual(result["你"]["write"]["due_in_days"], 2)
        
        # Retrievability should be present (exact value depends on FSRS defaults, but not None)
        self.assertIsNotNone(result["你"]["read"]["retrievability"])
        self.assertTrue(0 <= result["你"]["read"]["retrievability"] <= 1)

    def test_aggregate_lesson_stats(self):
        # Setup mock character stats
        character_stats = {
            "A": {
                "read": {"retrievability": 0.95}, # Mastered
                "write": {"retrievability": 0.8}, # Learning
            },
            "B": {
                "read": {"retrievability": 0.5}, # Lapsing
                "write": {"retrievability": 0.95}, # Mastered
            },
            "C": {
                "read": {"retrievability": None}, # No data
                "write": {"retrievability": None},
            }
        }
        
        lesson_chars = ["A", "B", "C", "D"] # D is missing from stats
        
        # Aggregate
        result = stats.aggregate_lesson_stats(character_stats, lesson_chars)
        
        # Assertions for Read
        self.assertEqual(result["read"]["mastered"], 1) # A
        self.assertEqual(result["read"]["learning"], 0)
        self.assertEqual(result["read"]["lapsing"], 1) # B
        self.assertEqual(result["read"]["total"], 2) # A + B (C has None, D missing)
        
        # Assertions for Write
        self.assertEqual(result["write"]["mastered"], 1) # B
        self.assertEqual(result["write"]["learning"], 1) # A
        self.assertEqual(result["write"]["lapsing"], 0)
        self.assertEqual(result["write"]["total"], 2)

import unittest
import datetime
from fsrs import State
import fsrs_logic


class TestFsrsLogic(unittest.TestCase):
    def test_build_cards(self):
        # Test data extracted from the database
        unique_characters = ["在", "说", "九", "新"]
        all_records = [
            {
                "id": 1,
                "date": "2025-08-23",
                "character": "在",
                "type": "read",
                "score": 10,
            },
            {
                "id": 2,
                "date": "2025-08-23",
                "character": "说",
                "type": "write",
                "score": 10,
            },
            {
                "id": 3,
                "date": "2025-08-23",
                "character": "九",
                "type": "read",
                "score": 10,
            },
            {
                "id": 51,
                "date": "2025-08-23",
                "character": "九",
                "type": "write",
                "score": 10,
            },
        ]

        # Run the card building logic
        built_cards = fsrs_logic.build_cards(unique_characters, all_records)
        review_date = datetime.datetime.strptime("2025-08-23", "%Y-%m-%d").replace(
            tzinfo=datetime.timezone.utc
        )

        # --- Assertions ---

        # 1. Check if all cards were created
        self.assertEqual(len(built_cards), 8)  # 4 chars * 2 types

        # 2. Check the '在' read card (simple case)
        zai_read_card = built_cards[("在", "read")]
        self.assertEqual(zai_read_card.state, State.Review)
        days = (zai_read_card.due - review_date).days
        self.assertTrue(10 <= days <= 20, msg=days)

        # 3. Check the '九' write card (simple case)
        jiu_write_card = built_cards[("九", "write")]
        self.assertEqual(jiu_write_card.state, State.Review)
        days = (jiu_write_card.due - review_date).days
        self.assertTrue(250 <= days <= 300, msg=days)

        # 4. Check the '九' read card (implied record)
        # This card should have two reviews: one from the original 'read' record
        # and one implied from the 'write' record.
        jiu_read_card = built_cards[("九", "read")]
        self.assertEqual(jiu_read_card.state, State.Review)
        days = (jiu_read_card.due - review_date).days
        self.assertTrue(25 <= days <= 35, msg=days)

        # 5. Check a card with no read records
        shuo_read_card = built_cards[("说", "read")]
        self.assertEqual(shuo_read_card.state, State.Review)
        days = (shuo_read_card.due - review_date).days
        self.assertTrue(10 <= days <= 20, msg=days)
        shuo_write_card = built_cards[("说", "write")]
        self.assertEqual(shuo_write_card.state, State.Review)
        days = (shuo_write_card.due - review_date).days
        self.assertTrue(250 <= days <= 300, msg=days)

        # 6. Check a card with no read/write records
        xin_write_card = built_cards[("新", "write")]
        self.assertEqual(xin_write_card.state, State.Learning)
        days = (xin_write_card.due - review_date).days
        self.assertTrue(1 <= days <= 10, msg=days)
        xin_read_card = built_cards[("新", "read")]
        self.assertEqual(xin_read_card.state, State.Learning)
        days = (xin_read_card.due - review_date).days
        self.assertTrue(1 <= days <= 10, msg=days)


if __name__ == "__main__":
    unittest.main()

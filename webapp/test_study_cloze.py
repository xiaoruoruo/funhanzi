import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add the parent directory to the path so we can import webapp modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from webapp.study_cloze import generate_content, ClozeEntry


class TestStudyCloze(unittest.TestCase):
    """
    Unit tests for the study_cloze module.
    These tests use mock database data but call the real gemini API.
    """

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Mock database connection
        self.mock_conn = Mock()

        # Mock lesson characters - using a reasonable set of characters
        self.lesson_chars = [
            "黑",
            "得",
            "再",
            "星",
            "鸡",
            "一",
            "二",
            "三",
            "四",
            "五",
            "六",
            "七",
            "八",
            "九",
            "十",
            "人",
            "大",
            "小",
            "多",
            "少",
        ]

        # Characters to test with as specified in the requirements
        self.test_characters = ["黑", "得", "再", "星", "鸡"]

    @patch("webapp.study_cloze.words_gen")
    def test_generate_content_with_real_gemini_api(self, mock_words_gen):
        """
        Test generate_content function with mock database data but real gemini API.
        Uses the provided test case: characters='黑得再星鸡'
        """
        # Mock the words_gen.generate_words_max_score function to return a predictable set of words
        expected_words = ["黑夜", "得到", "再次", "星星", "鸡蛋"]
        mock_words_gen.generate_words_max_score.return_value = expected_words

        # Call the function with real gemini API (no patching of ai module)
        result = generate_content(conn=self.mock_conn, characters=self.test_characters)

        # Print the generated sentences
        print("\nGenerated sentences:")
        for i, entry in enumerate(result, 1):
            print(f"{i}. {entry.cloze_sentence} (Word: {entry.word})")

        # Assertions
        self.assertIsInstance(result, list)
        self.assertEqual(len(result), 5)  # Should return up to 5 entries

        for entry in result:
            self.assertIsInstance(entry, ClozeEntry)
            # Check that sentence contains the blank '（ ）'
            self.assertIn("（ ）", entry.cloze_sentence)
            # Check that word is part of the expected words
            self.assertIn(entry.word, expected_words)

        # Verify that the mock was called correctly
        mock_words_gen.generate_words_max_score.assert_called_once_with(
            self.mock_conn, self.test_characters
        )

    @patch("webapp.study_cloze.words_gen")
    def test_generate_content_with_fallback_on_api_error(self, mock_words_gen):
        """
        Test that the function handles API errors gracefully by returning fallback content.
        """
        # Mock the words_gen.generate_words_max_score function to return a predictable set of words
        expected_words = ["黑夜", "得到", "再次", "星星", "鸡蛋"]
        mock_words_gen.generate_words_max_score.return_value = expected_words

        # Mock the genai API call to simulate API failure
        with patch("webapp.study_cloze.genai.Client") as mock_client:
            # Set up the mock to raise an exception when generating content
            mock_client.return_value.models.generate_content.side_effect = Exception(
                "API Error"
            )

            result = generate_content(
                conn=self.mock_conn, characters=self.test_characters
            )

            # Should return fallback content
            self.assertIsInstance(result, list)
            self.assertEqual(len(result), 5)

            for entry in result:
                self.assertIsInstance(entry, ClozeEntry)
                self.assertEqual(entry.word, "错误")
                self.assertEqual(entry.cloze_sentence, "无法生成句子")


if __name__ == "__main__":
    unittest.main()

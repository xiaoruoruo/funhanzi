#!/usr/bin/env python3
"""
Unit tests for the words_gen module methods using mocks.
"""
import unittest
from unittest.mock import Mock, patch, MagicMock
from webapp import words_gen, fsrs_logic

class TestGenerateExamWords(unittest.TestCase):
    """
    Test cases for the generate_exam_words function in words_gen module.
    """
    
    def setUp(self):
        """
        Set up mock database connection and test data for each test.
        """
        # Create a mock database connection
        self.mock_conn = Mock()

    @patch('webapp.words_gen.get_words_for_char')
    def test_generate_exam_words_basic_functionality(self, mock_get_words_for_char):
        def mock_get_words_for_char_side_effect(conn, char):
            if char == '人':
                return [('人口', 0.8), ('人民', 0.9)]
            elif char == '口':
                return [('人口', 0.6), ('开口', 0.7)]
            elif char == '大':
                return [('大人', 0.7), ('广大', 0.8)]
            else:
                return [('单字', 0.5)]  # should not happen
        
        mock_get_words_for_char.side_effect = mock_get_words_for_char_side_effect
        
        test_characters = ['人', '口', '大']

        # Call the function
        result = words_gen.generate_exam_words(self.mock_conn, test_characters)
        
        # Print the result words
        print(f"result: {result}")

        self.assertListEqual(result, ['人口', '大'])        


class TestGenerateWordsMaxScore(unittest.TestCase):
    """
    Test cases for the generate_words_max_score function in words_gen module.
    """
    
    def setUp(self):
        """
        Set up mock database connection and test data for each test.
        """
        # Create a mock database connection
        self.mock_conn = Mock()

    @patch('webapp.words_gen.get_words_for_char')
    @patch('webapp.fsrs_logic.cards', {})
    @patch('webapp.fsrs_logic.read_scheduler')
    def test_generate_words_max_score_basic_functionality(self, mock_scheduler, mock_get_words_for_char):
        """Test the basic functionality of generate_words_max_score."""
        # Mock the FSRS cards and their retrievability scores
        mock_card1 = Mock()
        mock_card2 = Mock()
        mock_card3 = Mock()
        
        # Set up the mock scheduler's get_card_retrievability method
        def mock_get_retrievability(card, date):
            if card == mock_card1:
                return 90.0  # character '人' has retrievability of 90
            elif card == mock_card2:
                return 60.0  # character '口' has retrievability of 60
            elif card == mock_card3:
                return 80.0  # character '大' has retrievability of 80
            return 0.0
        
        mock_scheduler.get_card_retrievability.side_effect = mock_get_retrievability
        
        # Add cards to the fsrs_logic.cards dictionary
        fsrs_logic.cards = {
            ('人', 'read'): mock_card1,
            ('口', 'read'): mock_card2,
            ('大', 'read'): mock_card3
        }
        
        def mock_get_words_for_char_side_effect(conn, char):
            if char == '人':
                return [('人口', 0.8), ('人大', 0.9)]
            elif char == '口':
                return [('人口', 0.6), ('开口', 0.7)]
            elif char == '大':
                return [('大人', 0.7), ('大口', 0.8)]
            else:
                return [('单字', 0.5)]
        
        mock_get_words_for_char.side_effect = mock_get_words_for_char_side_effect
        
        test_characters = ['人', '口', '大']
        
        # Call the function
        result = words_gen.generate_words_max_score(self.mock_conn, test_characters)
        
        # Print the result for debugging
        print(f"result: {result}")
        
        self.assertListEqual(result, ['人大', '人口', '大人'])


if __name__ == '__main__':
    unittest.main()
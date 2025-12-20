from django.test import TestCase
from unittest.mock import patch, MagicMock
from studies.logic.logic import create_ch_en_matching_study

class ChEnMatchingStudyTest(TestCase):
    @patch('studies.logic.study_ch_en_matching.words_gen.generate_words_max_score')
    @patch('studies.logic.study_ch_en_matching.genai.Client')
    def test_create_ch_en_matching_study(self, mock_genai_client, mock_generate_words):
        # Mock the word generation to return a fixed list of words
        mock_generate_words.return_value = ['你好', '谢谢', '再见', '早上好']

        # Mock the Gemini API response
        mock_translations = [
            MagicMock(chinese_word='你好', english_translation='Hello'),
            MagicMock(chinese_word='谢谢', english_translation='Thank you'),
            MagicMock(chinese_word='再见', english_translation='Goodbye'),
            MagicMock(chinese_word='早上好', english_translation='Good morning')
        ]

        mock_response = MagicMock()
        mock_response.parsed = MagicMock(translations=mock_translations)

        mock_genai_instance = MagicMock()
        mock_genai_instance.models.generate_content.return_value = mock_response
        mock_genai_client.return_value = mock_genai_instance

        # Call the function to be tested
        result = create_ch_en_matching_study(num_chars=4)

        # Assertions
        self.assertEqual(result['type'], 'ch_en_matching')
        self.assertIn('content', result)
        self.assertEqual(len(result['content']), 4)

        entry = result['content'][0]
        self.assertIn(entry['chinese_word'], ['你好', '谢谢', '再见', '早上好'])
        self.assertIn(entry['correct_translation'], ['Hello', 'Thank you', 'Goodbye', 'Good morning'])
        self.assertEqual(len(entry['options']), 4)

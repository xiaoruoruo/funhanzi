import unittest
import sqlite3
import os
import sys
import json
from unittest.mock import patch

# Add the project root to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from cli.find_words import generate_sentence_and_words

class TestFindWords(unittest.TestCase):

    def setUp(self):
        # Create a dummy database for testing
        self.db_path = 'test_records.db'
        self.conn = sqlite3.connect(self.db_path)
        self.c = self.conn.cursor()
        self.c.execute('''
            CREATE TABLE records (
                character TEXT,
                type TEXT,
                score INTEGER,
                date TEXT
            )
        ''')
        # Add some "learned" characters
        learned_chars = [('你', 'read', 10), ('好', 'read', 10), ('吗', 'write', 8)]
        for char, type, score in learned_chars:
            self.c.execute("INSERT INTO records (character, type, score, date) VALUES (?, ?, ?, date('now'))", (char, type, score))
        self.conn.commit()

    def tearDown(self):
        self.conn.close()
        os.remove(self.db_path)

    @patch('cli.find_words.get_db_connection')
    def test_sentence_with_learned_chars(self, mock_get_db_connection):
        # Mock the database connection to use the test database
        mock_get_db_connection.return_value = sqlite3.connect(self.db_path)

        study_chars = ['我', '是', '谁']
        learned_chars = ['你', '好', '吗']
        allowed_chars = set(study_chars + learned_chars)

        # Mock the Gemini API response
        mock_response = {
            "words": ["你好", "是我"],
            "sentence": "你好吗我是谁"
        }
        # Convert dict to a valid JSON string
        mock_json_response = json.dumps(mock_response)

        with patch('google.generativeai.GenerativeModel.generate_content') as mock_generate_content:
            # Configure the mock to return a specific structure
            mock_generate_content.return_value.text = f'```json\n{mock_json_response}\n```'

            words, sentence = generate_sentence_and_words(study_chars)

            # Check if all characters in the sentence are in the allowed set
            self.assertTrue(all(c in allowed_chars for c in sentence))
            self.assertLessEqual(len(sentence), 18)

if __name__ == '__main__':
    unittest.main()
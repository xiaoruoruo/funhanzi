"""Tests for Lesson model character cleaning on save."""

from django.test import TestCase
from studies.models import Book, Lesson


class LessonSavingTest(TestCase):
    """Test that lesson characters are cleaned when saving."""

    def setUp(self):
        """Create a test book."""
        self.book = Book.objects.create(title="Test Book", order=1)

    def test_comma_separated_with_duplicates(self):
        """Test that comma-separated characters with duplicates are cleaned."""
        lesson = Lesson.objects.create(
            book=self.book,
            lesson_num=1,
            characters="你,好,你,世,界,好"
        )
        # Should remove duplicates, preserving first occurrence order
        self.assertEqual(lesson.characters, "你,好,世,界")

    def test_comma_separated_with_whitespace(self):
        """Test that comma-separated characters with extra whitespace are cleaned."""
        lesson = Lesson.objects.create(
            book=self.book,
            lesson_num=2,
            characters=" 你 , 好 , 世 , 界 "
        )
        # Should remove whitespace around characters
        self.assertEqual(lesson.characters, "你,好,世,界")

    def test_whitespace_separated_with_duplicates(self):
        """Test that whitespace-separated characters with duplicates are cleaned."""
        lesson = Lesson.objects.create(
            book=self.book,
            lesson_num=3,
            characters="你 好 你 世 界 好"
        )
        # Should remove duplicates and convert to comma-separated
        self.assertEqual(lesson.characters, "你,好,世,界")

    def test_individual_characters_with_duplicates(self):
        """Test that individual characters (no separators) with duplicates are cleaned."""
        lesson = Lesson.objects.create(
            book=self.book,
            lesson_num=4,
            characters="你好你世界好"
        )
        # Should remove duplicates and convert to comma-separated
        self.assertEqual(lesson.characters, "你,好,世,界")

    def test_mixed_format_with_leading_trailing_whitespace(self):
        """Test that leading/trailing whitespace is removed."""
        lesson = Lesson.objects.create(
            book=self.book,
            lesson_num=5,
            characters="   你,好,世,界   "
        )
        # Should remove leading/trailing whitespace
        self.assertEqual(lesson.characters, "你,好,世,界")

    def test_update_existing_lesson(self):
        """Test that updating an existing lesson also cleans characters."""
        lesson = Lesson.objects.create(
            book=self.book,
            lesson_num=6,
            characters="你,好"
        )
        # Update with duplicates
        lesson.characters = "你,好,你,世,界,好"
        lesson.save()
        # Should remove duplicates
        self.assertEqual(lesson.characters, "你,好,世,界")

    def test_preserves_order_of_first_occurrence(self):
        """Test that the order of first occurrence is preserved."""
        lesson = Lesson.objects.create(
            book=self.book,
            lesson_num=7,
            characters="世,界,你,好,你,世"
        )
        # Should preserve the order: 世,界,你,好 (first occurrence)
        self.assertEqual(lesson.characters, "世,界,你,好")

    def test_empty_string_handling(self):
        """Test that empty strings are handled gracefully."""
        lesson = Lesson.objects.create(
            book=self.book,
            lesson_num=8,
            characters=""
        )
        # Should remain empty
        self.assertEqual(lesson.characters, "")

    def test_comma_separated_with_empty_entries(self):
        """Test that empty entries between commas are removed."""
        lesson = Lesson.objects.create(
            book=self.book,
            lesson_num=9,
            characters="你,,好,,世,界"
        )
        # Should remove empty entries
        self.assertEqual(lesson.characters, "你,好,世,界")

    def test_mixed_format_with_commas_and_spaces(self):
        """Test that mixed format (commas and spaces together) is handled correctly."""
        lesson = Lesson.objects.create(
            book=self.book,
            lesson_num=10,
            characters="你好, 世 界你"
        )
        # Should split into individual chars, remove all commas/spaces, remove duplicates
        self.assertEqual(lesson.characters, "你,好,世,界")

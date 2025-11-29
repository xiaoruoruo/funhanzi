from django.core.management.base import BaseCommand
from studies.models import Word, Book, Lesson
import os


class Command(BaseCommand):
    help = 'Import vocabulary from words.txt into the database'

    def add_arguments(self, parser):
        parser.add_argument(
            '--file',
            type=str,
            default='words.txt',
            help='Path to the words.txt file (default: words.txt)'
        )

    def handle(self, *args, **options):
        file_path = options['file']
        
        # Use the current working directory (project root) to locate words.txt
        import sys
        from pathlib import Path
        words_txt_path = Path.cwd() / file_path
        
        if not os.path.exists(words_txt_path):
            self.stdout.write(
                self.style.ERROR(f'File {words_txt_path} does not exist')
            )
            return

        # Read and parse the file
        lessons = []
        with open(words_txt_path, "r", encoding="utf-8") as f:
            for line_num, line in enumerate(f, 1):
                # remove any whitespace and store if not empty
                cleaned_line = "".join(line.split())
                if cleaned_line:
                    lessons.append(cleaned_line)

        # Ensure Book 1 exists
        book, _ = Book.objects.get_or_create(title="Book 1")

        # Import each lesson's characters
        total_imported = 0
        for lesson_num, lesson_content in enumerate(lessons, 1):
            # Update Lesson
            # lesson_content is a string of characters like "你好"
            # We want to store it as "你, 好"
            chars_list = list(lesson_content)
            chars_str = ", ".join(chars_list)
            
            Lesson.objects.update_or_create(
                book=book,
                lesson_num=lesson_num,
                defaults={'characters': chars_str}
            )

            # Ensure Words exist
            for char in chars_list:
                word, created = Word.objects.get_or_create(hanzi=char)
                if created:
                    total_imported += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully processed {len(lessons)} lessons and imported {total_imported} new words.'
            )
        )
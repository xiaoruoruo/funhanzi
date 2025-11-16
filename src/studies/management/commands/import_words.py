from django.core.management.base import BaseCommand
from studies.models import Word
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

        # Import each lesson's characters
        total_imported = 0
        for lesson_num, lesson_content in enumerate(lessons, 1):
            for char in lesson_content:
                word, created = Word.objects.get_or_create(
                    hanzi=char,
                    defaults={
                        'lesson': lesson_num,
                    }
                )
                if created:
                    total_imported += 1

        self.stdout.write(
            self.style.SUCCESS(
                f'Successfully imported {total_imported} new words from {len(lessons)} lessons'
            )
        )
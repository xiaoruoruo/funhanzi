import logging
from django.core.management.base import BaseCommand
from studies.models import Lesson

log = logging.getLogger(__name__)

log = logging.getLogger(__name__)

class Command(BaseCommand):
    help = 'Populates the WordEntry table for a given lesson using Gemini.'

    def add_arguments(self, parser):
        parser.add_argument('lesson_range', type=str, help='The lesson number or range (e.g. "1-10") to populate words for')

    def handle(self, *args, **options):
        lesson_range = options['lesson_range']
        
        lessons_to_process = []
        if '-' in lesson_range:
            try:
                start, end = map(int, lesson_range.split('-'))
                lessons_to_process = range(start, end + 1)
            except ValueError:
                self.stderr.write(self.style.ERROR(f"Invalid range format: {lesson_range}"))
                return
        else:
            try:
                lessons_to_process = [int(lesson_range)]
            except ValueError:
                self.stderr.write(self.style.ERROR(f"Invalid lesson number: {lesson_range}"))
                return

        chars = []
        for lesson_number in lessons_to_process:
            self.stdout.write(f'Populating WordEntry for lesson {lesson_number}...')

            try:
                lesson = Lesson.objects.get(lesson_num=lesson_number)
            except Lesson.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Lesson {lesson_number} not found."))
                continue

            chars += [c.strip() for c in lesson.characters.split(',')]

        from studies.logic import word_population
        word_population.seed_words_for_lesson(chars)

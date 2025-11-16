from django.core.management.base import BaseCommand
from studies.models import Word, Lesson

class Command(BaseCommand):
    help = 'Populates the Lesson table based on existing Word data.'

    def handle(self, *args, **options):
        self.stdout.write('Populating Lesson table...')

        # Clear existing lessons to prevent duplicates on re-run
        Lesson.objects.all().delete()

        # Group words by lesson number
        lessons_data = {}
        for word in Word.objects.all().order_by('lesson', 'hanzi'):
            if word.lesson not in lessons_data:
                lessons_data[word.lesson] = []
            lessons_data[word.lesson].append(word.hanzi)

        # Create Lesson objects
        for lesson_num, characters_list in lessons_data.items():
            Lesson.objects.create(
                lesson_num=lesson_num,
                characters=", ".join(characters_list),
                is_learned=False # Default to not learned
            )
        
        self.stdout.write(self.style.SUCCESS('Lesson table populated successfully.'))

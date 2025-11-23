import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from django.core.management.base import BaseCommand
from studies.models import WordEntry, Lesson
from studies.logic import ai

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

        self.seed_words_for_lesson(chars)

    def seed_words_for_lesson(self, lesson_chars):
        with ThreadPoolExecutor() as executor:
            futures = {
                executor.submit(self.seed_words_for_char, char): char for char in lesson_chars
            }
            for future in as_completed(futures):
                char = futures[future]
                try:
                    future.result()
                except Exception as e:
                    log.exception(f"An error occurred while processing character '{char}': {e}")
                    self.stderr.write(self.style.ERROR(f"Error processing '{char}': {e}"))

    def seed_words_for_char(self, char, desired_words=10):
        # Check existing words count
        existing_count = WordEntry.objects.filter(word__contains=char).count()
        if existing_count >= desired_words:
            log.info(f"Enough words for {char} ({existing_count} >= {desired_words}). Skipping.")
            return

        log.info(f"Generating words for {char}")
        client = ai.get_gemini_client()

        def generate_words(length, count):
            prompt = f"Generate {length}-character Chinese words containing the character '{char}', generate {count} words. Output the words separated by space, no quotes please."
            response = ai.generate_content(client, prompt)
            if response and response.text:
                return response.text.split()
            return []

        new_words = []
        new_words.extend(generate_words(2, 20))
        new_words.extend(generate_words(3, 5))
        new_words.extend(generate_words(4, 5))

        # Filter unique and existing
        new_words = sorted(list(set(w for w in new_words if char in w)))
        
        existing_words = set(WordEntry.objects.filter(word__in=new_words).values_list('word', flat=True))
        new_words = [w for w in new_words if w not in existing_words]

        if not new_words:
            log.info(f"No new words generated for {char}.")
            return

        def score_words(words_to_score):
            prompt = f"""
        你是一位经验丰富的小学语文老师。请为以下中文词语打分，分数范围为0到1。评分标准请严格按照常用度以及小学生是否容易理解来判断。
        1分：小学生日常学习生活中常用，意思简单明了。
        0.5分：常用词，但小学生可能不常用或不易理解其确切含义。
        0分：生僻词、专业术语或无意义的组合。

        举例，包含“日”字的词：
        - 1分：日本, 日期, 日子
        - 0.5分：日企
        - 0分：日星

        待评分的词语:
        {", ".join(words_to_score)}

        请严格按照“词语:分数”的格式返回，并用英文逗号分隔，不要包含任何其他说明。
        """
            response = ai.generate_content(client, prompt)
            if response and response.text:
                return response.text.strip().split(",")
            return []

        scores_text = score_words(new_words)
        scored_words = []
        for item in scores_text:
            try:
                if ":" in item:
                    word, score_str = item.split(":")
                    word = word.replace("'", "").strip()
                    score = float(score_str.strip())
                    scored_words.append((word, score))
            except ValueError:
                log.warning(f"Could not parse score for '{item}'")

        for word, score in scored_words:
            WordEntry.objects.get_or_create(word=word, defaults={'score': score})

        log.info(f"Added {len(scored_words)} new words for character '{char}'.")

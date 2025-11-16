from django.db import models

class Word(models.Model):
    """
    Model to store vocabulary with hanzi only.
    """
    lesson = models.IntegerField(help_text="The lesson number the character belongs to")
    hanzi = models.CharField(max_length=10, unique=True, help_text="The Chinese character")
    
    class Meta:
        db_table = 'words'
        ordering = ['lesson', 'hanzi']
    
    def __str__(self):
        return self.hanzi


class Study(models.Model):
    """
    Model to store study sessions with structured content in JSON
    """
    STUDY_TYPES = [
        ('cloze', 'Cloze Test'),
        ('chars', 'Character Study'),
        ('failed', 'Failed Words Review'),
        ('review', 'Exam/Review Session'),
        ('words', 'Find Words Puzzle'),
    ]
    
    type = models.CharField(max_length=20, choices=STUDY_TYPES)
    content = models.JSONField(help_text="Structured study content as JSON")
    created_at = models.DateTimeField(auto_now_add=True)
    done = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'studies'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.type} study"


class Exam(models.Model):
    """
    Model to store exam sessions with structured content in JSON
    """
    EXAM_TYPES = [
        ('read', 'Reading Exam'),
        ('write', 'Writing Exam'),
    ]
    
    type = models.CharField(max_length=20, choices=EXAM_TYPES)
    content = models.JSONField(help_text="Structured exam content as JSON")
    created_at = models.DateTimeField(auto_now_add=True)
    recorded = models.BooleanField(default=False)
    
    class Meta:
        db_table = 'exams'
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.type} exam"


class StudyLog(models.Model):
    """
    Model to store study interactions (character, type, score, date)
    """
    word = models.ForeignKey(Word, on_delete=models.CASCADE, related_name='study_logs')
    
    # Type of study session (read, write, etc.)
    TYPE_CHOICES = [
        ('read', 'Read Exam'),
        ('write', 'Write Exam'),
        ('readstudy', 'Read Study'),
        ('writestudy', 'Write Study'),
    ]
    
    type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    score = models.IntegerField(default=0) # Not nullable, with default value
    study_date = models.DateField()

    class Meta:
        db_table = 'study_logs'
        ordering = ['study_date']
    
    def __str__(self):
        return f"{self.word.hanzi} ({self.type})"


class ExamSettings(models.Model):
    """
    Model to store exam generation settings
    """
    EXAM_TYPE_CHOICES = [
        ('read', 'Read Exam'),
        ('write', 'Write Exam'),
        ('read_review', 'Read Review'),
        ('write_review', 'Write Review'),
    ]
    
    exam_type = models.CharField(max_length=20, choices=EXAM_TYPE_CHOICES, unique=True)
    num_chars = models.IntegerField(default=10)
    score_filter = models.IntegerField(null=True, blank=True)
    days_filter = models.IntegerField(null=True, blank=True)
    title = models.CharField(max_length=200, default='')
    header_text = models.CharField(max_length=500, default='')
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        db_table = 'exam_settings'
    
    def __str__(self):
        return f"{self.get_exam_type_display()} Settings"


class WordEntry(models.Model):
    """
    Model to store multi-character words.
    This is based on the 'words' table from the original SQLite database.
    """
    word = models.CharField(max_length=50, unique=True, help_text="A multi-character Chinese word")
    score = models.FloatField(default=0.5, help_text="A score indicating how common the word is (0.0 to 1.0)")

    class Meta:
        db_table = 'word_entries'
        ordering = ['-score', 'word']

    def __str__(self):
        return self.word

class Lesson(models.Model):
    """Represents a single lesson and its learned status."""
    lesson_num = models.IntegerField(unique=True, primary_key=True)
    is_learned = models.BooleanField(default=False)
    characters = models.TextField() # Store characters as a comma-separated string

    def __str__(self):
        return f"Lesson {self.lesson_num}"

    class Meta:
        ordering = ['lesson_num']

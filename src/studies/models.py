from django.db import models

class Word(models.Model):
    """
    Model to store vocabulary with hanzi only.
    """
    hanzi = models.CharField(max_length=10, unique=True, help_text="The Chinese character")
    
    class Meta:
        db_table = 'words'
        ordering = ['hanzi']
    
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

    @property
    def log_type(self):
        log_type_map = {
            'chars': 'writestudy',
            'failed': 'writestudy',
            'cloze': 'readstudy',
            'review': 'readstudy',
            'words': 'readstudy',
            'ch_en_matching': 'readstudy'
        }
        if self.type not in log_type_map:
             raise ValueError(f"Unknown study type: {self.type}")
        return log_type_map[self.type]


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
    include_hard_mode = models.BooleanField(default=False)
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

class Book(models.Model):
    """Represents a book containing multiple lessons."""
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True, default='')
    order = models.IntegerField(default=0, help_text="Order of the book in the curriculum")

    class Meta:
        ordering = ['order', 'title']
        db_table = 'books'

    def __str__(self):
        return self.title


class Lesson(models.Model):
    """Represents a single lesson and its learned status."""
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name='lessons')
    lesson_num = models.IntegerField()
    is_learned = models.BooleanField(default=False)
    characters = models.TextField() # Store characters as a comma-separated string

    def save(self, *args, **kwargs):
        """Clean characters by removing duplicates and whitespace before saving."""
        # Split into individual characters, filter out commas and whitespace
        chars = [c for c in self.characters if c not in (',', ' ', '\t', '\n', '\r')]
        
        # Remove duplicates while preserving order
        unique_chars = list(dict.fromkeys(chars))
        
        # Store as comma-separated string
        self.characters = ','.join(unique_chars)
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Lesson {self.lesson_num}"

    class Meta:
        ordering = ['book__order', 'lesson_num']
        unique_together = ['book', 'lesson_num']

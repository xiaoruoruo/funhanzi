from django.shortcuts import render, redirect, get_object_or_404
from studies.models import Book, Lesson, StudyLog
import threading
from django.utils import timezone
import pytz
from ..logic import word_population, fsrs, stats

def lesson_list(request):
    """Displays a list of all lessons grouped by book with progress stats."""
    books = Book.objects.prefetch_related('lessons').all()
    
    # Fetch all study logs for stats calculation
    study_logs = StudyLog.objects.filter(
        type__in=['read', 'write']
    ).select_related('word')
    
    local_tz = pytz.timezone('America/Los_Angeles')
    local_now = timezone.now().astimezone(local_tz)
    
    # Build FSRS cards and stats
    fsrs_cards = fsrs.build_cards_from_logs(list(study_logs))
    character_stats = stats.calculate_character_stats(fsrs_cards, local_now)
    recent_history = stats.calculate_recent_history(study_logs, local_now)
    
    # Attach stats to lessons
    for book in books:
        for lesson in book.lessons.all():
            chars = [c.strip() for c in lesson.characters.split(',')]
            lesson.stats = stats.aggregate_lesson_stats(character_stats, chars)
            
            # Attach detailed stats for the accordion view
            lesson.detailed_stats = []
            for char in chars:
                char_data = character_stats.get(char, {
                    "read": {"retrievability_str": "N/A", "due_in_days_str": "N/A"},
                    "write": {"retrievability_str": "N/A", "due_in_days_str": "N/A"}
                })
                
                # Get recent history safely
                char_history = recent_history.get(char, {"read": [], "write": []})
                
                lesson.detailed_stats.append({
                    "char": char,
                    "read": char_data["read"],
                    "read_history": char_history.get("read", []),
                    "write": char_data["write"],
                    "write_history": char_history.get("write", [])
                })
            
    return render(request, 'studies/lessons.html', {'books': books})


def toggle_lesson_learned(request, lesson_id):
    """Toggles the is_learned status for a given lesson."""
    if request.method == 'POST':
        lesson = get_object_or_404(Lesson, id=lesson_id)
        
        # Check if we are marking it as learned (it was False, now becoming True)
        was_learned = lesson.is_learned
        lesson.is_learned = not lesson.is_learned
        lesson.save()
        
        if not was_learned and lesson.is_learned:
            # Trigger background population
            
            chars = [c.strip() for c in lesson.characters.split(',')]
            threading.Thread(target=word_population.seed_words_for_lesson, args=(chars,)).start()
            
    return redirect('lesson_list')


def parse_lesson_range(range_str):
    """
    Parses a string of lesson numbers and ranges (e.g., "1-3, 5") into a list of integers.
    """
    if not range_str:
        return []
    
    lesson_nums = set()
    parts = range_str.split(',')
    
    for part in parts:
        part = part.strip()
        if not part:
            continue
            
        if '-' in part:
            try:
                start, end = map(int, part.split('-'))
                # Handle range (inclusive)
                if start <= end:
                    lesson_nums.update(range(start, end + 1))
            except ValueError:
                continue # Ignore malformed ranges
        else:
            try:
                lesson_nums.add(int(part))
            except ValueError:
                continue # Ignore malformed numbers
                
    return sorted(list(lesson_nums))

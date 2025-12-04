from django.shortcuts import render, redirect, get_object_or_404
from studies.models import Book, Lesson
import threading
from ..logic import word_population

def lesson_list(request):
    """Displays a list of all lessons grouped by book."""
    books = Book.objects.prefetch_related('lessons').all()
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

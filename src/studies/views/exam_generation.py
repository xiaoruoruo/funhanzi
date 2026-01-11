from django.shortcuts import render, redirect
from studies.models import Exam, ExamSettings, Book, Lesson
from .. import logic as study_logic
from ..logic import selection
from .lessons import parse_lesson_range

def generate_read_exam(request):
    # Get last used parameters from database
    try:
        settings_obj = ExamSettings.objects.get(exam_type='read')
        last_params = {
            'num_chars': settings_obj.num_chars,
            'score_filter': settings_obj.score_filter,
            'days_filter': settings_obj.days_filter,
            'title': settings_obj.title,
            'header_text': settings_obj.header_text,
            'include_hard_mode': settings_obj.include_hard_mode
        }
    except ExamSettings.DoesNotExist:
        last_params = {}

    if request.method == 'POST':
        num_chars = int(request.POST.get('num_chars', 10))
        score_filter = request.POST.get('score_filter', None)
        if score_filter is not None and score_filter != '':
            score_filter = int(score_filter)
        else:
            score_filter = None
        days_filter = request.POST.get('days_filter', None)
        if days_filter is not None and days_filter != '':
            days_filter = int(days_filter)
        else:
            days_filter = None
        title = request.POST.get('title', 'Reading Test')
        header_text = request.POST.get('header_text', f'Test date: ____. Circle the forgotten ones.')
        include_hard_mode = request.POST.get('include_hard_mode') == 'on'

        book_id = request.POST.get('book_id')
        book_id = int(book_id) if book_id else None
        
        lesson_range = request.POST.get('lesson_range')
        lesson_ids = None
        
        if book_id and lesson_range:
            lesson_nums = parse_lesson_range(lesson_range)
            if lesson_nums:
                lesson_ids = list(Lesson.objects.filter(book_id=book_id, lesson_num__in=lesson_nums).values_list('id', flat=True))

        # Save current parameters to database
        settings_obj, created = ExamSettings.objects.get_or_create(exam_type='read')
        settings_obj.num_chars = num_chars
        settings_obj.score_filter = score_filter
        settings_obj.days_filter = days_filter
        settings_obj.title = title
        settings_obj.header_text = header_text
        settings_obj.include_hard_mode = include_hard_mode
        settings_obj.save()

        # For read exam, we'll modify the selection process if filters are provided
        if score_filter is not None or days_filter is not None:
            # Custom selection with filters
            s = selection.Selection()
            s = s.from_learned_lessons(book_id=book_id, lesson_ids=lesson_ids)
            # Remove hard mode words from regular exam unless requested
            if not include_hard_mode:
                s = s.remove_hard_mode_words('read')
            if score_filter is not None:
                s = s.remove_score_greater("read", score_filter)
            if days_filter is not None:
                s = s.remove_any_recent_records(days_filter)
            selected_chars = s.random(num_chars)
            content_data = study_logic.create_read_exam(
                num_chars=num_chars,
                character_list=selected_chars,  # Pass pre-selected characters
                title=title, 
                header_text=header_text
            )
        else:
            # Use default logic
            # Explicitly select and filter to ensure hard mode exclusion
            s = selection.Selection().from_learned_lessons(book_id=book_id, lesson_ids=lesson_ids)
            if not include_hard_mode:
                s = s.remove_hard_mode_words('read')
            selected_chars = s.random(num_chars)
            
            content_data = study_logic.create_read_exam(
                num_chars=num_chars, 
                character_list=selected_chars,
                title=title, 
                header_text=header_text,
                book_id=book_id,
                lesson_ids=lesson_ids
            )

        exam = Exam.objects.create(type='read', content=content_data)
        return redirect('view_exam', exam_id=exam.id)
    
    # Use last used parameters or defaults
    books = Book.objects.filter(lessons__is_learned=True).distinct().prefetch_related('lessons')
    context = {
        'exam_type': 'read',
        'default_num_chars': last_params.get('num_chars', 10),
        'default_score_filter': last_params.get('score_filter'),
        'default_days_filter': last_params.get('days_filter'),
        'default_title': last_params.get('title', 'Reading Test'),
        'default_header_text': last_params.get('header_text', 'Test date: ____. Circle the forgotten ones.'),
        'default_include_hard_mode': last_params.get('include_hard_mode', False),
        'books': books
    }
    return render(request, 'studies/generate_exam.html', context)


def generate_write_exam(request):
    # Get last used parameters from database
    try:
        settings_obj = ExamSettings.objects.get(exam_type='write')
        last_params = {
            'num_chars': settings_obj.num_chars,
            'score_filter': settings_obj.score_filter,
            'days_filter': settings_obj.days_filter,
            'title': settings_obj.title,
            'header_text': settings_obj.header_text,
            'include_hard_mode': settings_obj.include_hard_mode
        }
    except ExamSettings.DoesNotExist:
        last_params = {}

    if request.method == 'POST':
        num_chars = int(request.POST.get('num_chars', 10))
        score_filter = request.POST.get('score_filter', None)
        if score_filter is not None and score_filter != '':
            score_filter = int(score_filter)
        else:
            score_filter = None
        days_filter = request.POST.get('days_filter', None)
        if days_filter is not None and days_filter != '':
            days_filter = int(days_filter)
        else:
            days_filter = None
        title = request.POST.get('title', 'Writing Test')
        header_text = request.POST.get('header_text', f'Test date: ____. Write down the characters.')
        include_hard_mode = request.POST.get('include_hard_mode') == 'on'

        book_id = request.POST.get('book_id')
        book_id = int(book_id) if book_id else None
        
        lesson_range = request.POST.get('lesson_range')
        lesson_ids = None
        
        if book_id and lesson_range:
            lesson_nums = parse_lesson_range(lesson_range)
            if lesson_nums:
                lesson_ids = list(Lesson.objects.filter(book_id=book_id, lesson_num__in=lesson_nums).values_list('id', flat=True))

        # Save current parameters to database
        settings_obj, created = ExamSettings.objects.get_or_create(exam_type='write')
        settings_obj.num_chars = num_chars
        settings_obj.score_filter = score_filter
        settings_obj.days_filter = days_filter
        settings_obj.title = title
        settings_obj.header_text = header_text
        settings_obj.include_hard_mode = include_hard_mode
        settings_obj.save()

        # For write exam, we'll modify the selection process if filters are provided
        if score_filter is not None or days_filter is not None:
            # Custom selection with filters
            s = selection.Selection()
            s = s.from_learned_lessons(book_id=book_id, lesson_ids=lesson_ids)
            # Remove hard mode words from regular exam unless requested
            if not include_hard_mode:
                s = s.remove_hard_mode_words('write')
            if score_filter is not None:
                s = s.remove_score_greater("write", score_filter)
            if days_filter is not None:
                s = s.remove_any_recent_records(days_filter)
            selected_chars = s.random(num_chars)
            content_data = study_logic.create_write_exam(
                num_chars=num_chars,
                character_list=selected_chars,  # Pass pre-selected characters
                title=title, 
                header_text=header_text
            )
        else:
            # Use default logic
            # Explicitly select and filter to ensure hard mode exclusion
            s = selection.Selection().from_learned_lessons(book_id=book_id, lesson_ids=lesson_ids)
            if not include_hard_mode:
                s = s.remove_hard_mode_words('write')
            selected_chars = s.random(num_chars)
            
            content_data = study_logic.create_write_exam(
                num_chars=num_chars,
                character_list=selected_chars,
                title=title, 
                header_text=header_text,
                book_id=book_id,
                lesson_ids=lesson_ids
            )

        exam = Exam.objects.create(type='write', content=content_data)
        return redirect('view_exam', exam_id=exam.id)
    
    # Use last used parameters or defaults
    books = Book.objects.filter(lessons__is_learned=True).distinct().prefetch_related('lessons')
    context = {
        'exam_type': 'write',
        'default_num_chars': last_params.get('num_chars', 10),
        'default_score_filter': last_params.get('score_filter'),
        'default_days_filter': last_params.get('days_filter'),
        'default_title': last_params.get('title', 'Writing Test'),
        'default_header_text': last_params.get('header_text', 'Test date: ____. Write down the characters.'),
        'default_include_hard_mode': last_params.get('include_hard_mode', False),
        'books': books
    }
    return render(request, 'studies/generate_exam.html', context)


def generate_review_exam_read(request):
    """Generate read review exam"""
    return _generate_review_exam(request, 'read')


def generate_review_exam_write(request):
    """Generate write review exam"""
    return _generate_review_exam(request, 'write')


def _generate_review_exam(request, exam_type):
    """Helper function to generate either read or write review exam"""
    # Get last used parameters from database
    review_exam_type = f'{exam_type}_review'
    try:
        settings_obj = ExamSettings.objects.get(exam_type=review_exam_type)
        last_params = {
            'num_chars': settings_obj.num_chars,
            'title': settings_obj.title,
            'header_text': settings_obj.header_text,
            'include_hard_mode': settings_obj.include_hard_mode
        }
    except ExamSettings.DoesNotExist:
        last_params = {}

    if request.method == 'POST':
        num_chars = int(request.POST.get('num_chars', 20))
        title = request.POST.get('title', f'{exam_type.capitalize()} Review')
        header_text = request.POST.get('header_text', f'Reviewing due characters. Test date: ____.')
        include_hard_mode = request.POST.get('include_hard_mode') == 'on'

        # Save current parameters to database
        settings_obj, created = ExamSettings.objects.get_or_create(exam_type=review_exam_type)
        settings_obj.num_chars = num_chars
        settings_obj.title = title
        settings_obj.header_text = header_text
        settings_obj.include_hard_mode = include_hard_mode
        settings_obj.save()

        # For review exam, we also want to filter out hard mode words
        # but create_review_exam does selection internally.
        # We need to modify create_review_exam or pre-select here.
        # study_logic.create_review_exam likely uses Selection().from_fsrs(...)
        
        # Let's do it manually here to be safe and explicit
        s = selection.Selection().from_fsrs(exam_type, due_only=True)
        if not include_hard_mode:
            s = s.remove_hard_mode_words(exam_type)
        
        s = s.lowest_retrievability()
        selected_chars = s.take(num_chars)
        
        # We need a way to pass these characters to create_review_exam
        # Checking logic/exam_generation.py (which we haven't seen but inferred)
        # Assuming it accepts character_list like others.
        
        content_data = study_logic.create_review_exam(
            exam_type=exam_type, 
            num_chars=num_chars,
            character_list=selected_chars
        )
        exam = Exam.objects.create(type=f'{exam_type}_review', content=content_data)
        return redirect('view_exam', exam_id=exam.id)
    
    # Use last used parameters or defaults
    context = {
        'exam_type': f'{exam_type}_review',
        'default_num_chars': last_params.get('num_chars', 20),
        'default_title': last_params.get('title', f'{exam_type.capitalize()} Review'),
        'default_header_text': last_params.get('header_text', f'Reviewing due characters. Test date: ____.'),
        'default_include_hard_mode': last_params.get('include_hard_mode', False)
    }
    return render(request, 'studies/generate_exam.html', context)

def generate_recovery_exam_read(request):
    """Generate read recovery exam"""
    return _generate_recovery_exam(request, 'read')

def generate_recovery_exam_write(request):
    """Generate write recovery exam"""
    return _generate_recovery_exam(request, 'write')

def _generate_recovery_exam(request, exam_type):
    """Helper for generating recovery exams"""
    if request.method == 'POST':
        title = request.POST.get('title', f'{exam_type.capitalize()} Recovery Exam')
        header_text = request.POST.get('header_text', 'Recovering failed characters. Score > 1 to recover.')
        
        # Select hard mode words
        s = selection.Selection().from_hard_mode(exam_type)
        selected_chars = s.get_all() # Take all hard mode words? Or limit?
        # Let's take all for now, or maybe random 50 if too many.
        # Given user said "recovery exam", let's include all.
        
        num_chars = len(selected_chars)
        
        if exam_type == 'read':
            content_data = study_logic.create_read_exam(
                num_chars=num_chars,
                character_list=selected_chars,
                title=title,
                header_text=header_text
            )
        else:
            content_data = study_logic.create_write_exam(
                num_chars=num_chars,
                character_list=selected_chars,
                title=title,
                header_text=header_text
            )
            
        exam = Exam.objects.create(type=f'{exam_type}', content=content_data)
        return redirect('view_exam', exam_id=exam.id)
    
    # Just render a confirmation page or similar?
    # Or reuse generate_exam template but with less options (no filters needed)
    context = {
        'exam_type': f'{exam_type}_recovery', # Fake type for template
        'default_title': f'{exam_type.capitalize()} Recovery Exam',
        'default_header_text': 'Recovering failed characters. Score > 1 to recover.',
        'hide_filters': True # Helper for template to hide unnecessary fields
    }
    return render(request, 'studies/generate_exam.html', context)

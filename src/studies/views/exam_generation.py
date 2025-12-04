from django.shortcuts import render, redirect
from studies.models import Exam, ExamSettings
from .. import logic as study_logic
from ..logic import selection

def generate_read_exam(request):
    # Get last used parameters from database
    try:
        settings_obj = ExamSettings.objects.get(exam_type='read')
        last_params = {
            'num_chars': settings_obj.num_chars,
            'score_filter': settings_obj.score_filter,
            'days_filter': settings_obj.days_filter,
            'title': settings_obj.title,
            'header_text': settings_obj.header_text
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

        # Save current parameters to database
        settings_obj, created = ExamSettings.objects.get_or_create(exam_type='read')
        settings_obj.num_chars = num_chars
        settings_obj.score_filter = score_filter
        settings_obj.days_filter = days_filter
        settings_obj.title = title
        settings_obj.header_text = header_text
        settings_obj.save()

        # For read exam, we'll modify the selection process if filters are provided
        if score_filter is not None or days_filter is not None:
            # Custom selection with filters
            s = selection.Selection()
            s = s.from_learned_lessons()
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
            content_data = study_logic.create_read_exam(
                num_chars=num_chars, 
                title=title, 
                header_text=header_text
            )

        exam = Exam.objects.create(type='read', content=content_data)
        return redirect('view_exam', exam_id=exam.id)
    
    # Use last used parameters or defaults
    context = {
        'exam_type': 'read',
        'default_num_chars': last_params.get('num_chars', 10),
        'default_score_filter': last_params.get('score_filter'),
        'default_days_filter': last_params.get('days_filter'),
        'default_title': last_params.get('title', 'Reading Test'),
        'default_header_text': last_params.get('header_text', 'Test date: ____. Circle the forgotten ones.')
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
            'header_text': settings_obj.header_text
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

        # Save current parameters to database
        settings_obj, created = ExamSettings.objects.get_or_create(exam_type='write')
        settings_obj.num_chars = num_chars
        settings_obj.score_filter = score_filter
        settings_obj.days_filter = days_filter
        settings_obj.title = title
        settings_obj.header_text = header_text
        settings_obj.save()

        # For write exam, we'll modify the selection process if filters are provided
        if score_filter is not None or days_filter is not None:
            # Custom selection with filters
            s = selection.Selection()
            s = s.from_learned_lessons()
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
            content_data = study_logic.create_write_exam(
                num_chars=num_chars, 
                title=title, 
                header_text=header_text
            )

        exam = Exam.objects.create(type='write', content=content_data)
        return redirect('view_exam', exam_id=exam.id)
    
    # Use last used parameters or defaults
    context = {
        'exam_type': 'write',
        'default_num_chars': last_params.get('num_chars', 10),
        'default_score_filter': last_params.get('score_filter'),
        'default_days_filter': last_params.get('days_filter'),
        'default_title': last_params.get('title', 'Writing Test'),
        'default_header_text': last_params.get('header_text', 'Test date: ____. Write down the characters.')
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
            'header_text': settings_obj.header_text
        }
    except ExamSettings.DoesNotExist:
        last_params = {}

    if request.method == 'POST':
        num_chars = int(request.POST.get('num_chars', 20))
        title = request.POST.get('title', f'{exam_type.capitalize()} Review')
        header_text = request.POST.get('header_text', f'Reviewing due characters. Test date: ____.')

        # Save current parameters to database
        settings_obj, created = ExamSettings.objects.get_or_create(exam_type=review_exam_type)
        settings_obj.num_chars = num_chars
        settings_obj.title = title
        settings_obj.header_text = header_text
        settings_obj.save()

        content_data = study_logic.create_review_exam(exam_type=exam_type, num_chars=num_chars)
        exam = Exam.objects.create(type=f'{exam_type}_review', content=content_data)
        return redirect('view_exam', exam_id=exam.id)
    
    # Use last used parameters or defaults
    context = {
        'exam_type': f'{exam_type}_review',
        'default_num_chars': last_params.get('num_chars', 20),
        'default_title': last_params.get('title', f'{exam_type.capitalize()} Review'),
        'default_header_text': last_params.get('header_text', f'Reviewing due characters. Test date: ____.')
    }
    return render(request, 'studies/generate_exam.html', context)

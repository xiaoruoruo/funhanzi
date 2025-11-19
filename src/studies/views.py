from datetime import timedelta
import logging
from django.shortcuts import render, redirect, get_object_or_404
from studies.models import StudyLog, Word, Study, Exam, ExamSettings
from django.db.models import Window
from django.db.models.functions import RowNumber
from django.utils import timezone
from .logic import fsrs
from . import logic as study_logic
from .logic import selection

# Get an instance of a logger
logger = logging.getLogger(__name__)


def progress_view(request):
    """
    View function for the progress page, replicating the logic from the original Flask app.
    """
    # Use Django ORM with window functions to get the last 3 records per character-type
    ranked_study_logs = StudyLog.objects.filter(
        type__in=['read', 'write']
    ).select_related('word').annotate(
        rn=Window(
            expression=RowNumber(),
            partition_by=['word__hanzi', 'type'],
            order_by=['-study_date']
        )
    ).filter(rn__lte=3).order_by('word__hanzi', 'type', 'study_date')

    logger.info(f"Found {ranked_study_logs.count()} ranked study logs.")
    for log in ranked_study_logs[:5]:
        logger.info(f"  - Char: {log.word.hanzi}, Type: {log.type}, Score: {log.score}, Date: {log.study_date}")

    progress_data = {}
    for log in ranked_study_logs:
        char = log.word.hanzi
        if char not in progress_data:
            progress_data[char] = {
                "read": {"records": [], "retrievability": "N/A", "due_in_days": "N/A"},
                "write": {"records": [], "retrievability": "N/A", "due_in_days": "N/A"},
            }

        record_type = log.type
        from django.utils import timezone
        import pytz
        local_tz = pytz.timezone('America/Los_Angeles')
        local_now = timezone.now().astimezone(local_tz)
        days_ago = (local_now.date() - log.study_date).days

        score = log.score
        rating = fsrs.score_to_rating(score if score is not None else 0)
        color = fsrs.RATING_TO_COLOR.get(rating, "")

        progress_data[char][record_type]["records"].append(
            {"days_ago": days_ago, "color": color}
        )

    try:
        study_logs = StudyLog.objects.filter(
            type__in=['read', 'write']
        ).select_related('word')
        fsrs_cards = fsrs.build_cards_from_logs(list(study_logs))  # Assuming function updated to not need user

        for (char, card_type), card in fsrs_cards.items():
            if char not in progress_data:
                continue
            try:
                scheduler = fsrs.read_scheduler if card_type == "read" else fsrs.write_scheduler
                retrievability_val = scheduler.get_card_retrievability(card, local_now)
                if retrievability_val is not None:
                    progress_data[char][card_type]["retrievability"] = f"{float(retrievability_val) * 100:.2f}%"
                if hasattr(card, 'due') and card.due:
                    due_in_days = (card.due - local_now).days
                    progress_data[char][card_type]["due_in_days"] = due_in_days
            except Exception as e:
                logger.error(f"Error processing FSRS card for {char} ({card_type}): {e}")
                pass
    except Exception as e:
        logger.error(f"Error in FSRS processing: {e}")
        pass
    
    return render(request, 'studies/progress.html', {'progress_data': progress_data})


# Study Generation Views
def generate_study_chars(request):
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
        header_text = request.POST.get('header_text', 'Character Study Session')

        content_data = study_logic.create_study_chars_sheet(num_chars=num_chars, score_filter=score_filter, days_filter=days_filter, header_text=header_text)
        study = Study.objects.create(type='chars', content=content_data)
        return redirect('view_study', study_id=study.id)
    return render(request, 'studies/generate_study.html', {'study_type': 'chars'})


def generate_failed_study(request):
    if request.method == 'POST':
        num_chars = int(request.POST.get('num_chars', 10))
        header_text = request.POST.get('header_text', 'Failed Characters Review')
        threshold = request.POST.get('threshold', 5)
        if threshold is not None and threshold != '':
            threshold = int(threshold)
        else:
            threshold = 5
        recency_days = request.POST.get('recency_days', 8)
        if recency_days is not None and recency_days != '':
            recency_days = int(recency_days)
        else:
            recency_days = 8

        content_data = study_logic.create_failed_study_sheet(num_chars=num_chars, header_text=header_text, threshold=threshold, recency_days=recency_days)
        study = Study.objects.create(type='failed', content=content_data)
        return redirect('view_study', study_id=study.id)
    return render(request, 'studies/generate_study.html', {'study_type': 'failed'})


def generate_review_study(request):
    if request.method == 'POST':
        num_chars = int(request.POST.get('num_chars', 10))
        days_filter = request.POST.get('days_filter', None)
        if days_filter is not None and days_filter != '':
            days_filter = int(days_filter)
        else:
            days_filter = None
        header_text = request.POST.get('header_text', 'Review Session')

        content_data = study_logic.create_study_review_sheet(num_chars=num_chars, days_filter=days_filter, header_text=header_text)
        study = Study.objects.create(type='review', content=content_data)
        return redirect('view_study', study_id=study.id)
    return render(request, 'studies/generate_study.html', {'study_type': 'review'})


def generate_cloze_test(request):
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
        study_source = request.POST.get('study_source', None)
        if study_source == '':
            study_source = None
        header_text = request.POST.get('header_text', 'Cloze Test')

        content_data = study_logic.create_cloze_test(num_chars=num_chars, score_filter=score_filter, days_filter=days_filter, study_source=study_source, header_text=header_text)
        study = Study.objects.create(type='cloze', content=content_data)
        return redirect('view_study', study_id=study.id)
    return render(request, 'studies/generate_study.html', {'study_type': 'cloze'})


def generate_find_words_puzzle(request):
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
        study_source = request.POST.get('study_source', None)
        if study_source == '':
            study_source = None
        header_text = request.POST.get('header_text', 'Find Words Puzzle')

        content_data = study_logic.create_find_words_puzzle(num_chars=num_chars, score_filter=score_filter, days_filter=days_filter, study_source=study_source, header_text=header_text)
        study = Study.objects.create(type='words', content=content_data)
        return redirect('view_study', study_id=study.id)
    return render(request, 'studies/generate_study.html', {'study_type': 'words'})


def generate_ch_en_matching_study(request):
    if request.method == 'POST':
        num_chars = int(request.POST.get('num_chars', 10))
        score_filter = request.POST.get('score_filter')
        score_filter = int(score_filter) if score_filter else None
        days_filter = request.POST.get('days_filter')
        days_filter = int(days_filter) if days_filter else None
        study_source = request.POST.get('study_source')
        header_text = request.POST.get('header_text', 'Chinese-English Matching')

        content_data = study_logic.create_ch_en_matching_study(
            num_chars=num_chars,
            score_filter=score_filter,
            days_filter=days_filter,
            study_source=study_source,
            header_text=header_text,
        )
        study = Study.objects.create(type='ch_en_matching', content=content_data)
        return redirect('view_study', study_id=study.id)

    return render(request, 'studies/generate_study.html', {'study_type': 'ch_en_matching'})


# Exam Generation Views
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


# Study and Exam Rendering Views
def view_study(request, study_id):
    study = get_object_or_404(Study, id=study_id)
    content = study.content
    templates_by_type = {
        'chars': 'studies/study_chars.html',
        'failed': 'studies/study_failed.html',
        'review': 'studies/study_review.html',
        'cloze': 'studies/study_cloze.html',
        'words': 'studies/study_words.html',
        'ch_en_matching': 'studies/study_ch_en_matching.html'
    }
    template_name = templates_by_type.get(study.type, 'studies/study_default.html')
    
    context = {'study': study, 'content': content}
    if study.type == 'cloze':
        words = content.get('words', [])
        sentences = content.get('sentences', [])
        context['cloze_pairs'] = zip(words, sentences)
    elif study.type == 'words':
        from .logic import study_find_words
        grid, start_row = study_find_words.generate_grid(
            content['content']['sentence'],
            content['content']['words'],
            list(set("".join(content['content']['words'])))
        )
        context['grid'] = grid
        context['start_row'] = start_row
        context['start_marker_top'] = f"calc((100% / 16) + (100% / 8) * {start_row})"


    return render(request, template_name, context)


def view_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    content = exam.content
    
    # Use the unified print-friendly format for all exam types
    template_name = 'studies/exam_print.html'
    
    return render(request, template_name, {'exam': exam, 'content': content})


# History Views
def exam_history(request):
    exams = Exam.objects.all().order_by('-created_at')
    return render(request, 'studies/exam_history.html', {'exams': exams})


def study_history(request):
    studies = Study.objects.all().order_by('-created_at')
    return render(request, 'studies/study_history.html', {'studies': studies})


# Exam Recording Views
def record_exam(request, exam_id):
    exam = get_object_or_404(Exam, id=exam_id)
    
    content = exam.content
    items = content.get('items', [])
    
    # Correctly parse all unique characters from the items (which can be words)
    char_set = set()
    for item in items:
        for char in item:
            char_set.add(char)
    characters = sorted(list(char_set))
    
    if request.method == 'POST':
        from django.utils import timezone
        today = timezone.now().date()
        
        # When saving, the `type` should match the exam's original type ('read' or 'write')
        # not the review type.
        record_type = exam.type
        if record_type.endswith('_review'):
            record_type = record_type.replace('_review', '')

        for char in characters:
            score_str = request.POST.get(f"score_{char}")
            if score_str:
                score = int(score_str)
                word, created = Word.objects.get_or_create(hanzi=char)
                StudyLog.objects.create(word=word, type=record_type, score=score, study_date=today)
        
        exam.recorded = True
        exam.save()
        
        return redirect('exam_history')
    
    return render(request, 'studies/record_exam.html', {'exam': exam, 'characters': characters, 'score_range': range(11)})


def stats_view(request):
    from django.db.models import Count, Q
    from datetime import datetime, date
    import pytz
    from collections import defaultdict
    
    # Fetch all records ordered by date (no user filter)
    all_study_logs = StudyLog.objects.order_by('study_date')
    
    if not all_study_logs:
        return render(request, 'studies/stats.html', {'stats': []})

    # Group all records by month to identify months to process
    records_by_month = defaultdict(list)
    all_chars_in_records = set()
    
    # Convert StudyLog objects to dictionaries similar to the original format
    all_records = []
    for log in all_study_logs:
        record_dict = {
            'character': log.word.hanzi,
            'type': log.type,
            'score': log.score,
            'date': log.study_date.strftime('%Y-%m-%d')
        }
        all_records.append(record_dict)
        month_str = log.study_date.strftime('%Y-%m')  # Format like '2025-10'
        records_by_month[month_str].append(record_dict)
        all_chars_in_records.add(log.word.hanzi)

    all_chars_in_records = sorted(list(all_chars_in_records))

    # Identify the date range from first record to last record
    first_date = all_study_logs.first().study_date
    last_date = all_study_logs.last().study_date

    # Generate all months between first and last date
    current_date = date(first_date.year, first_date.month, 1)
    end_date = date(last_date.year, last_date.month, 1)
    months_to_process = []

    while current_date <= end_date:
        months_to_process.append(current_date.strftime('%Y-%m'))
        # Move to next month
        if current_date.month == 12:
            current_date = date(current_date.year + 1, 1, 1)
        else:
            current_date = date(current_date.year, current_date.month + 1, 1)

    # Initialize FSRS schedulers
    read_scheduler = fsrs.read_scheduler
    write_scheduler = fsrs.write_scheduler

    monthly_stats = []
    cumulative_chars = set()

    for month in months_to_process:
        year = int(month[:4])
        month_num = int(month[5:7])
        
        # Calculate the last day of the current month
        if month_num == 12:
            next_month_first_day = date(year + 1, 1, 1)
        else:
            next_month_first_day = date(year, month_num + 1, 1)
        last_day_of_month = next_month_first_day - timedelta(days=1)
        month_end_date_str = last_day_of_month.strftime('%Y-%m-%d')

        # Filter records up to the end of the current month
        historical_records = [r for r in all_records if r['date'] <= month_end_date_str]

        # Build cards using the historical records up to month end
        # Create a temporary function to build cards from historical records similar to the original
        fsrs_cards = build_fsrs_cards_from_records(historical_records, all_chars_in_records)

        # Update cumulative unique characters
        for record in historical_records:
            cumulative_chars.add(record['character'])

        # Calculate retrievability and categorize at the end of the month
        read_mastered, read_learning, read_lapsing = 0, 0, 0
        write_mastered, write_learning, write_lapsing = 0, 0, 0

        # Calculate FSRS retrievability as of the end of the month
        calculation_time = datetime.combine(
            last_day_of_month, datetime.max.time()
        ).replace(tzinfo=pytz.UTC)

        for char in cumulative_chars:
            # Read card
            read_card = fsrs_cards.get((char, "read"))
            if read_card:
                r = read_scheduler.get_card_retrievability(read_card, calculation_time)
                if r is not None:
                    r = float(r)
                    if r > 0.9:
                        read_mastered += 1
                    elif r >= 0.6:
                        read_learning += 1
                    else:
                        read_lapsing += 1

            # Write card
            write_card = fsrs_cards.get((char, "write"))
            if write_card:
                r = write_scheduler.get_card_retrievability(write_card, calculation_time)
                if r is not None:
                    r = float(r)
                    if r > 0.9:
                        write_mastered += 1
                    elif r >= 0.6:
                        write_learning += 1
                    else:
                        write_lapsing += 1

        # Count reviews and studies specifically for the current month
        month_records = records_by_month.get(month, [])
        reviews_this_month = sum(1 for r in month_records if r['type'] in ['read', 'write'])
        studies_this_month = sum(1 for r in month_records if r['type'] in ['readstudy', 'writestudy'])

        stats = {
            'month': month,  # Keep in YYYY-MM format to match Flask
            'total_reviews': reviews_this_month,
            'total_studies': studies_this_month,
            'cumulative_unique_chars': len(cumulative_chars),
            'read_mastered': read_mastered,
            'read_learning': read_learning,
            'read_lapsing': read_lapsing,
            'write_mastered': write_mastered,
            'write_learning': write_learning,
            'write_lapsing': write_lapsing,
        }
        monthly_stats.append(stats)

    # Return sorted in reverse order (newest first), like in Flask
    return render(request, 'studies/stats.html', {'stats': sorted(monthly_stats, key=lambda x: x["month"], reverse=True)})


def build_fsrs_cards_from_records(historical_records, all_chars_in_records):
    """
    Build FSRS cards from historical records, replicating the logic from the original Flask app
    """
    from .logic.fsrs import read_scheduler, write_scheduler, score_to_rating
    from fsrs import Card, Rating
    import datetime
    
    # Group records by (character, type)
    records_by_card = {}
    for record in historical_records:
        char = record['character']
        record_type = record['type']
        score = record['score']

        # Add the original record
        key = (char, record_type)
        if key not in records_by_card:
            records_by_card[key] = []
        records_by_card[key].append({
            'character': char,
            'type': record_type,
            'score': score,
            'date': record['date']
        })

        # If it's a write record, add an implied read record
        if record_type == "write":
            read_key = (char, "read")
            if read_key not in records_by_card:
                records_by_card[read_key] = []

            implied_read_record = {
                "character": char,
                "type": "read",
                "score": min(score + 3, 10),  # Limit to 10
                "date": record['date'],
            }
            records_by_card[read_key].append(implied_read_record)

    built_cards = {}
    # Build cards
    for char in all_chars_in_records:
        for card_type in ["read", "write"]:
            card_key = (char, card_type)
            card_records = records_by_card.get(card_key, [])

            # Sort records by date before replaying
            card_records.sort(key=lambda r: r["date"])

            scheduler = read_scheduler if card_type == "read" else write_scheduler

            card = Card()
            if card_records:
                for record in card_records:
                    rating = score_to_rating(record["score"])
                    review_date = datetime.datetime.strptime(record["date"], "%Y-%m-%d")
                    review_time = datetime.datetime.combine(
                        review_date.date(), 
                        datetime.datetime.min.time()
                    ).replace(tzinfo=datetime.timezone.utc)
                    card, _ = scheduler.review_card(card, rating, review_time)

            built_cards[card_key] = card
    return built_cards


def mark_study_done(request, study_id):
    study = get_object_or_404(Study, id=study_id)  # Removed user filter

    today = timezone.now().date()
    
    characters = study.content.get('selected_chars', [])
    
    for char in characters:
        word, created = Word.objects.get_or_create(hanzi=char)
        StudyLog.objects.create(word=word, type='readstudy', score=5, study_date=today)

    study.done = True
    study.save()
    return redirect('study_history')


from studies.models import Lesson

def lesson_list(request):
    """Displays a list of all lessons with their learned status and characters."""
    lessons = Lesson.objects.all().order_by('lesson_num')
    return render(request, 'studies/lessons.html', {'lessons': lessons})


def toggle_lesson_learned(request, lesson_num):
    """Toggles the is_learned status for a given lesson."""
    if request.method == 'POST':
        lesson = get_object_or_404(Lesson, lesson_num=lesson_num)
        lesson.is_learned = not lesson.is_learned
        lesson.save()
    return redirect('lesson_list')

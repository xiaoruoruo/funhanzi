from django.shortcuts import render, redirect
from studies.models import Study, Book, Lesson
from .. import logic as study_logic
from .lessons import parse_lesson_range

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
        study_source = request.POST.get('study_source', None)
        
        book_id = request.POST.get('book_id')
        book_id = int(book_id) if book_id else None
        
        lesson_range = request.POST.get('lesson_range')
        lesson_ids = None
        
        if book_id and lesson_range:
            lesson_nums = parse_lesson_range(lesson_range)
            if lesson_nums:
                # Find lesson IDs for these numbers in the selected book
                lesson_ids = list(Lesson.objects.filter(book_id=book_id, lesson_num__in=lesson_nums).values_list('id', flat=True))

        content_data = study_logic.create_study_chars_sheet(
            num_chars=num_chars, 
            score_filter=score_filter, 
            days_filter=days_filter, 
            header_text=header_text, 
            study_source=study_source,
            book_id=book_id,
            lesson_ids=lesson_ids
        )
        study = Study.objects.create(type='chars', content=content_data)
        return redirect('view_study', study_id=study.id)
    
    books = Book.objects.prefetch_related('lessons').all()
    return render(request, 'studies/generate_study.html', {'study_type': 'chars', 'books': books})


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
        
        book_id = request.POST.get('book_id')
        book_id = int(book_id) if book_id else None
        
        lesson_range = request.POST.get('lesson_range')
        lesson_ids = None
        
        if book_id and lesson_range:
            lesson_nums = parse_lesson_range(lesson_range)
            if lesson_nums:
                lesson_ids = list(Lesson.objects.filter(book_id=book_id, lesson_num__in=lesson_nums).values_list('id', flat=True))

        content_data = study_logic.create_cloze_test(
            num_chars=num_chars, 
            score_filter=score_filter, 
            days_filter=days_filter, 
            study_source=study_source, 
            header_text=header_text,
            book_id=book_id,
            lesson_ids=lesson_ids
        )
        study = Study.objects.create(type='cloze', content=content_data)
        return redirect('view_study', study_id=study.id)
    
    books = Book.objects.prefetch_related('lessons').all()
    return render(request, 'studies/generate_study.html', {'study_type': 'cloze', 'books': books})


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
        
        book_id = request.POST.get('book_id')
        book_id = int(book_id) if book_id else None
        
        lesson_range = request.POST.get('lesson_range')
        lesson_ids = None
        
        if book_id and lesson_range:
            lesson_nums = parse_lesson_range(lesson_range)
            if lesson_nums:
                lesson_ids = list(Lesson.objects.filter(book_id=book_id, lesson_num__in=lesson_nums).values_list('id', flat=True))

        content_data = study_logic.create_find_words_puzzle(
            num_chars=num_chars, 
            score_filter=score_filter, 
            days_filter=days_filter, 
            study_source=study_source, 
            header_text=header_text,
            book_id=book_id,
            lesson_ids=lesson_ids
        )
        study = Study.objects.create(type='words', content=content_data)
        return redirect('view_study', study_id=study.id)
    
    books = Book.objects.prefetch_related('lessons').all()
    return render(request, 'studies/generate_study.html', {'study_type': 'words', 'books': books})


def generate_ch_en_matching_study(request):
    if request.method == 'POST':
        num_chars = int(request.POST.get('num_chars', 10))
        score_filter = request.POST.get('score_filter')
        score_filter = int(score_filter) if score_filter else None
        days_filter = request.POST.get('days_filter')
        days_filter = int(days_filter) if days_filter else None
        study_source = request.POST.get('study_source')
        header_text = request.POST.get('header_text', 'Chinese-English Matching')
        
        book_id = request.POST.get('book_id')
        book_id = int(book_id) if book_id else None
        
        lesson_range = request.POST.get('lesson_range')
        lesson_ids = None
        
        if book_id and lesson_range:
            lesson_nums = parse_lesson_range(lesson_range)
            if lesson_nums:
                lesson_ids = list(Lesson.objects.filter(book_id=book_id, lesson_num__in=lesson_nums).values_list('id', flat=True))

        content_data = study_logic.create_ch_en_matching_study(
            num_chars=num_chars,
            score_filter=score_filter,
            days_filter=days_filter,
            study_source=study_source,
            header_text=header_text,
            book_id=book_id,
            lesson_ids=lesson_ids
        )
        study = Study.objects.create(type='ch_en_matching', content=content_data)
        return redirect('view_study', study_id=study.id)
    
    books = Book.objects.prefetch_related('lessons').all()
    return render(request, 'studies/generate_study.html', {'study_type': 'ch_en_matching', 'books': books})

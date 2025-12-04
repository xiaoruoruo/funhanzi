from django.shortcuts import render, redirect, get_object_or_404
from studies.models import Study, Exam, Word, StudyLog
from django.utils import timezone
from ..logic import study_find_words

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
    if study.type == 'ch_en_matching':
        context['header_text'] = content.get('header_text', 'Chinese-English Matching Study')
    if study.type == 'cloze':
        words = content.get('words', [])
        sentences = content.get('sentences', [])
        context['cloze_pairs'] = zip(words, sentences)
    elif study.type == 'words':
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

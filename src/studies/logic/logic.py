"""
This module orchestrates the full "select -> generate -> return JSON content" pipeline for both studies and exams.
It imports from the new modules that contain the specific logic for each step.
"""

import random
from datetime import date, timedelta

from . import selection
from . import study_char_word
from . import study_cloze
from . import study_find_words
from . import study_ch_en_matching
from studies.models import Word, StudyLog


def create_study_chars_sheet(
    num_chars,
    score_filter=None,
    days_filter=None,
    character_list=None,
    header_text=None,
    study_source=None,
    book_id=None,
    lesson_id=None,
    lesson_ids=None,
):
    """
    Orchestrates the creation of character study sheets as JSON content.
    """
    # Select
    if character_list is not None:
        selected_chars = character_list
    else:
        s = selection.Selection()

        if study_source == "review":
            # Review logic: lowest write retrievability
            s = s.from_fsrs("write", book_id=book_id, lesson_id=lesson_id, lesson_ids=lesson_ids) \
                 .retrievability(min_val=0.000001) \
                 .lowest_retrievability()
            
            if days_filter is not None:
                s = s.remove_any_recent_records(days_filter)
            
            selected_chars = s.take(num_chars)
        else:
            # Basic logic (default)
            s = s.from_learned_lessons(book_id=book_id, lesson_id=lesson_id, lesson_ids=lesson_ids)
            if score_filter is not None:
                s = s.remove_score_greater("read", score_filter)
            if days_filter is not None:
                s = s.remove_any_recent_records(days_filter)

            selected_chars = s.random(num_chars)

    # Generate
    content = study_char_word.generate_content(selected_chars)

    # Return the content as a JSON-serializable structure
    result = {
        'type': 'chars',
        'header_text': header_text,
        'content': content,
        'selected_chars': selected_chars
    }

    return result


def create_ch_en_matching_study(
    num_chars,
    score_filter=None,
    days_filter=None,
    study_source=None,
    header_text=None,
    book_id=None,
    lesson_id=None,
    lesson_ids=None,
):
    """
    Create a Chinese-English matching study as JSON content.
    """
    # Character selection logic (similar to cloze and find_words)
    if study_source == "review":
        s = selection.Selection()
        s.from_fsrs("read", due_only=False, book_id=book_id, lesson_id=lesson_id, lesson_ids=lesson_ids).retrievability(
            min_val=-1, max_val=1
        ).lowest_retrievability()
        if days_filter is not None:
            s.remove_recent_records_by_type(days_filter, ["readstudy"])

        all_sorted_chars = s.get_all()
        pool_size = min(len(all_sorted_chars), num_chars * 3)
        character_pool = all_sorted_chars[:pool_size]
        selected_chars = random.sample(
            character_pool, min(len(character_pool), num_chars)
        )
    else:
        s = selection.Selection()
        s = s.from_learned_lessons(book_id=book_id, lesson_id=lesson_id, lesson_ids=lesson_ids)
        if score_filter is not None:
            s = s.remove_score_greater("read", score_filter)
        if days_filter is not None:
            s = s.remove_any_recent_records(days_filter)

        selected_chars = s.random(num_chars)

    # Generate
    content = study_ch_en_matching.generate_content(selected_chars)

    # Return the content as a JSON-serializable structure
    result = {
        'type': 'ch_en_matching',
        'header_text': header_text,
        'content': content,
        'selected_chars': selected_chars
    }

    return result


def create_failed_study_sheet(
    num_chars,
    header_text=None,
    threshold=None,
    recency_days=None,
):
    """
    Orchestrates the creation of failed character study sheets as JSON content.
    This implementation uses the Django ORM to replicate the logic from the legacy app
    and corrects the truncation algorithm.
    """
    # 1. Set default values
    threshold = threshold if threshold is not None else 5
    recency_days = recency_days if recency_days is not None else 8

    # 2. Get failed characters using the Selection class
    # Calculate cutoff_date
    cutoff_date = (date.today() - timedelta(days=recency_days)).isoformat()

    # 2. Get failed characters using the Selection class
    s = selection.Selection()
    failed_read_chars = s.from_failed_records("read", cutoff_date, threshold).get_all()
    failed_write_chars = s.from_failed_records("write", cutoff_date, threshold).get_all()

    # 3. Combine and truncate the character lists with corrected logic
    read_set = set(failed_read_chars)
    write_set = set(failed_write_chars)
    
    # Characters that failed both read and write are prioritized
    failed_both = list(read_set.intersection(write_set))
    failed_read_only = list(read_set - write_set)
    failed_write_only = list(write_set - read_set)

    # Shuffle to avoid always selecting the same characters if truncation occurs
    random.shuffle(failed_read_only)
    random.shuffle(failed_write_only)

    # Combine in order of priority
    combined_chars = failed_both + failed_read_only + failed_write_only
    
    # Truncate if necessary
    if len(combined_chars) > num_chars:
        final_chars = combined_chars[:num_chars]
    else:
        final_chars = combined_chars

    # Distribute the final characters back into read and write lists for content generation
    final_read_chars = [char for char in final_chars if char in read_set]
    final_write_chars = [char for char in final_chars if char in write_set]

    # 4. Generate content for the final character lists
    # Since we are reusing study_chars.html, we merge them into a single content list.
    # The distinction between read/write failures is implicitly handled by the fact that
    # they are all "failed characters" being reviewed.
    content = study_char_word.generate_content(final_chars)

    # 5. Return the content as a JSON-serializable structure
    result = {
        'type': 'failed',
        'header_text': header_text,
        'content': content,
        'selected_chars': final_chars
    }

    return result


def create_study_review_sheet(
    num_chars, days_filter=None, header_text=None
):
    """
    Orchestrates the creation of review study sheets based on FSRS retrievability as JSON content.
    """
    # Select
    s = selection.Selection()
    s.from_fsrs("write", due_only=False).retrievability(
        min_val=-1, max_val=1
    ).lowest_retrievability()
    if days_filter is not None:
        # Remove characters that have been recently studied
        s.remove_recent_records_by_type(days_filter, ["readstudy", "writestudy"])

    # Get all characters sorted by lowest retrievability
    all_sorted_chars = s.get_all()

    # Take a larger pool of characters, e.g., 3 times the number needed, to introduce randomness
    pool_size = min(len(all_sorted_chars), num_chars * 3)
    character_pool = all_sorted_chars[:pool_size]

    selected_chars = random.sample(character_pool, min(len(character_pool), num_chars))

    # Generate
    content = study_char_word.generate_content(selected_chars)

    # Return the content as a JSON-serializable structure
    result = {
        'type': 'review',
        'header_text': header_text,
        'content': content,
        'selected_chars': selected_chars
    }

    return result


def create_cloze_test(
    num_chars,
    score_filter=None,
    days_filter=None,
    study_source=None,
    header_text=None,
    book_id=None,
    lesson_id=None,
    lesson_ids=None,
):
    """
    Create a cloze test as JSON content.
    """
    if study_source == "review":
        s = selection.Selection()
        s.from_fsrs("read", due_only=False, book_id=book_id, lesson_id=lesson_id, lesson_ids=lesson_ids).retrievability(
            min_val=-1, max_val=1
        ).lowest_retrievability()
        if days_filter is not None:
            s.remove_recent_records_by_type(days_filter, ["readstudy"])

        all_sorted_chars = s.get_all()
        pool_size = min(len(all_sorted_chars), num_chars * 3)
        character_pool = all_sorted_chars[:pool_size]
        selected_chars = random.sample(
            character_pool, min(len(character_pool), num_chars)
        )
    else:
        s = selection.Selection()

        s = s.from_learned_lessons(book_id=book_id, lesson_id=lesson_id, lesson_ids=lesson_ids)
        if score_filter is not None:
            s = s.remove_score_greater("read", score_filter)
        if days_filter is not None:
            s = s.remove_any_recent_records(days_filter)

        selected_chars = s.random(num_chars)

    # Generate
    content = study_cloze.generate_content(selected_chars)

    # Prepare data for the template
    words = [item['word'] for item in content]
    shuffled_sentences = [item['cloze_sentence'] for item in content]
    random.shuffle(words)
    random.shuffle(shuffled_sentences)

    # Return the content as a JSON-serializable structure
    result = {
        'type': 'cloze',
        'header_text': header_text,
        'words': words,
        'sentences': shuffled_sentences,
        'selected_chars': selected_chars
    }

    return result


def create_find_words_puzzle(
    num_chars,
    score_filter=None,
    days_filter=None,
    study_source=None,
    header_text=None,
    book_id=None,
    lesson_id=None,
    lesson_ids=None,
):
    """
    Orchestrates the creation of find-words puzzles as JSON content.
    """
    # Select
    if study_source == "review":
        s = selection.Selection()
        s.from_fsrs("read", due_only=False, book_id=book_id, lesson_id=lesson_id, lesson_ids=lesson_ids).retrievability(
            min_val=-1, max_val=1
        ).lowest_retrievability()
        if days_filter is not None:
            s.remove_recent_records_by_type(days_filter, ["readstudy"])

        all_sorted_chars = s.get_all()
        pool_size = min(len(all_sorted_chars), num_chars * 3)
        character_pool = all_sorted_chars[:pool_size]
        selected_chars = random.sample(
            character_pool, min(len(character_pool), num_chars)
        )
    else:
        s = selection.Selection()

        s = s.from_learned_lessons(book_id=book_id, lesson_id=lesson_id, lesson_ids=lesson_ids)
        if score_filter is not None:
            s = s.remove_score_greater("read", score_filter)
        if days_filter is not None:
            s = s.remove_any_recent_records(days_filter)

        selected_chars = s.random(num_chars)

    # Generate
    content = study_find_words.generate_content(selected_chars)

    # Return the content as a JSON-serializable structure
    result = {
        'type': 'words',
        'header_text': header_text,
        'content': content,
        'selected_chars': selected_chars
    }

    return result


def create_read_exam(
    num_chars,
    character_list=None,
    title=None,
    header_text=None,
    book_id=None,
    lesson_id=None,
    lesson_ids=None,
):
    """
    Orchestrates the creation of read exams as JSON content.
    """
    # Select
    if character_list is not None:
        selected_chars = character_list
    else:
        s = selection.Selection()
        selected_chars = s.from_learned_lessons(book_id=book_id, lesson_id=lesson_id, lesson_ids=lesson_ids).random(num_chars)

    # Return the content as a JSON-serializable structure
    final_title = title if title is not None else "Reading Test"
    final_header_text = (
        header_text
        if header_text is not None
        else f"Test date: ____. Circle the forgotten ones."
    )
    
    result = {
        'type': 'read',
        'title': final_title,
        'header_text': final_header_text,
        'items': selected_chars,
        'items_per_row': 6,
        'font_size': 36
    }

    return result


from studies.models import Word, StudyLog, WordEntry


def create_write_exam(
    num_chars,
    score_filter=None,
    days_filter=None,
    character_list=None,
    title=None,
    header_text=None,
    book_id=None,
    lesson_id=None,
    lesson_ids=None,
):
    """
    Orchestrates the creation of write exams as JSON content.
    This implementation replicates the greedy algorithm from the original Flask app,
    selecting words to maximize character coverage without overlap.
    """
    # 1. Select initial characters
    if character_list is not None:
        selected_chars = character_list
    else:
        s = selection.Selection()
        selected_chars = s.from_learned_lessons(book_id=book_id, lesson_id=lesson_id, lesson_ids=lesson_ids).random(num_chars)

    # 2. Generate word list using the greedy coverage algorithm
    remaining_chars = set(selected_chars)
    final_word_list = []

    for char in selected_chars:
        if char not in remaining_chars:
            continue

        # Get all candidate words containing the current character
        candidate_words = WordEntry.objects.filter(word__contains=char)

        best_word = char
        best_word_score = -1.0
        best_word_covered_count = 1

        # Find the best word among candidates that can be formed from remaining characters
        for entry in candidate_words:
            word_chars = set(entry.word)
            
            # The candidate word is only valid if all its characters are in the pool
            if word_chars.issubset(remaining_chars):
                covered_count = len(word_chars)
                
                # Prioritize words that cover more characters
                if covered_count > best_word_covered_count:
                    best_word_covered_count = covered_count
                    best_word = entry.word
                    best_word_score = entry.score
                # If coverage is the same, prioritize by score
                elif covered_count == best_word_covered_count:
                    if entry.score > best_word_score:
                        best_word = entry.word
                        best_word_score = entry.score
        
        final_word_list.append(best_word)
        remaining_chars -= set(best_word)

    random.shuffle(final_word_list)

    # 3. Return the content as a JSON-serializable structure
    final_title = title if title is not None else "Writing Test"
    final_header_text = (
        header_text
        if header_text is not None
        else f"Test date: ____. Write down the characters."
    )
    
    result = {
        'type': 'write',
        'title': final_title,
        'header_text': final_header_text,
        'items': final_word_list,
        'items_per_row': 4,
        'font_size': 30
    }

    return result



def create_review_exam(exam_type, num_chars, character_list=None):
    """
    Orchestrates the creation of a review exam (read or write) based on FSRS due cards as JSON content.
    This implementation replicates the legacy app's logic of selecting due cards and then
    delegating to the standard exam creation functions.
    """
    # 1. Select due characters using the Selection API
    if character_list is not None:
        due_chars = character_list
    else:
        s = selection.Selection()
        # Note: The Django 'selection' implementation needs to handle FSRS logic.
        # We assume it has been updated to do so.
        due_chars = s.from_fsrs(exam_type, due_only=True).get_all()

    if not due_chars:
        return None  # No due characters, so no exam to generate

    # 2. Limit the number of characters for the review exam
    # The legacy app sorted by due date implicitly. Here we'll just take the first `num_chars`.
    if len(due_chars) > num_chars:
        due_chars = due_chars[:num_chars]

    # 3. Delegate to the appropriate standard exam creation function
    if exam_type == "read":
        title = "Reading Review"
        header_text = f"Reviewing {len(due_chars)} due characters. Test date: ____."
        
        return create_read_exam(
            num_chars=len(due_chars),
            character_list=due_chars,
            title=title,
            header_text=header_text,
        )
    elif exam_type == "write":
        title = "Writing Review"
        header_text = f"Reviewing {len(due_chars)} due characters. Test date: ____."
        
        return create_write_exam(
            num_chars=len(due_chars),
            character_list=due_chars,
            title=title,
            header_text=header_text,
        )
    else:
        raise ValueError(f"Invalid exam type for review: {exam_type}")
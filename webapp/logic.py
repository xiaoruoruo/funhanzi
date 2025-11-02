"""
This module orchestrates the full "select -> generate -> format" pipeline for both studies and exams.
It imports from the new modules that contain the specific logic for each step.
"""

import random

from . import selection
from . import study_char_word
from . import study_cloze
from . import study_find_words
from . import formatter_exam
from . import formatter_char_word
from . import formatter_cloze
from . import formatter_find_words
from . import words_gen


def create_study_chars_sheet(
    conn,
    num_chars,
    lessons,
    output_filename,
    score_filter=None,
    days_filter=None,
    character_list=None,
    header_text=None,
):
    """
    Orchestrates the creation of character study sheets.
    """
    # Select
    if character_list is not None:
        selected_chars = character_list
    else:
        s = selection.Selection(conn)

        # Corrected and simplified selection logic
        s = s.from_lesson_range(lessons)
        if score_filter is not None:
            s = s.remove_score_greater("read", score_filter)
        if days_filter is not None:
            s = s.remove_any_recent_records(days_filter)

        selected_chars = s.random(num_chars)

    # Generate
    content = study_char_word.generate_content(selected_chars)

    # Format
    sections = {"chars": content}
    formatter_char_word.format_html(sections, output_filename, header_text)

    return output_filename


def create_failed_study_sheet(
    conn,
    num_chars,
    output_filename,
    header_text=None,
    threshold=None,
    recency_days=None,
):
    """
    Orchestrates the creation of failed character study sheets.
    """
    # Use default values or provided values for threshold and recency_days
    if threshold is None:
        threshold = 5  # Default threshold
    if recency_days is None:
        recency_days = 8  # Default recency days

    # Calculate cutoff date
    from datetime import date, timedelta

    cutoff_date = (date.today() - timedelta(days=recency_days)).strftime("%Y-%m-%d")

    # Get characters that have failed recent exams
    s = selection.Selection(conn)
    failed_read_chars = s.from_failed_records("read", cutoff_date, threshold).get_all()
    failed_write_chars = s.from_failed_records(
        "write", cutoff_date, threshold
    ).get_all()

    # Combine and limit the total number of characters if necessary
    all_chars = failed_read_chars + failed_write_chars
    if len(all_chars) > num_chars:
        # Limit the number of characters if necessary
        # This uses a simple approach, prioritizing failed read chars first
        total_chars = len(all_chars)
        excess = total_chars - num_chars
        if len(failed_read_chars) > len(failed_write_chars):
            # Remove excess from read chars first
            remove_from_read = min(excess, len(failed_read_chars))
            new_read_chars = failed_read_chars[
                : (len(failed_read_chars) - remove_from_read)
            ]
            failed_read_chars = new_read_chars
            remaining_excess = excess - remove_from_read
            if remaining_excess > 0:
                failed_write_chars = failed_write_chars[
                    : (len(failed_write_chars) - remaining_excess)
                ]
        else:
            # Remove excess from write chars first
            remove_from_write = min(excess, len(failed_write_chars))
            new_write_chars = failed_write_chars[
                : (len(failed_write_chars) - remove_from_write)
            ]
            failed_write_chars = new_write_chars
            remaining_excess = excess - remove_from_write
            if remaining_excess > 0:
                failed_read_chars = failed_read_chars[
                    : (len(failed_read_chars) - remaining_excess)
                ]

    # Generate content for failed characters
    read_content = study_char_word.generate_content(failed_read_chars)
    write_content = study_char_word.generate_content(failed_write_chars)

    # Format using the char_word formatter
    sections = {"read": read_content, "write": write_content}
    formatter_char_word.format_html(sections, output_filename, header_text)

    return output_filename


def create_study_review_sheet(
    conn, num_chars, output_filename, days_filter=None, header_text=None
):
    """
    Orchestrates the creation of review study sheets based on FSRS retrievability.
    """
    # Select
    s = selection.Selection(conn)
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

    # Format
    sections = {"review": content}
    formatter_char_word.format_html(sections, output_filename, header_text)

    return output_filename


def create_cloze_test(
    conn,
    num_chars,
    lessons,
    output_filename,
    score_filter=None,
    days_filter=None,
    study_source=None,
    header_text=None,
):
    if study_source == "review":
        s = selection.Selection(conn)
        s.from_fsrs("read", due_only=False).retrievability(
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
        s = selection.Selection(conn)

        s = s.from_lesson_range(lessons)
        if score_filter is not None:
            s = s.remove_score_greater("read", score_filter)
        if days_filter is not None:
            s = s.remove_any_recent_records(days_filter)

        selected_chars = s.random(num_chars)

    # Generate
    content = study_cloze.generate_content(conn, selected_chars)

    # Format
    formatter_cloze.format_html(content, output_filename, header_text)

    return output_filename


def create_find_words_puzzle(
    conn,
    num_chars,
    lessons,
    output_filename,
    score_filter=None,
    days_filter=None,
    study_source=None,
    header_text=None,
):
    """
    Orchestrates the creation of find-words puzzles.
    """
    # Select
    if study_source == "review":
        s = selection.Selection(conn)
        s.from_fsrs("read", due_only=False).retrievability(
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
        s = selection.Selection(conn)

        s = s.from_lesson_range(lessons)
        if score_filter is not None:
            s = s.remove_score_greater("read", score_filter)
        if days_filter is not None:
            s = s.remove_any_recent_records(days_filter)

        selected_chars = s.random(num_chars)

    # Generate
    content = study_find_words.generate_content(selected_chars)

    # Format
    formatter_find_words.format_html(content, output_filename, header_text)

    return output_filename


def create_read_exam(
    conn,
    num_chars,
    lessons,
    output_filename,
    character_list=None,
    title=None,
    header_text=None,
):
    """
    Orchestrates the creation of read exams.
    """
    # Select
    if character_list is not None:
        selected_chars = character_list
    else:
        s = selection.Selection(conn)
        selected_chars = s.from_lesson_range(lessons).random(num_chars)

    # Format
    final_title = title if title is not None else "Reading Test"
    final_header_text = (
        header_text
        if header_text is not None
        else f"Lessons: {lessons}. Test date: ____. Circle the forgotten ones."
    )
    formatter_exam.format_html(
        items=selected_chars,
        output_filename=output_filename,
        title=final_title,
        header_text=final_header_text,
        items_per_row=6,
        font_size=36,
    )

    return output_filename


def create_write_exam(
    conn,
    num_chars,
    lessons,
    output_filename,
    score_filter=None,
    days_filter=None,
    character_list=None,
    title=None,
    header_text=None,
):
    """
    Orchestrates the creation of write exams.
    """
    # Select
    if character_list is not None:
        selected_chars = character_list
    else:
        s = selection.Selection(conn)
        selected_chars = s.from_lesson_range(lessons).random(num_chars)

    # Generate
    word_list = words_gen.generate_exam_words(conn, selected_chars)
    random.shuffle(word_list)

    # Format
    final_title = title if title is not None else "Writing Test"
    final_header_text = (
        header_text
        if header_text is not None
        else f"Lessons: {lessons}. Test date: ____. Write down the characters."
    )
    formatter_exam.format_html(
        items=word_list,
        output_filename=output_filename,
        title=final_title,
        header_text=final_header_text,
        items_per_row=4,
        font_size=30,
    )

    return output_filename


def create_review_exam(conn, exam_type, num_chars, lessons, output_filename):
    """
    Orchestrates the creation of a review exam (read or write) based on FSRS due cards.
    """
    # Select due characters using the Selection API
    s = selection.Selection(conn)
    due_chars = s.from_fsrs(exam_type, due_only=True).get_all()

    if not due_chars:
        return None  # No due characters, so no exam to generate

    # Limit the number of characters for the review exam
    due_chars = due_chars[:num_chars]

    # Define title and header text based on exam type
    if exam_type == "read":
        title = "Reading Review"
        header_text = f"Reviewing {len(due_chars)} due characters. Test date: ____."
        create_read_exam(
            conn,
            num_chars,
            lessons,
            output_filename,
            character_list=due_chars,
            title=title,
            header_text=header_text,
        )
    elif exam_type == "write":
        title = "Writing Review"
        header_text = f"Reviewing {len(due_chars)} due characters. Test date: ____."
        create_write_exam(
            conn,
            num_chars,
            lessons,
            output_filename,
            character_list=due_chars,
            title=title,
            header_text=header_text,
        )
    else:
        raise ValueError(f"Invalid exam type: {exam_type}")

    return output_filename

import argparse
import random
import sys

from .exam_formatter import generate_exam_html
from .exam_record import filter_chars_by_score, filter_chars_by_days
from .words import get_lesson, parse_lesson_ranges



def main():
    """
    Main function to parse arguments and generate the exam.
    """
    parser = argparse.ArgumentParser(
        description="Generate an exam with random Chinese characters for recognition."
    )
    parser.add_argument(
        "num_chars",
        type=int,
        help="The total number of characters to include in the exam."
    )
    parser.add_argument(
        "lessons",
        type=str,
        help='Lessons to choose characters from. e.g., "2,3,5", "2-8", or "2-8,10".'
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="output",
        help="The base name for the output HTML file (default: output)."
    )
    parser.add_argument(
        "--score_filter",
        type=int,
        help="Exclude characters with a score >= to this value. Requires record.db."
    )
    parser.add_argument(
        "--days_filter",
        type=int,
        help="Exclude characters tested in the last N days. Requires record.db."
    )
    args = parser.parse_args()

    lesson_numbers = parse_lesson_ranges(args.lessons)

    char_pool = []
    for num in lesson_numbers:
        lesson_chars = get_lesson(num)
        if lesson_chars:
            char_pool.extend(list(lesson_chars))
        else:
            print(f"Warning: Lesson {num} not found or is empty.", file=sys.stderr)

    if not char_pool:
        print("Error: No characters available from the specified lessons.", file=sys.stderr)
        sys.exit(1)
        
    unique_chars = list(set(char_pool))

    if args.score_filter is not None:
        unique_chars = filter_chars_by_score(unique_chars, "read", args.score_filter)
        unique_chars = filter_chars_by_score(unique_chars, "readstudy", args.score_filter)

    if args.days_filter is not None:
        unique_chars = filter_chars_by_days(unique_chars, args.days_filter)

    unique_chars_count = len(unique_chars)
    if unique_chars_count == 0:
        print("Error: No characters left after filtering.", file=sys.stderr)
        sys.exit(1)

    if args.num_chars > unique_chars_count:
        print(f"Warning: Requested {args.num_chars} characters, but only {unique_chars_count} unique characters are available. Using all {unique_chars_count} unique characters in random order.", file=sys.stderr)

    num_to_select = min(args.num_chars, unique_chars_count)
    selected_chars = random.sample(unique_chars, k=num_to_select)

    title = "Reading Test"
    header_text = f"Lessons: {args.lessons}. Test date: ____. Circle the forgotten ones."
    generate_exam_html(
        items=selected_chars,
        output_filename=args.output,
        title=title,
        header_text=header_text,
        items_per_row=6,
        font_size=36
    )

    print(f"Successfully generated HTML file: {args.output}.html")
    print("You can open this file in a web browser and print it.")


if __name__ == "__main__":
    main()

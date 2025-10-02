import argparse
import os
import random
import sys

from . import exam_formatter
from .ai import get_gemini_model

def main():
    """Main function to generate study material for characters."""
    parser = argparse.ArgumentParser(description="Generate study material for characters.")
    parser.add_argument(
        "num_chars",
        type=int,
        help="The total number of characters to select for studying.",
    )
    parser.add_argument(
        "lessons",
        type=str,
        help='Lessons to choose characters from. e.g., "2,3,5", "2-8", or "2-8,10".'
    )
    parser.add_argument(
        "--days_filter",
        type=int,
        help="Exclude characters tested in the last N days. Requires record.db."
    )
    parser.add_argument(
        "--score_filter",
        type=int,
        help="Exclude characters with a score >= to this value. Requires record.db."
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="study_sheet",
        help="The name of the output HTML file (without extension).",
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

    if not unique_chars:
        print("Error: No characters left after filtering.", file=sys.stderr)
        sys.exit(1)

    unique_chars_count = len(unique_chars)

    if args.num_chars > unique_chars_count:
        print(f"Warning: Requested {args.num_chars} characters, but only {unique_chars_count} unique characters are available. Using all {unique_chars_count} characters.", file=sys.stderr)

    num_to_select = min(args.num_chars, unique_chars_count)
    selected_chars = random.sample(unique_chars, k=num_to_select)

    print(f"Selected {len(selected_chars)} characters to study: {''.join(selected_chars)}")

    model = get_gemini_model()


    characters_data = []
    # Generate pinyin and words for the selected characters.
    for char in selected_chars:
        prompt = f"请为“{char}”这个字，提供它的拼音，以及一个最常见的、由两个字组成的词语。请用这个格式返回：拼音，词语。例如：pīn yīn, 词语"
        response = model.generate_content(prompt)
        try:
            pinyin, word = response.text.strip().split(",", 1)
            characters_data.append((char, pinyin.strip(), word.strip()))
        except ValueError:
            print(f"Warning: Could not parse response for '{char}': {response.text.strip()}", file=sys.stderr)
            characters_data.append((char, "N/A", "N/A"))

    exam_formatter.format_study_sheet_html(characters_data, args.output)
    print(f"Successfully generated study sheet: {args.output}.html")


if __name__ == "__main__":
    main()

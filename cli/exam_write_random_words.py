import argparse
import os
import random
import sys
import time

import google.generativeai as genai
from .exam_formatter import generate_exam_html
from .exam_record import filter_chars_by_score, filter_chars_by_days
from .words import get_lesson, parse_lesson_ranges
from .ai import get_gemini_model


def main():
    """
    Main function to parse arguments and generate the exam.
    """
    parser = argparse.ArgumentParser(
        description="Generate a writing exam with words made from random Chinese characters."
    )
    parser.add_argument(
        "num_chars",
        type=int,
        help="The total number of characters to draw from to create words."
    )
    parser.add_argument(
        "lessons",
        type=str,
        help='Lessons to choose characters from. e.g., "2,3,5", "2-8", or "2-8,10".'
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="output_write",
        help="The base name for the output HTML file (default: output_write)."
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

    model = get_gemini_model()

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
        unique_chars = filter_chars_by_score(unique_chars, "write", args.score_filter)
        unique_chars = filter_chars_by_score(unique_chars, "writestudy", args.score_filter)

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
    
    print(f"Selected {len(selected_chars)} unique characters.")


    
    remaining_chars = set(selected_chars)
    final_word_list = []
    
    # Keep calling API as long as we have enough characters to form words
    while len(remaining_chars) > 1:
        chunk_size = 30
        
        current_char_list = list(remaining_chars)
        chunk = random.sample(current_char_list, k=min(chunk_size, len(current_char_list)))

        char_list_str = "".join(chunk)
        prompt = (
            f"From this list of Chinese characters: {char_list_str}\n"
            "Create as many common two-character words as you can. "
            "Use ONLY characters from the provided list. "
            "Output the words separated by spaces. Do not output anything else."
        )
        print(f"Asking AI to form words for: {char_list_str}")

        try:
            response = model.generate_content(prompt)
            text_response = response.text.strip().replace('`', '')
            generated_words = text_response.split()
            
            random.shuffle(generated_words)
            
            chunk_set = set(chunk)
            for word in generated_words:
                word_chars = set(word)
                # Ensure word is made of chars from the chunk and they are still available
                if len(word) > 1 and word_chars.issubset(chunk_set) and word_chars.issubset(remaining_chars):
                    final_word_list.append(word)
                    remaining_chars -= word_chars
            
            time.sleep(1) # Respect API rate limits

        except Exception as e:
            print(f"An error occurred with the Gemini API: {e}", file=sys.stderr)
            print("Stopping AI word generation.", file=sys.stderr)
            break
    
    unused_chars = list(remaining_chars)
    final_word_list.extend(unused_chars)
    random.shuffle(final_word_list)
    
    num_generated_words = len(final_word_list) - len(unused_chars)
    print(f"Generated {num_generated_words} words and {len(unused_chars)} single characters.")

    title = "Writing Test"
    header_text = f"Lessons: {args.lessons}. Test date: ____. Write down the characters."
    generate_exam_html(
        items=final_word_list,
        output_filename=args.output,
        title=title,
        header_text=header_text,
        items_per_row=4,
        font_size=30
    )

    print(f"Successfully generated HTML file: {args.output}.html")
    print("You can open this file in a web browser and print it.")


if __name__ == "__main__":
    main()

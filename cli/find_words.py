import argparse
import json
import os
import random
import sys

import google.generativeai as genai
from dotenv import load_dotenv
from exam_formatter import format_find_words_html
from exam_record import filter_chars_by_days, filter_chars_by_score
from words import get_lesson, parse_lesson_ranges

GRID_SIZE = 8

def generate_grid(sentence, words, filler_chars):
    """
    Generates the 8x8 character grid based on the new algorithm.
    """
    # Step 1: Initialize an empty 8x8 grid.
    grid = [[None for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]

    # Step 2: Place the sentence characters in a random path.
    # Start at a random row in the first column.
    start_row = random.randint(0, GRID_SIZE - 1)
    r, c = start_row, 0
    
    # Place each character of the sentence and find the next random, empty cell.
    for char in sentence:
        grid[r][c] = char
        
        # Find all valid, empty neighboring cells for the next move.
        possible_moves = []
        # Check all 8 directions (including diagonals).
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue # Skip the current cell itself.
                
                # Heavily prefer moving to the right to ensure the sentence progresses.
                if dc < 1 and random.random() < 0.4:
                    continue

                nr, nc = r + dr, c + dc
                
                # Check if the new position is within the grid and is empty.
                if 0 <= nr < GRID_SIZE and 0 <= nc < GRID_SIZE and grid[nr][nc] is None:
                    possible_moves.append((nr, nc))

        # Choose a random next move from the possible options.
        if possible_moves:
            r, c = random.choice(possible_moves)
        else:
            # If there are no available neighbors, the path is stuck.
            print("Warning: Ran out of space for the sentence.", file=sys.stderr)
            return

    # Step 3: Place the words horizontally in random empty spots.
    # First, get a list of all cells that are still empty.
    empty_cells = []
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            if grid[r][c] is None:
                empty_cells.append((r, c))
    
    random.shuffle(empty_cells)
    
    # For each word, find an empty horizontal slot of two characters.
    for word in words:
        is_filled = False
        # Iterate through the shuffled empty cells to find a suitable spot.
        while empty_cells:
            r, c = empty_cells.pop()
            # Check if the current cell and the one to its right are both empty.
            if grid[r][c] is None and c + 1 < GRID_SIZE and grid[r][c+1] is None:
                grid[r][c] = word[0]
                grid[r][c+1] = word[1]
                is_filled = True
                break # Move to the next word.

        if not is_filled:
            print("Warning: Ran out of space for words.", file=sys.stderr)
            return

    # Step 4: Fill any remaining empty cells with random filler characters.
    empty_cells = []
    for r in range(GRID_SIZE):
        for c in range(GRID_SIZE):
            if grid[r][c] is None:
                empty_cells.append((r, c))

    for r, c in empty_cells:
        if filler_chars:
            grid[r][c] = random.choice(filler_chars)

    return grid, start_row


def main():
    """
    Main function to parse arguments and generate the find words exam.
    """
    parser = argparse.ArgumentParser(
        description="Generate a 'find words' exam paper."
    )
    parser.add_argument(
        "num_chars",
        type=int,
        help="The total number of characters to use as a base for the exam."
    )
    parser.add_argument(
        "lessons",
        type=str,
        help='Lessons to choose characters from. e.g., "2,3,5", "2-8", or "2-8,10".'
    )
    parser.add_argument(
        "-o", "--output",
        type=str,
        default="find_words_exam",
        help="The base name for the output HTML file (default: find_words_exam)."
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

    num_to_select = min(args.num_chars, unique_chars_count)
    selected_chars = random.sample(unique_chars, k=num_to_select)
    
    print(f"Selected {len(selected_chars)} characters: {''.join(selected_chars)}")

    # Load environment variables from .env file
    load_dotenv()

    # Configure the generative AI model
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in .env file.", file=sys.stderr)
        sys.exit(1)
    genai.configure(api_key=api_key)

    model = genai.GenerativeModel("gemini-2.5-flash")

    characters_str = "".join(selected_chars)
    prompt = f"""
请根据以下汉字：'{characters_str}'
1. 生成8个双字词语。这些词语应该尽可能使用列表中的汉字。
2. 生成一个包含部分词语的简单句子。

请以JSON格式返回，不要包含任何其他说明文字或代码块标记。结构如下：
{{
  "words": ["词语1", "词语2", "词语3", "词语4", "词语5", "词语6", "词语7", "词语8"],
  "sentence": "一个句子。"
}}
"""

    print("Generating content with Gemini...")
    response = model.generate_content(prompt)

    try:
        cleaned_text = response.text.strip()
        if cleaned_text.startswith("```json"):
            cleaned_text = cleaned_text[7:]
        if cleaned_text.endswith("```"):
            cleaned_text = cleaned_text[:-3]
        
        data = json.loads(cleaned_text)
        words = data["words"]
        sentence = data["sentence"]
    except (json.JSONDecodeError, KeyError) as e:
        print(f"Error: Failed to parse response from Gemini.", file=sys.stderr)
        print(f"Received text: {response.text}", file=sys.stderr)
        print(f"Error details: {e}", file=sys.stderr)
        sys.exit(1)

    grid, start_row = generate_grid(sentence, words, selected_chars)

    format_find_words_html(
        words=words,
        sentence=sentence,
        grid=grid,
        start_row=start_row,
        output_filename=args.output,
        title="找朋友"
    )

    print(f"Successfully generated HTML file: {args.output}.html")


if __name__ == "__main__":
    main()
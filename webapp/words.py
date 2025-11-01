import os
import sys

_lessons = []
# Get the directory where this script is located
script_dir = os.path.dirname(os.path.abspath(__file__))
# Construct the full path to words.txt
words_txt_path = os.path.join(script_dir, "..", "words.txt")

with open(words_txt_path, "r", encoding="utf-8") as f:
    for line in f:
        # remove any whitespace and store if not empty
        cleaned_line = "".join(line.split())
        if cleaned_line:
            _lessons.append(cleaned_line)


def get_lesson(lesson_number):
    """
    Retrieves characters for a given lesson number.
    Lesson numbers are 1-based.
    Returns None if lesson_number is out of bounds.
    """
    index = lesson_number - 1
    if 0 <= index < len(_lessons):
        return _lessons[index]
    return None


def parse_lesson_ranges(lesson_str):
    """
    Parses a string of lesson ranges into a sorted list of unique lesson numbers.
    e.g., "1,3-5,8" -> [1, 3, 4, 5, 8]
    """
    lessons = set()
    parts = lesson_str.split(",")
    for part in parts:
        part = part.strip()
        if not part:
            continue
        if "-" in part:
            try:
                start, end = map(int, part.split("-"))
                if start > end:
                    print(
                        f"Error: Invalid lesson range '{part}'. Start is greater than end.",
                        file=sys.stderr,
                    )
                    sys.exit(1)
                lessons.update(range(start, end + 1))
            except ValueError:
                print(f"Error: Invalid lesson range format '{part}'.", file=sys.stderr)
                sys.exit(1)
        else:
            try:
                lessons.add(int(part))
            except ValueError:
                print(f"Error: Invalid lesson number '{part}'.", file=sys.stderr)
                sys.exit(1)
    return sorted(list(lessons))

from dataclasses import dataclass
from typing import List
import random
import sys
from google import genai
from pydantic import BaseModel

from studies.models import WordEntry
from . import selection


class SentencesResponse(BaseModel):
    sentences: List[str]


@dataclass
class FindWordsContent:
    words: List[str]
    sentence: str

    def to_dict(self):
        return {"words": self.words, "sentence": self.sentence}


def get_learned_chars() -> set:
    """Fetches all unique characters with FSRS retrievability > 0.9."""
    return set(
        selection.Selection()
        .from_fsrs("read", due_only=False)
        .retrievability(min_val=0.9)
        .get_all()
    )


def generate_content(characters: List[str]) -> dict:
    """
    Generate find-words puzzle content with words and a sentence containing those words.

    Args:
        characters: List of Chinese characters to generate content for

    Returns:
        A dictionary representing the FindWordsContent object.
    """
    # Get words from the database
    words_with_scores = []
    for char in characters:
        entries = WordEntry.objects.filter(word__contains=char)
        for entry in entries:
            words_with_scores.append((entry.word, entry.score))

    learned_chars = get_learned_chars()
    allowed_chars = set(characters).union(learned_chars)

    # Filter for 2-character words, unique, and select 8 with score >= 0.8
    two_char_words_filtered = []
    seen_words = set()
    for w, score in words_with_scores:
        if len(w) == 2 and score >= 0.8 and w not in seen_words:
            if any(c in characters for c in w) and all(c in allowed_chars for c in w):
                two_char_words_filtered.append(w)
                seen_words.add(w)

    random.shuffle(two_char_words_filtered)
    selected_words = two_char_words_filtered[:8]

    print(f"汉字: {characters} 词语: {selected_words}")

    if not selected_words:
        print(
            "Error: Could not find enough words to generate the puzzle.",
            file=sys.stderr,
        )
        fallback_content = FindWordsContent(words=["错误"] * 8, sentence="无法生成句子")
        return fallback_content.to_dict()

    allowed_chars_set = set(characters).union(learned_chars).union(set("，。"))
    characters_set = set(characters)

    words_str = ", ".join(selected_words)

    client = genai.Client()
    best_sentence = "无法生成句子"
    best_score = -float("inf")

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=f"""
你是一个小学语文老师。请根据以下词语：
- 词语列表: '{words_str}'

请生成5个包含部分词语的句子。
每个句子必须满足以下条件：
   - 长度在10到18个汉字。
""",
            config={
                "response_mime_type": "application/json",
                "response_schema": SentencesResponse,
            },
        )

        response_data: SentencesResponse = response.parsed
        candidate_sentences = response_data.sentences

        for sentence in candidate_sentences:
            if len(sentence) > 18:
                continue

            score = 0
            # Rule 1: +1 for each character in `characters`
            for char in sentence:
                if char in characters_set:
                    score += 1

            # Rule 2: +4 for each word in `selected_words`
            for word in selected_words:
                if word in sentence:
                    score += 4

            # Rule 3: -4 for each character not in `allowed_chars`
            for char in sentence:
                if char not in allowed_chars_set:
                    score -= 4

            print(f"{score} points: {sentence}")
            if score > best_score:
                best_score = score
                best_sentence = sentence

    except Exception as e:
        print(f"Could not generate or parse sentences: {e}", file=sys.stderr)

    if best_score < 6:
        print("No great sentence generated, using fallback.", file=sys.stderr)
        best_sentence = "无法为这些词语生成一个好的句子。"


    final_content = FindWordsContent(words=selected_words, sentence=best_sentence)
    return final_content.to_dict()


def generate_grid(
    sentence: str, words: List[str], filler_chars: List[str]
) -> tuple[List[List[str]], int]:
    """
    Generate a character grid with the sentence laid out and words placed in it.

    Args:
        sentence: The sentence to be laid out in the grid
        words: The words to be placed in the grid
        filler_chars: Characters to fill empty spaces

    Returns:
        Tuple of (grid, start_row) where grid is the 8x8 character grid and start_row is the row where the sentence starts
    """
    GRID_SIZE = 8
    grid = [[None for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
    start_row = random.randint(0, GRID_SIZE - 1)
    r, c = start_row, 0

    # Lay out the sentence in the grid
    for char in sentence:
        if r < GRID_SIZE and c < GRID_SIZE:
            grid[r][c] = char
        possible_moves = []
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                if dr == 0 and dc == 0:
                    continue
                if dc < 1 and random.random() < 0.4:
                    continue
                nr, nc = r + dr, c + dc
                if 0 <= nr < GRID_SIZE and 0 <= nc < GRID_SIZE and grid[nr][nc] is None:
                    possible_moves.append((nr, nc))
        if possible_moves:
            r, c = random.choice(possible_moves)
        else:
            break

    # Collect empty cells
    empty_cells = []
    for r_ in range(GRID_SIZE):
        for c_ in range(GRID_SIZE):
            if grid[r_][c_] is None:
                empty_cells.append((r_, c_))

    # Randomly shuffle empty cells
    random.shuffle(empty_cells)

    # Place words in the grid
    for word in words:
        is_filled = False
        while empty_cells and not is_filled:
            r_, c_ = empty_cells.pop()
            if grid[r_][c_] is None and c_ + 1 < GRID_SIZE and grid[r_][c_ + 1] is None:
                grid[r_][c_] = word[0]
                grid[r_][c_ + 1] = word[1]
                is_filled = True
                break

    # Collect remaining empty cells
    empty_cells = [
        (r_, c_)
        for r_ in range(GRID_SIZE)
        for c_ in range(GRID_SIZE)
        if grid[r_][c_] is None
    ]

    # Fill remaining empty cells with random filler characters
    for r_, c_ in empty_cells:
        if filler_chars:
            grid[r_][c_] = random.choice(filler_chars)

    return grid, start_row

import random
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class FindWordsContent:
    words: List[str]
    sentence: str


def generate_grid(
    sentence: str, words: List[str], filler_chars: List[str]
) -> Tuple[List[List[str]], int]:
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


def format_html(
    content: FindWordsContent, output_filename: str, header_text: str = None
):
    """
    Format find words puzzle as HTML.

    Args:
        content: FindWordsContent object containing words and sentence
        output_filename: Path to output HTML file
        header_text: Optional header text to display
    """
    grid, start_row = generate_grid(
        content.sentence, content.words, list(set("".join(content.words)))
    )

    start_marker_top = f"calc((100% / 16) + (100% / 8) * {start_row})"

    html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>找朋友</title>
    <style>
        @page {{ size: letter; margin: 1in; }}
        body {{ font-family: 'Songti SC', 'STSong', serif; font-size: 16pt; display: flex; flex-direction: column; align-items: center; }}
        .container {{ width: 80%; }}
        h1 {{ text-align: center; margin-bottom: 20px; }}
        .header {{ font-size: 10pt; text-align: right; padding-bottom: 20px; page-break-inside: avoid; }}
        .word-list {{ display: flex; flex-wrap: wrap; justify-content: center; gap: 10px; margin-bottom: 20px; padding: 0; list-style: none; }}
        .word-item {{ border: 2px solid #ccc; border-radius: 25px; padding: 5px 15px; }}
        .instructions {{ text-align: center; margin-bottom: 20px; }}
        .sentence-box {{ border: 2px dotted #999; padding: 15px; margin-bottom: 20px; text-align: center; font-size: 18pt; }}
        .grid-container {{ position: relative; width: 100%; margin: 0 auto; }}
        .char-grid {{ display: grid; grid-template-columns: repeat(8, 1fr); border-top: 2px solid black; border-left: 2px solid black; }}
        .grid-cell {{ border-right: 2px solid black; border-bottom: 2px solid black; aspect-ratio: 1 / 1; display: flex; align-items: center; justify-content: center; font-size: 24pt; }}
        .start-marker {{ position: absolute; left: -30px; top: {start_marker_top}; transform: translateY(-50%); color: orange; font-size: 20pt; }}
    </style>
</head>
<body>
    <h1>找朋友</h1>
    <div class="container">"""

    if header_text:
        html_content += f'        <div class="header"><p>{header_text}</p></div>\n'

    html_content += f"""        <ul class="word-list">{"".join(f'<li class="word-item">{word}</li>' for word in content.words)}</ul>
        <p class="instructions">逐一读出词组，并将词组在下方方格中圈出。将下方的句子连起来。</p>
        <div class="sentence-box">{content.sentence}</div>
        <div class="grid-container">
            <div class="char-grid">{"".join(f'<div class="grid-cell">{char if char is not None else ""}</div>' for row in grid for char in row)}</div>
            <div class="start-marker">▶</div>
        </div>
    </div>
</body>
</html>"""

    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(html_content)

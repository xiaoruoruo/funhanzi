import random


def generate_exam_html(
    items, output_filename, title, header_text, items_per_row, font_size
):
    html_content = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset='UTF-8'>",
        f"<title>{title}</title>",
        "<style>",
        "  @page { size: letter; margin: 1in; }",
        "  body { font-family: 'Songti SC', 'STSong', serif; }",
        "  h1 { text-align: center; }",
        "  .items-grid { display: grid;",
        f"   grid-template-columns: repeat({items_per_row}, 1fr);",
        "    gap: 1em 0;",
        "  }",
        "  .item {",
        f"   font-size: {font_size}pt;",
        "    display: flex;",
        "    align-items: center;",
        "    justify-content: center;",
        "  }",
        "  .header { font-size: 10pt; text-align: right; padding-bottom: 20px; page-break-inside: avoid; }",
        "</style>",
        "</head>",
        "<body>",
        f"<h1>{title}</h1>",
    ]
    html_content.append("<div class='header'>")
    html_content.append(f"<p>{header_text}</p>")
    html_content.append("</div>")
    if items:
        html_content.append("<div class='items-grid'>")
        for item in items:
            html_content.append(f"<div class='item'>{item}</div>")
        html_content.append("</div>")
    html_content.extend(["</body>", "</html>"])
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write("\n".join(html_content))


def generate_failed_study_sheet(
    failed_read_chars, failed_write_chars, output_filename, header_text
):
    html_content = [
        "<!DOCTYPE html>",
        "<html>",
        "<head>",
        "<meta charset='UTF-8'>",
        "<title>Character Review</title>",
        "<style>",
        "  @page { size: letter; margin: 1in; }",
        "  body { font-family: 'Songti SC', 'STSong', serif; }",
        "  h1, h2 { text-align: center; }",
        "  .items-grid { display: grid;",
        "   grid-template-columns: repeat(6, 1fr);",
        "    gap: 1em 0;",
        "  }",
        "  .item {",
        "   font-size: 36pt;",
        "    display: flex;",
        "    align-items: center;",
        "    justify-content: center;",
        "  }",
        "  .header { font-size: 10pt; text-align: right; padding-bottom: 20px; page-break-inside: avoid; }",
        "  .section { margin-bottom: 40px; }",
        "</style>",
        "</head>",
        "<body>",
        "<h1>Character Review</h1>",
    ]
    html_content.append("<div class='header'>")
    html_content.append(f"<p>{header_text}</p>")
    html_content.append("</div>")

    if failed_read_chars:
        html_content.append("<div class='section'>")
        html_content.append("<h2>Reading Practice</h2>")
        html_content.append("<div class='items-grid'>")
        for item in failed_read_chars:
            html_content.append(f"<div class='item'>{item}</div>")
        html_content.append("</div></div>")

    if failed_write_chars:
        html_content.append("<div class='section'>")
        html_content.append("<h2>Writing Practice</h2>")
        html_content.append("<div class='items-grid'>")
        for item in failed_write_chars:
            html_content.append(f"<div class='item'>{item}</div>")
        html_content.append("</div></div>")

    html_content.extend(["</body>", "</html>"])
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write("\n".join(html_content))


def format_study_sheet_html(characters_data, output_filename):
    html = """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>汉字学习</title>
    <style>
        @page { size: letter; margin: 0.75in; }
        body { font-family: 'Songti SC', 'STSong', serif; font-size: 18pt; }
        h1 { text-align: center; margin-bottom: 20px; }
        table { width: 100%; border-collapse: collapse; margin-top: 20px; }
        th, td { border: 1px solid #000; padding: 15px; text-align: center; height: 60px; }
        th { background-color: #f2f2f2; font-weight: bold; }
        .character-col { width: 10%; }
        .pinyin-col { width: 15%; }
        .word-col { width: 20%; }
        .empty-col { width: 11%; }
    </style>
</head>
<body>
    <h1>汉字学习</h1>
    <table>
        <thead>
            <tr>
                <th class="character-col">汉字</th>
                <th class="pinyin-col">拼音</th>
                <th class="word-col">词语</th>
                <th class="empty-col"></th><th class="empty-col"></th><th class="empty-col"></th>
                <th class="empty-col"></th><th class="empty-col"></th>
            </tr>
        </thead>
        <tbody>
"""
    for char, pinyin, word in characters_data:
        html += f"""
            <tr>
                <td>{char}</td><td>{pinyin}</td><td>{word}</td>
                <td></td><td></td><td></td><td></td><td></td>
            </tr>
"""
    html += "</tbody></table></body></html>"
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(html)


def format_find_words_html(
    words, sentence, grid, start_row, output_filename, title="找朋友"
):
    start_marker_top = f"calc((100% / 16) + (100% / 8) * {start_row})"
    html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        @page {{ size: letter; margin: 1in; }}
        body {{ font-family: 'Songti SC', 'STSong', serif; font-size: 16pt; display: flex; flex-direction: column; align-items: center; }}
        .container {{ width: 80%; }}
        h1 {{ text-align: center; margin-bottom: 20px; }}
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
    <h1>{title}</h1>
    <div class="container">
        <ul class="word-list">{"".join(f'<li class="word-item">{word}</li>' for word in words)}</ul>
        <p class="instructions">逐一读出词组，并将词组在下方方格中圈出。将下方的句子连起来。</p>
        <div class="sentence-box">{sentence}</div>
        <div class="grid-container">
            <div class="char-grid">{"".join(f'<div class="grid-cell">{char if char is not None else ""}</div>' for row in grid for char in row)}</div>
            <div class="start-marker">▶</div>
        </div>
    </div>
</body>
</html>
"""
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(html_content)


def format_cloze_test_html(pairs, output_filename, title="句子填空"):
    words = [p[0] for p in pairs]
    sentences = [p[1] for p in pairs]
    random.shuffle(words)
    random.shuffle(sentences)

    html_content = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>{title}</title>
    <style>
        @page {{ size: letter; margin: 1in; }}
        body {{ font-family: 'Songti SC', 'STSong', serif; font-size: 16pt; }}
        .container {{ width: 90%; margin: auto; }}
        h1 {{ text-align: center; margin-bottom: 20px; }}
        .instructions {{ text-align: center; margin-bottom: 30px; }}
        .cloze-table {{ width: 100%; border-collapse: collapse; }}
        .cloze-table td {{ padding: 15px 5px; vertical-align: middle; }}
        .word-cell {{ width: 25%; text-align: center; }}
        .sentence-cell {{ width: 75%; }}
        .word-box {{ border: 2px solid #ccc; border-radius: 15px; padding: 10px 20px; display: inline-block; }}
        .bullet {{ font-size: 20px; margin-right: 10px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <p class="instructions">找出句子中正确的词组，将它们连起来。</p>
        <table class="cloze-table">
"""
    for i in range(len(words)):
        html_content += f"""
            <tr>
                <td class="word-cell"><div class="word-box">{words[i]}</div></td>
                <td class="sentence-cell"><span class="bullet">&bull;</span>{sentences[i]}</td>
            </tr>
"""
    html_content += """
        </table>
    </div>
</body>
</html>
"""
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(html_content)

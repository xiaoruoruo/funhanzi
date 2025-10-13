import random
from dataclasses import dataclass
from typing import List


@dataclass
class ClozeEntry:
    word: str
    cloze_sentence: str


def format_html(content: List[ClozeEntry], output_filename: str, header_text: str = None):
    """
    Format cloze tests as HTML.
    
    Args:
        content: List of ClozeEntry objects containing words and sentences
        output_filename: Path to output HTML file
        header_text: Optional header text to display
    """
    # Extract words and sentences to shuffle them separately
    words = [entry.word for entry in content]
    sentences = [entry.cloze_sentence for entry in content]
    
    # Shuffle both lists to mix the content
    random.shuffle(words)
    random.shuffle(sentences)

    html_content = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>句子填空</title>
    <style>
        @page {{ size: letter; margin: 1in; }}
        body {{ font-family: 'Songti SC', 'STSong', serif; font-size: 16pt; }}
        .container {{ width: 90%; margin: auto; }}
        h1 {{ text-align: center; margin-bottom: 20px; }}
        .header {{ font-size: 10pt; text-align: right; padding-bottom: 20px; page-break-inside: avoid; }}
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
        <h1>句子填空</h1>'''
    
    if header_text:
        html_content += f'        <div class="header"><p>{header_text}</p></div>\n'
    
    html_content += '''        <p class="instructions">找出句子中正确的词组，将它们连起来。</p>
        <table class="cloze-table">
'''
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
</html>"""
    
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(html_content)
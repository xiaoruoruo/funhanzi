from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class CharWordEntry:
    char: str
    pinyin: str
    word: str


def format_html(sections: dict[str, List[CharWordEntry]], output_filename: str, header_text: str = None):
    """
    Format character/word study sheets as HTML.
    
    Args:
        sections: A dictionary where keys are section names and values are lists of CharWordEntry objects
        output_filename: Path to output HTML file
        header_text: Optional header text to display
    """
    html = '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>汉字学习</title>
    <style>
        @page { size: letter; margin: 0.75in; }
        body { font-family: 'Songti SC', 'STSong', serif; font-size: 18pt; }
        h1 { text-align: center; margin-bottom: 20px; }
        h2 { text-align: center; margin-top: 30px; margin-bottom: 15px; }
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
    <h1>汉字学习</h1>'''
    
    if header_text:
        html += f'    <div class="header"><p>{header_text}</p></div>\n'
    
    for section_name, entries in sections.items():
        if section_name:  # Only add section header if section name exists 
            html += f'    <h2>{section_name}</h2>\n'
        html += '''    <table>
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
'''
        for entry in entries:
            html += f"""            <tr>
                <td>{entry.char}</td><td>{entry.pinyin}</td><td>{entry.word}</td>
                <td></td><td></td><td></td><td></td><td></td>
            </tr>
"""
        html += "        </tbody></table>\n"
    
    html += "</body></html>"
    
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(html)
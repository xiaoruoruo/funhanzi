from dataclasses import dataclass
from typing import List
import random
from . import ai
import json


@dataclass
class ClozeEntry:
    word: str
    cloze_sentence: str


def generate_content(characters: List[str]) -> List[ClozeEntry]:
    """
    Generate cloze test entries with words and sentences containing blanks.
    
    Args:
        characters: List of Chinese characters to generate content for
        
    Returns:
        List of ClozeEntry objects containing word and cloze sentence
    """
    model = ai.get_gemini_model()
    characters_str = "".join(characters)
    prompt = f"""
    我在给2年级的孩子准备中文生字复习，请根据以下汉字：'{characters_str}'
    1. 生成5个双字词语。这些词语要使用到列表中的汉字，每个汉字只能用一次。
    2. 为每个词语生成一个包含该词语的简单句子。

    请以JSON格式返回，不要包含任何其他说明文字或代码块标记。结构如下：
    {{
      "pairs": [
        {{"word": "词语1", "sentence": "包含词语1的句子。"}},
        {{"word": "词语2", "sentence": "包含词语2的句子。"}},
        {{"word": "词语3", "sentence": "包含词语3的句子。"}},
        {{"word": "词语4", "sentence": "包含词语4的句子。"}},
        {{"word": "词语5", "sentence": "包含词语5的句子。"}}
      ]
    }}
    """
    response = ai.generate_content(model, prompt)
    try:
        if response is not None:
            cleaned_text = response.text.strip()
            if cleaned_text.startswith("```json"):
                cleaned_text = cleaned_text[7:]
            if cleaned_text.endswith("```"):
                cleaned_text = cleaned_text[:-3]
            data = json.loads(cleaned_text)
        else:
            print("Failed to generate cloze test data")
            data = {"pairs": [{"word": "错误", "sentence": "无法生成句子"}] * 5}
        
        pairs = []
        for item in data['pairs']:
            word = item['word']
            sentence = item['sentence']
            cloze_sentence = sentence.replace(word, '（ ）', 1)
            pairs.append(ClozeEntry(
                word=word,
                cloze_sentence=cloze_sentence
            ))
    except (json.JSONDecodeError, KeyError) as e:
        print(f"无法生成句子: {e}")
        pairs = [ClozeEntry(word="错误", cloze_sentence="无法生成句子")] * 5

    return pairs
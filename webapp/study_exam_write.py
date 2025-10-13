from typing import List
import random
from . import ai


def generate_content(characters: List[str]) -> List[str]:
    """
    Generate a list of words for write exam based on the given characters.
    
    Args:
        characters: List of Chinese characters to generate words for
        
    Returns:
        List of words that contain the given characters
    """
    model = ai.get_gemini_model()
    
    remaining_chars = set(characters)
    final_word_list = []
    tries = 4
    
    while len(remaining_chars) > 1 and tries > 0:
        print("Remaining chars ", remaining_chars)
        tries -= 1
        chunk_size = 30
        current_char_list = list(remaining_chars)
        chunk = random.sample(current_char_list, k=min(chunk_size, len(current_char_list)))
        char_list_str = "".join(chunk)
        prompt = (
            f"给定以下中文字: {char_list_str}\n"
            "请根据这些中文字组词，尽可能的只使用给定的字。如果实在有个字不能组词，可以用给定的字以外的字来为它组词，但一定要是简单的字。"
            "给定的字每个字都要有组词。"
            "输出词语，每个词语之间用空格分割，不要输出任何其他的内容。"
        )

        try:
            response = ai.generate_content(model, prompt)
            if response is not None:
                text_response = response.text.strip().replace('`', '')
            else:
                print(f"Failed to generate content for prompt, continuing...")
                continue
        except ValueError:
            print(f"ValueError when generating words for prompt, continuing...")
            continue
        generated_words = text_response.split()
        print("Generated Words", generated_words)
        
        random.shuffle(generated_words)
        
        for word in generated_words:
            final_word_list.append(word)
            remaining_chars -= set(word)
    
    unused_chars = list(remaining_chars)
    final_word_list.extend(unused_chars)
    random.shuffle(final_word_list)

    return final_word_list
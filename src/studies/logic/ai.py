import os
import sys
from google import genai
from dotenv import load_dotenv


def get_gemini_client():
    """
    Initializes and returns a Gemini client.
    """
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: Neither GOOGLE_API_KEY nor GEMINI_API_KEY found in environment variables.", file=sys.stderr)
        raise ValueError("Neither GOOGLE_API_KEY nor GEMINI_API_KEY found in environment variables.")
    return genai.Client(api_key=api_key)


def generate_content(client, prompt, model_name="gemini-2.5-flash"):
    """
    Wrapper function to generate content using the specified model and prompt.
    """
    try:
        response = client.models.generate_content(model=model_name, contents=prompt)
        return response
    except Exception as e:
        print(f"Error generating content: {e}")
        return None

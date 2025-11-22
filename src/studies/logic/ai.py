import os
import sys
from google import genai
from dotenv import load_dotenv


def get_gemini_client():
    """
    Initializes and returns a Gemini client.
    """
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in .env file.", file=sys.stderr)
        # In a Django context, raising an exception might be better than sys.exit
        raise ValueError("GEMINI_API_KEY not found in environment variables.")
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

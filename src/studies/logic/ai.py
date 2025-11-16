import os
import sys
import google.generativeai as genai
from dotenv import load_dotenv


def get_gemini_model(model_name="gemini-2.5-flash"):
    """
    Initializes and returns a Gemini generative model.
    """
    load_dotenv()
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        print("Error: GEMINI_API_KEY not found in .env file.", file=sys.stderr)
        # In a Django context, raising an exception might be better than sys.exit
        raise ValueError("GEMINI_API_KEY not found in environment variables.")
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name)


def generate_content(model, prompt):
    """
    Wrapper function to generate content using the specified model and prompt.
    """
    try:
        response = model.generate_content(prompt)
        return response
    except Exception as e:
        print(f"Error generating content: {e}")
        return None

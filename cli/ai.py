
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
        sys.exit(1)
    genai.configure(api_key=api_key)
    return genai.GenerativeModel(model_name)

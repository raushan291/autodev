import os
from dotenv import load_dotenv
import google.generativeai as genai
from app.config import settings

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")

if not API_KEY:
    raise ValueError("GEMINI_API_KEY not found in .env")

genai.configure(api_key=API_KEY)


def ask_llm(prompt: str, model_name: str = None):
    if model_name is None:
        model_name = settings.DEFAULT_MODEL
    
    model = genai.GenerativeModel(model_name)
    response = model.generate_content(prompt)
    return response.text

"""
gemini_flash_generator.py
Generates a concise nutrition or recovery tip using Gemini 1.5 Flash.
"""

import os
from dotenv import load_dotenv
from google import genai

load_dotenv()

_api_key = os.getenv("GEMINI_API_KEY")
if not _api_key:
    raise EnvironmentError("GEMINI_API_KEY is not set in the .env file.")

_client = genai.Client(api_key=_api_key)
_FLASH_MODEL = "gemini-1.5-flash"


def generate_nutrition_tip_with_flash(goal: str) -> str:
    """
    Call Gemini 1.5 Flash to generate a short, practical nutrition or
    recovery tip tailored to the user's fitness goal.

    Returns a single sentence (max ~30 words).
    """
    prompt = f"""
You are FitBuddy, a certified nutritionist and recovery coach.
Give one concise, actionable nutrition or recovery tip (a single sentence,
max 30 words) specifically for someone whose fitness goal is: {goal}.

Focus on one of: hydration, protein intake, sleep, meal timing, or
post-workout recovery. Return only the tip sentence — no labels, no bullet
points, no extra text.
"""
    try:
        response = _client.models.generate_content(model=_FLASH_MODEL, contents=prompt)
        return response.text.strip()
    except Exception as exc:
        raise RuntimeError(f"Gemini Flash error during tip generation: {exc}") from exc

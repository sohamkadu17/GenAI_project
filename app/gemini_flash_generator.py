"""
gemini_flash_generator.py
Generates a concise nutrition or recovery tip using Gemini 1.5 Flash.
"""

import os
import time
from dotenv import load_dotenv
from google import genai

load_dotenv()

_api_key = os.getenv("GEMINI_API_KEY")
if not _api_key:
    raise EnvironmentError("GEMINI_API_KEY is not set in the .env file.")

_client = genai.Client(api_key=_api_key)
_FLASH_MODEL = "gemini-2.0-flash-lite"  # highest free-tier quota

_RETRY_DELAYS = [5, 15]

# Static fallback tips used when the API quota is exhausted
_FALLBACK_TIPS: dict[str, str] = {
    "Weight Loss":           "Aim for a 300-500 kcal daily deficit and prioritise protein to preserve muscle while cutting.",
    "Muscle Gain":           "Consume 1.6–2.2 g of protein per kg of bodyweight daily and eat in a slight caloric surplus.",
    "Improve Endurance":     "Stay well-hydrated during training and replenish glycogen with complex carbs within 30 min of finishing.",
    "General Fitness":       "Eat whole foods, keep protein at each meal, and aim for 7–9 hours of sleep for optimal recovery.",
    "Flexibility & Mobility":"Hydrate consistently throughout the day and consider magnesium-rich foods to support muscle relaxation.",
}
_DEFAULT_TIP = "Fuel your workouts with balanced meals, stay hydrated, and prioritise 7–9 hours of quality sleep each night."


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
    last_exc = None
    for delay in (*_RETRY_DELAYS, None):
        try:
            response = _client.models.generate_content(model=_FLASH_MODEL, contents=prompt)
            return response.text.strip()
        except Exception as exc:
            last_exc = exc
            if "429" in str(exc) and delay is not None:
                time.sleep(delay)
                continue
            break
    # Quota exhausted — return a static tip rather than failing the whole request
    return _FALLBACK_TIPS.get(goal, _DEFAULT_TIP)

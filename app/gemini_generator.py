"""
gemini_generator.py
Generates a personalised 7-day workout plan using Gemini 1.5 Pro.
"""

import os
import json
import re
import time
from dotenv import load_dotenv
from google import genai

load_dotenv()

_api_key = os.getenv("GEMINI_API_KEY")
if not _api_key:
    raise EnvironmentError("GEMINI_API_KEY is not set in the .env file.")

_client = genai.Client(api_key=_api_key)
_PRO_MODEL = "gemini-2.0-flash-lite"  # highest free-tier quota

_MAX_RETRIES = 3
_RETRY_DELAYS = [5, 15, 30]  # seconds between retries on 429


def _extract_json(text: str) -> dict:
    """Strip markdown fences and parse the first JSON object in the response."""
    clean = re.sub(r"```(?:json)?", "", text).replace("```", "").strip()
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", clean, re.DOTALL)
    if match:
        return json.loads(match.group())
    raise ValueError(f"Could not parse JSON from Gemini Pro response:\n{text}")


def generate_workout_gemini(name: str, age: int, weight: float, goal: str, intensity: str) -> dict:
    """
    Call Gemini 1.5 Pro to generate a structured 7-day workout plan.

    Returns a dict with keys 'Day 1' … 'Day 7'. Each day contains:
      - focus     : muscle group / theme
      - warmup    : 5-10 min warm-up description
      - exercises : list of {name, sets, reps}
      - cooldown  : cooldown / recovery tip
    """
    prompt = f"""
You are FitBuddy, a professional personal trainer.
Create a detailed, personalised 7-day workout plan for this user:

- Name      : {name}
- Age       : {age} years
- Weight    : {weight} kg
- Goal      : {goal}
- Intensity : {intensity}

Return ONLY valid JSON — no extra text, no markdown — using exactly this structure:

{{
  "Day 1": {{
    "focus": "<muscle group or theme>",
    "warmup": "<5–10 min warm-up description>",
    "exercises": [
      {{"name": "<exercise name>", "sets": <integer>, "reps": "<reps or duration>"}},
      ...
    ],
    "cooldown": "<cooldown or recovery tip>"
  }},
  "Day 2": {{ ... }},
  ...
  "Day 7": {{ ... }}
}}

Ensure the plan is realistic, progressive, and appropriate for the given intensity.
Rest days should still include light activity or stretching.
"""
    last_exc = None
    for attempt, delay in enumerate((*_RETRY_DELAYS, None), start=1):
        try:
            response = _client.models.generate_content(model=_PRO_MODEL, contents=prompt)
            return _extract_json(response.text)
        except ValueError as exc:
            raise RuntimeError(f"Failed to parse workout plan JSON: {exc}") from exc
        except Exception as exc:
            last_exc = exc
            if "429" in str(exc) and delay is not None:
                time.sleep(delay)
                continue
            raise RuntimeError(f"Gemini Pro error during plan generation: {exc}") from exc
    raise RuntimeError(f"Gemini Pro error during plan generation: {last_exc}") from last_exc

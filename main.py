import os
import json
import re
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, Depends, HTTPException, Request, Form
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel
from sqlalchemy.orm import Session
from dotenv import load_dotenv
import google.generativeai as genai

from database import engine, get_db, Base
import models

# ---------------------------------------------------------------------------
# Startup
# ---------------------------------------------------------------------------
load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

if not GEMINI_API_KEY:
    raise RuntimeError("GEMINI_API_KEY is not set. Add it to your .env file.")

genai.configure(api_key=GEMINI_API_KEY)
gemini_model = genai.GenerativeModel("gemini-1.5-flash")


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="FitBuddy", lifespan=lifespan)
templates = Jinja2Templates(directory="templates")


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------
class GenerateRequest(BaseModel):
    name: str
    age: int
    weight: float
    goal: str
    intensity: str


class RefineRequest(BaseModel):
    plan_id: int
    feedback: str


# ---------------------------------------------------------------------------
# Gemini helpers
# ---------------------------------------------------------------------------
def _extract_json(text: str) -> dict:
    """Pull the first JSON object / code-block from a Gemini response."""
    # Strip markdown fences if present
    clean = re.sub(r"```(?:json)?", "", text).replace("```", "").strip()
    # Try to parse the whole string
    try:
        return json.loads(clean)
    except json.JSONDecodeError:
        pass
    # Fallback: grab the first {...} block
    match = re.search(r"\{.*\}", clean, re.DOTALL)
    if match:
        return json.loads(match.group())
    raise ValueError(f"Could not parse JSON from Gemini response:\n{text}")


def generate_plan_from_gemini(name: str, age: int, weight: float, goal: str, intensity: str) -> dict:
    prompt = f"""
You are FitBuddy, an expert personal trainer.
Create a personalised 7-day workout plan for the following user:

- Name      : {name}
- Age       : {age} years
- Weight    : {weight} kg
- Goal      : {goal}
- Intensity : {intensity}

Return ONLY valid JSON with no extra commentary, in this exact structure:
{{
  "Day 1": {{"focus": "<muscle group / theme>", "exercises": [{{"name": "<exercise>", "sets": <int>, "reps": "<reps or duration>"}}]}},
  "Day 2": ...,
  ...
  "Day 7": ...
}}
"""
    try:
        response = gemini_model.generate_content(prompt)
        return _extract_json(response.text)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Gemini error (generate): {exc}")


def refine_plan_from_gemini(current_plan: dict, feedback: str) -> dict:
    prompt = f"""
You are FitBuddy, an expert personal trainer.
A user has the following 7-day workout plan:

{json.dumps(current_plan, indent=2)}

The user's feedback is: "{feedback}"

Update the plan according to the feedback and return ONLY a valid JSON object
with the same Day 1 – Day 7 structure. No extra text.
"""
    try:
        response = gemini_model.generate_content(prompt)
        return _extract_json(response.text)
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Gemini error (refine): {exc}")


def get_tip_from_gemini(goal: str) -> str:
    prompt = f"""
You are FitBuddy, a nutrition and recovery expert.
Give one short, practical tip (a single sentence, max 25 words) for someone
whose fitness goal is: {goal}.
Return only the tip sentence, no labels or extra text.
"""
    try:
        response = gemini_model.generate_content(prompt)
        return response.text.strip()
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"Gemini error (tip): {exc}")


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/generate")
async def generate(payload: GenerateRequest, db: Session = Depends(get_db)):
    """Scenario 1 – create user and generate initial 7-day plan."""
    # Persist user
    user = models.User(
        name=payload.name,
        age=payload.age,
        weight=payload.weight,
        goal=payload.goal,
        intensity=payload.intensity,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    # Generate plan via Gemini
    plan_dict = generate_plan_from_gemini(
        payload.name, payload.age, payload.weight, payload.goal, payload.intensity
    )

    # Fetch a tip while we're at it
    tip = get_tip_from_gemini(payload.goal)

    # Persist plan
    plan = models.WorkoutPlan(
        user_id=user.id,
        plan_json=json.dumps(plan_dict),
        nutrition_tip=tip,
    )
    db.add(plan)
    db.commit()
    db.refresh(plan)

    return {
        "plan_id": plan.id,
        "user_id": user.id,
        "plan": plan_dict,
        "tip": tip,
    }


@app.post("/refine")
async def refine(payload: RefineRequest, db: Session = Depends(get_db)):
    """Scenario 2 – refine an existing plan based on user feedback."""
    plan = db.query(models.WorkoutPlan).filter(models.WorkoutPlan.id == payload.plan_id).first()
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found.")

    current_plan = json.loads(plan.plan_json)
    updated_plan = refine_plan_from_gemini(current_plan, payload.feedback)

    plan.plan_json = json.dumps(updated_plan)
    plan.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(plan)

    return {
        "plan_id": plan.id,
        "plan": updated_plan,
        "tip": plan.nutrition_tip,
    }


@app.get("/tip/{goal}")
async def tip(goal: str):
    """Scenario 3 – get a nutrition / recovery tip for a given goal."""
    tip_text = get_tip_from_gemini(goal)
    return {"goal": goal, "tip": tip_text}

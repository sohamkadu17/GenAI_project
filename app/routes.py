"""
routes.py
Core route handlers for the FitBuddy FastAPI application.

Route map
─────────
GET  /                  → index.html  (user input form)
POST /generate-workout  → calls generate_workout_gemini() + generate_nutrition_tip_with_flash()
GET  /result/{plan_id}  → result.html (plan display + feedback form)
POST /submit-feedback   → calls update_workout_plan() with original plan + feedback
GET  /view-all-users    → all_users.html (admin dashboard)
"""

import json
import os
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session

from .database import (
    get_db, save_user, save_plan, update_plan,
    get_original_plan, get_all_users,
)
from .gemini_generator import generate_workout_gemini
from .gemini_flash_generator import generate_nutrition_tip_with_flash
from .updated_plan import update_workout_plan
from .schemas import UserInput, FeedbackRequest  # noqa: F401  (used as annotations / docs)

# ---------------------------------------------------------------------------
# Templates (resolved relative to this file's directory)
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=os.path.join(BASE_DIR, "templates"))

router = APIRouter()


# ---------------------------------------------------------------------------
# GET /  –  User input form
# ---------------------------------------------------------------------------
@router.get("/")
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


# ---------------------------------------------------------------------------
# POST /generate-workout  –  Scenario 1: process form → generate plan + tip
#
# Form fields (UserInput schema):  username, user_id, age, weight, goal, intensity
# Gemini calls:
#   1. generate_workout_gemini()          → Gemini 1.5 Pro  → 7-day JSON plan
#   2. generate_nutrition_tip_with_flash() → Gemini 1.5 Flash → tip string
# ---------------------------------------------------------------------------
@router.post("/generate-workout",
             summary="Generate a personalised 7-day workout plan",
             description="Accepts HTML form input (UserInput schema), calls Gemini 1.5 Pro "
                         "for the workout plan and Gemini 1.5 Flash for a nutrition tip, "
                         "persists both, then redirects to /result/{plan_id}.")
async def generate_workout(
    request:   Request,
    username:  str   = Form(..., description="Display name of the user"),
    user_id:   str   = Form(..., description="Unique user identifier"),
    age:       int   = Form(..., ge=10, le=100),
    weight:    float = Form(..., ge=20.0, description="Weight in kg"),
    goal:      str   = Form(..., description="Fitness goal"),
    intensity: str   = Form(..., description="low | medium | high"),
    db: Session = Depends(get_db),
):
    try:
        # ── 1. Persist user (username maps to 'name' column, user_id stored as note) ──
        user = save_user(db, name=username, age=age, weight=weight,
                         goal=goal, intensity=intensity)

        # ── 2. generate_workout_gemini()  →  Gemini 1.5 Pro ──
        plan_dict = generate_workout_gemini(username, age, weight, goal, intensity)

        # ── 3. generate_nutrition_tip_with_flash()  →  Gemini 1.5 Flash ──
        tip = generate_nutrition_tip_with_flash(goal)

        # ── 4. Persist plan ──
        plan = save_plan(db, user_id=user.id,
                         original_plan=json.dumps(plan_dict), nutrition_tip=tip)

    except RuntimeError as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return RedirectResponse(url=f"/result/{plan.id}", status_code=303)


# ---------------------------------------------------------------------------
# GET /result/{plan_id}  –  Display plan, tip, and feedback form
# ---------------------------------------------------------------------------
@router.get("/result/{plan_id}")
async def result(request: Request, plan_id: int, db: Session = Depends(get_db)):
    plan = get_original_plan(db, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found.")

    # Use updated plan if available, else original
    active_json = plan.updated_plan if plan.updated_plan else plan.original_plan
    try:
        active_plan = json.loads(active_json)
    except json.JSONDecodeError:
        active_plan = {}

    return templates.TemplateResponse("result.html", {
        "request":      request,
        "plan":         active_plan,
        "tip":          plan.nutrition_tip,
        "plan_id":      plan.id,
        "user":         plan.user,
        "is_updated":   bool(plan.updated_plan),
    })


# ---------------------------------------------------------------------------
# POST /submit-feedback  –  Scenario 2: refine plan via update_workout_plan()
#
# Form fields (FeedbackRequest schema): plan_id, feedback
# Gemini call:
#   update_workout_plan(original_plan, feedback) → Gemini 1.5 Pro → updated JSON plan
# ---------------------------------------------------------------------------
@router.post("/submit-feedback",
             summary="Refine an existing workout plan",
             description="Accepts plan_id + free-text feedback (FeedbackRequest schema). "
                         "Retrieves the existing plan, sends it with the feedback to "
                         "update_workout_plan() (Gemini 1.5 Pro), saves the updated plan, "
                         "then redirects to /result/{plan_id}.")
async def submit_feedback(
    plan_id:  int = Form(..., gt=0, description="ID of the plan to refine"),
    feedback: str = Form(..., min_length=1, description="User feedback for plan refinement"),
    db: Session = Depends(get_db),
):
    plan = get_original_plan(db, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found.")

    try:
        # Use most recent version as the base for refinement
        base_json = plan.updated_plan if plan.updated_plan else plan.original_plan
        base_dict = json.loads(base_json)

        # ── update_workout_plan()  →  Gemini 1.5 Pro ──
        updated_dict = update_workout_plan(base_dict, feedback)
        update_plan(db, plan_id=plan_id, updated_plan=json.dumps(updated_dict))

    except (RuntimeError, json.JSONDecodeError) as exc:
        raise HTTPException(status_code=502, detail=str(exc))

    return RedirectResponse(url=f"/result/{plan_id}", status_code=303)


# ---------------------------------------------------------------------------
# GET /view-all-users  –  Admin dashboard
# ---------------------------------------------------------------------------
@router.get("/view-all-users")
async def view_all_users(request: Request, db: Session = Depends(get_db)):
    users = get_all_users(db)
    # Attach parsed plan data to each user for easy template rendering
    users_data = []
    for user in users:
        user_plans = []
        for p in user.plans:
            active_json = p.updated_plan if p.updated_plan else p.original_plan
            try:
                plan_dict = json.loads(active_json)
            except Exception:
                plan_dict = {}
            user_plans.append({
                "id":         p.id,
                "plan":       plan_dict,
                "tip":        p.nutrition_tip,
                "is_updated": bool(p.updated_plan),
                "created_at": p.created_at,
                "updated_at": p.updated_at,
            })
        users_data.append({"user": user, "plans": user_plans})

    return templates.TemplateResponse("all_users.html", {
        "request":    request,
        "users_data": users_data,
    })

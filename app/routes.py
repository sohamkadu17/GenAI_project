"""
routes.py
Core route handlers for the FitBuddy FastAPI application.
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
# POST /generate  –  Scenario 1: create user + generate initial plan
# ---------------------------------------------------------------------------
@router.post("/generate")
async def generate(
    request: Request,
    name:      str   = Form(...),
    age:       int   = Form(...),
    weight:    float = Form(...),
    goal:      str   = Form(...),
    intensity: str   = Form(...),
    db: Session = Depends(get_db),
):
    try:
        # 1. Persist user
        user = save_user(db, name=name, age=age, weight=weight, goal=goal, intensity=intensity)

        # 2. Generate 7-day plan (Gemini 1.5 Pro)
        plan_dict = generate_workout_gemini(name, age, weight, goal, intensity)

        # 3. Generate nutrition tip (Gemini 1.5 Flash)
        tip = generate_nutrition_tip_with_flash(goal)

        # 4. Persist plan
        plan = save_plan(db, user_id=user.id, original_plan=json.dumps(plan_dict), nutrition_tip=tip)

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
# POST /feedback  –  Scenario 2: refine plan based on feedback
# ---------------------------------------------------------------------------
@router.post("/feedback")
async def feedback(
    plan_id:  int = Form(...),
    feedback: str = Form(...),
    db: Session = Depends(get_db),
):
    plan = get_original_plan(db, plan_id)
    if not plan:
        raise HTTPException(status_code=404, detail="Plan not found.")

    try:
        # Use the most recent plan as the base
        base_json = plan.updated_plan if plan.updated_plan else plan.original_plan
        base_dict = json.loads(base_json)

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

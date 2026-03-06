from pydantic import BaseModel, Field
from typing import Optional


class UserCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=100)
    age: int = Field(..., ge=10, le=100)
    weight: float = Field(..., ge=20.0)
    goal: str = Field(..., min_length=1)
    intensity: str = Field(..., pattern="^(low|medium|high)$")


class FeedbackRequest(BaseModel):
    plan_id: int
    feedback: str = Field(..., min_length=1)


class PlanResponse(BaseModel):
    plan_id: int
    user_id: int
    original_plan: str
    updated_plan: Optional[str] = None
    nutrition_tip: Optional[str] = None

    class Config:
        from_attributes = True

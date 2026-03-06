import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, Float, Text, DateTime, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship

# ---------------------------------------------------------------------------
# Engine & session
# ---------------------------------------------------------------------------
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATABASE_URL = f"sqlite:///{os.path.join(BASE_DIR, 'fitbuddy.db')}"

engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


# ---------------------------------------------------------------------------
# ORM models
# ---------------------------------------------------------------------------
class User(Base):
    __tablename__ = "users"

    id         = Column(Integer, primary_key=True, index=True)
    user_id    = Column(String(50), nullable=True, index=True)  # unique identifier from form
    name       = Column(String(100), nullable=False)
    age        = Column(Integer, nullable=False)
    weight     = Column(Float, nullable=False)
    goal       = Column(String(100), nullable=False)
    intensity  = Column(String(50), nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    plans = relationship("Plan", back_populates="user")


class Plan(Base):
    __tablename__ = "plans"

    id            = Column(Integer, primary_key=True, index=True)
    user_id       = Column(Integer, ForeignKey("users.id"), nullable=False)
    original_plan = Column(Text, nullable=False)
    updated_plan  = Column(Text, nullable=True)
    nutrition_tip = Column(Text, nullable=True)
    created_at    = Column(DateTime, default=datetime.utcnow)
    updated_at    = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="plans")


# ---------------------------------------------------------------------------
# DB dependency (for FastAPI)
# ---------------------------------------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    Base.metadata.create_all(bind=engine)


# ---------------------------------------------------------------------------
# CRUD helpers
# ---------------------------------------------------------------------------
def save_user(db, name: str, age: int, weight: float, goal: str,
              intensity: str, user_id: str = None) -> User:
    user = User(name=name, age=age, weight=weight, goal=goal,
                intensity=intensity, user_id=user_id)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def save_plan(db, user_id: int, original_plan: str, nutrition_tip: str) -> Plan:
    plan = Plan(user_id=user_id, original_plan=original_plan, nutrition_tip=nutrition_tip)
    db.add(plan)
    db.commit()
    db.refresh(plan)
    return plan


def update_plan(db, plan_id: int, updated_plan: str) -> Plan:
    plan = db.query(Plan).filter(Plan.id == plan_id).first()
    if not plan:
        return None
    plan.updated_plan = updated_plan
    plan.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(plan)
    return plan


def get_original_plan(db, plan_id: int) -> Plan:
    return db.query(Plan).filter(Plan.id == plan_id).first()


def get_user(db, user_id: int) -> User:
    return db.query(User).filter(User.id == user_id).first()


def get_all_users(db):
    return db.query(User).order_by(User.created_at.desc()).all()


def get_all_plans(db):
    """Return every plan ordered newest-first, with user eagerly loaded."""
    return db.query(Plan).order_by(Plan.created_at.desc()).all()

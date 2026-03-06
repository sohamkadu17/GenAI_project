# 💪 FitBuddy – AI-Powered Fitness Planner

FitBuddy is a full-stack web application that generates personalised 7-day workout plans using Google's Gemini AI. Users can submit their fitness profile, receive a structured plan, refine it with natural-language feedback, and get targeted nutrition/recovery tips.

---

## Features

- **AI Plan Generation** – Gemini creates a structured 7-day workout plan in JSON format based on your profile.
- **Feedback & Refinement** – Tell FitBuddy what to change ("more cardio", "too hard") and it updates the plan instantly.
- **Nutrition / Recovery Tips** – Get a concise, goal-specific tip powered by Gemini.
- **Persistent Storage** – Users and workout plans are saved to a local SQLite database.
- **Modern UI** – Dark-themed single-page interface built with Tailwind CSS.

---

## Tech Stack

| Layer     | Technology                          |
|-----------|-------------------------------------|
| Backend   | FastAPI (Python 3.10+)              |
| AI        | Google Gemini API (Gemini 1.5 Pro + 1.5 Flash) |
| Database  | SQLite + SQLAlchemy ORM             |
| Frontend  | Jinja2 Templates + Tailwind CSS CDN |
| Config    | python-dotenv                       |

---

## Project Structure

```
fitbuddy/
├── requirements.txt              # Project dependencies
│
├── app/
│   ├── main.py                   # FastAPI entry point
│   ├── routes.py                 # Core route handlers
│   ├── database.py               # SQLAlchemy models and DB logic (CRUD helpers)
│   ├── schemas.py                # Pydantic models for validation
│   ├── gemini_generator.py       # Gemini 1.5 Pro – workout plan generator
│   ├── gemini_flash_generator.py # Gemini 1.5 Flash – nutrition tips
│   ├── updated_plan.py           # Feedback-based plan updater
│   ├── nutrition.py              # Nutrition context helpers (optional)
│   │
│   └── templates/
│       ├── index.html            # User input form
│       ├── result.html           # Workout plan, tip, feedback
│       └── all_users.html        # Admin dashboard
│
├── static/
│   └── images/
│       └── gym-bg.jpg            # Gym-themed background (add your own)
│
├── .env                          # GEMINI_API_KEY (not committed)
├── .gitignore
└── fitbuddy.db                   # SQLite database (auto-generated)
```

---

## Getting Started

### Prerequisites

- Python 3.10 or higher
- A [Google Gemini API key](https://aistudio.google.com/app/apikey)

### 1. Clone the Repository

```bash
git clone <your-repo-url>
cd GenAI_project
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Edit the `.env` file and add your Gemini API key:

```env
GEMINI_API_KEY=your_actual_gemini_api_key_here
```

### 4. Run the Application

```bash
uvicorn app.main:app --reload
```

> **Optional:** Add your own `gym-bg.jpg` to `static/images/` for the background image on the home screen.

### 5. Open in Browser

Navigate to [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## API Endpoints

### `GET /`
Serves the user input form (`index.html`).

---

### `GET /result/{plan_id}`
Renders the workout plan, nutrition tip, and feedback form for plan `plan_id`.

---

### `POST /generate`
Creates a new user profile and generates an initial 7-day workout plan.

**Form Fields** (submitted via HTML form):
```
name=Alex Johnson&age=25&weight=70&goal=Weight Loss&intensity=medium
```

**Response:** Redirects to `GET /result/{plan_id}` (HTTP 303).

---

### `POST /feedback`
Refines an existing workout plan based on user feedback.

**Form Fields:**
```
plan_id=1&feedback=too hard, add more rest days
```

**Response:** Redirects to `GET /result/{plan_id}` (HTTP 303).

---

### `GET /view-all-users`
Admin dashboard showing all registered users and their plans in an expandable table.

---

## Database Schema

### `users`
| Column     | Type    | Description                         |
|------------|---------|-------------------------------------|
| id         | Integer | Primary key                         |
| name       | String  | User's full name                    |
| age        | Integer | User's age in years                 |
| weight     | Float   | User's weight in kg                 |
| goal       | String  | Fitness goal (e.g., Weight Loss)    |
| intensity  | String  | Workout intensity (low/medium/high) |
| created_at | DateTime| Timestamp of record creation        |

### `plans`
| Column        | Type    | Description                                      |
|---------------|---------|--------------------------------------------------|
| id            | Integer | Primary key                                      |
| user_id       | Integer | Foreign key → users.id                           |
| original_plan | Text    | Initial Gemini-generated plan (JSON string)      |
| updated_plan  | Text    | Feedback-refined plan (JSON string, nullable)    |
| nutrition_tip | Text    | Gemini Flash tip                                 |
| created_at    | DateTime| Timestamp of creation                            |
| updated_at    | DateTime| Timestamp of last refinement                     |

---

## How It Works

```
index.html  ──POST /generate──►  routes.py
                                     │
                                     ├─ save_user()          → SQLite users
                                     ├─ generate_workout_gemini()   (Gemini 1.5 Pro)
                                     ├─ generate_nutrition_tip_with_flash()  (Gemini 1.5 Flash)
                                     └─ save_plan()          → SQLite plans
                                              │
                                              ▼
                                    redirect → /result/{plan_id}
                                              │
                                              ▼
                                        result.html
                                              │
                              POST /feedback (feedback text)
                                              │
                                     update_workout_plan()   (Gemini 1.5 Pro)
                                              │
                                     update_plan()           → SQLite plans.updated_plan
                                              │
                                    redirect → /result/{plan_id}

/view-all-users  ──►  get_all_users()  ──►  all_users.html
```

## Module Responsibilities

| Module | Responsibility |
|--------|----------------|
| `app/main.py` | App factory, lifespan, static mounting, router registration |
| `app/routes.py` | All HTTP route handlers, template rendering |
| `app/database.py` | ORM models (`User`, `Plan`), engine setup, CRUD helpers |
| `app/schemas.py` | Pydantic request/response validation models |
| `app/gemini_generator.py` | `generate_workout_gemini()` via Gemini 1.5 Pro |
| `app/gemini_flash_generator.py` | `generate_nutrition_tip_with_flash()` via Gemini 1.5 Flash |
| `app/updated_plan.py` | `update_workout_plan()` – feedback-based refinement |
| `app/nutrition.py` | Macro/food context helpers for enriching prompts |

---

## Environment Variables

| Variable        | Required | Description                  |
|-----------------|----------|------------------------------|
| `GEMINI_API_KEY`| Yes      | Your Google Gemini API key   |

---

## License

This project is licensed under the MIT License.

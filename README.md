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
| AI        | Google Gemini API (`gemini-1.5-flash`) |
| Database  | SQLite + SQLAlchemy ORM             |
| Frontend  | Jinja2 Templates + Tailwind CSS CDN |
| Config    | python-dotenv                       |

---

## Project Structure

```
GenAI_project/
├── main.py              # FastAPI app, API routes, Gemini integration
├── models.py            # SQLAlchemy ORM models (User, WorkoutPlan)
├── database.py          # Database engine, session, and base setup
├── requirements.txt     # Python dependencies
├── .env                 # Environment variables (API key) — not committed
├── .gitignore
└── templates/
    └── index.html       # Single-page frontend UI
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
uvicorn main:app --reload
```

### 5. Open in Browser

Navigate to [http://127.0.0.1:8000](http://127.0.0.1:8000)

---

## API Endpoints

### `GET /`
Serves the main frontend page.

---

### `POST /generate`
Creates a new user profile and generates an initial 7-day workout plan.

**Request Body:**
```json
{
  "name": "Alex Johnson",
  "age": 25,
  "weight": 70.0,
  "goal": "Weight Loss",
  "intensity": "medium"
}
```

**Response:**
```json
{
  "plan_id": 1,
  "user_id": 1,
  "plan": {
    "Day 1": { "focus": "Cardio", "exercises": [...] },
    ...
    "Day 7": { "focus": "Rest & Stretch", "exercises": [...] }
  },
  "tip": "Drink at least 2 litres of water daily to support fat metabolism."
}
```

---

### `POST /refine`
Refines an existing workout plan based on user feedback.

**Request Body:**
```json
{
  "plan_id": 1,
  "feedback": "too hard, add more rest days"
}
```

**Response:**
```json
{
  "plan_id": 1,
  "plan": { "Day 1": {...}, ... },
  "tip": "..."
}
```

---

### `GET /tip/{goal}`
Returns a single nutrition or recovery tip for a given fitness goal.

**Example:** `GET /tip/Weight Loss`

**Response:**
```json
{
  "goal": "Weight Loss",
  "tip": "Include protein in every meal to reduce hunger and preserve muscle mass."
}
```

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

### `workout_plans`
| Column        | Type    | Description                       |
|---------------|---------|-----------------------------------|
| id            | Integer | Primary key                       |
| user_id       | Integer | Foreign key → users.id            |
| plan_json     | Text    | 7-day plan stored as JSON string  |
| nutrition_tip | Text    | Latest tip from Gemini            |
| created_at    | DateTime| Timestamp of creation             |
| updated_at    | DateTime| Timestamp of last refinement      |

---

## How It Works

```
User submits form
       │
       ▼
FastAPI /generate
       │
       ├─→ Save User to SQLite
       │
       ├─→ Build prompt → Gemini API → Parse JSON plan
       │
       ├─→ Fetch tip → Gemini API
       │
       └─→ Save WorkoutPlan to SQLite → Return to frontend

User submits feedback
       │
       ▼
FastAPI /refine
       │
       ├─→ Load existing plan from DB
       │
       ├─→ Build refined prompt → Gemini API → Parse updated JSON
       │
       └─→ Update WorkoutPlan in DB → Return to frontend
```

---

## Environment Variables

| Variable        | Required | Description                  |
|-----------------|----------|------------------------------|
| `GEMINI_API_KEY`| Yes      | Your Google Gemini API key   |

---

## License

This project is licensed under the MIT License.

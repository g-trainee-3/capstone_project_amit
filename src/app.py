# CANARY_TEST_ABC_789
"""
High School Management System API

A super simple FastAPI application that allows students to view and sign up
for extracurricular activities at Mergington High School.
"""

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, RedirectResponse
import os
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from src.extensions.kb_extension import rag_search
from src.sql.text2sql import run_text2sql

app = FastAPI(title="Mergington High School API",
              description="API for viewing and signing up for extracurricular activities")

# Mount the static files directory
current_dir = Path(__file__).parent
app.mount("/static", StaticFiles(directory=os.path.join(Path(__file__).parent,
          "static")), name="static")

# In-memory activity database
activities = {
    "Chess Club": {
        "description": "Learn strategies and compete in chess tournaments",
        "schedule": "Fridays, 3:30 PM - 5:00 PM",
        "max_participants": 12,
        "participants": ["michael@mergington.edu", "daniel@mergington.edu"]
    },
    "Programming Class": {
        "description": "Learn programming fundamentals and build software projects",
        "schedule": "Tuesdays and Thursdays, 3:30 PM - 4:30 PM",
        "max_participants": 20,
        "participants": ["emma@mergington.edu", "sophia@mergington.edu"]
    },
    "Gym Class": {
        "description": "Physical education and sports activities",
        "schedule": "Mondays, Wednesdays, Fridays, 2:00 PM - 3:00 PM",
        "max_participants": 30,
        "participants": ["john@mergington.edu", "olivia@mergington.edu"]
    }
}


@app.get("/")
def root():
    return RedirectResponse(url="/static/index.html")

# ============================================================
# UAT-LOCKED: This route has passed UAT. DO NOT MODIFY.
# ============================================================
@app.get("/activities")
def get_activities():
    return activities


# ============================================================
# UAT-LOCKED: This route has passed UAT. DO NOT MODIFY.
# ============================================================
@app.post("/activities/{activity_name}/signup")
def signup_for_activity(activity_name: str, email: str):
    """Sign up a student for an activity"""
    if activity_name not in activities:
        raise HTTPException(status_code=404, detail="Activity not found")

    # Get the specific activity
    activity = activities[activity_name]

    # Add student
    activity["participants"].append(email)
    return {"message": f"Signed up {email} for {activity_name}"}

@app.get("/api/activities/{activity_id}")
async def get_activity(activity_id: int):
    """
    Retrieves the details for a specific activity by its ID.
    """
    # This is a placeholder for your actual data lookup logic
    # (e.g., querying a database).
    activities_db = {
        1: {"id": 1, "name": "Morning Yoga Session", "instructor": "Lena"},
        2: {"id": 2, "name": "Introduction to Pottery", "instructor": "Sam"},
    }

    activity = activities_db.get(activity_id)

    if not activity:
        # If the activity is not found, raise an HTTPException for the 404 case.
        raise HTTPException(status_code=404, detail="Activity not found")

    # If found, return the activity details. FastAPI handles the JSON conversion.
    return activity

def jsonify(content: dict, status_code: int = 200):
    """Return a JSON response with the given content and status."""
    return JSONResponse(content=content, status_code=status_code)


def classify_query(question: str) -> str:
    """Classify a question as 'rag', 'text2sql', or 'unknown' using keyword matching."""
    normalized = question.strip().lower()
    quantitative_keywords = (
        "how many", "which", "list", "count", "total", "how much", "how full"
    )
    qualitative_keywords = (
        "what", "describe", "tell me about", "how does", "explain"
    )

    if any(keyword in normalized for keyword in quantitative_keywords):
        return "text2sql"
    if any(keyword in normalized for keyword in qualitative_keywords):
        return "rag"
    return "unknown"




app = FastAPI()

@app.post("/api/ask")
async def ask(request: Request):
    """Handle a question and route it to the appropriate tool based on classification."""
    payload = await request.json()
    question = payload.get("question") if isinstance(payload, dict) else None

    if not isinstance(question, str) or not question.strip():
        return jsonify({"error": "question field required"}, status_code=400)

    route = classify_query(question)
    if route == "unknown":
        return jsonify(
            {
                "answer": (
                    "I can only answer questions about activities. Try asking what an activity is about, "
                    "or how many students have joined."
                ),
                "source": "direct",
                "confidence": 1.0,
            }
        )

    try:
        if route == "rag":
            result = rag_search(question)
        else:
            result = run_text2sql(question)

        return jsonify(result)
    except Exception:
        return jsonify({"error": "tool error"}, status_code=500)




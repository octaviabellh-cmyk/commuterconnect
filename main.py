import os
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from supabase import create_client, Client
from google import genai

app = FastAPI()

# Database & AI Client Initialization
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://your-supabase-url.supabase.co")
SUPABASE_KEY = os.getenv("SUPABASE_KEY", "your-anon-key")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "your-gemini-api-key")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
ai_client = genai.Client(api_key=GEMINI_API_KEY)

class UserProfile(BaseModel):
    name: str
    neighborhood: str
    role: str
    schedule: str

@app.get("/", response_class=HTMLResponse)
def read_root():
    with open("index.html", "r", encoding="utf-8") as f:
        return f.read()

@app.post("/api/match")
def get_matches(user: UserProfile):
    try:
        # 1. Insert submitted profile into Supabase
        supabase.table("Profiles").insert({
            "name": user.name,
            "neighborhood": user.neighborhood,
            "role": user.role,
            "schedule": user.schedule
        }).execute()

        # 2. Fetch all profiles from Supabase
        response = supabase.table("Profiles").select("*").execute()
        existing_profiles = response.data

        # 3. Request AI match recommendation
        prompt = f"""
A student submitted a commute profile:
Name: {user.name}, Neighborhood: {user.neighborhood}, Role: {user.role}, Schedule: {user.schedule}

Existing student profiles in database:
{existing_profiles}

Provide a brief 2-sentence carpool/departure recommendation for {user.name} based on schedule and location.
"""

        ai_response = ai_client.models.generate_content(
            model="gemini-3.8-flash",
            contents=prompt
        )

        # 4. Filter and score matches
        matches = []
        for profile in existing_profiles:
            if profile["name"] != user.name:
                score = 85 if profile["neighborhood"] == user.neighborhood else 60
                matches.append({
                    "name": profile["name"],
                    "neighborhood": profile["neighborhood"],
                    "role": profile["role"],
                    "schedule": profile["schedule"],
                    "score": score
                })

        return {
            "status": "success",
            "recommendation": ai_response.text,
            "existing_profiles": matches
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

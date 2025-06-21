"""
Turtil – FastAPI backend
───────────────────────
Exposes three main endpoints:

GET  /health         – simple uptime ping
GET  /version        – returns model / API version
POST /evaluate       – resume ↔︎ job-description fit analysis
                       (legacy alias /evaluate-fit kept for tests)

The service loads skill & config data from the JSON files that
are already present in the repository:
* skills.json
* config.json
* learning_path_skills.json
"""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# ───────────────────────────────────────────────────────────────
# Data loading helpers
# ───────────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent

def _load_json(filename: str) -> dict:
    try:
        with open(BASE_DIR / filename, "r", encoding="utf-8") as fp:
            return json.load(fp)
    except FileNotFoundError as exc:
        raise RuntimeError(f"Required data file {filename} not found") from exc


SKILL_CONFIG = _load_json("skills.json")              # -> {"skills": [...]}
LEARNING_PATHS = _load_json("learning_path_skills.json")
SETTINGS = _load_json("config.json")

ALL_SKILLS: List[str] = SKILL_CONFIG.get("skills", [])
SKILL_ALIASES = SETTINGS.get("skill_aliases", {})
THRESHOLDS = SETTINGS.get("fit_score_cutoffs", {})

# ───────────────────────────────────────────────────────────────
# Helper functions
# ───────────────────────────────────────────────────────────────

def normalise_skill(token: str) -> str:
    """Apply alias mapping (e.g. 'Amazon Web Services' → 'AWS')."""
    return SKILL_ALIASES.get(token, token)

def extract_skills(text: str) -> List[str]:
    """Very naïve skill extractor based on exact word boundaries."""
    text_lower = text.lower()
    found = {
        s for s in ALL_SKILLS
        if re.search(rf"\b{re.escape(s.lower())}\b", text_lower)
    }
    return [normalise_skill(s) for s in found]

# Import verdict helper (module file name is misspelled in repo)
try:
    from fit_scrore_engine import compute_verdict        # type: ignore
except ModuleNotFoundError:
    from fit_score_engine import compute_verdict         # type: ignore  # noqa: E501

def score_fit(matched: int, wanted: int) -> float:
    """Simple ratio of matched / wanted skills."""
    return matched / wanted if wanted else 0.0

def build_learning_path(missing: List[str]) -> List[dict]:
    """Return step lists from learning_path_skills.json."""
    steps = []
    for skill in missing:
        if skill in LEARNING_PATHS:
            steps.append(
                {"skill": skill, "steps": LEARNING_PATHS[skill]["steps"][:4]}
            )
    return steps

# ───────────────────────────────────────────────────────────────
# FastAPI app & models
# ───────────────────────────────────────────────────────────────

app = FastAPI(
    title="Turtil Resume ↔︎ Role Fit API",
    version="1.0.0",
    description="Evaluates how well a resume matches a job description.",
)

# Allow everything while you’re prototyping; tighten in prod!
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class EvaluateRequest(BaseModel):
    resume_text: str
    job_description: str

class LearningStep(BaseModel):
    skill: str
    steps: List[str]

class FitResponse(BaseModel):
    fit_score: float
    verdict: str
    matched_skills: List[str]
    missing_skills: List[str]
    recommended_learning_path: List[LearningStep]

# ───────────────────────────────────────────────────────────────
# Endpoints
# ───────────────────────────────────────────────────────────────

@app.get("/health")
def health() -> dict:
    return {"status": "ok"}

@app.get("/version")
def version() -> dict:
    return {"model_version": app.version}

@app.post("/evaluate", response_model=FitResponse)
@app.post("/evaluate-fit", response_model=FitResponse, include_in_schema=False)  # legacy
def evaluate(req: EvaluateRequest):
    resume_skills = set(extract_skills(req.resume_text))
    jd_skills     = set(extract_skills(req.job_description))

    matched       = list(resume_skills & jd_skills)
    missing       = list(jd_skills - resume_skills)
    fit_score     = score_fit(len(matched), len(jd_skills))
    verdict       = compute_verdict(fit_score)

    return {
        "fit_score": fit_score,
        "verdict": verdict,
        "matched_skills": matched,
        "missing_skills": missing,
        "recommended_learning_path": build_learning_path(missing),
        "status":"success"
    }

# ───────────────────────────────────────────────────────────────
# Local dev entry-point
# ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    import uvicorn

    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)
    resume_text: str
    job_description: str

# Output model (optional, for strict typing)
class LearningStep(BaseModel):
    skill: str
    steps: List[str]

class FitResponse(BaseModel):
    fit_score: float
    verdict: str
    matched_skills: List[str]
    missing_skills: List[str]
    recommended_learning_track: List[LearningStep]
    status: str

@app.post("/evaluate-fit", response_model=FitResponse)
def evaluate_fit(data: FitRequest):
    # Dummy logic (replace with actual scoring + skill extraction)
    return {
        "fit_score": 0.46,
        "verdict": "moderate_fit",
        "matched_skills": ["Python", "Cloud Basics"],
        "missing_skills": ["Node.js", "MongoDB", "Docker", "AWS", "System Design"],
        "recommended_learning_track": [
            {
                "skill": "Node.js",
                "steps": [
                    "Install Node.js and learn basic syntax",
                    "Understand asynchronous programming in JS",
                    "Build a REST API with Express.js",
                    "Handle authentication and routing"
                ]
            },
            {
                "skill": "Docker",
                "steps": [
                    "Understand containers vs virtual machines",
                    "Install Docker CLI and Docker Desktop",
                    "Write a Dockerfile for a simple app",
                    "Build and run Docker containers locally"
                ]
            }
        ],
        "status": "success"
    }

# Optional: dynamic port for local testing
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 10000))
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=True)


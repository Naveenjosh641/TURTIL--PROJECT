import pytest
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_strong_fit():
    payload = {
        "resume_text": "Experienced in Node.js, MongoDB, Docker, AWS, and system design.",
        "job_description": "Looking for a backend engineer skilled in Node.js, MongoDB, Docker, AWS, and system design."
    }
    response = client.post("/evaluate-fit", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["verdict"] == "strong_fit"
    assert data["fit_score"] >= 0.9
    assert data["missing_skills"] == []

def test_moderate_fit():
    payload = {
        "resume_text": "Proficient in Python and Flask with some experience in cloud deployments.",
        "job_description": "Seeking a backend developer with expertise in Node.js, MongoDB, Docker, AWS, and system design."
    }
    response = client.post("/evaluate-fit", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["verdict"] == "moderate_fit"
    assert 0.4 <= data["fit_score"] < 0.7
    assert "Node.js" in data["missing_skills"]

def test_weak_fit():
    payload = {
        "resume_text": "Background in graphic design and marketing.",
        "job_description": "Hiring a backend engineer with skills in Node.js, MongoDB, Docker, AWS, and system design."
    }
    response = client.post("/evaluate-fit", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["verdict"] == "weak_fit"
    assert data["fit_score"] < 0.4
    assert len(data["missing_skills"]) >= 4

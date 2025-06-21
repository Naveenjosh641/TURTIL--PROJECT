import json

# Load thresholds from config.json
with open('config.json') as f:
    config = json.load(f)
    thresholds = config.get("fit_score_thresholds", {})

def compute_verdict(score):
    if score >= thresholds.get("strong_fit", 0.9):
        return "strong_fit"
    elif score >= thresholds.get("moderate_fit", 0.7):
        return "moderate_fit"
    elif score >= thresholds.get("weak_fit", 0.4):
        return "weak_fit"
    else:
        return "very_weak_fit"

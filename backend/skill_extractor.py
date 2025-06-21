import json
import re

# Load skill aliases from config.json
with open('config.json') as f:
    config = json.load(f)
    skill_aliases = config.get("skill_aliases", {})

def extract_skills(text, skills_list):
    text = text.lower()
    extracted = set()
    for skill in skills_list:
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        if re.search(pattern, text):
            extracted.add(skill)
    # Apply aliases
    normalized = set()
    for skill in extracted:
        normalized.add(skill_aliases.get(skill, skill))
    return list(normalized)

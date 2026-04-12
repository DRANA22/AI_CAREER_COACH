import json
import re

def analyze_resume(resume_text, job_description, model):
    """
    ATS simulation — returns match percentage, keywords, and suggestions.
    """
    prompt = f"""
Act as an expert ATS (Applicant Tracking System) and senior technical recruiter.
Evaluate the resume against the provided job description.

Resume:
{resume_text}

Job Description:
{job_description}

Respond ONLY with a valid JSON object using exactly these keys:
{{
  "match_percentage": <integer 0-100>,
  "missing_keywords": ["keyword1", "keyword2"],
  "improvement_suggestions": ["suggestion1", "suggestion2"],
  "profile_summary": "<2-3 sentence honest summary of candidate>"
}}

No markdown, no explanation, just the JSON object.
"""
    response = model.generate_content(prompt)
    raw = response.text.strip()
    # Clean any markdown code fences if present
    raw = re.sub(r"```json|```", "", raw).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "match_percentage": 0,
            "missing_keywords": [],
            "improvement_suggestions": ["Could not parse AI response. Try again."],
            "profile_summary": raw
        }


def detect_skill_gaps(resume_text, job_description, model):
    """
    Identifies missing technical skills, soft skills, and certifications.
    """
    prompt = f"""
You are a senior career coach analysing a candidate's skill gaps.

Resume:
{resume_text}

Target Job Description:
{job_description}

Respond ONLY with a valid JSON object:
{{
  "critical_technical_gaps": [
    {{"skill": "skill name", "reason": "why it matters"}}
  ],
  "soft_skill_gaps": [
    {{"skill": "skill name", "reason": "why it matters"}}
  ],
  "missing_certifications": ["cert1", "cert2"],
  "emerging_skills": ["skill1", "skill2"],
  "priority_action": "<single most important thing to do next>"
}}

No markdown. JSON only.
"""
    response = model.generate_content(prompt)
    raw = response.text.strip()
    raw = re.sub(r"```json|```", "", raw).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "critical_technical_gaps": [],
            "soft_skill_gaps": [],
            "missing_certifications": [],
            "emerging_skills": [],
            "priority_action": "Review AI response manually."
        }


def generate_roadmap(gaps, target_role, duration_months, model):
    """
    Creates a month-by-month learning roadmap based on skill gaps.
    """
    prompt = f"""
You are an expert career roadmap planner for aspiring tech professionals.

Target Role: {target_role}
Duration: {duration_months} months
Skill Gaps to Address: {gaps}

Create a structured {duration_months}-month roadmap. Respond ONLY with a valid JSON array:
[
  {{
    "month": 1,
    "phase": "Phase name",
    "focus": "Main focus area",
    "goals": ["goal1", "goal2"],
    "resources": ["resource1", "resource2"],
    "milestone": "What the student can build/achieve by end of month"
  }}
]

Make it practical, specific, and progressively challenging. JSON only.
"""
    response = model.generate_content(prompt)
    raw = response.text.strip()
    raw = re.sub(r"```json|```", "", raw).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return [{"month": 1, "phase": "Start", "focus": "Review AI response", "goals": [], "resources": [], "milestone": "N/A"}]
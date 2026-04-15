import json
import re


def analyze_resume(resume_text, job_description, target_role, model):
    """
    ATS-level resume analysis — returns detailed scoring breakdown.
    """
    if not job_description.strip() and target_role.strip():
        job_description = f"Hiring for a {target_role} role. The ideal candidate should have the skills, experience, and formatting to match this position."

    prompt = f"""
Act as an expert ATS (Applicant Tracking System) and senior technical recruiter.
Perform a comprehensive evaluation of this resume against the job description or target role.

Resume:
{resume_text}

Job Description / Target Role:
{job_description}

Respond ONLY with a valid JSON object using exactly these keys:
{{
  "ats_score": <integer 0-100>,
  "match_percentage": <integer 0-100>,
  "missing_keywords": ["keyword1", "keyword2"],
  "matched_keywords": ["keyword1", "keyword2"],
  "improvement_suggestions": ["suggestion1", "suggestion2"],
  "profile_summary": "<2-3 sentence honest summary of candidate>",
  "section_scores": {{
    "contact_info": <0-100>,
    "experience": <0-100>,
    "skills": <0-100>,
    "education": <0-100>,
    "formatting": <0-100>
  }},
  "strengths": ["strength1", "strength2"],
  "red_flags": ["flag1", "flag2"]
}}

No markdown, no explanation, just the JSON object.
"""
    response = model.generate_content(prompt)
    raw = response.text.strip()
    raw = re.sub(r"```json|```", "", raw).strip()
    try:
        result = json.loads(raw)
        # Ensure ats_score exists
        if "ats_score" not in result:
            result["ats_score"] = result.get("match_percentage", 0)
        return result
    except json.JSONDecodeError:
        return {
            "ats_score": 0,
            "match_percentage": 0,
            "missing_keywords": [],
            "matched_keywords": [],
            "improvement_suggestions": ["Could not parse AI response. Try again."],
            "profile_summary": raw[:500],
            "section_scores": {
                "contact_info": 0, "experience": 0,
                "skills": 0, "education": 0, "formatting": 0
            },
            "strengths": [],
            "red_flags": []
        }


def detect_skill_gaps(resume_text, job_description, target_role, model):
    """
    Identifies missing technical skills, soft skills, certifications,
    with learning resource recommendations.
    """
    if not job_description.strip() and target_role.strip():
        job_description = f"Hiring for a {target_role} role. Focus on the skills and experience expected for this position."

    prompt = f"""
You are a senior career coach analysing a candidate's skill gaps.

Resume:
{resume_text}

Target Job Description / Role:
{job_description}

Respond ONLY with a valid JSON object:
{{
  "critical_technical_gaps": [
    {{"skill": "skill name", "reason": "why it matters", "resource": "where to learn it"}}
  ],
  "soft_skill_gaps": [
    {{"skill": "skill name", "reason": "why it matters"}}
  ],
  "missing_certifications": ["cert1", "cert2"],
  "emerging_skills": ["skill1", "skill2"],
  "priority_action": "<single most important thing to do next>",
  "readiness_score": <integer 0-100>
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
            "priority_action": "Review AI response manually.",
            "readiness_score": 50
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
    "milestone": "What the student can build/achieve by end of month",
    "xp_reward": 100
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
        return [{"month": 1, "phase": "Start", "focus": "Review AI response",
                 "goals": [], "resources": [], "milestone": "N/A", "xp_reward": 50}]


def predict_placement(profile, model):
    """
    Multi-factor placement prediction from user profile data.
    Returns detailed breakdown with actionable insights.
    """
    prompt = f"""
You are an expert placement prediction AI. Analyze this user's complete career profile
and predict their placement chances with detailed reasoning.

User Profile:
{json.dumps(profile, indent=2)}

Respond ONLY with a valid JSON object:
{{
  "placement_chance": <integer 0-100>,
  "timeframe": "<realistic time estimate>",
  "confidence_score": <float 1-10>,
  "next_action": "<most impactful next step>",
  "factors": {{
    "technical_skills": <0-100>,
    "experience": <0-100>,
    "resume_quality": <0-100>,
    "interview_readiness": <0-100>,
    "market_demand": <0-100>
  }},
  "top_strengths": ["strength1", "strength2"],
  "critical_improvements": ["improvement1", "improvement2"],
  "recommended_companies": ["company1", "company2", "company3"],
  "salary_range": "<estimated salary range>"
}}

Be realistic and data-driven. JSON only.
"""
    response = model.generate_content(prompt)
    raw = response.text.strip()
    raw = re.sub(r"```json|```", "", raw).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "placement_chance": 50,
            "timeframe": "6 months",
            "confidence_score": 5.0,
            "next_action": "Improve resume and interview skills.",
            "factors": {
                "technical_skills": 50, "experience": 50,
                "resume_quality": 50, "interview_readiness": 50,
                "market_demand": 60
            },
            "top_strengths": [],
            "critical_improvements": ["Build more projects", "Practice interviews"],
            "recommended_companies": [],
            "salary_range": "Varies by location"
        }
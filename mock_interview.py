import json
import re


def mock_interview(role, difficulty, model):
    """
    Generate role-specific mock interview questions with difficulty level.
    Difficulty: easy, medium, hard
    """
    prompt = f"""
You are an expert interviewer at a top tech company.
Generate a mock interview for the role: {role}
Difficulty Level: {difficulty}

Provide exactly 5 questions covering different types.
Respond ONLY with a valid JSON array:
[
  {{
    "id": 1,
    "question": "Your interview question here",
    "type": "behavioral|technical|situational|system_design",
    "difficulty": "{difficulty}",
    "followup": "A natural follow-up question",
    "tips": "Brief tip on how to approach this question",
    "time_limit": <seconds to answer, 60-180>
  }}
]

Make questions realistic and challenging for {difficulty} level. JSON only.
"""
    response = model.generate_content(prompt)
    raw = response.text.strip()
    raw = re.sub(r"```json|```", "", raw).strip()
    try:
        questions = json.loads(raw)
        # Ensure IDs
        for i, q in enumerate(questions):
            q["id"] = i + 1
        return questions
    except json.JSONDecodeError:
        return [
            {"id": 1, "question": "Tell me about a challenging project you led.",
             "type": "behavioral", "difficulty": difficulty,
             "followup": "What was the outcome?",
             "tips": "Use the STAR method.", "time_limit": 120},
            {"id": 2, "question": "How do you approach debugging a production issue?",
             "type": "technical", "difficulty": difficulty,
             "followup": "What tools do you use?",
             "tips": "Walk through your systematic process.", "time_limit": 120},
            {"id": 3, "question": "Describe a time you disagreed with your manager.",
             "type": "behavioral", "difficulty": difficulty,
             "followup": "How did you resolve it?",
             "tips": "Show maturity and communication skills.", "time_limit": 120},
            {"id": 4, "question": "How would you design a URL shortener?",
             "type": "system_design", "difficulty": difficulty,
             "followup": "How would you handle scale?",
             "tips": "Start with requirements, then components.", "time_limit": 180},
            {"id": 5, "question": "What is your process for learning new tech?",
             "type": "behavioral", "difficulty": difficulty,
             "followup": "Give a specific example.",
             "tips": "Show curiosity and structured learning.", "time_limit": 90}
        ]


def evaluate_answer(question, answer, role, model):
    """
    AI evaluates a user's interview answer with detailed scoring.
    """
    prompt = f"""
You are a senior interviewer evaluating a candidate's answer.

Role: {role}
Question: {question}
Candidate's Answer: {answer}

Evaluate the answer and respond ONLY with a valid JSON object:
{{
  "score": <integer 0-100>,
  "grade": "A+|A|B+|B|C+|C|D|F",
  "feedback": "<2-3 sentences of constructive feedback>",
  "strengths": ["what they did well"],
  "improvements": ["what could be better"],
  "ideal_answer_points": ["key points a great answer would include"],
  "confidence_level": "<low|medium|high — how confident the answer sounds>"
}}

Be fair but rigorous. JSON only.
"""
    response = model.generate_content(prompt)
    raw = response.text.strip()
    raw = re.sub(r"```json|```", "", raw).strip()
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return {
            "score": 50,
            "grade": "C",
            "feedback": "Could not evaluate. Please try again.",
            "strengths": [],
            "improvements": ["Try providing more specific examples."],
            "ideal_answer_points": [],
            "confidence_level": "medium"
        }
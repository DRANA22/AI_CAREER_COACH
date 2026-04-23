"""
Career AI Chat — Context-aware career mentoring chatbot
Uses the centralized generate_ai() helper for retry + fallback.
"""

import json


def career_chat(user_message, user_profile, chat_history, generate_fn):
    """
    Context-aware Career AI chatbot.
    Uses user profile + chat history for hyper-personalized responses.
    """
    profile_context = json.dumps(user_profile, indent=2, default=str) if user_profile else "{}"

    history_text = ""
    if chat_history and len(chat_history) > 0:
        recent = chat_history[-6:]
        for msg in recent:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            history_text += f"{role}: {content}\n"

    prompt = f"""
You are CareerAI — an expert AI career coach and mentor. You provide personalized,
actionable career advice. You're warm, encouraging, but brutally honest when needed.

USER PROFILE (use this to personalize your advice):
{profile_context}

RECENT CONVERSATION:
{history_text}

USER'S NEW MESSAGE:
{user_message}

INSTRUCTIONS:
- Reference the user's actual data (level, XP, resume score, etc.) when relevant
- Give specific, actionable advice — not generic platitudes
- If they ask about skills, reference their actual gaps
- Be concise but thorough (2-4 paragraphs max)
- Use encouraging tone with specific next steps
- If relevant, suggest using features like Resume Analyzer, Mock Interview, etc.

Respond naturally as a career mentor. Do NOT use JSON format — just plain text.
"""

    try:
        response = generate_fn(prompt)
        return response.text.strip()
    except Exception as e:
        return (
            f"I'm having trouble connecting right now. Please try again "
            f"in a moment. (Error: {str(e)})"
        )


def get_career_tip(user_profile, generate_fn):
    """
    Generate a personalized daily career tip based on user profile.
    """
    profile_context = json.dumps(user_profile, indent=2, default=str) if user_profile else "{}"

    prompt = f"""
Based on this user's career profile, generate ONE specific, actionable career tip for today.

User Profile:
{profile_context}

Keep it under 2 sentences. Make it specific to their situation, not generic.
Return ONLY the tip text, nothing else.
"""

    try:
        response = generate_fn(prompt)
        return response.text.strip()
    except Exception:
        return "Focus on building one project that showcases your strongest skill today."

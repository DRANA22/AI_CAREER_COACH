# ═══════════════════════════════════════════════════════════════
#  AI CAREER OS — Python / Flask Server
#  Replaces server.js (Express)
# ═══════════════════════════════════════════════════════════════

import os
import math
from datetime import datetime, timedelta
from functools import wraps

from flask import (
    Flask, render_template, request, session, redirect, url_for, jsonify,
    send_file
)
from dotenv import load_dotenv
from google import genai
import pyrebase

load_dotenv()

# ─────────────────────────────────────────────────────────────────
#  APP SETUP
# ─────────────────────────────────────────────────────────────────
app = Flask(
    __name__,
    template_folder="templates",
    static_folder="static",
    static_url_path="/static",
)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "career-os-hackathon-secret")

# ─────────────────────────────────────────────────────────────────
#  🔥 AI SETUP — Gemini (with retry + fallback)
# ─────────────────────────────────────────────────────────────────
import time

genai_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

# Multiple models to try — each has its own quota bucket
MODELS = ["gemini-2.5-flash", "gemini-2.0-flash"]


def generate_ai(prompt, retries=2):
    """Generate content with retry + automatic model fallback on 429/503."""
    last_error = None

    for model in MODELS:
        for attempt in range(retries + 1):
            try:
                response = genai_client.models.generate_content(
                    model=model, contents=prompt
                )
                return response
            except Exception as e:
                last_error = e
                err_str = str(e)

                # 429 = quota exhausted → skip to next model immediately
                if "429" in err_str or "RESOURCE_EXHAUSTED" in err_str:
                    print(f"[AI] {model} quota exhausted, trying next model...")
                    break  # Break inner loop, try next model

                # 503 = overloaded → retry with backoff
                if "503" in err_str or "UNAVAILABLE" in err_str:
                    wait = (attempt + 1) * 2
                    print(f"[AI] {model} unavailable (attempt {attempt+1}), retrying in {wait}s...")
                    time.sleep(wait)
                    continue

                # Other errors → raise immediately
                raise

        else:
            # All retries for this model exhausted (503s)
            print(f"[AI] {model} failed after {retries+1} attempts, trying next...")
            continue

    raise last_error

# ─────────────────────────────────────────────────────────────────
#  🔥 FIREBASE SETUP
# ─────────────────────────────────────────────────────────────────
firebase_config = {
    "apiKey": os.getenv("FIREBASE_API_KEY"),
    "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
    "databaseURL": os.getenv("FIREBASE_DATABASE_URL"),
    "projectId": os.getenv("FIREBASE_PROJECT_ID"),
    "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
    "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
    "appId": os.getenv("FIREBASE_APP_ID"),
}

firebase = pyrebase.initialize_app(firebase_config)
firebase_auth = firebase.auth()
db = firebase.database()

# ─────────────────────────────────────────────────────────────────
#  LOGIC MODULE IMPORTS
# ─────────────────────────────────────────────────────────────────
from logic.pdf_handler import extract_resume_text
from logic.analyzer import analyze_resume, detect_skill_gaps, generate_roadmap, predict_placement
from logic.mock_interview import mock_interview, evaluate_answer
from logic.career_chat import career_chat, get_career_tip

# ─────────────────────────────────────────────────────────────────
#  ACHIEVEMENT DEFINITIONS
# ─────────────────────────────────────────────────────────────────
ACHIEVEMENTS = {
    "first_login": {"name": "First Steps", "icon": "🚀", "desc": "Logged in for the first time", "xp": 50},
    "resume_analyzed": {"name": "Resume Pro", "icon": "📄", "desc": "Analyzed your first resume", "xp": 100},
    "interview_complete": {"name": "Interview Ready", "icon": "🎯", "desc": "Completed a mock interview", "xp": 150},
    "streak_3": {"name": "On Fire", "icon": "🔥", "desc": "3-day login streak", "xp": 75},
    "streak_7": {"name": "Unstoppable", "icon": "⚡", "desc": "7-day login streak", "xp": 200},
    "level_5": {"name": "Rising Star", "icon": "⭐", "desc": "Reached Level 5", "xp": 250},
    "score_80": {"name": "ATS Master", "icon": "💎", "desc": "Got 80%+ ATS score", "xp": 300},
    "chat_10": {"name": "Curious Mind", "icon": "🧠", "desc": "Had 10 career chats", "xp": 100},
    "roadmap_gen": {"name": "Planner", "icon": "🗺️", "desc": "Generated a career roadmap", "xp": 100},
    "placement_pred": {"name": "Fortune Teller", "icon": "🔮", "desc": "Got your placement prediction", "xp": 100},
}



# ─────────────────────────────────────────────────────────────────
#  HELPER FUNCTIONS
# ─────────────────────────────────────────────────────────────────

def get_user_profile(uid):
    """Get user profile from Firebase, with safe defaults."""
    try:
        data = db.child("users").child(uid).get().val()
    except Exception:
        data = None

    profile = data if data and isinstance(data, dict) else {}

    defaults = {
        "name": "Developer",
        "level": 1,
        "xp": 0,
        "streak": 0,
        "resume_score": 0,
        "placement_chance": 25,
        "completed_tasks": [],
        "achievements": [],
        "chat_count": 0,
        "interviews_done": 0,
        "total_xp_earned": 0,
    }

    for key, val in defaults.items():
        if profile.get(key) is None:
            profile[key] = val

    return profile


def award_xp(uid, amount, action=""):
    """Award XP, handle level ups, return updated profile."""
    profile = get_user_profile(uid)
    profile["xp"] = (profile.get("xp") or 0) + amount
    profile["total_xp_earned"] = (profile.get("total_xp_earned") or 0) + amount

    # Level calculation: every 500 XP = 1 level
    new_level = max(1, math.floor(profile["xp"] / 500) + 1)
    leveled_up = new_level > (profile.get("level") or 1)
    profile["level"] = new_level

    # Update placement chance based on activity
    base_chance = 25
    if profile.get("resume_score", 0) > 0:
        base_chance += profile["resume_score"] * 0.3
    base_chance += min((profile.get("interviews_done") or 0) * 5, 20)
    base_chance += min(profile["level"] * 3, 30)
    profile["placement_chance"] = min(int(base_chance), 95)

    profile["last_active"] = datetime.utcnow().isoformat()

    try:
        db.child("users").child(uid).update(profile)
    except Exception:
        pass

    return profile, leveled_up


def check_and_award_achievement(uid, achievement_id):
    """Check if user already has achievement, award if not."""
    profile = get_user_profile(uid)
    achievements = profile.get("achievements") or []

    if achievement_id in achievements:
        return None
    if achievement_id not in ACHIEVEMENTS:
        return None

    achievements.append(achievement_id)
    achievement = ACHIEVEMENTS[achievement_id]

    try:
        db.child("users").child(uid).update({"achievements": achievements})
    except Exception:
        pass

    award_xp(uid, achievement["xp"], f"Achievement: {achievement['name']}")

    return achievement


# ─────────────────────────────────────────────────────────────────
#  AUTH MIDDLEWARE
# ─────────────────────────────────────────────────────────────────
def require_auth(f):
    """Decorator that checks session for user_id."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get("user_id"):
            if request.path.startswith("/api/"):
                return jsonify({"error": "Unauthorized"}), 401
            return redirect("/login")
        return f(*args, **kwargs)
    return decorated_function


# ─────────────────────────────────────────────────────────────────
#  PAGE ROUTES
# ─────────────────────────────────────────────────────────────────
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET"])
def register_page():
    return render_template("register.html", error=None)


@app.route("/register", methods=["POST"])
def register():
    email = request.form.get("email", "")
    password = request.form.get("password", "")
    name = request.form.get("name", "")

    try:
        user = firebase_auth.create_user_with_email_and_password(email, password)
        uid = user["localId"]

        profile = {
            "name": name,
            "email": email,
            "level": 1,
            "xp": 100,
            "streak": 0,
            "resume_score": 0,
            "placement_chance": 25,
            "completed_tasks": [],
            "achievements": ["first_login"],
            "chat_count": 0,
            "interviews_done": 0,
            "total_xp_earned": 100,
            "joined": datetime.utcnow().isoformat(),
            "last_active": datetime.utcnow().isoformat(),
        }

        db.child("users").child(uid).set(profile)
        session["user_id"] = uid
        session["user_name"] = name
        return redirect("/dashboard")

    except Exception as e:
        err_str = str(e)
        error_msg = "Registration failed. Please try again."
        if "EMAIL_EXISTS" in err_str:
            error_msg = "This email is already registered. Please login instead."
        elif "WEAK_PASSWORD" in err_str:
            error_msg = "Password must be at least 6 characters."
        return render_template("register.html", error=error_msg)


@app.route("/login", methods=["GET"])
def login_page():
    return render_template("login.html", error=None)


@app.route("/login", methods=["POST"])
def login():
    email = request.form.get("email", "")
    password = request.form.get("password", "")

    try:
        user = firebase_auth.sign_in_with_email_and_password(email, password)
        uid = user["localId"]
        profile = get_user_profile(uid)

        # Update streak
        last_active = profile.get("last_active", "")
        today = datetime.utcnow().replace(hour=0, minute=0, second=0, microsecond=0)

        if last_active:
            try:
                last_date = datetime.fromisoformat(last_active.replace("Z", "+00:00")).replace(
                    hour=0, minute=0, second=0, microsecond=0, tzinfo=None
                )
                yesterday = today - timedelta(days=1)

                if last_date == yesterday:
                    profile["streak"] = (profile.get("streak") or 0) + 1
                elif last_date != today:
                    profile["streak"] = 1
            except Exception:
                profile["streak"] = 1
        else:
            profile["streak"] = 1

        profile["last_active"] = datetime.utcnow().isoformat()

        try:
            db.child("users").child(uid).update(profile)
        except Exception:
            pass

        # Check streak achievements
        if profile.get("streak", 0) >= 3:
            check_and_award_achievement(uid, "streak_3")
        if profile.get("streak", 0) >= 7:
            check_and_award_achievement(uid, "streak_7")

        session["user_id"] = uid
        session["user_name"] = profile.get("name", "Developer")
        return redirect("/dashboard")

    except Exception:
        return render_template("login.html", error="Invalid email or password. Please try again.")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")


@app.route("/dashboard")
@require_auth
def dashboard():
    uid = session["user_id"]
    profile = get_user_profile(uid)
    name = session.get("user_name") or profile.get("name", "Developer")
    return render_template("dashboard.html", user=profile, name=name)


# ─────────────────────────────────────────────────────────────────
#  API: CAREER STATS
# ─────────────────────────────────────────────────────────────────
@app.route("/api/career-stats")
@require_auth
def api_career_stats():
    try:
        uid = session["user_id"]
        profile = get_user_profile(uid)

        # Add achievement details
        user_achievements = []
        for ach_id in (profile.get("achievements") or []):
            if ach_id in ACHIEVEMENTS:
                ach = {**ACHIEVEMENTS[ach_id], "id": ach_id}
                user_achievements.append(ach)

        # Calculate next level XP
        current_xp = profile.get("xp", 0)
        current_level = profile.get("level", 1)
        next_level_xp = current_level * 500
        xp_progress = ((current_xp % 500) / 500) * 100

        return jsonify({
            **profile,
            "achievement_details": user_achievements,
            "all_achievements": ACHIEVEMENTS,
            "xp_progress": round(xp_progress, 1),
            "xp_to_next_level": next_level_xp - current_xp,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────
#  API: CAREER AI CHAT
# ─────────────────────────────────────────────────────────────────
@app.route("/api/career-chat", methods=["POST"])
@require_auth
def api_career_chat():
    try:
        data = request.get_json()
        message = (data.get("message") or "").strip()
        history = data.get("history") or []

        if not message:
            return jsonify({"error": "Empty message"}), 400

        uid = session["user_id"]
        profile = get_user_profile(uid)

        response_text = career_chat(message, profile, history, generate_ai)

        # Update chat count and award XP
        chat_count = (profile.get("chat_count") or 0) + 1
        try:
            db.child("users").child(uid).update({"chat_count": chat_count})
        except Exception:
            pass
        award_xp(uid, 10, "Career chat")

        # Achievement check
        achievement = None
        if chat_count >= 10:
            achievement = check_and_award_achievement(uid, "chat_10")

        return jsonify({
            "success": True,
            "response": response_text,
            "xp_earned": 10,
            "achievement": achievement,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────
#  API: RESUME ANALYSIS
# ─────────────────────────────────────────────────────────────────
@app.route("/api/analyze-resume", methods=["POST"])
@require_auth
def api_analyze_resume():
    try:
        if "resume" not in request.files:
            return jsonify({"error": "No resume file uploaded"}), 400

        resume_file = request.files["resume"]
        job_desc = (request.form.get("job_description") or "").strip()
        target_role = (request.form.get("target_role") or "").strip()

        if not job_desc and not target_role:
            return jsonify({"error": "Please provide a job description or target role."}), 400

        # Extract text from PDF
        resume_text = extract_resume_text(resume_file)
        if "Error" in resume_text or "Could not extract" in resume_text:
            return jsonify({"error": resume_text}), 400

        # AI Analysis
        analysis = analyze_resume(resume_text, job_desc, target_role, generate_ai)
        gaps = detect_skill_gaps(resume_text, job_desc, target_role, generate_ai)

        # Save to user profile
        uid = session["user_id"]
        ats_score = analysis.get("ats_score", 0)

        analysis_data = {
            "timestamp": datetime.utcnow().isoformat(),
            "ats_score": ats_score,
            "analysis": analysis,
            "gaps": gaps,
            "job_desc": job_desc[:200],
        }

        try:
            db.child("users").child(uid).child("recent_analyses").push(analysis_data)
            db.child("users").child(uid).update({
                "resume_score": ats_score,
                "last_analysis": datetime.utcnow().isoformat(),
            })
        except Exception:
            pass

        # Award XP and achievements
        profile, leveled_up = award_xp(uid, 50, "Resume analysis")
        achievement = check_and_award_achievement(uid, "resume_analyzed")

        score_achievement = None
        if ats_score >= 80:
            score_achievement = check_and_award_achievement(uid, "score_80")

        return jsonify({
            "success": True,
            "analysis": analysis,
            "gaps": gaps,
            "xp_earned": 50,
            "leveled_up": leveled_up,
            "achievement": achievement,
            "score_achievement": score_achievement,
        })

    except Exception as e:
        return jsonify({"error": f"Resume analysis failed: {str(e)}"}), 500


# ─────────────────────────────────────────────────────────────────
#  API: MOCK INTERVIEW
# ─────────────────────────────────────────────────────────────────
@app.route("/api/mock-interview", methods=["POST"])
@require_auth
def api_mock_interview():
    try:
        data = request.get_json()
        role = data.get("role", "Software Engineer")
        difficulty = data.get("difficulty", "medium")

        questions = mock_interview(role, difficulty, generate_ai)

        return jsonify({
            "success": True,
            "questions": (questions or [])[:5],
            "role": role,
            "difficulty": difficulty,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/evaluate-answer", methods=["POST"])
@require_auth
def api_evaluate_answer():
    try:
        data = request.get_json()
        question = data.get("question", "")
        answer = (data.get("answer") or "").strip()
        role = data.get("role", "Software Engineer")

        if not answer:
            return jsonify({"error": "Please provide an answer"}), 400

        evaluation = evaluate_answer(question, answer, role, generate_ai)

        # Award XP based on score
        xp_earned = max(10, math.floor((evaluation.get("score", 50)) / 5))

        uid = session["user_id"]
        profile = get_user_profile(uid)

        interviews_done = (profile.get("interviews_done") or 0) + 1
        try:
            db.child("users").child(uid).update({"interviews_done": interviews_done})
        except Exception:
            pass
        award_xp(uid, xp_earned, "Interview answer")

        # Achievement check
        achievement = None
        if interviews_done >= 1:
            achievement = check_and_award_achievement(uid, "interview_complete")

        return jsonify({
            "success": True,
            "evaluation": evaluation,
            "xp_earned": xp_earned,
            "achievement": achievement,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────
#  API: PLACEMENT PREDICTION
# ─────────────────────────────────────────────────────────────────
@app.route("/api/predict-placement", methods=["POST"])
@require_auth
def api_predict_placement():
    try:
        uid = session["user_id"]
        profile = get_user_profile(uid)

        prediction = predict_placement(profile, generate_ai)

        try:
            db.child("users").child(uid).update({
                "placement_chance": prediction.get("placement_chance", 50),
            })
        except Exception:
            pass

        award_xp(uid, 30, "Placement prediction")
        achievement = check_and_award_achievement(uid, "placement_pred")

        return jsonify({
            "success": True,
            "prediction": prediction,
            "xp_earned": 30,
            "achievement": achievement,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────
#  API: ROADMAP GENERATION
# ─────────────────────────────────────────────────────────────────
@app.route("/api/generate-roadmap", methods=["POST"])
@require_auth
def api_generate_roadmap():
    try:
        data = request.get_json()
        gaps = data.get("gaps", "")
        target_role = data.get("target_role", "Software Engineer")
        duration = data.get("duration", "6")

        roadmap = generate_roadmap(gaps, target_role, duration, generate_ai)

        uid = session["user_id"]
        award_xp(uid, 40, "Roadmap generation")
        achievement = check_and_award_achievement(uid, "roadmap_gen")

        return jsonify({
            "success": True,
            "roadmap": roadmap,
            "xp_earned": 40,
            "achievement": achievement,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────
#  API: COMMUNITY
# ─────────────────────────────────────────────────────────────────
@app.route("/api/community/post", methods=["POST"])
@require_auth
def api_community_post():
    try:
        data = request.get_json()
        content = (data.get("content") or "").strip()
        post_type = data.get("type", "discussion")

        if not content:
            return jsonify({"error": "Post cannot be empty"}), 400

        uid = session["user_id"]
        profile = get_user_profile(uid)

        post = {
            "author": profile.get("name", "Anonymous"),
            "author_level": profile.get("level", 1),
            "content": content[:500],
            "type": post_type,
            "timestamp": datetime.utcnow().isoformat(),
            "likes": 0,
            "uid": uid,
        }

        db.child("community_posts").push(post)
        award_xp(uid, 15, "Community post")

        return jsonify({"success": True, "post": post, "xp_earned": 15})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/community/feed")
@require_auth
def api_community_feed():
    try:
        posts = []
        try:
            snapshot = db.child("community_posts").order_by_key().limit_to_last(20).get()
            if snapshot and snapshot.each():
                for item in snapshot.each():
                    post = item.val()
                    if isinstance(post, dict):
                        post["id"] = item.key()
                        posts.append(post)
        except Exception:
            pass

        posts.reverse()  # Newest first
        return jsonify({"success": True, "posts": posts})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/api/community/like", methods=["POST"])
@require_auth
def api_community_like():
    try:
        data = request.get_json()
        post_id = data.get("post_id", "")

        if not post_id:
            return jsonify({"error": "Invalid post"}), 400

        try:
            snapshot = db.child("community_posts").child(post_id).get()
            if snapshot and snapshot.val():
                post = snapshot.val()
                likes = (post.get("likes") or 0) + 1
                db.child("community_posts").child(post_id).update({"likes": likes})
                return jsonify({"success": True, "likes": likes})
        except Exception:
            pass

        return jsonify({"error": "Post not found"}), 404

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────
#  API: LEADERBOARD
# ─────────────────────────────────────────────────────────────────
@app.route("/api/leaderboard")
@require_auth
def api_leaderboard():
    try:
        leaders = []
        try:
            snapshot = db.child("users").get()
            if snapshot and snapshot.each():
                for item in snapshot.each():
                    user = item.val()
                    if user and isinstance(user, dict) and user.get("name"):
                        leaders.append({
                            "name": user.get("name", "Anonymous"),
                            "level": user.get("level", 1),
                            "xp": user.get("xp", 0),
                            "streak": user.get("streak", 0),
                            "resume_score": user.get("resume_score", 0),
                        })
        except Exception:
            pass

        leaders.sort(key=lambda x: x.get("xp", 0), reverse=True)
        return jsonify({"success": True, "leaders": leaders[:10]})

    except Exception:
        return jsonify({"success": True, "leaders": []})


# ─────────────────────────────────────────────────────────────────
#  API: DAILY GOAL
# ─────────────────────────────────────────────────────────────────
@app.route("/api/daily-goal", methods=["POST"])
@require_auth
def api_daily_goal():
    try:
        uid = session["user_id"]
        profile, leveled_up = award_xp(uid, 25, "Daily goal")

        return jsonify({
            "success": True,
            "xp_earned": 25,
            "leveled_up": leveled_up,
        })

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────
#  API: DOWNLOAD ROADMAP AS PDF
# ─────────────────────────────────────────────────────────────────
@app.route("/api/download-roadmap", methods=["POST"])
@require_auth
def api_download_roadmap():
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas as pdf_canvas
        from reportlab.lib.units import inch
        import io

        data = request.get_json()
        roadmap = data.get("roadmap") or []

        if not roadmap:
            return jsonify({"error": "No roadmap data"}), 400

        buffer = io.BytesIO()
        c = pdf_canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        y = height - 50

        # Title
        c.setFont("Helvetica-Bold", 24)
        c.setFillColorRGB(0.02, 0.84, 0.63)  # #06d6a0
        c.drawCentredString(width / 2, y, "CareerAI")
        y -= 30

        c.setFont("Helvetica-Bold", 18)
        c.setFillColorRGB(0.24, 0.24, 0.24)
        c.drawCentredString(width / 2, y, "Your Personalized Career Roadmap")
        y -= 20

        c.setFont("Helvetica", 10)
        c.setFillColorRGB(0.47, 0.47, 0.47)
        c.drawCentredString(
            width / 2, y,
            f"Generated on {datetime.utcnow().strftime('%B %d, %Y')}"
        )
        y -= 40

        # Roadmap Content
        for item in roadmap:
            month = item.get("month", "")
            phase = item.get("phase", "")
            focus = item.get("focus", "")
            goals = item.get("goals") or []
            resources = item.get("resources") or []
            milestone = item.get("milestone", "")

            # Check if we need a new page
            if y < 120:
                c.showPage()
                y = height - 50

            # Month header
            c.setFont("Helvetica-Bold", 13)
            c.setFillColorRGB(0.02, 0.84, 0.63)
            c.drawString(40, y, f"  Month {month}: {phase}")
            y -= 18

            # Focus
            c.setFont("Helvetica", 10)
            c.setFillColorRGB(0.16, 0.16, 0.16)
            c.drawString(40, y, f"Focus: {focus}")
            y -= 16

            # Goals
            if goals:
                c.setFont("Helvetica-Bold", 10)
                c.setFillColorRGB(0.24, 0.24, 0.24)
                c.drawString(40, y, "Goals:")
                y -= 14
                c.setFont("Helvetica", 9)
                for g in goals:
                    if y < 60:
                        c.showPage()
                        y = height - 50
                    c.drawString(55, y, f"• {g}")
                    y -= 13

            # Resources
            if resources:
                c.setFont("Helvetica-Bold", 10)
                c.setFillColorRGB(0.24, 0.24, 0.24)
                c.drawString(40, y, "Resources:")
                y -= 14
                c.setFont("Helvetica", 9)
                for r in resources:
                    if y < 60:
                        c.showPage()
                        y = height - 50
                    c.drawString(55, y, f"• {r}")
                    y -= 13

            # Milestone
            if milestone:
                c.setFont("Helvetica-Oblique", 10)
                c.setFillColorRGB(0.02, 0.59, 0.47)
                c.drawString(40, y, f"Milestone: {milestone}")
                y -= 18

            y -= 15

        # Footer
        c.setFont("Helvetica", 8)
        c.setFillColorRGB(0.59, 0.59, 0.59)
        c.drawCentredString(width / 2, 30, "Generated by CareerAI - Your AI-Powered Career OS")

        c.save()
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name="My_Career_Roadmap.pdf",
            mimetype="application/pdf",
        )

    except Exception as e:
        return jsonify({"error": f"PDF generation failed: {str(e)}"}), 500


# ─────────────────────────────────────────────────────────────────
#  LEGACY ROUTES (keep for compatibility)
# ─────────────────────────────────────────────────────────────────
@app.route("/analyze", methods=["POST"])
@require_auth
def legacy_analyze():
    try:
        if "resume" not in request.files:
            return jsonify({"error": "No resume file"}), 400

        resume_file = request.files["resume"]
        job_desc = request.form.get("job_description", "")
        target_role = (request.form.get("target_role") or "").strip()

        resume_text = extract_resume_text(resume_file)
        analysis = analyze_resume(resume_text, job_desc, target_role, generate_ai)
        gaps = detect_skill_gaps(resume_text, job_desc, target_role, generate_ai)

        uid = session["user_id"]
        award_xp(uid, 50, "Resume analysis")

        return jsonify({"success": True, "analysis": analysis, "gaps": gaps})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/roadmap", methods=["POST"])
@require_auth
def legacy_roadmap():
    try:
        data = request.get_json()
        gaps = data.get("gaps", "")
        target_role = data.get("target_role", "Software Engineer")
        duration = data.get("duration", "6")

        roadmap = generate_roadmap(gaps, target_role, duration, generate_ai)
        return jsonify({"success": True, "roadmap": roadmap})

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ─────────────────────────────────────────────────────────────────
#  START SERVER
# ─────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    print(f"[CareerAI] Server running on http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=True)

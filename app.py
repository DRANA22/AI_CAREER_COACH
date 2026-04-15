import os
from flask import Flask, render_template, request, session, jsonify, redirect, url_for, send_file
import io
from dotenv import load_dotenv
import google.generativeai as genai
import pyrebase
import json
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename

# Load environment
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "career-os-hackathon-secret")

# 🔥 AI Setup - Gemini
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.0-flash")

# 🔥 Firebase Setup
firebase_config = {
    "apiKey": os.getenv("FIREBASE_API_KEY"),
    "authDomain": os.getenv("FIREBASE_AUTH_DOMAIN"),
    "databaseURL": os.getenv("FIREBASE_DATABASE_URL"),
    "projectId": os.getenv("FIREBASE_PROJECT_ID"),
    "storageBucket": os.getenv("FIREBASE_STORAGE_BUCKET"),
    "messagingSenderId": os.getenv("FIREBASE_MESSAGING_SENDER_ID"),
    "appId": os.getenv("FIREBASE_APP_ID")
}

firebase = pyrebase.initialize_app(firebase_config)
auth = firebase.auth()
db = firebase.database()

# 🔥 Import logic modules
from logic.pdf_handler import extract_resume_text
from logic.analyzer import (
    analyze_resume, detect_skill_gaps, generate_roadmap, predict_placement
)
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
    profile = db.child("users").child(uid).get().val() or {}
    # Ensure defaults
    profile.setdefault("name", "Developer")
    profile.setdefault("level", 1)
    profile.setdefault("xp", 0)
    profile.setdefault("streak", 0)
    profile.setdefault("resume_score", 0)
    profile.setdefault("placement_chance", 25)
    profile.setdefault("completed_tasks", [])
    profile.setdefault("achievements", [])
    profile.setdefault("chat_count", 0)
    profile.setdefault("interviews_done", 0)
    profile.setdefault("total_xp_earned", 0)
    return profile


def award_xp(uid, amount, action=""):
    """Award XP, handle level ups, return updated profile."""
    profile = get_user_profile(uid)
    profile["xp"] = profile.get("xp", 0) + amount
    profile["total_xp_earned"] = profile.get("total_xp_earned", 0) + amount

    # Level calculation: every 500 XP = 1 level
    new_level = max(1, profile["xp"] // 500 + 1)
    leveled_up = new_level > profile.get("level", 1)
    profile["level"] = new_level

    # Update placement chance based on activity
    base_chance = 25
    if profile["resume_score"] > 0:
        base_chance += profile["resume_score"] * 0.3
    base_chance += min(profile.get("interviews_done", 0) * 5, 20)
    base_chance += min(profile["level"] * 3, 30)
    profile["placement_chance"] = min(int(base_chance), 95)

    profile["last_active"] = str(datetime.now())
    db.child("users").child(uid).update(profile)

    return profile, leveled_up


def check_and_award_achievement(uid, achievement_id):
    """Check if user already has achievement, award if not."""
    profile = get_user_profile(uid)
    achievements = profile.get("achievements", [])

    if achievement_id in achievements:
        return None  # Already has it

    if achievement_id not in ACHIEVEMENTS:
        return None

    achievements.append(achievement_id)
    achievement = ACHIEVEMENTS[achievement_id]

    db.child("users").child(uid).update({"achievements": achievements})
    award_xp(uid, achievement["xp"], f"Achievement: {achievement['name']}")

    return achievement


# ─────────────────────────────────────────────────────────────────
#  PAGE ROUTES
# ─────────────────────────────────────────────────────────────────
@app.route("/")
def home():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        name = request.form["name"]

        try:
            user = auth.create_user_with_email_and_password(email, password)
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
                "joined": str(datetime.now()),
                "last_active": str(datetime.now())
            }

            db.child("users").child(uid).set(profile)
            session["user_id"] = uid
            session["user_name"] = name
            return redirect(url_for("dashboard"))

        except Exception as e:
            error_msg = str(e)
            if "EMAIL_EXISTS" in error_msg:
                error_msg = "This email is already registered. Please login instead."
            elif "WEAK_PASSWORD" in error_msg:
                error_msg = "Password must be at least 6 characters."
            else:
                error_msg = "Registration failed. Please try again."
            return render_template("register.html", error=error_msg)

    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        try:
            user = auth.sign_in_with_email_and_password(email, password)
            uid = user["localId"]
            profile = get_user_profile(uid)

            # Update streak
            last_active = profile.get("last_active", "")
            today = datetime.now().date()
            if last_active:
                try:
                    last_date = datetime.fromisoformat(last_active).date()
                    if last_date == today - timedelta(days=1):
                        profile["streak"] = profile.get("streak", 0) + 1
                    elif last_date != today:
                        profile["streak"] = 1
                except ValueError:
                    profile["streak"] = 1
            else:
                profile["streak"] = 1

            profile["last_active"] = str(datetime.now())
            db.child("users").child(uid).update(profile)

            # Check streak achievements
            if profile["streak"] >= 3:
                check_and_award_achievement(uid, "streak_3")
            if profile["streak"] >= 7:
                check_and_award_achievement(uid, "streak_7")

            session["user_id"] = uid
            session["user_name"] = profile.get("name", "Developer")
            return redirect(url_for("dashboard"))

        except Exception as e:
            return render_template("login.html", error="Invalid email or password. Please try again.")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect(url_for("login"))

    uid = session["user_id"]
    profile = get_user_profile(uid)
    name = session.get("user_name", profile.get("name", "Developer"))

    return render_template("dashboard.html", user=profile, name=name)


# ─────────────────────────────────────────────────────────────────
#  API: CAREER STATS
# ─────────────────────────────────────────────────────────────────
@app.route("/api/career-stats")
def career_stats():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    uid = session["user_id"]
    profile = get_user_profile(uid)

    # Add achievement details
    user_achievements = []
    for ach_id in profile.get("achievements", []):
        if ach_id in ACHIEVEMENTS:
            ach = ACHIEVEMENTS[ach_id].copy()
            ach["id"] = ach_id
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
        "xp_to_next_level": next_level_xp - current_xp
    })


# ─────────────────────────────────────────────────────────────────
#  API: CAREER AI CHAT
# ─────────────────────────────────────────────────────────────────
@app.route("/api/career-chat", methods=["POST"])
def career_chat_api():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    message = data.get("message", "")
    chat_history = data.get("history", [])

    if not message.strip():
        return jsonify({"error": "Empty message"}), 400

    uid = session["user_id"]
    profile = get_user_profile(uid)

    response_text = career_chat(message, profile, chat_history, model)

    # Update chat count and award XP
    chat_count = profile.get("chat_count", 0) + 1
    db.child("users").child(uid).update({"chat_count": chat_count})
    award_xp(uid, 10, "Career chat")

    # Achievement check
    if chat_count >= 10:
        achievement = check_and_award_achievement(uid, "chat_10")
    else:
        achievement = None

    return jsonify({
        "success": True,
        "response": response_text,
        "xp_earned": 10,
        "achievement": achievement
    })


# ─────────────────────────────────────────────────────────────────
#  API: RESUME ANALYSIS
# ─────────────────────────────────────────────────────────────────
@app.route("/api/analyze-resume", methods=["POST"])
def analyze_resume_api():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        if 'resume' not in request.files:
            return jsonify({"error": "No resume file uploaded"}), 400

        resume_file = request.files['resume']
        job_desc = request.form.get('job_description', '').strip()
        target_role = request.form.get('target_role', '').strip()

        if not job_desc and not target_role:
            return jsonify({"error": "Please provide a job description or target role."}), 400

        # Extract text from PDF
        resume_text = extract_resume_text(resume_file)
        if "Error" in resume_text or "Could not extract" in resume_text:
            return jsonify({"error": resume_text}), 400

        # AI Analysis
        analysis = analyze_resume(resume_text, job_desc, target_role, model)
        gaps = detect_skill_gaps(resume_text, job_desc, target_role, model)

        # Save to user profile
        uid = session["user_id"]
        profile = get_user_profile(uid)

        ats_score = analysis.get("ats_score", 0)

        analysis_data = {
            "timestamp": str(datetime.now()),
            "ats_score": ats_score,
            "analysis": analysis,
            "gaps": gaps,
            "job_desc": job_desc[:200]  # Store truncated
        }

        db.child("users").child(uid).child("recent_analyses").push(analysis_data)
        db.child("users").child(uid).update({
            "resume_score": ats_score,
            "last_analysis": str(datetime.now())
        })

        # Award XP and achievements
        profile, leveled_up = award_xp(uid, 50, "Resume analysis")
        achievement = check_and_award_achievement(uid, "resume_analyzed")

        if ats_score >= 80:
            score_achievement = check_and_award_achievement(uid, "score_80")
        else:
            score_achievement = None

        return jsonify({
            "success": True,
            "analysis": analysis,
            "gaps": gaps,
            "xp_earned": 50,
            "leveled_up": leveled_up,
            "achievement": achievement,
            "score_achievement": score_achievement
        })
    except Exception as e:
        return jsonify({"error": f"Resume analysis failed: {str(e)}"}), 500


# ─────────────────────────────────────────────────────────────────
#  API: MOCK INTERVIEW
# ─────────────────────────────────────────────────────────────────
@app.route("/api/mock-interview", methods=["POST"])
def mock_interview_api():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    role = data.get("role", "Software Engineer")
    difficulty = data.get("difficulty", "medium")

    questions = mock_interview(role, difficulty, model)

    return jsonify({
        "success": True,
        "questions": questions[:5],
        "role": role,
        "difficulty": difficulty
    })


@app.route("/api/evaluate-answer", methods=["POST"])
def evaluate_answer_api():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    question = data.get("question", "")
    answer = data.get("answer", "")
    role = data.get("role", "Software Engineer")

    if not answer.strip():
        return jsonify({"error": "Please provide an answer"}), 400

    evaluation = evaluate_answer(question, answer, role, model)

    # Award XP based on score
    xp_earned = max(10, evaluation.get("score", 50) // 5)

    uid = session["user_id"]
    profile = get_user_profile(uid)

    interviews_done = profile.get("interviews_done", 0) + 1
    db.child("users").child(uid).update({"interviews_done": interviews_done})
    award_xp(uid, xp_earned, "Interview answer")

    # Achievement check
    if interviews_done >= 1:
        achievement = check_and_award_achievement(uid, "interview_complete")
    else:
        achievement = None

    return jsonify({
        "success": True,
        "evaluation": evaluation,
        "xp_earned": xp_earned,
        "achievement": achievement
    })


# ─────────────────────────────────────────────────────────────────
#  API: PLACEMENT PREDICTION
# ─────────────────────────────────────────────────────────────────
@app.route("/api/predict-placement", methods=["POST"])
def predict_placement_api():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    uid = session["user_id"]
    profile = get_user_profile(uid)

    prediction = predict_placement(profile, model)

    # Update placement chance
    db.child("users").child(uid).update({
        "placement_chance": prediction.get("placement_chance", 50)
    })

    # Award XP and achievement
    award_xp(uid, 30, "Placement prediction")
    achievement = check_and_award_achievement(uid, "placement_pred")

    return jsonify({
        "success": True,
        "prediction": prediction,
        "xp_earned": 30,
        "achievement": achievement
    })


# ─────────────────────────────────────────────────────────────────
#  API: ROADMAP GENERATION
# ─────────────────────────────────────────────────────────────────
@app.route("/api/generate-roadmap", methods=["POST"])
def generate_roadmap_api():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    gaps = data.get("gaps", "")
    target_role = data.get("target_role", "Software Engineer")
    duration = data.get("duration", "6")

    roadmap = generate_roadmap(gaps, target_role, duration, model)

    # Award XP and achievement
    uid = session["user_id"]
    award_xp(uid, 40, "Roadmap generation")
    achievement = check_and_award_achievement(uid, "roadmap_gen")

    return jsonify({
        "success": True,
        "roadmap": roadmap,
        "xp_earned": 40,
        "achievement": achievement
    })


# ─────────────────────────────────────────────────────────────────
#  API: COMMUNITY
# ─────────────────────────────────────────────────────────────────
@app.route("/api/community/post", methods=["POST"])
def community_post():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    content = data.get("content", "").strip()
    post_type = data.get("type", "discussion")  # discussion, achievement, question

    if not content:
        return jsonify({"error": "Post cannot be empty"}), 400

    uid = session["user_id"]
    profile = get_user_profile(uid)

    post = {
        "author": profile.get("name", "Anonymous"),
        "author_level": profile.get("level", 1),
        "content": content[:500],  # Limit length
        "type": post_type,
        "timestamp": str(datetime.now()),
        "likes": 0,
        "uid": uid
    }

    db.child("community_posts").push(post)
    award_xp(uid, 15, "Community post")

    return jsonify({"success": True, "post": post, "xp_earned": 15})


@app.route("/api/community/feed")
def community_feed():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    posts_data = db.child("community_posts").order_by_key().limit_to_last(20).get()
    posts = []

    if posts_data.each():
        for p in posts_data.each():
            post = p.val()
            post["id"] = p.key()
            posts.append(post)

    posts.reverse()  # Newest first
    return jsonify({"success": True, "posts": posts})


@app.route("/api/community/like", methods=["POST"])
def community_like():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    post_id = data.get("post_id", "")

    if not post_id:
        return jsonify({"error": "Invalid post"}), 400

    post = db.child("community_posts").child(post_id).get().val()
    if post:
        likes = post.get("likes", 0) + 1
        db.child("community_posts").child(post_id).update({"likes": likes})
        return jsonify({"success": True, "likes": likes})

    return jsonify({"error": "Post not found"}), 404


# ─────────────────────────────────────────────────────────────────
#  API: LEADERBOARD
# ─────────────────────────────────────────────────────────────────
@app.route("/api/leaderboard")
def leaderboard():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    leaders = []
    try:
        users_data = db.child("users").get()
        if users_data.each():
            for u in users_data.each():
                user = u.val()
                if isinstance(user, dict):
                    leaders.append({
                        "name": user.get("name", "Anonymous"),
                        "level": user.get("level", 1),
                        "xp": user.get("xp", 0),
                        "streak": user.get("streak", 0),
                        "resume_score": user.get("resume_score", 0)
                    })
    except Exception:
        pass

    leaders.sort(key=lambda x: x["xp"], reverse=True)
    return jsonify({"success": True, "leaders": leaders[:10]})


# ─────────────────────────────────────────────────────────────────
#  API: DAILY GOAL
# ─────────────────────────────────────────────────────────────────
@app.route("/api/daily-goal", methods=["POST"])
def complete_daily_goal():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    uid = session["user_id"]
    profile, leveled_up = award_xp(uid, 25, "Daily goal")

    return jsonify({
        "success": True,
        "xp_earned": 25,
        "leveled_up": leveled_up
    })


# ─────────────────────────────────────────────────────────────────
#  API: DOWNLOAD ROADMAP AS PDF
# ─────────────────────────────────────────────────────────────────
@app.route("/api/download-roadmap", methods=["POST"])
def download_roadmap_pdf():
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    roadmap = data.get("roadmap", [])

    if not roadmap:
        return jsonify({"error": "No roadmap data"}), 400

    try:
        from fpdf import FPDF

        pdf = FPDF()
        pdf.set_auto_page_break(auto=True, margin=20)
        pdf.add_page()

        # ── Title Page ──
        pdf.set_font("Helvetica", "B", 24)
        pdf.set_text_color(6, 214, 160)
        pdf.cell(0, 20, "CareerAI", ln=True, align="C")

        pdf.set_font("Helvetica", "B", 18)
        pdf.set_text_color(60, 60, 60)
        pdf.cell(0, 12, "Your Personalized Career Roadmap", ln=True, align="C")

        pdf.set_font("Helvetica", "", 10)
        pdf.set_text_color(120, 120, 120)
        pdf.cell(0, 8, f"Generated on {datetime.now().strftime('%B %d, %Y')}", ln=True, align="C")
        pdf.ln(10)

        # ── Roadmap Content ──
        for item in roadmap:
            month = item.get("month", "")
            phase = item.get("phase", "")
            focus = item.get("focus", "")
            goals = item.get("goals", [])
            resources = item.get("resources", [])
            milestone = item.get("milestone", "")

            # Month header
            pdf.set_fill_color(6, 214, 160)
            pdf.set_text_color(255, 255, 255)
            pdf.set_font("Helvetica", "B", 13)
            pdf.cell(0, 10, f"  Month {month}: {phase}", ln=True, fill=True)

            # Focus
            pdf.set_text_color(40, 40, 40)
            pdf.set_font("Helvetica", "B", 10)
            pdf.cell(0, 8, f"Focus: {focus}", ln=True)
            pdf.ln(2)

            # Goals
            if goals:
                pdf.set_font("Helvetica", "B", 10)
                pdf.set_text_color(60, 60, 60)
                pdf.cell(0, 7, "Goals:", ln=True)
                pdf.set_font("Helvetica", "", 9)
                for g in goals:
                    pdf.cell(8)
                    pdf.cell(0, 6, f"  - {g}", ln=True)
                pdf.ln(2)

            # Resources
            if resources:
                pdf.set_font("Helvetica", "B", 10)
                pdf.set_text_color(60, 60, 60)
                pdf.cell(0, 7, "Resources:", ln=True)
                pdf.set_font("Helvetica", "", 9)
                for r in resources:
                    pdf.cell(8)
                    pdf.cell(0, 6, f"  - {r}", ln=True)
                pdf.ln(2)

            # Milestone
            if milestone:
                pdf.set_font("Helvetica", "BI", 10)
                pdf.set_text_color(6, 150, 120)
                pdf.cell(0, 7, f"Milestone: {milestone}", ln=True)

            pdf.ln(6)

        # ── Footer ──
        pdf.set_font("Helvetica", "I", 8)
        pdf.set_text_color(150, 150, 150)
        pdf.cell(0, 10, "Generated by CareerAI - Your AI-Powered Career OS", ln=True, align="C")

        # Output to bytes
        pdf_bytes = pdf.output()
        buffer = io.BytesIO(pdf_bytes)
        buffer.seek(0)

        return send_file(
            buffer,
            as_attachment=True,
            download_name="My_Career_Roadmap.pdf",
            mimetype="application/pdf"
        )

    except ImportError:
        return jsonify({"error": "PDF library not installed. Run: pip install fpdf2"}), 500
    except Exception as e:
        return jsonify({"error": f"PDF generation failed: {str(e)}"}), 500


# ─────────────────────────────────────────────────────────────────
#  LEGACY ROUTES (keep for compatibility)
# ─────────────────────────────────────────────────────────────────
@app.route("/analyze", methods=["POST"])
def analyze_legacy():
    """Legacy analyze endpoint used by old main.js form."""
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    if 'resume' not in request.files:
        return jsonify({"error": "No resume file"}), 400

    resume_file = request.files['resume']
    job_desc = request.form.get('job_description', '')
    resume_text = extract_resume_text(resume_file)
    target_role = request.form.get('target_role', '').strip()

    analysis = analyze_resume(resume_text, job_desc, target_role, model)
    gaps = detect_skill_gaps(resume_text, job_desc, target_role, model)

    uid = session["user_id"]
    award_xp(uid, 50, "Resume analysis")

    return jsonify({
        "success": True,
        "analysis": analysis,
        "gaps": gaps
    })


@app.route("/roadmap", methods=["POST"])
def roadmap_legacy():
    """Legacy roadmap endpoint."""
    if "user_id" not in session:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.get_json()
    gaps = data.get("gaps", "")
    target_role = data.get("target_role", "Software Engineer")
    duration = data.get("duration", "6")

    roadmap = generate_roadmap(gaps, target_role, duration, model)

    return jsonify({"success": True, "roadmap": roadmap})


if __name__ == "__main__":
    app.run(debug=True, host='0.0.0.0', port=5000)
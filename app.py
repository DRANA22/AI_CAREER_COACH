import os
from flask import Flask, render_template, request, session, jsonify, redirect, url_for
from dotenv import load_dotenv
import google.generativeai as genai
import pyrebase
import json

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")

# ── Gemini AI Setup ──────────────────────────────────────────────
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-3-flash-preview")

# ── Firebase Setup ───────────────────────────────────────────────
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

# ── Import Logic Modules ─────────────────────────────────────────
from logic.pdf_handler import extract_resume_text
from logic.analyzer import analyze_resume, detect_skill_gaps, generate_roadmap


# ── Routes ──────────────────────────────────────────────────────

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
            session["user"] = user["localId"]
            session["name"] = name
            db.child("users").child(user["localId"]).set({"name": name, "email": email})
            return redirect(url_for("dashboard"))
        except Exception as e:
            return render_template("register.html", error="Registration failed. Try again.")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        try:
            user = auth.sign_in_with_email_and_password(email, password)
            session["user"] = user["localId"]
            user_data = db.child("users").child(user["localId"]).get().val()
            session["name"] = user_data.get("name", "Student") if user_data else "Student"
            return redirect(url_for("dashboard"))
        except Exception as e:
            return render_template("login.html", error="Invalid credentials. Try again.")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("home"))


@app.route("/dashboard")
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))
    return render_template("dashboard.html", name=session.get("name", "Student"))


@app.route("/analyze", methods=["POST"])
def analyze():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    try:
        resume_file = request.files.get("resume")
        job_description = request.form.get("job_description", "")
        if not resume_file:
            return jsonify({"error": "No resume uploaded"}), 400
        resume_text = extract_resume_text(resume_file)
        result = analyze_resume(resume_text, job_description, model)
        gaps = detect_skill_gaps(resume_text, job_description, model)
        # Save to Firebase
        db.child("users").child(session["user"]).child("analyses").push({
            "result": result,
            "gaps": gaps
        })
        return jsonify({"analysis": result, "gaps": gaps})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@app.route("/roadmap", methods=["POST"])
def roadmap():
    if "user" not in session:
        return jsonify({"error": "Unauthorized"}), 401
    try:
        data = request.get_json()
        gaps = data.get("gaps", "")
        target_role = data.get("target_role", "Software Engineer")
        duration = data.get("duration", "6")
        result = generate_roadmap(gaps, target_role, duration, model)
        return jsonify({"roadmap": result})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
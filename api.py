from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from models import db, User, QuizResult
from gemini_helper import generate_questions
import datetime
import bcrypt
from dotenv import load_dotenv
import os
import secrets

# Load .env
load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY")
CORS(app)

# Database config
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Init DB
db.init_app(app)
with app.app_context():
    print("\u2705 Membuat database jika belum ada...")
    db.create_all()

# ========== UTIL FUNCTIONS ==========


def get_badge(points):
    if points >= 1000:
        return "\ud83c\udfc6 Diamond"
    elif points >= 700:
        return "\ud83d\udc8e Platinum"
    elif points >= 400:
        return "\ud83e\udd47 Gold"
    elif points >= 200:
        return "\ud83e\udd48 Silver"
    else:
        return "\ud83e\udd49 Bronze"


def get_iq_badge(iq):
    if iq >= 150:
        return "\ud83d\udca1 Genius"
    elif iq >= 130:
        return "\ud83d\udcd8\ufe0f Sangat Cerdas"
    elif iq >= 110:
        return "\ud83d\udcd7 Cerdas"
    else:
        return "\ud83d\udcd5 Rata-rata"


def calculate_iq(user_id):
    results = QuizResult.query.filter_by(user_id=user_id).all()
    if not results:
        return 100
    total_score = sum(r.score for r in results)
    total_quiz = len(results)
    total_wrong = sum(r.wrong for r in results)
    average_score = total_score / total_quiz
    level_bonus = sum(1.2 if r.level == "sulit" else 1.0 for r in results)
    penalty = total_wrong * 0.5
    raw_iq = 80 + (average_score * level_bonus / total_quiz) - penalty
    return max(80, int(raw_iq))


def get_leaderboard_data():
    users = User.query.all()
    leaderboard_data = []

    for u in users:
        results = QuizResult.query.filter_by(user_id=u.id).all()
        if results:
            total_quiz = len(results)
            top_score = max(r.score for r in results)
            avg_score = round(sum(r.score for r in results) / total_quiz)
            total_score = sum(r.score for r in results)
            bonus = total_quiz * 10
            total_points = total_score + bonus
            level = total_points // 100
            badge = get_badge(total_points)
            iq = calculate_iq(u.id)
            iq_badge = get_iq_badge(iq)

            leaderboard_data.append(
                {
                    "name": u.name,
                    "email": u.email,
                    "score": top_score,
                    "avgScore": avg_score,
                    "totalQuizzes": total_quiz,
                    "level": level,
                    "points": total_points,
                    "badge": badge,
                    "iq": iq,
                    "iq_badge": iq_badge,
                }
            )

    sorted_data = sorted(leaderboard_data, key=lambda x: x["score"], reverse=True)
    for idx, user in enumerate(sorted_data, start=1):
        user["rank"] = idx

    return sorted_data


# ========== ROUTES ==========


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["POST"])
def register():
    data = request.json
    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email sudah terdaftar"}), 400

    hashed = bcrypt.hashpw(data["password"].encode(), bcrypt.gensalt())
    user = User(
        name=data["name"],
        email=data["email"],
        password=hashed.decode(),
        join_date=datetime.date.today().isoformat(),
        token=secrets.token_hex(32),  # Generate token saat register
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({"message": "Berhasil daftar", "user_id": user.id})


@app.route("/login", methods=["POST"])
def login():
    data = request.json
    user = User.query.filter_by(email=data["email"]).first()

    if user and bcrypt.checkpw(data["password"].encode(), user.password.encode()):
        # Generate new token on login
        user.token = secrets.token_hex(32)
        db.session.commit()

        return jsonify(
            {
                "message": "Berhasil login",
                "token": user.token,
                "user": {
                    "id": user.id,
                    "name": user.name,
                    "email": user.email,
                    "join_date": user.join_date,
                    "iq_score": user.iq_score,
                },
            }
        )
    return jsonify({"error": "Email atau password salah"}), 401


@app.route("/generate-quiz", methods=["POST"])
def generate_quiz():
    token = request.headers.get("Authorization")
    user = User.query.filter_by(token=token).first()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    questions = generate_questions(data["topic"], data["level"], int(data["count"]))
    return jsonify({"questions": questions})


@app.route("/submit-result", methods=["POST"])
def submit_result():
    token = request.headers.get("Authorization")
    user = User.query.filter_by(token=token).first()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    result = QuizResult(
        user_id=user.id,
        topic=data["topic"],
        level=data["level"],
        score=data["score"],
        correct=data["correct"],
        wrong=data["wrong"],
        total=data["total"],
    )
    user.iq_score = calculate_iq(user.id)

    db.session.add(result)
    db.session.commit()

    return jsonify({"message": "Hasil kuis disimpan"})


@app.route("/api/leaderboard", methods=["GET"])
def api_leaderboard():
    token = request.headers.get("Authorization")
    user = User.query.filter_by(token=token).first()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        data = get_leaderboard_data()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ========== RUN APP ==========

if __name__ == "__main__":
    app.run(debug=True)

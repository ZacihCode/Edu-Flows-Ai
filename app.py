from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from models import db, User, QuizResult
from gemini_helper import generate_questions
from dotenv import load_dotenv
import datetime, bcrypt, secrets, os

# Load environment variables
load_dotenv()
print(os.getenv("DATABASE_URL"))

app = Flask(__name__)
CORS(app)

# Database config
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Init DB
db.init_app(app)
# with app.app_context():
#     print("✅ Membuat database jika belum ada...")
#     db.create_all()


# ========== UTIL FUNCTIONS ==========


def get_badge(points):
    if points >= 1000:
        return "🏆 Diamond"
    elif points >= 700:
        return "💎 Platinum"
    elif points >= 400:
        return "🥇 Gold"
    elif points >= 200:
        return "🥈 Silver"
    return "🥉 Bronze"


def get_iq_badge(iq):
    if iq >= 150:
        return "💡 Genius"
    elif iq >= 130:
        return "📘 Sangat Cerdas"
    elif iq >= 110:
        return "📗 Cerdas"
    return "📕 Rata-rata"


def calculate_iq(user_id):
    results = QuizResult.query.filter_by(user_id=user_id).all()
    if not results:
        return 100
    total_score = sum(r.score for r in results)
    total_quiz = len(results)
    total_wrong = sum(r.wrong for r in results)
    avg_score = total_score / total_quiz
    level_bonus = sum(1.2 if r.level == "sulit" else 1.0 for r in results)
    penalty = total_wrong * 0.5
    raw_iq = 80 + (avg_score * level_bonus / total_quiz) - penalty
    return max(80, int(raw_iq))


def get_leaderboard_data():
    users = User.query.all()
    leaderboard = []
    for u in users:
        results = QuizResult.query.filter_by(user_id=u.id).all()
        if results:
            total_quiz = len(results)
            top_score = max(r.score for r in results)
            avg_score = round(sum(r.score for r in results) / total_quiz)
            total_points = sum(r.score for r in results) + (total_quiz * 10)
            badge = get_badge(total_points)
            level = total_points // 100
            iq = calculate_iq(u.id)
            iq_badge = get_iq_badge(iq)

            leaderboard.append(
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

    leaderboard.sort(key=lambda x: x["score"], reverse=True)
    for i, user in enumerate(leaderboard):
        user["rank"] = i + 1

    return leaderboard


# ========== ROUTES ==========


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["POST"])
def register():
    data = request.json
    if User.query.filter_by(email=data["email"]).first():
        return jsonify({"error": "Email sudah terdaftar"}), 400

    hashed_pw = bcrypt.hashpw(data["password"].encode(), bcrypt.gensalt())
    user = User(
        name=data["name"],
        email=data["email"],
        password=hashed_pw.decode(),
        join_date=datetime.date.today().isoformat(),
        token=secrets.token_hex(32),
    )
    db.session.add(user)
    db.session.commit()
    return jsonify({"message": "Berhasil daftar", "user_id": user.id})


@app.route("/login", methods=["POST"])
def login():
    data = request.json
    user = User.query.filter_by(email=data["email"]).first()

    if user and bcrypt.checkpw(data["password"].encode(), user.password.encode()):
        user.token = secrets.token_hex(32)  # Perbarui token
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
    db.session.add(result)
    db.session.commit()

    # Update IQ user
    user.iq_score = calculate_iq(user.id)
    db.session.commit()

    return jsonify({"message": "Hasil kuis disimpan"})


@app.route("/api/leaderboard", methods=["GET"])
def api_leaderboard():
    token = request.headers.get("Authorization")
    user = User.query.filter_by(token=token).first()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    try:
        return jsonify(get_leaderboard_data())
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ========== RUN APP ==========

if __name__ == "__main__":
    app.run(debug=True)

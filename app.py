from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from dotenv import load_dotenv
from gemini_helper import generate_questions
import os, datetime, bcrypt, secrets

# Load .env
load_dotenv()

app = Flask(__name__)
CORS(app)

# MongoDB connection
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["quiz_app"]
users = db["users"]
results = db["quiz_results"]

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
    user_results = list(results.find({"user_id": user_id}))
    if not user_results:
        return 100

    total_score = sum(r["score"] for r in user_results)
    total_wrong = sum(r["wrong"] for r in user_results)
    total_quiz = len(user_results)
    avg_score = total_score / total_quiz
    level_bonus = sum(1.2 if r["level"] == "sulit" else 1.0 for r in user_results)
    penalty = total_wrong * 0.5
    raw_iq = 80 + (avg_score * level_bonus / total_quiz) - penalty
    return max(80, int(raw_iq))


def get_leaderboard_data():
    all_users = list(users.find())
    leaderboard = []

    for u in all_users:
        user_id = str(u["_id"])
        user_results = list(results.find({"user_id": user_id}))

        if user_results:
            total_quiz = len(user_results)
            top_score = max(r["score"] for r in user_results)
            avg_score = round(sum(r["score"] for r in user_results) / total_quiz)
            total_points = sum(r["score"] for r in user_results) + (total_quiz * 10)
            badge = get_badge(total_points)
            level = total_points // 100
            iq = calculate_iq(user_id)
            iq_badge = get_iq_badge(iq)

            leaderboard.append(
                {
                    "name": u["name"],
                    "email": u["email"],
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
    if users.find_one({"email": data["email"]}):
        return jsonify({"error": "Email sudah terdaftar"}), 400

    hashed = bcrypt.hashpw(data["password"].encode(), bcrypt.gensalt())

    new_user = {
        "name": data["name"],
        "email": data["email"],
        "password": hashed.decode(),
        "join_date": datetime.date.today().isoformat(),
        "iq_score": 100,
        "token": secrets.token_hex(32),
    }
    result = users.insert_one(new_user)
    return jsonify({"message": "Berhasil daftar", "user_id": str(result.inserted_id)})


@app.route("/login", methods=["POST"])
def login():
    data = request.json
    user = users.find_one({"email": data["email"]})

    if user and bcrypt.checkpw(data["password"].encode(), user["password"].encode()):
        new_token = secrets.token_hex(32)
        users.update_one({"_id": user["_id"]}, {"$set": {"token": new_token}})

        return jsonify(
            {
                "message": "Berhasil login",
                "token": new_token,
                "user": {
                    "id": str(user["_id"]),
                    "name": user["name"],
                    "email": user["email"],
                    "join_date": user["join_date"],
                    "iq_score": user.get("iq_score", 100),
                },
            }
        )

    return jsonify({"error": "Email atau password salah"}), 401


@app.route("/submit-result", methods=["POST"])
def submit_result():
    token = request.headers.get("Authorization")
    user = users.find_one({"token": token})
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    result_data = {
        "user_id": str(user["_id"]),
        "topic": data["topic"],
        "level": data["level"],
        "score": data["score"],
        "correct": data["correct"],
        "wrong": data["wrong"],
        "total": data["total"],
    }
    results.insert_one(result_data)

    # Update IQ
    iq_score = calculate_iq(str(user["_id"]))
    users.update_one({"_id": user["_id"]}, {"$set": {"iq_score": iq_score}})
    return jsonify({"message": "Hasil kuis disimpan"})


@app.route("/generate-quiz", methods=["POST"])
def generate_quiz():
    token = request.headers.get("Authorization")
    user = users.find_one({"token": token})
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    data = request.json
    topic = data["topic"]
    level = data["level"]
    count = int(data.get("count", 5))  # pakai default 5 kalau kosong

    questions = generate_questions(topic, level, count)
    return jsonify({"questions": questions})


@app.route("/api/leaderboard", methods=["GET"])
def api_leaderboard():
    token = request.headers.get("Authorization")
    user = users.find_one({"token": token})
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    return jsonify(get_leaderboard_data())


@app.route("/api/stats", methods=["GET"])
def get_stats():
    try:
        user_count = users.count_documents({})
        quiz_count = results.count_documents({})

        quiz_docs = results.find({}, {"score": 1})
        total_score = sum(doc["score"] for doc in quiz_docs if "score" in doc)
        return jsonify(
            {
                "userCount": user_count,
                "quizCount": quiz_count,
                "totalScore": total_score,
            }
        )

    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ========== RUN ==========
if __name__ == "__main__":
    app.run(debug=True)

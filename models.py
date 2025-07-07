from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100))
    email = db.Column(db.String(120), unique=True)
    password = db.Column(db.String(100))
    join_date = db.Column(db.String(50))
    iq_score = db.Column(db.Integer, default=100)
    token = db.Column(db.String(64), unique=True)


class QuizResult(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    topic = db.Column(db.String(100))
    level = db.Column(db.String(50))
    score = db.Column(db.Integer)
    correct = db.Column(db.Integer)
    wrong = db.Column(db.Integer)
    total = db.Column(db.Integer)

import requests
import re
import json
import random
import time

API_KEY = "AIzaSyAn_brR-jg117C0FXlt2n8ju6OOyc6T3II"
MODEL = "gemini-2.0-flash"


def clean_response(text):
    # Ambil isi JSON dari dalam blok markdown ```json ... ```
    match = re.search(r"```(?:json)?\s*(\[.*?\])\s*```", text, re.DOTALL)
    if match:
        return match.group(1)
    return text  # fallback


def validate_questions(questions):
    # Pastikan 'correct' adalah index valid dari options
    valid = []
    for q in questions:
        options = q.get("options", [])
        correct = q.get("correct", 0)
        if isinstance(options, list) and len(options) == 4:
            if isinstance(correct, int) and 0 <= correct < len(options):
                valid.append(q)
    return valid


def generate_questions(topic, level, count):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent?key={API_KEY}"

    seed = int(time.time())
    prompt = f"""
Buatkan {count} soal pilihan ganda tentang topik '{topic}' dengan tingkat kesulitan '{level}'.

Format output:
[
  {{
    "question": "...",
    "options": ["...","...","...","..."],
    "correct": 0
  }}
]

Catatan penting:
- Jawaban benar harus akurat secara logika.
- Field "correct" adalah angka index (0–3) dari array 'options', bukan string.
- Opsi harus acak urutan dan terdiri dari 4 pilihan.
- Hindari soal berulang dan gunakan variasi gaya bahasa.

Seed unik: {seed}
Variasi ke-{random.randint(1000, 9999)}
"""
    payload = {"contents": [{"parts": [{"text": prompt}]}]}
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        text = response.json()["candidates"][0]["content"]["parts"][0]["text"]
        cleaned_text = clean_response(text)
        questions = json.loads(cleaned_text)
        return validate_questions(questions)  # validasi jawaban benar

    except Exception as e:
        print("⚠️ Error generate soal:", e)
        return []

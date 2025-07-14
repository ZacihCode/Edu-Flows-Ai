import os
from pymongo import MongoClient
import json
from dotenv import load_dotenv
import datetime

# Load .env
load_dotenv()

# Koneksi MongoDB
MONGO_URI = os.getenv("MONGO_URI")
client = MongoClient(MONGO_URI)
db = client["quiz_app"]

# Ambil semua nama koleksi
collections = db.list_collection_names()

print(f"Database: quiz_app")
print("=================================")

for collection_name in collections:
    print(f"\nKoleksi: {collection_name}")
    fields = set()

    # Ambil dokumen untuk sampling field dan data
    documents = list(db[collection_name].find().limit(100))  # ambil max 5 contoh data
    for doc in documents:
        fields.update(doc.keys())

    print("Field:")
    for field in sorted(fields):
        print(f" - {field}")

    print("Contoh Data:")
    for doc in documents:
        # Ubah ObjectId jadi string agar bisa ditampilkan
        doc["_id"] = str(doc["_id"])
        print(json.dumps(doc, indent=2, ensure_ascii=False))

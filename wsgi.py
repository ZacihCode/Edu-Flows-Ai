# wsgi.py
from app import app

# Ini penting agar vercel bisa mengenali WSGI callable
app = app
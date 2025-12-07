import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "8570013024:AAEBDhWeV4dZJykQsb8IlcK4dK9g0VTUT04")
ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "8064043725").split(',')))

# Database configuration
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///bot_data.db")

# File storage paths
FILES_DIR = "storage"
LECTURES_DIR = os.path.join(FILES_DIR, "lectures")
NOTES_DIR = os.path.join(FILES_DIR, "notes")
DPP_DIR = os.path.join(FILES_DIR, "dpp")

# Create directories if they don't exist
for directory in [FILES_DIR, LECTURES_DIR, NOTES_DIR, DPP_DIR]:
    os.makedirs(directory, exist_ok=True)

# Subjects with symbols
SUBJECTS = {
    "physics": "⚛️ Physics",
    "chemistry": "🧪 Chemistry", 
    "maths": "📐 Maths",
    "english": "📚 English",
    "biology": "🔬 Biology"
}

CONTENT_TYPES = {
    "lecture": "🎥 Lecture",
    "note": "📝 Note", 
    "dpp": "📊 DPP"
}

MAX_WARNINGS = 5
BLOCK_DURATION = 24 * 60 * 60  # 24 hours in seconds

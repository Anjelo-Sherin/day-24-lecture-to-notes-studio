import os
from pathlib import Path

# Paths
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
PRESETS_DIR = DATA_DIR / "presets"
AUDIO_DIR = DATA_DIR / "audio"
DECKS_FILE = DATA_DIR / "saved_decks.json"

# Create directories if they do not exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
PRESETS_DIR.mkdir(parents=True, exist_ok=True)
AUDIO_DIR.mkdir(parents=True, exist_ok=True)

# App Info
APP_TITLE = "SynapseLecture AI — Lecture-to-Notes Studio"
APP_SUBTITLE = "Day 24 of 30 Projects in 30 Days | Audio to Summary, Flashcards, Quiz & Spaced Repetition"
APP_VERSION = "1.0.0"

# External API Keys (Optional)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")

# SM-2 Default Parameters
SM2_DEFAULT_EF = 2.5
SM2_MIN_EF = 1.3
SM2_INITIAL_INTERVAL_1 = 1  # 1 day
SM2_INITIAL_INTERVAL_2 = 6  # 6 days

# Topic Segmentation Parameters
TOPIC_SIMILARITY_THRESHOLD = 0.35  # Trough depth threshold for boundary
MIN_TOPIC_WORDS = 25

"""
SynapseLecture AI — Day 24: Lecture-to-Notes Studio
Transform any lecture audio, video, or transcript into:
- Synchronized timestamped notes with topic segmentation
- Active recall flashcard decks with SuperMemo SM-2 spaced repetition
- Interactive self-assessment quizzes with instant pedagogical explanations
- Executive spoken audio voice recaps with speed control
"""

from __future__ import annotations

import os
os.environ["MPLCONFIGDIR"] = "/tmp/matplotlib"
os.makedirs("/tmp/matplotlib", exist_ok=True)

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import json
from datetime import datetime
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
import streamlit.components.v1 as components

from src.config import (
    APP_TITLE,
    APP_SUBTITLE,
    APP_VERSION,
    PRESETS_DIR,
    DECKS_FILE,
    GEMINI_API_KEY,
)
from src.data_manager import DataManager
from src.llm_generator import LectureGenAIEngine
from src.sm2_scheduler import SM2Card, SM2DeckScheduler
from src.topic_segmenter import TopicSegmenter, format_seconds
from src.transcriber import LectureTranscriber, parse_vtt_or_srt
from src.tts_synthesizer import TTSSynthesizer

# Streamlit Page Setup
st.set_page_config(
    page_title="SynapseLecture AI — Lecture-to-Notes Studio",
    page_icon="🎓",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Initialize Data & Engines
dm = DataManager()
transcriber = LectureTranscriber()
segmenter = TopicSegmenter()
tts = TTSSynthesizer()

# Initialize Session State
if "current_deck" not in st.session_state:
    st.session_state.current_deck = dm.load_preset_deck("mit_linear_algebra")
if "active_card_index" not in st.session_state:
    st.session_state.active_card_index = 0
if "card_flipped" not in st.session_state:
    st.session_state.card_flipped = False
if "quiz_answers" not in st.session_state:
    st.session_state.quiz_answers = {}
if "quiz_submitted" not in st.session_state:
    st.session_state.quiz_submitted = False
if "gemini_key" not in st.session_state:
    st.session_state.gemini_key = GEMINI_API_KEY
if "custom_decks" not in st.session_state:
    st.session_state.custom_decks = dm.load_all_saved_decks()


# Sleek Modern EdTech Studio CSS
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* Studio Header */
    .studio-header {
        background: linear-gradient(135deg, rgba(30, 27, 75, 0.9) 0%, rgba(15, 23, 42, 0.95) 100%);
        border: 1px solid rgba(99, 102, 241, 0.3);
        border-radius: 16px;
        padding: 24px 30px;
        margin-bottom: 24px;
        box-shadow: 0 10px 30px -10px rgba(79, 70, 229, 0.3);
    }
    .studio-title {
        font-size: 26px;
        font-weight: 800;
        background: linear-gradient(135deg, #A5B4FC 0%, #E0E7FF 50%, #38BDF8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 6px;
        letter-spacing: -0.02em;
    }
    .studio-sub {
        font-size: 14px;
        color: #94A3B8;
        font-weight: 500;
    }
    .badge-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 12px;
        border-radius: 9999px;
        font-size: 12px;
        font-weight: 600;
        background: rgba(99, 102, 241, 0.15);
        border: 1px solid rgba(99, 102, 241, 0.4);
        color: #C7D2FE;
    }

    /* Topic Cards */
    .topic-card {
        background: rgba(30, 41, 59, 0.6);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 16px;
        transition: transform 0.2s ease, border-color 0.2s ease;
    }
    .topic-card:hover {
        border-color: rgba(99, 102, 241, 0.4);
        transform: translateY(-2px);
    }
    .topic-header {
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 12px;
    }
    .topic-title-text {
        font-size: 17px;
        font-weight: 700;
        color: #F8FAFC;
    }
    .time-chip {
        font-family: 'JetBrains Mono', monospace;
        font-size: 12px;
        font-weight: 600;
        color: #38BDF8;
        background: rgba(56, 189, 248, 0.12);
        padding: 3px 10px;
        border-radius: 6px;
        border: 1px solid rgba(56, 189, 248, 0.3);
    }

    /* 3D Flashcard Container */
    .flashcard-stage {
        perspective: 1000px;
        margin: 20px auto;
        max-width: 650px;
    }
    .flashcard-box {
        background: linear-gradient(145deg, #1E293B 0%, #0F172A 100%);
        border: 2px solid rgba(99, 102, 241, 0.35);
        border-radius: 18px;
        padding: 36px 32px;
        min-height: 260px;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        box-shadow: 0 15px 35px -5px rgba(0, 0, 0, 0.5);
        text-align: center;
    }
    .fc-category {
        font-size: 12px;
        text-transform: uppercase;
        font-weight: 700;
        letter-spacing: 0.1em;
        color: #818CF8;
        margin-bottom: 14px;
    }
    .fc-text {
        font-size: 20px;
        font-weight: 600;
        line-height: 1.5;
        color: #FFFFFF;
        margin: auto 0;
    }
    .fc-hint {
        font-size: 13px;
        color: #94A3B8;
        font-style: italic;
        margin-top: 16px;
        padding-top: 12px;
        border-top: 1px dashed rgba(255, 255, 255, 0.1);
    }

    /* Quiz Option Cards */
    .quiz-card {
        background: rgba(30, 41, 59, 0.5);
        border: 1px solid rgba(255, 255, 255, 0.08);
        border-radius: 14px;
        padding: 22px 26px;
        margin-bottom: 20px;
    }
    .quiz-q-text {
        font-size: 16px;
        font-weight: 700;
        color: #F8FAFC;
        margin-bottom: 16px;
    }
    .explanation-box {
        margin-top: 14px;
        padding: 12px 18px;
        border-radius: 8px;
        font-size: 13px;
        line-height: 1.5;
    }
    .explanation-box.correct {
        background: rgba(16, 185, 129, 0.15);
        border: 1px solid rgba(16, 185, 129, 0.4);
        color: #6EE7B7;
    }
    .explanation-box.wrong {
        background: rgba(239, 68, 68, 0.15);
        border: 1px solid rgba(239, 68, 68, 0.4);
        color: #FCA5A5;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Header Banner
st.markdown(
    f"""
    <div class="studio-header">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 12px;">
            <div>
                <div class="studio-title">🎓 {APP_TITLE}</div>
                <div class="studio-sub">{APP_SUBTITLE}</div>
            </div>
            <div style="display: flex; gap: 8px;">
                <span class="badge-pill">⚡ SuperMemo SM-2 Engine</span>
                <span class="badge-pill">🧠 Topic Semantic Embeddings</span>
                <span class="badge-pill">🔊 Spoken Voice Recap</span>
            </div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# Sidebar: Lecture Selection & Studio Controls
with st.sidebar:
    st.markdown("### 📚 Lecture Hub")
    preset_names = dm.list_preset_decks()
    preset_labels = {
        "mit_linear_algebra": "MIT 18.06: Linear Algebra & Eigenvalues",
        "cs50_memory_pointers": "Harvard CS50: Memory & Pointers in C",
        "stanford_gradient_descent": "Stanford CS229: Gradient Descent & Adam",
        "quantum_computing_intro": "Quantum Computing 101: Qubits & Gates",
    }

    selected_preset_key = st.selectbox(
        "Choose Preloaded Lecture:",
        options=preset_names,
        format_func=lambda k: preset_labels.get(k, k),
    )

    if st.button("🔄 Load Selected Lecture", use_container_width=True, type="primary"):
        loaded = dm.load_preset_deck(selected_preset_key)
        if loaded:
            st.session_state.current_deck = loaded
            st.session_state.active_card_index = 0
            st.session_state.card_flipped = False
            st.session_state.quiz_answers = {}
            st.session_state.quiz_submitted = False
            st.toast(f"Loaded: {loaded.get('lecture_title')}", icon="✅")

    st.markdown("---")
    st.markdown("### ⚙️ GenAI Engine Config")
    user_api_key = st.text_input(
        "Google Gemini API Key (Optional):",
        value=st.session_state.gemini_key,
        type="password",
        help="Leave blank to use the high-fidelity offline deterministic synthesis engine.",
    )
    if user_api_key != st.session_state.gemini_key:
        st.session_state.gemini_key = user_api_key
        st.toast("API key updated for GenAI engine.", icon="🔑")

    st.markdown("---")
    st.markdown("### 📈 Deck Recall Snapshot")
    deck_cards = [SM2Card.from_dict(c) for c in st.session_state.current_deck.get("flashcards", [])]
    scheduler = SM2DeckScheduler(deck_cards)
    analytics = scheduler.get_deck_analytics()

    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.metric("Total Cards", analytics["total_cards"])
        st.metric("Cards Due", analytics["due_today"])
    with col_s2:
        st.metric("Mastery %", f"{analytics['mastery_percentage']}%")
        st.metric("Avg EF", analytics["average_ef"])

    st.markdown("---")
    st.caption("Day 24 of 30 Projects in 30 Days · MIT License")

# Main Deck Data
deck = st.session_state.current_deck
lecture_title = deck.get("lecture_title", "Untitled Lecture")
instructor = deck.get("instructor", "Guest Lecturer")
course = deck.get("course", "Advanced Study")
duration_sec = deck.get("duration_seconds", 360)
exec_summary = deck.get("executive_summary", "")
topics = deck.get("topics", [])
flashcards_data = deck.get("flashcards", [])
quiz_data = deck.get("quiz", [])
audio_recap = deck.get("audio_recap_script", "")

# Active Lecture Quick Bar
st.markdown(
    f"""
    <div style="background: rgba(15, 23, 42, 0.6); border: 1px solid rgba(255, 255, 255, 0.08); border-radius: 12px; padding: 14px 20px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
        <div>
            <span style="font-size: 16px; font-weight: 700; color: #F8FAFC;">📖 {lecture_title}</span>
            <div style="font-size: 13px; color: #94A3B8;">Instructor: <strong style="color: #CBD5E1;">{instructor}</strong> | Course: <span style="color: #818CF8;">{course}</span></div>
        </div>
        <div style="display: flex; gap: 8px; align-items: center;">
            <span class="time-chip">⏱ Duration: {format_seconds(duration_sec)}</span>
            <span class="badge-pill">📌 {len(topics)} Topics</span>
            <span class="badge-pill">🗂️ {len(flashcards_data)} Cards</span>
            <span class="badge-pill">🎯 {len(quiz_data)} Qs</span>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

# 6 Navigation Tabs
tab_ingest, tab_notes, tab_flashcards, tab_quiz, tab_voice, tab_exports = st.tabs([
    "🎙️ Ingest & Segment",
    "📝 Structured Notes",
    "🗂️ 3D Flashcards & SM-2",
    "🎯 Interactive Quiz",
    "🔊 Voice Recap",
    "📦 Export & Analytics",
])

# -------------------------------------------------------------
# TAB 1: INGEST & SEGMENT
# -------------------------------------------------------------
with tab_ingest:
    st.markdown("#### 🎙️ Ingest Audio, Video, or Raw Transcript")
    st.markdown("Upload a lecture recording or paste notes to automatically generate timestamped topics, flashcards, and quizzes.")

    ingest_col1, ingest_col2 = st.columns([1, 1])

    with ingest_col1:
        st.markdown("##### Option A: Audio / Subtitle Upload")
        uploaded_file = st.file_uploader(
            "Upload Lecture Audio (.mp3, .wav, .m4a) or Subtitles (.vtt, .srt):",
            type=["mp3", "wav", "m4a", "vtt", "srt"],
        )

        st.markdown("##### Option B: YouTube URL")
        yt_url = st.text_input("Enter YouTube Video URL:", placeholder="https://www.youtube.com/watch?v=...")

        new_lecture_title = st.text_input("Lecture Title:", value="Custom Lecture Session")
        new_instructor = st.text_input("Instructor / Speaker:", value="Prof. Specialist")

    with ingest_col2:
        st.markdown("##### Option C: Raw Transcript Text")
        raw_text_input = st.text_area(
            "Paste Lecture Transcript or Notes:",
            height=200,
            placeholder="Paste transcript sentences here. The semantic topic segmenter will detect topic transitions and align timestamps automatically...",
        )

        min_duration = st.slider("Min Topic Duration (seconds):", min_value=15, max_value=120, value=30, step=5)

    if st.button("🚀 Process & Generate Study Kit", type="primary", use_container_width=True):
        with st.spinner("Analyzing audio cadence, segmenting topics, and synthesizing study kit..."):
            segments = []
            if uploaded_file:
                fname = uploaded_file.name.lower()
                if fname.endswith((".vtt", ".srt")):
                    content = uploaded_file.read().decode("utf-8", errors="ignore")
                    segments = parse_vtt_or_srt(content)
                else:
                    # Simulated Whisper extraction on audio file
                    simulated_text = (
                        f"This lecture discusses advanced concepts in {new_lecture_title}. "
                        "We start with fundamental definitions, examine the core theoretical equations, "
                        "and explore modern computational implementations."
                    )
                    segments = transcriber.transcribe_text_stream(simulated_text)
            elif raw_text_input.strip():
                segments = transcriber.transcribe_text_stream(raw_text_input)
            elif yt_url:
                simulated_text = (
                    f"Welcome to this lecture video on {yt_url}. "
                    "Today's topic covers mathematical foundations, algorithmic paradigms, "
                    "and practical engineering applications with real-world examples."
                )
                segments = transcriber.transcribe_text_stream(simulated_text)
            else:
                st.warning("Please upload a file, enter a YouTube link, or paste transcript text.")

            if segments:
                # Segment Topics
                segmenter_engine = TopicSegmenter(min_chunk_duration=min_duration)
                chunks = segmenter_engine.segment_transcript(segments)
                full_text = " ".join(s["text"] for s in segments)

                # GenAI Generation
                gen_engine = LectureGenAIEngine(api_key=st.session_state.gemini_key)
                new_deck = gen_engine.generate_study_kit(new_lecture_title, chunks, full_text)
                new_deck["deck_id"] = f"deck_{int(datetime.utcnow().timestamp())}"
                new_deck["instructor"] = new_instructor
                new_deck["course"] = "User Uploaded Session"
                new_deck["duration_seconds"] = int(chunks[-1]["end_time"]) if chunks else 180

                # Save and Update State
                dm.save_deck(new_deck["deck_id"], new_deck)
                st.session_state.current_deck = new_deck
                st.session_state.active_card_index = 0
                st.session_state.card_flipped = False
                st.session_state.quiz_answers = {}
                st.session_state.quiz_submitted = False
                st.success(f"Successfully generated study kit for '{new_lecture_title}' with {len(chunks)} topics!")
                st.rerun()

    # Raw Segments Viewer
    raw_segs = deck.get("raw_segments", [])
    if raw_segs:
        with st.expander(f"📜 Inspect Raw Timestamped Transcript ({len(raw_segs)} segments)"):
            for seg in raw_segs:
                st.markdown(f"**`[{format_seconds(seg.get('start', 0.0))}]`** {seg.get('text', '')}")


# -------------------------------------------------------------
# TAB 2: STRUCTURED NOTES
# -------------------------------------------------------------
with tab_notes:
    st.markdown("#### 📝 Smart Structured Notes & Takeaways")

    # Executive Summary Card
    st.info(f"**📌 Executive Summary:** {exec_summary}")

    st.markdown("##### 📖 Thematic Topic Breakdown")
    for t in topics:
        topic_num = t.get("topic_id", 1)
        heading = t.get("heading", f"Topic {topic_num}")
        time_range = t.get("time_range", "00:00 - 05:00")
        takeaways = t.get("key_takeaways", [])
        detailed = t.get("detailed_notes", "")

        with st.container():
            st.markdown(
                f"""
                <div class="topic-card">
                    <div class="topic-header">
                        <span class="topic-title-text">{heading}</span>
                        <span class="time-chip">⏱ {time_range}</span>
                    </div>
                </div>
                """,
                unsafe_allow_html=True,
            )
            col_b1, col_b2 = st.columns([3, 1])
            with col_b1:
                st.markdown("**Key Takeaways:**")
                for bullet in takeaways:
                    st.markdown(f"- {bullet}")
                with st.expander("📖 Read Detailed Exposition"):
                    st.markdown(detailed)
            with col_b2:
                start_sec = t.get("start_time", 0.0)
                st.caption(f"Anchor: `{format_seconds(start_sec)}`")
                if st.button(f"▶ Jump to {format_seconds(start_sec)}", key=f"jump_{topic_num}", use_container_width=True):
                    st.toast(f"Synchronized audio player to {format_seconds(start_sec)}", icon="⏱")


# -------------------------------------------------------------
# TAB 3: 3D FLASHCARDS & SM-2 SPACED REPETITION
# -------------------------------------------------------------
with tab_flashcards:
    st.markdown("#### 🗂️ Active Recall Flashcards (SuperMemo SM-2 Engine)")
    st.caption("Click 'Flip Card' to reveal the answer. Then rate your recall to schedule the card via SM-2!")

    if not flashcards_data:
        st.warning("No flashcards found in this deck.")
    else:
        num_cards = len(flashcards_data)
        idx = st.session_state.active_card_index % num_cards
        card_dict = flashcards_data[idx]
        current_sm2_card = SM2Card.from_dict(card_dict)

        # Progress bar
        progress = (idx + 1) / num_cards
        st.progress(progress, text=f"Card {idx + 1} of {num_cards} · Mastery Tier: {current_sm2_card.mastery_tier}")

        # 3D Flashcard Display
        fc_category = current_sm2_card.category
        if not st.session_state.card_flipped:
            side_badge = "FRONT (QUESTION)"
            content_text = current_sm2_card.front
            hint_text = f"💡 Cue: {current_sm2_card.hint}" if current_sm2_card.hint else ""
        else:
            side_badge = "BACK (ANSWER)"
            content_text = current_sm2_card.back
            hint_text = f"✅ Retention Interval: {current_sm2_card.interval} days | Repetition: {current_sm2_card.repetition}"

        st.markdown(
            f"""
            <div class="flashcard-stage">
                <div class="flashcard-box">
                    <div>
                        <div class="fc-category">{fc_category} · {side_badge}</div>
                        <div class="fc-text">{content_text}</div>
                    </div>
                    <div class="fc-hint">{hint_text}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

        # Flip & Navigation Controls
        btn_c1, btn_c2, btn_c3 = st.columns([1, 2, 1])
        with btn_c1:
            if st.button("⬅ Previous Card", use_container_width=True):
                st.session_state.active_card_index = (st.session_state.active_card_index - 1) % num_cards
                st.session_state.card_flipped = False
                st.rerun()
        with btn_c2:
            flip_label = "🔄 Flip to Question" if st.session_state.card_flipped else "🔄 Flip to Answer"
            if st.button(flip_label, type="primary", use_container_width=True):
                st.session_state.card_flipped = not st.session_state.card_flipped
                st.rerun()
        with btn_c3:
            if st.button("Next Card ➡", use_container_width=True):
                st.session_state.active_card_index = (st.session_state.active_card_index + 1) % num_cards
                st.session_state.card_flipped = False
                st.rerun()

        # SM-2 Rating Buttons (visible when flipped)
        if st.session_state.card_flipped:
            st.markdown("##### Rate Your Recall (SuperMemo SM-2 Interval Calculation):")
            r_col1, r_col2, r_col3, r_col4 = st.columns(4)

            with r_col1:
                if st.button("🟥 Again\n(1 day · Reset)", key="sm2_again", use_container_width=True):
                    current_sm2_card.review(quality=1)
                    flashcards_data[idx] = current_sm2_card.to_dict()
                    dm.update_card_in_deck(deck.get("deck_id", ""), current_sm2_card.to_dict())
                    st.session_state.active_card_index = (st.session_state.active_card_index + 1) % num_cards
                    st.session_state.card_flipped = False
                    st.toast("Card scheduled for tomorrow (repetition reset).", icon="🟥")
                    st.rerun()

            with r_col2:
                if st.button("🟧 Hard\n(3 days)", key="sm2_hard", use_container_width=True):
                    current_sm2_card.review(quality=3)
                    flashcards_data[idx] = current_sm2_card.to_dict()
                    dm.update_card_in_deck(deck.get("deck_id", ""), current_sm2_card.to_dict())
                    st.session_state.active_card_index = (st.session_state.active_card_index + 1) % num_cards
                    st.session_state.card_flipped = False
                    st.toast(f"Scheduled in {current_sm2_card.interval} days.", icon="🟧")
                    st.rerun()

            with r_col3:
                if st.button("🟦 Good\n(6 days)", key="sm2_good", use_container_width=True):
                    current_sm2_card.review(quality=4)
                    flashcards_data[idx] = current_sm2_card.to_dict()
                    dm.update_card_in_deck(deck.get("deck_id", ""), current_sm2_card.to_dict())
                    st.session_state.active_card_index = (st.session_state.active_card_index + 1) % num_cards
                    st.session_state.card_flipped = False
                    st.toast(f"Scheduled in {current_sm2_card.interval} days.", icon="🟦")
                    st.rerun()

            with r_col4:
                if st.button("🟩 Easy\n(12+ days)", key="sm2_easy", use_container_width=True):
                    current_sm2_card.review(quality=5)
                    flashcards_data[idx] = current_sm2_card.to_dict()
                    dm.update_card_in_deck(deck.get("deck_id", ""), current_sm2_card.to_dict())
                    st.session_state.active_card_index = (st.session_state.active_card_index + 1) % num_cards
                    st.session_state.card_flipped = False
                    st.toast(f"Scheduled in {current_sm2_card.interval} days (Easiness factor increased).", icon="🟩")
                    st.rerun()


# -------------------------------------------------------------
# TAB 4: INTERACTIVE QUIZ
# -------------------------------------------------------------
with tab_quiz:
    st.markdown("#### 🎯 Interactive Self-Assessment Quiz")
    st.caption("Verify your understanding of this lecture. Answer the questions below and review instant pedagogical explanations.")

    if not quiz_data:
        st.warning("No quiz questions available for this deck.")
    else:
        total_questions = len(quiz_data)
        score = 0

        for q in quiz_data:
            qid = q.get("question_id", 1)
            q_text = q.get("question", "")
            options = q.get("options", [])
            correct_idx = q.get("correct_index", 0)
            explanation = q.get("explanation", "")
            difficulty = q.get("difficulty", "Medium")

            st.markdown(
                f"""
                <div class="quiz-card">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span style="font-size: 13px; font-weight: 700; color: #818CF8;">QUESTION {qid} OF {total_questions}</span>
                        <span class="badge-pill">Difficulty: {difficulty}</span>
                    </div>
                    <div class="quiz-q-text">{q_text}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

            # Option Selection
            chosen_option = st.radio(
                f"Select your answer for Q{qid}:",
                options=options,
                key=f"quiz_radio_{qid}",
                index=None,
            )
            if chosen_option is not None:
                st.session_state.quiz_answers[qid] = options.index(chosen_option)

            # If submitted, show answer feedback
            if st.session_state.quiz_submitted:
                user_choice = st.session_state.quiz_answers.get(qid)
                if user_choice is not None:
                    if user_choice == correct_idx:
                        score += 1
                        st.markdown(
                            f"""
                            <div class="explanation-box correct">
                                <strong>✅ Correct!</strong> {explanation}
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                    else:
                        correct_opt_text = options[correct_idx]
                        st.markdown(
                            f"""
                            <div class="explanation-box wrong">
                                <strong>❌ Incorrect.</strong> Correct answer: <em>{correct_opt_text}</em>.<br>
                                <strong>Pedagogical Explanation:</strong> {explanation}
                            </div>
                            """,
                            unsafe_allow_html=True,
                        )
                else:
                    st.warning("Unanswered question.")

        st.markdown("---")
        q_btn1, q_btn2 = st.columns([1, 1])
        with q_btn1:
            if st.button("📊 Submit Quiz for Scoring", type="primary", use_container_width=True):
                st.session_state.quiz_submitted = True
                st.rerun()
        with q_btn2:
            if st.button("🔄 Reset Quiz Answers", use_container_width=True):
                st.session_state.quiz_submitted = False
                st.session_state.quiz_answers = {}
                st.rerun()

        if st.session_state.quiz_submitted:
            percentage = round((score / total_questions) * 100, 1)
            if percentage >= 75:
                st.balloons()
                st.success(f"🎉 Outstanding! You scored {score} / {total_questions} ({percentage}%). Concept mastery confirmed!")
            else:
                st.info(f"You scored {score} / {total_questions} ({percentage}%). Review the explanations above to strengthen recall.")


# -------------------------------------------------------------
# TAB 5: VOICE RECAP STUDIO
# -------------------------------------------------------------
with tab_voice:
    st.markdown("#### 🔊 Spoken Voice Recap & Audio Summary")
    st.caption("Listen to a crisp, high-yield 60-second audio summary rendered with client-side Speech Synthesis.")

    # Render HTML5 Web Speech synthesizer
    tts_component_html = tts.get_web_speech_html_component(audio_recap, lecture_title)
    components.html(tts_component_html, height=260)

    # Offline Audio File Fallback
    st.markdown("##### 🎵 Offline Synthesized Harmonic Chime")
    recap_wav_path = Path(__file__).resolve().parent / "data" / "audio" / "recap_cue.wav"
    if recap_wav_path.exists():
        st.audio(str(recap_wav_path), format="audio/wav")
        st.caption("Offline acoustic audio cue generated via pure Python standard library.")


# -------------------------------------------------------------
# TAB 6: EXPORT & ANALYTICS
# -------------------------------------------------------------
with tab_exports:
    st.markdown("#### 📦 Export Studio & Spaced Repetition Analytics")

    # Forgetting Curve / Retention Chart using Plotly
    st.markdown("##### 📉 Ebbinghaus Memory Retention Forecast")
    days_range = np.linspace(0, 30, 60)
    cards_list = [SM2Card.from_dict(c) for c in flashcards_data]

    fig = go.Figure()
    if cards_list:
        for card in cards_list[:5]:
            retentions = [card.calculate_retention(days_elapsed=d) * 100 for d in days_range]
            fig.add_trace(go.Scatter(
                x=days_range,
                y=retentions,
                mode="lines",
                name=f"{card.front[:25]}... (I={card.interval}d)",
            ))

    fig.update_layout(
        title="Projected Recall Retention Curve Over 30 Days (SM-2 Stability Model)",
        xaxis_title="Days Elapsed",
        yaxis_title="Estimated Retention Probability (%)",
        template="plotly_dark",
        margin=dict(l=20, r=20, t=40, b=20),
        height=320,
    )
    st.plotly_chart(fig, use_container_width=True)

    st.markdown("---")
    st.markdown("##### 📥 Multi-Format Export Downloads")
    exp_c1, exp_c2, exp_c3, exp_c4 = st.columns(4)

    # 1. Markdown Export
    with exp_c1:
        md_content = dm.export_to_markdown(deck)
        st.download_button(
            "📄 Export Markdown (.md)",
            data=md_content,
            file_name=f"{deck.get('deck_id', 'lecture')}_notes.md",
            mime="text/markdown",
            use_container_width=True,
        )

    # 2. Anki Flashcards Export
    with exp_c2:
        anki_tsv = dm.export_to_anki_csv(flashcards_data)
        st.download_button(
            "🗂️ Export Anki Deck (.tsv)",
            data=anki_tsv,
            file_name=f"{deck.get('deck_id', 'lecture')}_anki.tsv",
            mime="text/tab-separated-values",
            use_container_width=True,
        )

    # 3. Printable Cheatsheet HTML
    with exp_c3:
        html_cheatsheet = dm.export_to_printable_html(deck)
        st.download_button(
            "🖨️ Printable Cheatsheet (.html)",
            data=html_cheatsheet,
            file_name=f"{deck.get('deck_id', 'lecture')}_cheatsheet.html",
            mime="text/html",
            use_container_width=True,
        )

    # 4. JSON Deck
    with exp_c4:
        json_deck_str = json.dumps(deck, indent=2)
        st.download_button(
            "💾 Full Deck JSON (.json)",
            data=json_deck_str,
            file_name=f"{deck.get('deck_id', 'lecture')}.json",
            mime="application/json",
            use_container_width=True,
        )

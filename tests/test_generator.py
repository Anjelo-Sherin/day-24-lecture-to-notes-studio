"""
Unit Tests for Structured GenAI Study Kit Generator
"""

import pytest
from src.llm_generator import LectureGenAIEngine


def test_local_study_kit_generation():
    engine = LectureGenAIEngine(api_key="")  # Use deterministic local fallback
    topics = [
        {
            "topic_id": 1,
            "title": "Topic 1: Intro to Python",
            "start_time": 0.0,
            "end_time": 60.0,
            "start_str": "00:00",
            "end_str": "01:00",
            "text": "Python is an interpreted, high-level, dynamically typed language. It uses indentation to define code blocks."
        },
        {
            "topic_id": 2,
            "title": "Topic 2: Lists and Tuples",
            "start_time": 60.0,
            "end_time": 120.0,
            "start_str": "01:00",
            "end_str": "02:00",
            "text": "Lists are mutable sequences defined with square brackets. Tuples are immutable and defined with parentheses."
        }
    ]
    full_transcript = "Python is interpreted. Lists are mutable. Tuples are immutable."

    kit = engine.generate_study_kit("Python Crash Course", topics, full_transcript)

    assert kit["lecture_title"] == "Python Crash Course"
    assert "executive_summary" in kit
    assert "audio_recap_script" in kit
    assert len(kit["topics"]) == 2
    assert len(kit["flashcards"]) >= 2
    assert len(kit["quiz"]) >= 2

    # Verify quiz schema integrity
    for q in kit["quiz"]:
        assert "question" in q
        assert len(q["options"]) == 4
        assert 0 <= q["correct_index"] <= 3
        assert len(q["explanation"]) > 0

    # Verify flashcard schema integrity
    for fc in kit["flashcards"]:
        assert "front" in fc
        assert "back" in fc
        assert "hint" in fc

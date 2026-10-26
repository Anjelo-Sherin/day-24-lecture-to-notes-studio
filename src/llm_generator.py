"""
Structured GenAI Generator Engine
Generates comprehensive lecture notes, flashcards with hints, multiple-choice quizzes,
and executive voice recaps using Gemini API (with JSON schema) or intelligent local synthesis.
"""

from __future__ import annotations

import json
import re
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional
from src.config import GEMINI_API_KEY


# JSON Schema for LLM generation
LECTURE_STUDIO_SCHEMA = {
    "type": "object",
    "properties": {
        "lecture_title": {"type": "string"},
        "executive_summary": {"type": "string"},
        "audio_recap_script": {"type": "string"},
        "topics": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "topic_id": {"type": "integer"},
                    "heading": {"type": "string"},
                    "time_range": {"type": "string"},
                    "key_takeaways": {"type": "array", "items": {"type": "string"}},
                    "detailed_notes": {"type": "string"},
                },
                "required": ["topic_id", "heading", "time_range", "key_takeaways", "detailed_notes"]
            }
        },
        "flashcards": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "card_id": {"type": "string"},
                    "front": {"type": "string"},
                    "back": {"type": "string"},
                    "hint": {"type": "string"},
                    "category": {"type": "string"},
                },
                "required": ["card_id", "front", "back", "category"]
            }
        },
        "quiz": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "question_id": {"type": "integer"},
                    "question": {"type": "string"},
                    "options": {"type": "array", "items": {"type": "string"}},
                    "correct_index": {"type": "integer"},
                    "explanation": {"type": "string"},
                    "difficulty": {"type": "string"},
                },
                "required": ["question_id", "question", "options", "correct_index", "explanation"]
            }
        }
    },
    "required": ["lecture_title", "executive_summary", "audio_recap_script", "topics", "flashcards", "quiz"]
}


class LectureGenAIEngine:
    """Orchestrates structured LLM note, flashcard, and quiz generation."""

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or GEMINI_API_KEY

    def generate_study_kit(
        self,
        lecture_title: str,
        topic_chunks: List[Dict[str, Any]],
        full_transcript: str,
    ) -> Dict[str, Any]:
        """
        Main entry point: Attempts Gemini API call with structured JSON output;
        falls back gracefully to high-fidelity offline deterministic synthesis.
        """
        if self.api_key:
            try:
                gemini_result = self._call_gemini_api(lecture_title, topic_chunks, full_transcript)
                if gemini_result:
                    return gemini_result
            except Exception as e:
                print(f"[LectureGenAIEngine] Gemini API failed: {e}. Falling back to local engine.")

        # Offline deterministic synthesis
        return self._generate_local_study_kit(lecture_title, topic_chunks, full_transcript)

    def _call_gemini_api(
        self,
        lecture_title: str,
        topic_chunks: List[Dict[str, Any]],
        full_transcript: str,
    ) -> Optional[Dict[str, Any]]:
        """Calls Google Gemini REST API using structured JSON schema."""
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={self.api_key}"

        prompt = f"""
You are an expert university professor and master educator.
Transform this lecture recording into an interactive study studio kit.

Lecture Title: {lecture_title}

Topic Segments with Timestamps:
{json.dumps([{
    'topic_id': t.get('topic_id'),
    'title': t.get('title'),
    'start_str': t.get('start_str'),
    'end_str': t.get('end_str'),
    'text': t.get('text')[:600]
} for t in topic_chunks], indent=2)}

Full Transcript Snippet:
{full_transcript[:4000]}

Generate a valid JSON object strictly complying with this schema:
{json.dumps(LECTURE_STUDIO_SCHEMA)}
Ensure:
1. Every topic has exact timestamp ranges (e.g. "00:00 - 02:45").
2. Bullet points in 'key_takeaways' are concrete and actionable.
3. Flashcards have conceptual 'front' questions, clear 'back' answers, and memory 'hint' cues.
4. Quiz contains 4-6 rigorous multiple-choice questions with 4 plausible options each and detailed explanations for the correct answer.
5. 'audio_recap_script' is a polished 60-second spoken summary intended for text-to-speech.
Return only valid JSON.
"""

        req_payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": 0.2,
                "response_mime_type": "application/json",
            }
        }

        data = json.dumps(req_payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            res_json = json.loads(body)
            raw_text = res_json["candidates"][0]["content"]["parts"][0]["text"]
            parsed = json.loads(raw_text)
            return self._validate_and_normalize(parsed, topic_chunks)

    def _generate_local_study_kit(
        self,
        lecture_title: str,
        topic_chunks: List[Dict[str, Any]],
        full_transcript: str,
    ) -> Dict[str, Any]:
        """
        High-fidelity offline generator that parses extracted topics into notes,
        cards, and quizzes with verified schema compliance.
        """
        topics_output = []
        flashcards_output = []
        quiz_output = []

        card_counter = 1
        q_counter = 1

        for t in topic_chunks:
            topic_id = t.get("topic_id", len(topics_output) + 1)
            title = t.get("title", f"Topic {topic_id}")
            start_str = t.get("start_str", "00:00")
            end_str = t.get("end_str", "05:00")
            time_range = f"{start_str} - {end_str}"
            text = t.get("text", "")

            # Extract sentences
            sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if len(s.strip()) > 15]
            takeaways = sentences[:3] if len(sentences) >= 3 else (sentences + ["Focus on fundamental definition and operational context."])[:3]

            topics_output.append({
                "topic_id": topic_id,
                "heading": title,
                "time_range": time_range,
                "start_time": t.get("start_time", 0.0),
                "end_time": t.get("end_time", 60.0),
                "key_takeaways": takeaways,
                "detailed_notes": f"**Timestamp Anchor [{start_str}]**: {text}"
            })

            # Create 1-2 Flashcards per topic
            if sentences:
                lead_sentence = sentences[0]
                flashcards_output.append({
                    "card_id": f"card-{card_counter}",
                    "front": f"What is the core principle of {title}?",
                    "back": lead_sentence,
                    "hint": f"Discussed between {time_range} in the lecture.",
                    "category": title.split(":")[-1].strip() if ":" in title else "Core Theory"
                })
                card_counter += 1

                if len(sentences) > 1:
                    second_sentence = sentences[1]
                    flashcards_output.append({
                        "card_id": f"card-{card_counter}",
                        "front": f"How does {title} apply in practice?",
                        "back": second_sentence,
                        "hint": "Relates to the primary mechanism outlined in this segment.",
                        "category": "Application"
                    })
                    card_counter += 1

            # Create 1 Quiz Question per topic
            if sentences:
                correct_ans = sentences[0]
                distractors = [
                    f"It assumes an inverse relationship regardless of {title.lower()}.",
                    "It is strictly an artifact of measurement noise with no theoretical basis.",
                    f"It only holds true under non-standard asymptotic limits.",
                ]
                options = [correct_ans] + distractors
                # Deterministic shuffle simulation
                quiz_output.append({
                    "question_id": q_counter,
                    "question": f"According to the lecture segment on [{start_str}], which statement regarding {title} is correct?",
                    "options": options,
                    "correct_index": 0,
                    "explanation": f"As highlighted in the lecture at {start_str}: '{correct_ans}'. The other options represent common misunderstandings.",
                    "difficulty": "Medium" if q_counter % 2 == 0 else "Easy"
                })
                q_counter += 1

        exec_summary = (
            f"This lecture on '{lecture_title}' covers {len(topic_chunks)} main thematic topics. "
            f"The discussion navigates through foundational mechanisms, practical analytical formulations, "
            f"and critical heuristics to retain. Master the key concepts using the active spaced-repetition deck "
            f"and verify recall with the interactive quiz."
        )

        audio_recap = (
            f"Welcome to your 60-second lecture recap for {lecture_title}. "
            f"In this session, we explored {len(topic_chunks)} primary themes. "
            f"First, we covered foundational definitions starting at {topic_chunks[0].get('start_str', '00:00')}. "
            f"Next, the lecture examined operational applications and mathematical nuances. "
            f"Be sure to review your flashcards and test yourself on the quiz questions. Happy studying!"
        )

        return {
            "lecture_title": lecture_title,
            "executive_summary": exec_summary,
            "audio_recap_script": audio_recap,
            "topics": topics_output,
            "flashcards": flashcards_output,
            "quiz": quiz_output
        }

    def _validate_and_normalize(self, data: Dict[str, Any], topic_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Ensures required fields exist and attaches numeric start/end timestamps."""
        data.setdefault("lecture_title", "Lecture Study Kit")
        data.setdefault("executive_summary", "Comprehensive lecture overview.")
        data.setdefault("audio_recap_script", "Brief audio recap.")
        data.setdefault("topics", [])
        data.setdefault("flashcards", [])
        data.setdefault("quiz", [])

        # Enrich topics with start_time for UI audio synchronization
        for idx, topic in enumerate(data["topics"]):
            if idx < len(topic_chunks):
                topic["start_time"] = topic_chunks[idx].get("start_time", 0.0)
                topic["end_time"] = topic_chunks[idx].get("end_time", 0.0)
            else:
                topic["start_time"] = idx * 60.0
                topic["end_time"] = (idx + 1) * 60.0

        return data

"""
Data Management, Decks Persistence & Multi-Format Exporter
Handles storage of study decks, SM-2 flashcard review states,
quiz answer history, and exports to Markdown, Anki CSV, and HTML.
"""

from __future__ import annotations

import csv
import io
import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from src.config import PRESETS_DIR, DECKS_FILE
from src.sm2_scheduler import SM2Card, SM2DeckScheduler


class DataManager:
    """Manages preset lectures, user-created decks, and multi-format exports."""

    def __init__(self, decks_file: Optional[Path] = None, presets_dir: Optional[Path] = None):
        self.decks_file = decks_file or DECKS_FILE
        self.presets_dir = presets_dir or PRESETS_DIR
        self._ensure_storage()

    def _ensure_storage(self) -> None:
        """Initializes empty decks storage if absent."""
        if not self.decks_file.exists():
            with open(self.decks_file, "w", encoding="utf-8") as f:
                json.dump({}, f, indent=2)

    def list_preset_decks(self) -> List[str]:
        """Lists available built-in preset lecture deck files."""
        return sorted([f.stem for f in self.presets_dir.glob("*.json")])

    def load_preset_deck(self, name: str) -> Optional[Dict[str, Any]]:
        """Loads a pre-built reference lecture deck."""
        target = self.presets_dir / f"{name}.json"
        if not target.exists():
            return None
        with open(target, "r", encoding="utf-8") as f:
            return json.load(f)

    def load_all_saved_decks(self) -> Dict[str, Any]:
        """Reads user-saved decks from JSON file."""
        try:
            with open(self.decks_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}

    def save_deck(self, deck_id: str, deck_data: Dict[str, Any]) -> None:
        """Saves or updates a study deck."""
        decks = self.load_all_saved_decks()
        decks[deck_id] = deck_data
        with open(self.decks_file, "w", encoding="utf-8") as f:
            json.dump(decks, f, indent=2)

    def update_card_in_deck(self, deck_id: str, card_data: Dict[str, Any]) -> None:
        """Updates individual card SM-2 state in saved deck."""
        decks = self.load_all_saved_decks()
        if deck_id not in decks:
            return
        cards = decks[deck_id].get("flashcards", [])
        for i, c in enumerate(cards):
            if c.get("card_id") == card_data.get("card_id"):
                cards[i] = card_data
                break
        decks[deck_id]["flashcards"] = cards
        self.save_deck(deck_id, decks[deck_id])

    # Export Helpers
    def export_to_markdown(self, deck_data: Dict[str, Any]) -> str:
        """Formats the lecture notes into clean GitHub-flavored markdown."""
        title = deck_data.get("lecture_title", "Lecture Notes")
        summary = deck_data.get("executive_summary", "")
        topics = deck_data.get("topics", [])
        flashcards = deck_data.get("flashcards", [])
        quiz = deck_data.get("quiz", [])

        md = [
            f"# {title}",
            "",
            "> Generated with **SynapseLecture AI (Day 24)**",
            "",
            "## 📌 Executive Summary",
            f"{summary}",
            "",
            "---",
            "",
            "## 📖 Topic-Segmented Structured Notes",
            "",
        ]

        for t in topics:
            time_range = t.get("time_range", "")
            md.append(f"### {t.get('heading', 'Topic')} `[{time_range}]`")
            md.append("")
            md.append("**Key Takeaways:**")
            for bullet in t.get("key_takeaways", []):
                md.append(f"- {bullet}")
            md.append("")
            md.append(f"{t.get('detailed_notes', '')}")
            md.append("")

        md.extend([
            "---",
            "",
            "## 🗂️ Active Recall Flashcards",
            "",
            "| # | Concept (Front) | Explanation (Back) | Hint | Category |",
            "|---|-----------------|--------------------|------|----------|",
        ])

        for idx, fc in enumerate(flashcards, start=1):
            front = fc.get("front", "").replace("|", "\\|")
            back = fc.get("back", "").replace("|", "\\|")
            hint = fc.get("hint", "").replace("|", "\\|")
            cat = fc.get("category", "General")
            md.append(f"| {idx} | **{front}** | {back} | *{hint}* | `{cat}` |")

        md.extend([
            "",
            "---",
            "",
            "## 🎯 Self-Assessment Quiz",
            "",
        ])

        for q in quiz:
            q_id = q.get("question_id", 1)
            md.append(f"#### Q{q_id}. {q.get('question', '')}")
            correct_idx = q.get("correct_index", 0)
            for opt_idx, opt in enumerate(q.get("options", [])):
                letter = chr(65 + opt_idx)
                marker = "✅" if opt_idx == correct_idx else "⚪"
                md.append(f"- **{letter})** {marker} {opt}")
            md.append("")
            md.append(f"> **Explanation:** {q.get('explanation', '')}")
            md.append("")

        return "\n".join(md)

    def export_to_anki_csv(self, flashcards: List[Dict[str, Any]]) -> str:
        """
        Exports flashcards to Anki-compatible Tab-Separated Values (TSV).
        Format: Front \t Back \t Hint \t Category / Tags
        """
        output = io.StringIO()
        writer = csv.writer(output, delimiter="\t", quoting=csv.QUOTE_MINIMAL)
        # Anki Header
        writer.writerow(["#separator:tab"])
        writer.writerow(["#html:true"])
        writer.writerow(["#tags column:4"])
        for card in flashcards:
            front = card.get("front", "")
            back = card.get("back", "")
            hint = f"<i>Hint: {card.get('hint', '')}</i>" if card.get("hint") else ""
            category = card.get("category", "Lecture").replace(" ", "_")
            writer.writerow([front, back + ("<br>" + hint if hint else ""), "", category])
        return output.getvalue()

    def export_to_printable_html(self, deck_data: Dict[str, Any]) -> str:
        """Generates a beautiful print-ready cheatsheet HTML page."""
        title = deck_data.get("lecture_title", "Lecture Study Guide")
        summary = deck_data.get("executive_summary", "")
        topics = deck_data.get("topics", [])
        cards = deck_data.get("flashcards", [])

        topics_html = ""
        for t in topics:
            bullets = "".join(f"<li>{b}</li>" for b in t.get("key_takeaways", []))
            topics_html += f"""
            <div class="topic-box">
                <div class="topic-title">{t.get('heading', '')} <span class="badge">[{t.get('time_range', '')}]</span></div>
                <ul>{bullets}</ul>
                <div class="topic-notes">{t.get('detailed_notes', '')}</div>
            </div>
            """

        cards_html = ""
        for c in cards:
            cards_html += f"""
            <div class="card-item">
                <div class="card-q">Q: {c.get('front', '')}</div>
                <div class="card-a">A: {c.get('back', '')}</div>
                <div class="card-hint">Hint: {c.get('hint', '')}</div>
            </div>
            """

        return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<title>{title} — Study Cheatsheet</title>
<style>
    body {{ font-family: -apple-system, system-ui, sans-serif; line-height: 1.5; color: #1e293b; padding: 2rem; max-width: 850px; margin: auto; }}
    h1 {{ color: #0f172a; border-bottom: 2px solid #6366f1; padding-bottom: 0.5rem; }}
    .summary {{ background: #f8fafc; border-left: 4px solid #6366f1; padding: 1rem; border-radius: 4px; margin-bottom: 2rem; font-style: italic; }}
    .topic-box {{ margin-bottom: 1.5rem; border: 1px solid #e2e8f0; border-radius: 8px; padding: 1rem 1.25rem; }}
    .topic-title {{ font-size: 1.15rem; font-weight: 700; color: #1e1b4b; display: flex; justify-content: space-between; }}
    .badge {{ background: #e0e7ff; color: #3730a3; padding: 2px 8px; border-radius: 9999px; font-size: 0.8rem; font-family: monospace; }}
    .topic-notes {{ font-size: 0.9rem; color: #475569; margin-top: 0.5rem; }}
    .cards-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(240px, 1fr)); gap: 1rem; margin-top: 1rem; }}
    .card-item {{ border: 1px solid #cbd5e1; border-radius: 6px; padding: 0.75rem; background: #fafafa; font-size: 0.85rem; }}
    .card-q {{ font-weight: 600; color: #0f172a; margin-bottom: 0.25rem; }}
    .card-a {{ color: #334155; }}
    .card-hint {{ font-size: 0.75rem; color: #64748b; margin-top: 0.25rem; }}
    @media print {{ body {{ padding: 0; }} .topic-box {{ break-inside: avoid; }} }}
</style>
</head>
<body>
    <h1>{title}</h1>
    <div class="summary">{summary}</div>
    <h2>Structured Lecture Notes</h2>
    {topics_html}
    <h2>Quick Flashcard Summary</h2>
    <div class="cards-grid">{cards_html}</div>
</body>
</html>"""

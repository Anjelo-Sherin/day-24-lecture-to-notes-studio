"""
Unit Tests for Data Manager, Presets & Exporters
"""

import pytest
from src.data_manager import DataManager
from src.config import PRESETS_DIR


def test_presets_exist_and_load():
    dm = DataManager()
    presets = dm.list_preset_decks()
    assert len(presets) >= 4
    assert "mit_linear_algebra" in presets
    assert "cs50_memory_pointers" in presets
    assert "stanford_gradient_descent" in presets
    assert "quantum_computing_intro" in presets


def test_preset_data_integrity():
    dm = DataManager()
    deck = dm.load_preset_deck("mit_linear_algebra")
    assert deck is not None
    assert "topics" in deck
    assert "flashcards" in deck
    assert "quiz" in deck
    assert len(deck["topics"]) >= 3
    assert len(deck["flashcards"]) >= 5
    assert len(deck["quiz"]) >= 4


def test_markdown_exporter():
    dm = DataManager()
    deck = dm.load_preset_deck("cs50_memory_pointers")
    md = dm.export_to_markdown(deck)
    assert "# Harvard CS50: Pointers" in md
    assert "## 📖 Topic-Segmented Structured Notes" in md
    assert "## 🗂️ Active Recall Flashcards" in md
    assert "## 🎯 Self-Assessment Quiz" in md


def test_anki_tsv_exporter():
    dm = DataManager()
    deck = dm.load_preset_deck("stanford_gradient_descent")
    tsv = dm.export_to_anki_csv(deck["flashcards"])
    assert "#separator:tab" in tsv
    assert "Gradient Descent" in tsv or "Momentum" in tsv


def test_printable_html_exporter():
    dm = DataManager()
    deck = dm.load_preset_deck("quantum_computing_intro")
    html = dm.export_to_printable_html(deck)
    assert "<!DOCTYPE html>" in html
    assert "Quantum Computing 101" in html
    assert "Bloch Sphere" in html

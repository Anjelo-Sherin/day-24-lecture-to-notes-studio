"""
Unit Tests for Topic Segmentation & Keyword Extraction
"""

import pytest
from src.topic_segmenter import TopicSegmenter, format_seconds, extract_keywords_from_text


def test_format_seconds():
    assert format_seconds(0) == "00:00"
    assert format_seconds(65) == "01:05"
    assert format_seconds(3665) == "01:01:05"


def test_extract_keywords():
    text = "Machine learning algorithms optimize neural network weights using gradient descent and backpropagation."
    keywords = extract_keywords_from_text(text, top_n=3)
    assert len(keywords) > 0
    assert any(k.lower() in text.lower() for k in keywords)


def test_topic_segmenter_empty():
    segmenter = TopicSegmenter()
    chunks = segmenter.segment_transcript([])
    assert chunks == []


def test_topic_segmenter_short_transcript():
    segmenter = TopicSegmenter()
    segments = [
        {"start": 0.0, "end": 10.0, "text": "Hello world, welcome to computer science."},
        {"start": 10.5, "end": 20.0, "text": "Today we discuss simple data structures."},
    ]
    chunks = segmenter.segment_transcript(segments)
    assert len(chunks) == 1
    assert chunks[0]["start_time"] == 0.0
    assert chunks[0]["end_time"] == 20.0
    assert "data" in chunks[0]["text"].lower()


def test_topic_segmenter_thematic_transitions():
    segmenter = TopicSegmenter(min_chunk_duration=5.0)
    segments = [
        {"start": 0.0, "end": 10.0, "text": "Linear algebra studies vector spaces and matrix operations."},
        {"start": 10.5, "end": 20.0, "text": "Vectors have magnitude and direction in Euclidean space."},
        {"start": 20.5, "end": 30.0, "text": "Dot products calculate angles between vectors."},
        {"start": 30.5, "end": 40.0, "text": "Now switching gears completely to microbiology and cellular division."},
        {"start": 40.5, "end": 50.0, "text": "DNA replicates during interphase inside the eukaryotic nucleus."},
        {"start": 50.5, "end": 60.0, "text": "Mitosis produces two genetically identical diploid daughter cells."},
    ]
    chunks = segmenter.segment_transcript(segments, min_chunk_duration=15.0)
    assert len(chunks) >= 2
    assert "linear" in chunks[0]["text"].lower()
    assert "mitosis" in chunks[-1]["text"].lower()

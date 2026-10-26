"""
Semantic Topic Segmentation Engine
Chunks a continuous timestamped lecture transcript into coherent thematic sections
using TF-IDF semantic embeddings, cosine similarity valleys, and depth-score boundary detection.
"""

from __future__ import annotations

import re
from typing import List, Dict, Any, Tuple, Optional
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def format_seconds(seconds: float) -> str:
    """Formats float seconds into MM:SS or HH:MM:SS format."""
    total_sec = int(round(seconds))
    hrs = total_sec // 3600
    mins = (total_sec % 3600) // 60
    secs = total_sec % 60
    if hrs > 0:
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


def extract_keywords_from_text(text: str, top_n: int = 4) -> List[str]:
    """Extracts top representative keywords using TF-IDF."""
    clean = re.sub(r"[^a-zA-Z0-9\s]", " ", text.lower())
    words = [w for w in clean.split() if len(w) > 3]
    if not words:
        return ["Concepts"]
    
    try:
        vec = TfidfVectorizer(stop_words="english", max_features=10)
        tfidf = vec.fit_transform([clean])
        feature_names = vec.get_feature_names_out()
        scores = tfidf.toarray()[0]
        sorted_indices = np.argsort(scores)[::-1]
        keywords = [feature_names[i].capitalize() for i in sorted_indices[:top_n]]
        return keywords if keywords else ["Key Concept"]
    except Exception:
        # Fallback keyword extraction
        stop_words = {"this", "that", "with", "from", "have", "were", "what", "when", "where", "which"}
        freq = {}
        for w in words:
            if w not in stop_words:
                freq[w] = freq.get(w, 0) + 1
        sorted_words = sorted(freq.items(), key=lambda x: x[1], reverse=True)
        return [w.capitalize() for w, _ in sorted_words[:top_n]]


class TopicSegmenter:
    """Segments timestamped lecture sentences into coherent thematic topics."""

    def __init__(self, window_size: int = 2, threshold_percentile: float = 65.0, min_chunk_duration: float = 30.0):
        self.window_size = window_size
        self.threshold_percentile = threshold_percentile
        self.min_chunk_duration = min_chunk_duration

    def segment_transcript(
        self,
        segments: List[Dict[str, Any]],
        min_chunk_duration: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        """
        Segments transcript segments into structured topic units.
        Each input segment format:
        {'start': float, 'end': float, 'text': str, 'speaker': str (opt)}
        """
        if min_chunk_duration is None:
            min_chunk_duration = self.min_chunk_duration
        if not segments:
            return []

        # If too few segments to compute meaningful transitions, return as single topic
        if len(segments) <= 4:
            combined_text = " ".join(s["text"] for s in segments)
            keywords = extract_keywords_from_text(combined_text)
            return [
                {
                    "topic_id": 1,
                    "title": f"Lecture Overview: {', '.join(keywords[:2])}",
                    "start_time": segments[0]["start"],
                    "end_time": segments[-1]["end"],
                    "start_str": format_seconds(segments[0]["start"]),
                    "end_str": format_seconds(segments[-1]["end"]),
                    "summary_keywords": keywords,
                    "text": combined_text,
                    "raw_segments": segments,
                }
            ]

        # 1. Create pseudo-sentences with time anchors
        texts = [s["text"].strip() for s in segments]

        # 2. Vectorize texts using TF-IDF with sublinear tf
        try:
            vectorizer = TfidfVectorizer(
                stop_words="english",
                ngram_range=(1, 2),
                sublinear_tf=True,
                min_df=1,
            )
            tfidf_matrix = vectorizer.fit_transform(texts)
        except Exception:
            # Degenerate case fallback
            return self._fallback_equal_segmentation(segments)

        # 3. Compute cosine similarities between consecutive sliding windows
        similarities = []
        for i in range(len(segments) - 1):
            sim = cosine_similarity(tfidf_matrix[i], tfidf_matrix[i + 1])[0][0]
            similarities.append(float(sim))

        similarities = np.array(similarities)
        distances = 1.0 - similarities

        # 4. Depth score computation (valley / trough detection)
        # For index i, depth = (d_i - left_peak) + (d_i - right_peak)
        depth_scores = np.zeros(len(distances))
        for i in range(len(distances)):
            left_slice = distances[max(0, i - self.window_size):i + 1]
            right_slice = distances[i:min(len(distances), i + self.window_size + 1)]
            left_min = np.min(left_slice) if len(left_slice) > 0 else distances[i]
            right_min = np.min(right_slice) if len(right_slice) > 0 else distances[i]
            depth_scores[i] = (distances[i] - left_min) + (distances[i] - right_min)

        # 5. Determine cut points where depth score is high and chunk duration is satisfied
        threshold = np.percentile(depth_scores, self.threshold_percentile) if len(depth_scores) > 0 else 0.5
        cut_indices = []
        last_cut_time = segments[0]["start"]

        for i, score in enumerate(depth_scores):
            seg_time = segments[i + 1]["start"]
            if score >= threshold and (seg_time - last_cut_time) >= min_chunk_duration:
                cut_indices.append(i + 1)
                last_cut_time = seg_time

        # 6. Group segments by boundaries
        topic_chunks: List[Dict[str, Any]] = []
        start_idx = 0
        all_cuts = cut_indices + [len(segments)]

        for topic_num, end_idx in enumerate(all_cuts, start=1):
            if start_idx >= len(segments):
                break
            group = segments[start_idx:end_idx]
            if not group:
                continue

            chunk_text = " ".join(s["text"] for s in group)
            start_time = group[0]["start"]
            end_time = group[-1]["end"]
            keywords = extract_keywords_from_text(chunk_text)

            # Generate smart descriptive title
            title = f"Topic {topic_num}: {' & '.join(keywords[:2])}"

            topic_chunks.append(
                {
                    "topic_id": topic_num,
                    "title": title,
                    "start_time": start_time,
                    "end_time": end_time,
                    "start_str": format_seconds(start_time),
                    "end_str": format_seconds(end_time),
                    "summary_keywords": keywords,
                    "text": chunk_text,
                    "raw_segments": group,
                }
            )
            start_idx = end_idx

        return topic_chunks

    def _fallback_equal_segmentation(self, segments: List[Dict[str, Any]], num_chunks: int = 3) -> List[Dict[str, Any]]:
        """Splits segments evenly if vectorizer fails."""
        chunk_size = max(1, len(segments) // num_chunks)
        chunks = []
        for i in range(0, len(segments), chunk_size):
            group = segments[i:i + chunk_size]
            text = " ".join(s["text"] for s in group)
            keywords = extract_keywords_from_text(text)
            topic_num = (i // chunk_size) + 1
            chunks.append(
                {
                    "topic_id": topic_num,
                    "title": f"Topic {topic_num}: {' & '.join(keywords[:2])}",
                    "start_time": group[0]["start"],
                    "end_time": group[-1]["end"],
                    "start_str": format_seconds(group[0]["start"]),
                    "end_str": format_seconds(group[-1]["end"]),
                    "summary_keywords": keywords,
                    "text": text,
                    "raw_segments": group,
                }
            )
        return chunks

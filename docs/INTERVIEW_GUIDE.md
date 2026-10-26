# Interview Guide & Technical Defense

**SynapseLecture AI (Day 24 of 30 Projects in 30 Days)**  
*Domain: EdTech + Speech + GenAI*

---

## 1. Key Interview Talking Points

### Talking Point 1: Chunking Strategies — Semantic Similarity vs Fixed-Token Splitting
* **Question:** *"Why did you implement semantic topic segmentation instead of standard 512-token chunking?"*
* **Response:**  
  "Fixed-token or fixed-character chunking is naive for educational content. A lecturer might spend 80 seconds introducing a formula, and an arbitrary token cut would split the theorem statement across two chunks, leaving both incomplete.  
  By vectorizing sliding sentences and identifying **semantic distance valleys** (troughs where the vocabulary transitions from one thematic cluster to another), we detect natural pedagogical topic boundaries. This guarantees that each generated note section and flashcard corresponds to a coherent conceptual unit."

---

### Talking Point 2: Prompt Engineering & JSON Schema Enforcement
* **Question:** *"How do you guarantee that the LLM output doesn't break your frontend parsing?"*
* **Response:**  
  "We enforce strict JSON Schema validation at two layers:
  1. **API Level:** When calling Google Gemini API, we utilize `response_mime_type: 'application/json'` and supply a strict schema definition for `topics`, `flashcards`, and `quiz`.
  2. **Normalization & Fallback:** Our `LectureGenAIEngine` includes an intelligent deterministic local engine with schema normalizers that check required fields (`card_id`, `front`, `back`, `options`, `correct_index`, `explanation`) before state insertion. If the API fails or is unconfigured, the application runs 100% offline without crashing."

---

### Talking Point 3: Spaced Repetition — SM-2 vs Leitner vs FSRS
* **Question:** *"Why did you choose the SuperMemo SM-2 algorithm over a simple Leitner box system?"*
* **Response:**  
  "The Leitner system uses fixed discrete buckets (e.g., Box 1 = 1 day, Box 2 = 2 days, Box 3 = 4 days), which does not account for intrinsic card difficulty.  
  The SM-2 algorithm continuously modulates the **Easiness Factor ($EF$)** per card based on 6 recall grades ($0-5$). Difficult cards naturally stabilize at lower intervals, while intuitive cards rapidly expand their review intervals into weeks and months, saving student time while maintaining a target 90% recall retention rate."

---

### Talking Point 4: Evaluation of Generated Multiple Choice Questions
* **Question:** *"How do you ensure generated quiz questions aren't trivially easy or misleading?"*
* **Response:**  
  "A quiz question is only as good as its distractors. We evaluate questions across three criteria:
  1. **Grounding:** Every question is tied to an explicit timestamp range and concept extracted directly from the transcript, preventing open-ended hallucinations.
  2. **Plausible Distractors:** Rather than using absurd dummy answers, distractors embody common student misconceptions or inverted logical premises.
  3. **Pedagogical Feedback:** Every question includes an explanation explaining both why the correct answer is valid and why alternatives fail."

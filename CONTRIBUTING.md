# Contributing to SynapseLecture AI

Thank you for your interest in contributing to **SynapseLecture AI (Day 24 of 30 Projects in 30 Days)**!

## Development Workflow

1. **Fork & Clone** the repository:
   ```bash
   git clone https://github.com/Anjelo-Sherin/day-24-lecture-to-notes-studio.git
   cd day-24-lecture-to-notes-studio
   ```

2. **Set up Virtual Environment**:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Run the Test Suite**:
   ```bash
   pytest tests/
   ```

4. **Launch Local Development Studio**:
   ```bash
   streamlit run app.py --server.port=8024
   ```

## Code Standards
- Ensure all 20+ unit tests pass before opening a PR.
- Keep all algorithms (SM-2, Topic Segmentation, JSON Schema generators) deterministic and test-covered.
- Maintain clean, user-friendly UI standards with zero uncaught exceptions.

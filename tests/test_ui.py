"""
UI & End-to-End Streamlit App Test
Verifies that app.py initializes, loads preset decks, and renders components without uncaught exceptions.
"""

import pytest
from streamlit.testing.v1 import AppTest


def test_app_loads_successfully():
    """Simulates loading app.py through Streamlit AppTest framework."""
    at = AppTest.from_file("app.py", default_timeout=15)
    at.run()
    # Ensure no exception elements were rendered
    assert not at.exception
    # Check that title or selectbox is present
    assert len(at.selectbox) >= 1
    assert any("MIT 18.06" in opt for opt in at.selectbox[0].options)

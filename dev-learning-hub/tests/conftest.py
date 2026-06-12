"""
conftest.py — Shared fixtures for dev-learning-hub tests.
"""
import sys
import os
import json
import tempfile
import shutil
import pytest

# Ensure the app module is importable from the parent directory
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


@pytest.fixture(scope="session")
def app():
    """Create the Flask app with test configuration."""
    import app as flask_app_module

    flask_app_module.app.config.update(
        {
            "TESTING": True,
            "WTF_CSRF_ENABLED": False,
        }
    )

    # Point progress file to a temp file so tests don't pollute production progress
    tmp_dir = tempfile.mkdtemp()
    progress_path = os.path.join(tmp_dir, "test_progress.json")
    original_progress_file = flask_app_module.PROGRESS_FILE

    flask_app_module.PROGRESS_FILE = type(flask_app_module.PROGRESS_FILE)(progress_path)

    yield flask_app_module.app

    # Restore
    flask_app_module.PROGRESS_FILE = original_progress_file
    shutil.rmtree(tmp_dir, ignore_errors=True)


@pytest.fixture()
def client(app):
    """Return a test client for the app."""
    return app.test_client()


@pytest.fixture(scope="session")
def questions_data():
    """Load questions.json once for the whole test session."""
    questions_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "questions.json",
    )
    with open(questions_path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def library_data():
    """Load library.json once for the whole test session."""
    library_path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "library.json",
    )
    with open(library_path, encoding="utf-8") as f:
        return json.load(f)


@pytest.fixture(scope="session")
def challenges_data():
    """Load challenges.json once for the whole test session."""
    path = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "challenges.json",
    )
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return json.load(f)

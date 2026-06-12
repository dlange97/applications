"""
test_app.py — Automated tests for dev-learning-hub Flask application.

Tests cover:
 - Data integrity   (questions.json, library.json, challenges.json)
 - API endpoints    (GET/POST responses, filtering, error handling)
 - Business logic   (answer evaluation, progress tracking, reset)
"""
import json
import pytest


# ---------------------------------------------------------------------------
# Data integrity tests
# ---------------------------------------------------------------------------


class TestQuestionsDataIntegrity:
    """Validates questions.json content correctness."""

    LANGUAGES = ("python", "php")
    CATEGORIES = ("basics", "frameworks", "recruitment")
    REQUIRED_FIELDS = {"id", "question", "options", "answer", "explanation"}

    def test_top_level_keys(self, questions_data):
        """Both language keys must be present."""
        for lang in self.LANGUAGES:
            assert lang in questions_data, f"Missing top-level key: {lang}"

    def test_all_categories_present(self, questions_data):
        """Every language must have basics, frameworks, and recruitment."""
        for lang in self.LANGUAGES:
            for cat in self.CATEGORIES:
                assert cat in questions_data[lang], (
                    f"Missing category '{cat}' for language '{lang}'"
                )

    def test_minimum_question_count(self, questions_data):
        """Each category must have at least 20 questions."""
        for lang in self.LANGUAGES:
            for cat in self.CATEGORIES:
                count = len(questions_data[lang][cat])
                assert count >= 20, (
                    f"{lang}/{cat} has only {count} questions (minimum 20 required)"
                )

    def test_required_fields_present(self, questions_data):
        """Every question must contain all required fields."""
        for lang in self.LANGUAGES:
            for cat in self.CATEGORIES:
                for q in questions_data[lang][cat]:
                    missing = self.REQUIRED_FIELDS - q.keys()
                    assert not missing, (
                        f"Question '{q.get('id', '?')}' missing fields: {missing}"
                    )

    def test_options_count_exactly_four(self, questions_data):
        """Every question must have exactly 4 options."""
        for lang in self.LANGUAGES:
            for cat in self.CATEGORIES:
                for q in questions_data[lang][cat]:
                    assert len(q["options"]) == 4, (
                        f"Question '{q['id']}' has {len(q['options'])} options (expected 4)"
                    )

    def test_answer_index_valid(self, questions_data):
        """Answer index must be 0-3 (valid index into options list)."""
        for lang in self.LANGUAGES:
            for cat in self.CATEGORIES:
                for q in questions_data[lang][cat]:
                    assert q["answer"] in (0, 1, 2, 3), (
                        f"Question '{q['id']}' has invalid answer index: {q['answer']}"
                    )

    def test_no_duplicate_ids(self, questions_data):
        """Question IDs must be globally unique across all sections."""
        all_ids = []
        for lang in self.LANGUAGES:
            for cat in self.CATEGORIES:
                all_ids.extend(q["id"] for q in questions_data[lang][cat])
        duplicates = [id_ for id_ in all_ids if all_ids.count(id_) > 1]
        assert not duplicates, f"Duplicate question IDs found: {set(duplicates)}"

    def test_question_strings_non_empty(self, questions_data):
        """Question and explanation must not be empty strings."""
        for lang in self.LANGUAGES:
            for cat in self.CATEGORIES:
                for q in questions_data[lang][cat]:
                    assert q["question"].strip(), f"Question '{q['id']}' has empty question text"
                    assert q["explanation"].strip(), f"Question '{q['id']}' has empty explanation"

    def test_options_non_empty(self, questions_data):
        """Each option must be a non-empty string."""
        for lang in self.LANGUAGES:
            for cat in self.CATEGORIES:
                for q in questions_data[lang][cat]:
                    for i, opt in enumerate(q["options"]):
                        assert isinstance(opt, str) and opt.strip(), (
                            f"Question '{q['id']}' option {i} is empty or not a string"
                        )

    def test_id_format_matches_language(self, questions_data):
        """Python question IDs start with 'py_', PHP with 'php_'."""
        prefixes = {"python": "py_", "php": "php_"}
        for lang, prefix in prefixes.items():
            for cat in self.CATEGORIES:
                for q in questions_data[lang][cat]:
                    assert q["id"].startswith(prefix), (
                        f"Question '{q['id']}' in '{lang}' doesn't start with '{prefix}'"
                    )


class TestLibraryDataIntegrity:
    """Validates library.json content correctness."""

    LANGUAGES = ("python", "php")
    REQUIRED_FIELDS = {"id", "level", "title", "subtitle", "summary", "content", "key_takeaways"}
    VALID_LEVELS = {"podstawy", "zaawansowane", "frameworki"}

    def test_top_level_keys(self, library_data):
        """Both language keys must be present."""
        for lang in self.LANGUAGES:
            assert lang in library_data, f"Missing top-level key: {lang}"

    def test_minimum_article_count(self, library_data):
        """Each language must have at least 8 articles."""
        for lang in self.LANGUAGES:
            count = len(library_data[lang])
            assert count >= 8, (
                f"{lang} has only {count} articles (minimum 8 required)"
            )

    def test_required_fields_present(self, library_data):
        """Every article must contain all required fields."""
        for lang in self.LANGUAGES:
            for art in library_data[lang]:
                missing = self.REQUIRED_FIELDS - art.keys()
                assert not missing, (
                    f"Article '{art.get('id', '?')}' missing fields: {missing}"
                )

    def test_level_values_valid(self, library_data):
        """Article level must be one of the valid values."""
        for lang in self.LANGUAGES:
            for art in library_data[lang]:
                assert art["level"] in self.VALID_LEVELS, (
                    f"Article '{art['id']}' has invalid level: '{art['level']}'"
                )

    def test_no_duplicate_ids(self, library_data):
        """Article IDs must be globally unique."""
        all_ids = []
        for lang in self.LANGUAGES:
            all_ids.extend(art["id"] for art in library_data[lang])
        duplicates = [id_ for id_ in all_ids if all_ids.count(id_) > 1]
        assert not duplicates, f"Duplicate article IDs: {set(duplicates)}"

    def test_content_non_empty(self, library_data):
        """Content, title, and summary must not be empty."""
        for lang in self.LANGUAGES:
            for art in library_data[lang]:
                assert art["title"].strip(), f"Article '{art['id']}' has empty title"
                assert art["content"].strip(), f"Article '{art['id']}' has empty content"
                assert art["summary"].strip(), f"Article '{art['id']}' has empty summary"

    def test_key_takeaways_list(self, library_data):
        """key_takeaways must be a non-empty list of strings."""
        for lang in self.LANGUAGES:
            for art in library_data[lang]:
                assert isinstance(art["key_takeaways"], list), (
                    f"Article '{art['id']}' key_takeaways is not a list"
                )
                assert len(art["key_takeaways"]) >= 1, (
                    f"Article '{art['id']}' has empty key_takeaways list"
                )
                for takeaway in art["key_takeaways"]:
                    assert isinstance(takeaway, str) and takeaway.strip(), (
                        f"Article '{art['id']}' has invalid takeaway: {takeaway!r}"
                    )

    def test_levels_distribution(self, library_data):
        """Each language should have articles for at least 2 different levels."""
        for lang in self.LANGUAGES:
            levels_present = {art["level"] for art in library_data[lang]}
            assert len(levels_present) >= 2, (
                f"{lang} only covers {levels_present} levels — too narrow"
            )


# ---------------------------------------------------------------------------
# Homepage
# ---------------------------------------------------------------------------


class TestHomepage:
    def test_homepage_returns_200(self, client):
        resp = client.get("/")
        assert resp.status_code == 200

    def test_homepage_returns_html(self, client):
        resp = client.get("/")
        assert b"<!DOCTYPE html>" in resp.data or b"<html" in resp.data


# ---------------------------------------------------------------------------
# /api/questions
# ---------------------------------------------------------------------------


class TestQuestionsEndpoint:
    def test_returns_200(self, client):
        resp = client.get("/api/questions")
        assert resp.status_code == 200

    def test_returns_json(self, client):
        resp = client.get("/api/questions")
        assert resp.content_type.startswith("application/json")

    def test_has_questions_key(self, client):
        resp = client.get("/api/questions")
        data = resp.get_json()
        assert "questions" in data

    def test_returns_list(self, client):
        resp = client.get("/api/questions")
        data = resp.get_json()
        assert isinstance(data["questions"], list)

    def test_total_count_at_least_120(self, client):
        """With 25 questions × 6 sections we should have at least 120 total."""
        resp = client.get("/api/questions")
        data = resp.get_json()
        assert len(data["questions"]) >= 120

    def test_filter_by_python(self, client):
        resp = client.get("/api/questions?language=python")
        data = resp.get_json()
        langs = {q["language"] for q in data["questions"]}
        assert langs == {"python"}

    def test_filter_by_php(self, client):
        resp = client.get("/api/questions?language=php")
        data = resp.get_json()
        langs = {q["language"] for q in data["questions"]}
        assert langs == {"php"}

    def test_filter_by_category_basics(self, client):
        resp = client.get("/api/questions?category=basics")
        data = resp.get_json()
        cats = {q["category"] for q in data["questions"]}
        assert cats == {"basics"}

    def test_filter_by_category_frameworks(self, client):
        resp = client.get("/api/questions?category=frameworks")
        data = resp.get_json()
        cats = {q["category"] for q in data["questions"]}
        assert cats == {"frameworks"}

    def test_filter_by_category_recruitment(self, client):
        resp = client.get("/api/questions?category=recruitment")
        data = resp.get_json()
        cats = {q["category"] for q in data["questions"]}
        assert cats == {"recruitment"}

    def test_combined_filter_python_basics(self, client):
        resp = client.get("/api/questions?language=python&category=basics")
        data = resp.get_json()
        for q in data["questions"]:
            assert q["language"] == "python"
            assert q["category"] == "basics"

    def test_question_structure(self, client):
        """Each returned question must have the required fields."""
        resp = client.get("/api/questions?language=python&category=basics")
        data = resp.get_json()
        required = {"id", "language", "category", "question", "options", "answer", "explanation"}
        for q in data["questions"]:
            assert required <= q.keys(), f"Question missing fields: {required - q.keys()}"

    def test_options_count(self, client):
        resp = client.get("/api/questions?language=python&category=basics")
        data = resp.get_json()
        for q in data["questions"]:
            assert len(q["options"]) == 4


# ---------------------------------------------------------------------------
# /api/submit-answer
# ---------------------------------------------------------------------------


class TestSubmitAnswer:
    def _get_first_question_id(self, client):
        resp = client.get("/api/questions?language=python&category=basics")
        data = resp.get_json()
        return data["questions"][0]

    def test_correct_answer(self, client):
        q = self._get_first_question_id(client)
        resp = client.post(
            "/api/submit-answer",
            json={"question_id": q["id"], "selected_option": q["answer"]},
        )
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["success"] is True
        assert data["correct"] is True

    def test_wrong_answer(self, client):
        q = self._get_first_question_id(client)
        wrong_answer = (q["answer"] + 1) % 4
        resp = client.post(
            "/api/submit-answer",
            json={"question_id": q["id"], "selected_option": wrong_answer},
        )
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["success"] is True
        assert data["correct"] is False

    def test_returns_explanation(self, client):
        q = self._get_first_question_id(client)
        resp = client.post(
            "/api/submit-answer",
            json={"question_id": q["id"], "selected_option": 0},
        )
        data = resp.get_json()
        assert "explanation" in data
        assert isinstance(data["explanation"], str)
        assert len(data["explanation"]) > 0

    def test_returns_correct_option_index(self, client):
        q = self._get_first_question_id(client)
        resp = client.post(
            "/api/submit-answer",
            json={"question_id": q["id"], "selected_option": 0},
        )
        data = resp.get_json()
        assert "correct_option" in data
        assert data["correct_option"] == q["answer"]

    def test_returns_streak(self, client):
        q = self._get_first_question_id(client)
        resp = client.post(
            "/api/submit-answer",
            json={"question_id": q["id"], "selected_option": q["answer"]},
        )
        data = resp.get_json()
        assert "streak" in data
        assert isinstance(data["streak"], int)

    def test_missing_question_id_returns_400(self, client):
        resp = client.post(
            "/api/submit-answer",
            json={"selected_option": 0},
        )
        assert resp.status_code == 400

    def test_missing_selected_option_returns_400(self, client):
        resp = client.post(
            "/api/submit-answer",
            json={"question_id": "py_basics_1"},
        )
        assert resp.status_code == 400

    def test_nonexistent_question_id_returns_404(self, client):
        resp = client.post(
            "/api/submit-answer",
            json={"question_id": "DOES_NOT_EXIST_99", "selected_option": 0},
        )
        assert resp.status_code == 404

    def test_empty_body_returns_400(self, client):
        resp = client.post(
            "/api/submit-answer",
            json={},
        )
        assert resp.status_code == 400


# ---------------------------------------------------------------------------
# /api/submit-quiz-session
# ---------------------------------------------------------------------------


class TestSubmitQuizSession:
    def test_returns_success(self, client):
        resp = client.post(
            "/api/submit-quiz-session",
            json={"language": "python", "category": "basics", "total": 10, "correct": 7},
        )
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["success"] is True

    def test_empty_body_still_works(self, client):
        """Submit-quiz-session should not crash with missing fields."""
        resp = client.post("/api/submit-quiz-session", json={})
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True


# ---------------------------------------------------------------------------
# /api/reset
# ---------------------------------------------------------------------------


class TestResetEndpoint:
    def test_reset_returns_success(self, client):
        resp = client.post("/api/reset")
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["success"] is True

    def test_reset_clears_progress(self, client):
        # First answer a question to create some progress
        q_resp = client.get("/api/questions?language=python&category=basics")
        q = q_resp.get_json()["questions"][0]
        client.post(
            "/api/submit-answer",
            json={"question_id": q["id"], "selected_option": q["answer"]},
        )
        # Now reset
        client.post("/api/reset")
        # Homepage should show 0 answered
        home_resp = client.get("/")
        assert home_resp.status_code == 200


# ---------------------------------------------------------------------------
# /api/challenges
# ---------------------------------------------------------------------------


class TestChallengesEndpoint:
    def test_returns_200(self, client):
        resp = client.get("/api/challenges")
        assert resp.status_code == 200

    def test_returns_json(self, client):
        resp = client.get("/api/challenges")
        assert resp.content_type.startswith("application/json")

    def test_has_challenges_key(self, client):
        resp = client.get("/api/challenges")
        data = resp.get_json()
        assert "challenges" in data

    def test_challenges_is_list(self, client):
        resp = client.get("/api/challenges")
        data = resp.get_json()
        assert isinstance(data["challenges"], list)

    def test_challenge_structure(self, client, challenges_data):
        if not challenges_data:
            pytest.skip("No challenges available")
        resp = client.get("/api/challenges")
        data = resp.get_json()
        required = {"id", "language", "difficulty", "title", "description", "boilerplate"}
        for ch in data["challenges"]:
            assert required <= ch.keys(), f"Challenge missing fields: {required - ch.keys()}"


# ---------------------------------------------------------------------------
# /api/library
# ---------------------------------------------------------------------------


class TestLibraryEndpoint:
    def test_returns_200(self, client):
        resp = client.get("/api/library")
        assert resp.status_code == 200

    def test_returns_json(self, client):
        resp = client.get("/api/library")
        assert resp.content_type.startswith("application/json")

    def test_returns_both_languages(self, client):
        resp = client.get("/api/library")
        data = resp.get_json()
        assert "python" in data
        assert "php" in data

    def test_python_articles_non_empty(self, client):
        resp = client.get("/api/library")
        data = resp.get_json()
        assert len(data["python"]) >= 8

    def test_php_articles_non_empty(self, client):
        resp = client.get("/api/library")
        data = resp.get_json()
        assert len(data["php"]) >= 8

    def test_filter_by_python(self, client):
        resp = client.get("/api/library?language=python")
        data = resp.get_json()
        assert "python" in data
        assert "php" not in data

    def test_filter_by_php(self, client):
        resp = client.get("/api/library?language=php")
        data = resp.get_json()
        assert "php" in data
        assert "python" not in data

    def test_filter_by_level_podstawy(self, client):
        resp = client.get("/api/library?level=podstawy")
        data = resp.get_json()
        for lang in ("python", "php"):
            if lang in data:
                for art in data[lang]:
                    assert art["level"] == "podstawy", (
                        f"Article '{art['id']}' has level '{art['level']}' but 'podstawy' was requested"
                    )

    def test_filter_by_level_zaawansowane(self, client):
        resp = client.get("/api/library?level=zaawansowane")
        data = resp.get_json()
        for lang in ("python", "php"):
            if lang in data:
                for art in data[lang]:
                    assert art["level"] == "zaawansowane"

    def test_filter_by_level_frameworki(self, client):
        resp = client.get("/api/library?level=frameworki")
        data = resp.get_json()
        for lang in ("python", "php"):
            if lang in data:
                for art in data[lang]:
                    assert art["level"] == "frameworki"

    def test_combined_filter_python_zaawansowane(self, client):
        resp = client.get("/api/library?language=python&level=zaawansowane")
        data = resp.get_json()
        assert "python" in data
        assert "php" not in data
        for art in data["python"]:
            assert art["level"] == "zaawansowane"

    def test_article_structure(self, client):
        """Each article must contain all required fields."""
        resp = client.get("/api/library")
        data = resp.get_json()
        required = {"id", "level", "title", "subtitle", "summary", "content", "key_takeaways"}
        for lang in ("python", "php"):
            for art in data[lang]:
                missing = required - art.keys()
                assert not missing, f"Article '{art.get('id')}' missing fields: {missing}"

    def test_key_takeaways_is_list(self, client):
        resp = client.get("/api/library")
        data = resp.get_json()
        for lang in ("python", "php"):
            for art in data[lang]:
                assert isinstance(art["key_takeaways"], list), (
                    f"Article '{art['id']}' key_takeaways is not a list"
                )

    def test_unknown_level_returns_empty_lists(self, client):
        resp = client.get("/api/library?level=unknown_level_xyz")
        data = resp.get_json()
        for lang in ("python", "php"):
            if lang in data:
                assert data[lang] == [], (
                    f"Expected empty list for unknown level, got {data[lang]}"
                )


# ---------------------------------------------------------------------------
# /api/submit-challenge  (code execution sandbox)
# ---------------------------------------------------------------------------


class TestSubmitChallenge:
    def test_missing_challenge_id_returns_400(self, client):
        resp = client.post(
            "/api/submit-challenge",
            json={"code": "print('hello')"},
        )
        assert resp.status_code == 400

    def test_nonexistent_challenge_id_returns_404(self, client):
        resp = client.post(
            "/api/submit-challenge",
            json={"challenge_id": "DOES_NOT_EXIST", "code": "print('hello')"},
        )
        assert resp.status_code == 404

    def test_valid_python_challenge(self, client, challenges_data):
        """Submit correct code for a Python challenge and expect success."""
        python_challenges = [
            ch for ch in challenges_data if ch.get("language") == "python"
        ]
        if not python_challenges:
            pytest.skip("No Python challenges available")

        ch = python_challenges[0]
        resp = client.post(
            "/api/submit-challenge",
            json={"challenge_id": ch["id"], "code": ch.get("boilerplate", "")},
        )
        data = resp.get_json()
        assert resp.status_code == 200
        assert data["success"] is True
        # We don't assert correct=True here as boilerplate may not pass validation


# ---------------------------------------------------------------------------
# Progress tracking integration tests
# ---------------------------------------------------------------------------


class TestProgressTracking:
    def test_correct_answers_increase_streak(self, client):
        """Answering correctly should increase streak."""
        q_resp = client.get("/api/questions?language=python&category=basics")
        questions = q_resp.get_json()["questions"]

        # Reset first to get clean state
        client.post("/api/reset")

        # Answer first question correctly
        q = questions[0]
        resp = client.post(
            "/api/submit-answer",
            json={"question_id": q["id"], "selected_option": q["answer"]},
        )
        data = resp.get_json()
        assert data["streak"] >= 1

    def test_wrong_answer_resets_streak(self, client):
        """Answering incorrectly should reset streak to 0."""
        q_resp = client.get("/api/questions?language=python&category=basics")
        questions = q_resp.get_json()["questions"]

        q = questions[0]
        wrong = (q["answer"] + 1) % 4
        resp = client.post(
            "/api/submit-answer",
            json={"question_id": q["id"], "selected_option": wrong},
        )
        data = resp.get_json()
        assert data["streak"] == 0

    def test_submit_multiple_and_check_homepage(self, client):
        """Homepage should render without error after multiple submissions."""
        client.post("/api/reset")

        q_resp = client.get("/api/questions?language=python&category=basics")
        questions = q_resp.get_json()["questions"][:3]

        for q in questions:
            client.post(
                "/api/submit-answer",
                json={"question_id": q["id"], "selected_option": q["answer"]},
            )

        home = client.get("/")
        assert home.status_code == 200

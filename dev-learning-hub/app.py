#!/usr/bin/env python3
"""
app.py - Flask Web Application for Dev Learning Hub (Python & PHP)
Stores application state locally in progress.json without DB dependencies.
"""

from __future__ import annotations
import os
import json
import datetime
from pathlib import Path
from flask import Flask, request, jsonify, render_template

app = Flask(__name__)

# Base Paths
BASE_DIR = Path(__file__).resolve().parent
QUESTIONS_FILE = BASE_DIR / "questions.json"
PROGRESS_FILE = BASE_DIR / "progress.json"
CHALLENGES_FILE = BASE_DIR / "challenges.json"
LIBRARY_FILE = BASE_DIR / "library.json"

# In-memory cache of questions and challenges
questions_db = {}
if QUESTIONS_FILE.exists():
    try:
        with open(QUESTIONS_FILE, "r", encoding="utf-8") as f:
            questions_db = json.load(f)
    except Exception as e:
        print(f"⚠️ Error loading questions.json: {e}")
else:
    print("❌ Fatal: questions.json not found!")

challenges_db = []
if CHALLENGES_FILE.exists():
    try:
        with open(CHALLENGES_FILE, "r", encoding="utf-8") as f:
            challenges_db = json.load(f)
    except Exception as e:
        print(f"⚠️ Error loading challenges.json: {e}")
else:
    print("⚠️ Warning: challenges.json not found!")

library_db = {}
if LIBRARY_FILE.exists():
    try:
        with open(LIBRARY_FILE, "r", encoding="utf-8") as f:
            library_db = json.load(f)
    except Exception as e:
        print(f"⚠️ Error loading library.json: {e}")
else:
    print("⚠️ Warning: library.json not found!")

# Helper for loading/saving progress
def get_default_progress():
    return {
        "total_answered": 0,
        "correct_answers": 0,
        "incorrect_answers": 0,
        "streak": 0,
        "max_streak": 0,
        "completed_quizzes_count": 0,
        "last_activity": "",
        "category_stats": {
            "python:basics": {"answered": 0, "correct": 0},
            "python:frameworks": {"answered": 0, "correct": 0},
            "python:recruitment": {"answered": 0, "correct": 0},
            "php:basics": {"answered": 0, "correct": 0},
            "php:frameworks": {"answered": 0, "correct": 0},
            "php:recruitment": {"answered": 0, "correct": 0}
        },
        "by_question_id": {},
        "history": [] # list of {"timestamp": str, "language": str, "category": str, "total": int, "correct": int}
    }

def load_progress() -> dict:
    if not PROGRESS_FILE.exists():
        progress = get_default_progress()
        save_progress(progress)
        return progress
    try:
        with open(PROGRESS_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            # Ensure basic keys exist
            default = get_default_progress()
            for k, v in default.items():
                if k not in data:
                    data[k] = v
            # Backwards compatibility check for category_stats keys
            for cat in default["category_stats"].keys():
                if "category_stats" not in data:
                    data["category_stats"] = {}
                if cat not in data["category_stats"]:
                    data["category_stats"][cat] = {"answered": 0, "correct": 0}
            return data
    except Exception as e:
        print(f"⚠️ Error reading progress.json, resetting: {e}")
        return get_default_progress()
        print(f"⚠️ Error reading progress.json, resetting: {e}")
        return get_default_progress()

def save_progress(data: dict):
    try:
        with open(PROGRESS_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"⚠️ Error saving progress.json: {e}")


@app.route("/")
def index():
    progress = load_progress()
    # Calculate stats for homepage
    total_q = 0
    for lang, cats in questions_db.items():
        for cat, q_list in cats.items():
            total_q += len(q_list)
            
    # Success rate calculation
    success_rate = 0
    if progress["total_answered"] > 0:
        success_rate = round((progress["correct_answers"] / progress["total_answered"]) * 100, 1)

    return render_template(
        "index.html",
        progress=progress,
        total_questions=total_q,
        success_rate=success_rate
    )


@app.route("/api/questions", methods=["GET"])
def get_questions():
    lang = request.args.get("language")   # "python" or "php" or "all"
    category = request.args.get("category") # "basics" or "frameworks" or "all"
    
    result = []
    
    # Filter by language
    langs_to_scan = [lang] if lang in ["python", "php"] else ["python", "php"]
    
    for l in langs_to_scan:
        if l not in questions_db:
            continue
        # Filter by category
        cats_to_scan = [category] if category in ["basics", "frameworks", "recruitment"] else ["basics", "frameworks", "recruitment"]
        for c in cats_to_scan:
            if c not in questions_db[l]:
                continue
            for q in questions_db[l][c]:
                # We return fields required by frontend but avoid leaking index answer index directly if desired,
                # though since it's a completely local app we can send the full JSON. Let's send the full object
                # for easy offline evaluation or just keep it simple!
                result.append({
                    "id": q["id"],
                    "language": l,
                    "category": c,
                    "question": q["question"],
                    "options": q["options"],
                    "answer": q["answer"], # will evaluate on client-side / server-side
                    "explanation": q["explanation"]
                })
                
    return jsonify({"questions": result})


@app.route("/api/submit-answer", methods=["POST"])
def submit_answer():
    data = request.get_json() or {}
    q_id = data.get("question_id")
    selected_option = data.get("selected_option") # integer index
    
    if q_id is None or selected_option is None:
        return jsonify({"success": False, "error": "Brak wymaganych parametrów."}), 400
        
    # Find the question in questions_db
    found_q = None
    qlang = None
    qcat = None
    for lang, cats in questions_db.items():
        for cat, q_list in cats.items():
            for q in q_list:
                if q["id"] == q_id:
                    found_q = q
                    qlang = lang
                    qcat = cat
                    break
            if found_q:
                break
        if found_q:
            break
            
    if not found_q:
        return jsonify({"success": False, "error": "Nie znaleziono pytania o podanym ID."}), 404
        
    is_correct = (selected_option == found_q["answer"])
    
    # Update local progress file
    progress = load_progress()
    progress["total_answered"] += 1
    progress["last_activity"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    # Handle streak
    if is_correct:
        progress["correct_answers"] += 1
        progress["streak"] += 1
        if progress["streak"] > progress["max_streak"]:
            progress["max_streak"] = progress["streak"]
    else:
        progress["incorrect_answers"] += 1
        progress["streak"] = 0
        
    # Stats per category
    cat_key = f"{qlang}:{qcat}"
    if cat_key in progress["category_stats"]:
        progress["category_stats"][cat_key]["answered"] += 1
        if is_correct:
            progress["category_stats"][cat_key]["correct"] += 1
            
    # Stats per question id
    if q_id not in progress["by_question_id"]:
        progress["by_question_id"][q_id] = {"answered_count": 0, "correct_count": 0, "last_result": ""}
    
    progress["by_question_id"][q_id]["answered_count"] += 1
    if is_correct:
        progress["by_question_id"][q_id]["correct_count"] += 1
        progress["by_question_id"][q_id]["last_result"] = "correct"
    else:
        progress["by_question_id"][q_id]["last_result"] = "incorrect"
        
    save_progress(progress)
    
    return jsonify({
        "success": True,
        "correct": is_correct,
        "correct_option": found_q["answer"],
        "explanation": found_q["explanation"],
        "streak": progress["streak"],
        "max_streak": progress["max_streak"]
    })


@app.route("/api/submit-quiz-session", methods=["POST"])
def submit_quiz_session():
    """Saves the completed quiz session in history."""
    data = request.get_json() or {}
    language = data.get("language", "all")
    category = data.get("category", "all")
    total = data.get("total", 0)
    correct = data.get("correct", 0)
    
    progress = load_progress()
    progress["completed_quizzes_count"] += 1
    
    # Limit history list to last 50 entries
    session_record = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "language": language.upper(),
        "category": category.capitalize(),
        "total": total,
        "correct": correct
    }
    progress["history"].insert(0, session_record)
    progress["history"] = progress["history"][:50]
    
    save_progress(progress)
    return jsonify({"success": True})


@app.route("/api/reset", methods=["POST"])
def reset_progress():
    progress = get_default_progress()
    save_progress(progress)
    return jsonify({"success": True, "message": "Postępy zostały pomyślnie zresetowane."})


@app.route("/api/challenges", methods=["GET"])
def get_challenges():
    result = []
    for ch in challenges_db:
        result.append({
            "id": ch["id"],
            "language": ch["language"],
            "difficulty": ch["difficulty"],
            "title": ch["title"],
            "description": ch["description"],
            "boilerplate": ch["boilerplate"]
        })
    return jsonify({"challenges": result})


@app.route("/api/library", methods=["GET"])
def get_library():
    # Return entire library DB or filtered by language/level
    lang = request.args.get("language") # "python", "php" or "all"
    level = request.args.get("level")   # "podstawy", "zaawansowane", "frameworki" or "all"
    
    # Reload dynamically from library.json to ensure real-time accuracy
    active_library = library_db
    if LIBRARY_FILE.exists():
        try:
            with open(LIBRARY_FILE, "r", encoding="utf-8") as f:
                active_library = json.load(f)
        except Exception as e:
            print(f"⚠️ Error reloading library.json: {e}")
            
    result = {}
    langs_to_scan = [lang] if lang in ["python", "php"] else ["python", "php"]
    
    for l in langs_to_scan:
        if l not in active_library:
            continue
        result[l] = []
        for art in active_library[l]:
            if level and level != "all" and art["level"] != level:
                continue
            result[l].append(art)
            
    return jsonify(result)


@app.route("/api/submit-challenge", methods=["POST"])
def submit_challenge():
    import sys
    import tempfile
    import subprocess
    
    data = request.get_json() or {}
    challenge_id = data.get("challenge_id")
    code = data.get("code", "")
    
    if not challenge_id:
        return jsonify({"success": False, "error": "Brak identyfikatora zadania."}), 400
        
    challenge = None
    for ch in challenges_db:
        if ch["id"] == challenge_id:
            challenge = ch
            break
            
    if not challenge:
        return jsonify({"success": False, "error": "Zadanie o podanym ID nie istnieje."}), 404
        
    lang = challenge["language"]
    validation_code = challenge["validation_code"]
    
    if lang == "python":
        full_code = f"{code}\n\n{validation_code}"
        with tempfile.NamedTemporaryFile(suffix=".py", mode="w", encoding="utf-8", delete=False) as tmp:
            tmp.write(full_code)
            tmp_path = tmp.name
            
        try:
            res = subprocess.run(
                [sys.executable, tmp_path],
                capture_output=True,
                text=True,
                timeout=4.0
            )
            os.unlink(tmp_path)
            
            if res.returncode == 0:
                progress = load_progress()
                progress["total_answered"] += 1
                progress["correct_answers"] += 1
                progress["last_activity"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                save_progress(progress)
                
                return jsonify({
                    "success": True,
                    "correct": True,
                    "stdout": res.stdout,
                    "stderr": res.stderr
                })
            else:
                progress = load_progress()
                progress["total_answered"] += 1
                progress["incorrect_answers"] += 1
                save_progress(progress)
                
                return jsonify({
                    "success": True,
                    "correct": False,
                    "error_msg": res.stderr or res.stdout or "Błąd asercji lub błąd wykonania kodu."
                })
        except subprocess.TimeoutExpired:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
            return jsonify({
                "success": True,
                "correct": False,
                "error_msg": "Timeout! Przekroczono limit 4 sekund. Kod prawdopodobnie utknął w pętli nieskończonej."
            })
        except Exception as e:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
            return jsonify({"success": False, "error": f"Błąd weryfikacji: {str(e)}"}), 500
            
    elif lang == "php":
        full_code = f"<?php\nini_set('assert.exception', 1);\n\n{code}\n\n{validation_code}\n"
        with tempfile.NamedTemporaryFile(suffix=".php", mode="w", encoding="utf-8", delete=False) as tmp:
            tmp.write(full_code)
            tmp_path = tmp.name
            
        try:
            res = subprocess.run(
                ["php", "-f", tmp_path],
                capture_output=True,
                text=True,
                timeout=4.0
            )
            os.unlink(tmp_path)
            
            if res.returncode == 0:
                progress = load_progress()
                progress["total_answered"] += 1
                progress["correct_answers"] += 1
                progress["last_activity"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                save_progress(progress)
                
                return jsonify({
                    "success": True,
                    "correct": True,
                    "stdout": res.stdout,
                    "stderr": res.stderr
                })
            else:
                progress = load_progress()
                progress["total_answered"] += 1
                progress["incorrect_answers"] += 1
                save_progress(progress)
                
                err_out = res.stderr or res.stdout or "Błąd wykonania skryptu PHP."
                err_out = err_out.replace(tmp_path, "solution.php")
                return jsonify({
                    "success": True,
                    "correct": False,
                    "error_msg": err_out
                })
        except subprocess.TimeoutExpired:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
            return jsonify({
                "success": True,
                "correct": False,
                "error_msg": "Timeout! Przekroczono limit 4 sekund. Kod prawdopodobnie utknął w pętli nieskończonej."
            })
        except FileNotFoundError:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
            return jsonify({
                "success": True,
                "correct": False,
                "error_msg": "Błąd: Brak narzędzia 'php' (PHP CLI) w systemie operacyjnym."
            })
        except Exception as e:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass
            return jsonify({"success": False, "error": f"Błąd weryfikacji: {str(e)}"}), 500
            
    return jsonify({"success": False, "error": "Nieobsługiwany język."}), 400


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Dev Learning Hub Server")
    parser.add_argument("-p", "--port", type=int, default=9000, help="Port to run on")
    parser.add_argument("-H", "--host", type=str, default="127.0.0.1", help="Host to run on")
    parser.add_argument("--debug", action="store_true", help="Enable Flask debug mode")
    args = parser.parse_args()
    
    print(f"Starting Dev Learning Hub on http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)

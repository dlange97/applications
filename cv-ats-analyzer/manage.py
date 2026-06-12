#!/usr/bin/env python3
"""
manage.py — Process manager for CV ATS Analyzer.

Usage:
    python3 manage.py start
    python3 manage.py stop
    python3 manage.py restart
    python3 manage.py status
"""

import os
import sys
import signal
import subprocess
import time
from pathlib import Path
import socket
import shutil

BASE_DIR = Path(__file__).parent
PID_FILE = BASE_DIR / "cv_ats.pid"
LOG_FILE = BASE_DIR / "cv_ats.log"
PORT     = 9200


def _find_python() -> str:
    # Prefer a virtualenv in the project, then system python3, then sys.executable
    candidates = []
    # common venv locations: ./ .venv venv in repo root or parent
    candidates.append(BASE_DIR / ".venv" / "bin" / "python")
    candidates.append(BASE_DIR / "venv" / "bin" / "python")
    candidates.append(BASE_DIR.parent / ".venv" / "bin" / "python")
    candidates.append(BASE_DIR.parent.parent / ".venv" / "bin" / "python")
    # fallback to PATH python3 and common system locations
    which_py = shutil.which("python3")
    if which_py:
        candidates.append(Path(which_py))
    candidates.append(Path("/usr/local/bin/python3"))
    candidates.append(Path("/usr/bin/python3"))

    for p in candidates:
        try:
            if p and Path(p).exists():
                return str(p)
        except Exception:
            continue

    return sys.executable


def _port_available(port: int = PORT) -> bool:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", port))
        return True
    except OSError:
        return False
    finally:
        try:
            s.close()
        except Exception:
            pass


def _is_running() -> tuple[bool, int | None]:
    if not PID_FILE.exists():
        return False, None
    try:
        pid = int(PID_FILE.read_text().strip())
        os.kill(pid, 0)
        # basic verification: ps command to show process command
        try:
            cmd = subprocess.check_output(["ps", "-p", str(pid), "-o", "command="], stderr=subprocess.DEVNULL).decode().strip()
            if cmd:
                return True, pid
        except Exception:
            pass
        return True, pid
    except (ValueError, ProcessLookupError, PermissionError):
        PID_FILE.unlink(missing_ok=True)
        return False, None


def start() -> None:
    running, pid = _is_running()
    if running:
        print(f"⚠️  Już uruchomiony (PID: {pid}, port: {PORT})")
        return

    python = _find_python()
    if not python:
        print("❌ Nie znaleziono interpretera Pythona.")
        sys.exit(1)

    print(f"🔍 Sprawdzanie portu {PORT}...")

    if not _port_available(PORT):
        print(f"❌ Port {PORT} jest już używany. Sprawdź, co nasłuchuje na tym porcie.")
        sys.exit(1)

    env = {**os.environ, "FLASK_APP": "app.py", "FLASK_ENV": "production"}
    # Start detached process in its own session so we can signal the group later
    with open(LOG_FILE, "a") as log:
        try:
            process = subprocess.Popen(
                [python, "-m", "flask", "run", "--host=127.0.0.1", f"--port={PORT}", "--no-debugger"],
                cwd=str(BASE_DIR),
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                preexec_fn=os.setsid,
                close_fds=True,
            )
        except Exception as exc:
            print(f"❌ Błąd uruchamiania procesu: {exc}")
            print(f"🔎 Sprawdź logi: {LOG_FILE}")
            sys.exit(1)

    # write PID atomically
    tmp = PID_FILE.with_suffix(".pid.tmp")
    tmp.write_text(str(process.pid))
    tmp.replace(PID_FILE)

    time.sleep(1.5)

    running, pid = _is_running()
    if running:
        print(f"✅ CV ATS Analyzer uruchomiony!")
        print(f"🌐 URL: http://127.0.0.1:{PORT}")
        print(f"🆔 PID: {pid}")
        print(f"📝 Logi: {LOG_FILE}")
    else:
        print(f"❌ Nie udało się uruchomić. Sprawdź: {LOG_FILE}")
        # show last 30 lines of log to help debugging
        try:
            with open(LOG_FILE, "r") as f:
                lines = f.readlines()[-30:]
                print("--- ostatnie logi ---")
                for l in lines:
                    print(l.rstrip())
        except Exception:
            pass
        sys.exit(1)


def stop() -> None:
    running, pid = _is_running()
    if not running:
        print("⚠️  Nie jest uruchomiony.")
        return

    print(f"🛑 Zatrzymywanie CV ATS Analyzer (PID: {pid})...")
    try:
        try:
            # terminate entire process group if available
            os.killpg(pid, signal.SIGTERM)
        except Exception:
            os.kill(pid, signal.SIGTERM)

        for _ in range(40):
            time.sleep(0.25)
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                break

        PID_FILE.unlink(missing_ok=True)
        print("✅ Zatrzymano.")
    except ProcessLookupError:
        PID_FILE.unlink(missing_ok=True)
        print("✅ Już zatrzymany.")


def restart() -> None:
    stop()
    time.sleep(0.5)
    start()


def status() -> None:
    running, pid = _is_running()
    if running:
        print(f"✅ Uruchomiony — PID: {pid}  |  URL: http://127.0.0.1:{PORT}")
    else:
        print("❌ Nie jest uruchomiony.")


COMMANDS = {"start": start, "stop": stop, "restart": restart, "status": status}

if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "status"
    if cmd not in COMMANDS:
        print(f"Użycie: python3 manage.py [{' | '.join(COMMANDS)}]")
        sys.exit(1)
    COMMANDS[cmd]()

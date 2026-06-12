#!/usr/bin/env python3
"""
manage.py - CLI process manager for Dev Learning Hub service.
Supports start, stop/down, restart and status check.
Provides interactive port collision resolution and background daemonization.
"""

from __future__ import annotations
import os
import sys
import json
import time
import socket
import signal
import subprocess
from pathlib import Path

# Paths & Settings
BASE_DIR = Path(__file__).resolve().parent
PID_FILE = BASE_DIR / "learning_hub.pid"
LOG_FILE = BASE_DIR / "learning_hub.log"
APP_FILE = BASE_DIR / "app.py"

def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0

def find_next_free_port(start_port: int, max_scans: int = 50, host: str = "127.0.0.1") -> int | None:
    for port in range(start_port, start_port + max_scans):
        if not is_port_in_use(port, host):
            return port
    return None

def get_python_executable() -> str:
    # Try workspace virtualenv, local virtualenv, then fallback to current sys.executable
    candidates = [
        BASE_DIR.parent / ".venv" / "bin" / "python",
        BASE_DIR.parent / ".venv" / "Scripts" / "python.exe",
        BASE_DIR / ".venv" / "bin" / "python",
        BASE_DIR / "venv" / "bin" / "python"
    ]
    for candidate in candidates:
        if candidate.exists():
            return str(candidate)
    return sys.executable

def get_running_details() -> dict | None:
    if not PID_FILE.exists():
        return None
    try:
        with open(PID_FILE, "r", encoding="utf-8") as f:
            details = json.load(f)
        pid = details.get("pid")
        # Probe process with signal 0 to see if it actually exists
        os.kill(pid, 0)
        return details
    except (OSError, ProcessLookupError, json.JSONDecodeError, ValueError):
        # Process is dead or PID file corrupted: clean it up
        try:
            PID_FILE.unlink(missing_ok=True)
        except Exception:
            pass
        return None

def start_server(port: int = 9000, host: str = "127.0.0.1"):
    details = get_running_details()
    if details:
        pid_val = details.get("pid")
        port_val = details.get("port")
        url_val = details.get("url", f"http://127.0.0.1:{port_val}")
        print("🟢 Status: Serwer Dev Learning Hub jest już URUCHOMIONY!")
        print(f"   🆔 PID: {pid_val}")
        print(f"   🔌 PORT: {port_val}")
        print(f"   🌐 Otwórz w przeglądarce: {url_val}")
        return

    print(f"🔍 Sprawdzanie dostępności portu {port}...")
    if is_port_in_use(port, host):
        print(f"⚠️ Port {port} jest już używany przez inny serwis.")
        free_port = find_next_free_port(port + 1)
        if free_port:
            print(f"💡 Znaleziono wolny port alternatywny: {free_port}")
            try:
                user_input = input(f"Czy chcesz automatycznie uruchomić aplikację na porcie {free_port}? [Y/n]: ").strip().lower()
                if user_input in ("", "y", "yes", "tak"):
                    port = free_port
                else:
                    print("❌ Przerwano uruchamianie z powodu zajętości portu.")
                    sys.exit(1)
            except KeyboardInterrupt:
                print("\n❌ Anulowano.")
                sys.exit(1)
        else:
            print("❌ Brak wolnych wolnych portów w zakresie +50. Zamknij zajęty port lub zwolnij zasoby.")
            sys.exit(1)

    python_bin = get_python_executable()
    
    print(f"🚀 Uruchamianie usługi za pomocą: {python_bin}")
    print(f"📝 Szczegółowe logi rejestrowane są w: {LOG_FILE}")
    
    log_fd = open(LOG_FILE, "w", encoding="utf-8")
    
    # Detachowanie procesu przy użyciu start_new_session (działa jak demon systemowy UNIX)
    try:
        proc = subprocess.Popen(
            [python_bin, str(APP_FILE), "--port", str(port), "--host", host],
            stdout=log_fd,
            stderr=log_fd,
            start_new_session=True,
            cwd=os.path.dirname(__file__)
        )
    except Exception as e:
        log_fd.close()
        print(f"❌ Nie udało się zainicjalizować demona: {str(e)}")
        sys.exit(1)

    time.sleep(1.2) # Chwila na zbindowanie portu i weryfikację ewentualnego crasha
    
    # Sprawdzenie czy proces wciąż działa
    if proc.poll() is not None:
        print("❌ Serwer zakończył działanie tuż po starcie. Sprawdź logi błędów:")
        print(f"   tail -n 20 {LOG_FILE}")
        log_fd.close()
        sys.exit(1)

    # Zapis stanu PID
    status_data = {
        "pid": proc.pid,
        "port": port,
        "url": f"http://127.0.0.1:{port}"
    }
    
    with open(PID_FILE, "w", encoding="utf-8") as f:
        json.dump(status_data, f, indent=2)

    print(f"✅ Usługa pomyślnie uruchomiona w tle!")
    print(f"🌐 Adres URL: http://127.0.0.1:{port}")
    print(f"🆔 Process PID: {proc.pid}")
    log_fd.close()

def stop_server():
    if not PID_FILE.exists():
        print("🔴 Status: Brak aktywnych instancji do wyłączenia (Plik PID nie istnieje).")
        return False

    try:
        with open(PID_FILE, "r", encoding="utf-8") as f:
            status_data = json.load(f)
        pid = status_data.get("pid")
        port = status_data.get("port")
    except Exception:
        print("⚠️ Plik PID jest uszkodzony. Próba awaryjnego czyszczenia...")
        pid = None
        port = None

    if pid:
        print(f"🛑 Zatrzymywanie usługi Dev Learning Hub (PID: {pid}, port: {port})...")
        try:
            os.kill(pid, signal.SIGTERM)
            # Dajemy chwilę na zakończenie
            for _ in range(10):
                time.sleep(0.2)
                try:
                    os.kill(pid, 0)
                except OSError:
                    break
            else:
                # Jeśli nadal żyje, killujemy bezlitośnie
                os.kill(pid, signal.SIGKILL)
            print("✅ Aplikacja została pomyślnie wyłączona.")
        except ProcessLookupError:
            print("⚠️ Proces o podanym PID nie został odnaleziony w tabeli systemowej (mógł zostać wyłączony wcześniej).")
        except Exception as e:
            print(f"❌ Błąd podczas zamykania procesu: {str(e)}")

    if PID_FILE.exists():
        PID_FILE.unlink()
    return True

def show_status():
    if not PID_FILE.exists():
        print("🔴 Status: WYŁĄCZONA")
        return

    try:
        with open(PID_FILE, "r", encoding="utf-8") as f:
            status_data = json.load(f)
        pid = status_data.get("pid")
        port = status_data.get("port")
        url = status_data.get("url")
    except Exception:
        print("🔴 Status: BŁĄD ODCZYTU (Plik PID uszkodzony)")
        return

    # Sprawdź czy process faktycznie żyje w systemie
    try:
        os.kill(pid, 0)
        print("🟢 Status: DZIAŁA W TLE")
        print(f"   🆔 PID: {pid}")
        print(f"   🔌 PORT: {port}")
        print(f"   🌐 ADRES: {url}")
    except OSError:
        print("🔴 Status: WYŁĄCZONA (Zgłoszenie awarii: PID zapisany, ale brak aktywnego procesu w tabeli).")
        # Wyczyszczenie martwego pliku PID
        if PID_FILE.exists():
            PID_FILE.unlink()

def main():
    if len(sys.argv) < 2:
        print("Użycie: python manage.py [start|down|restart|status]")
        print("Dostępne opcje dodatkowe:")
        print("  --port PORT   Wymuś niestandardowy port startowy (domyślnie 9000)")
        sys.exit(1)

    command = sys.argv[1].lower()
    
    # Parser argumentów pomocniczych pod start
    port = 9000
    if "--port" in sys.argv:
        try:
            idx = sys.argv.index("--port")
            port = int(sys.argv[idx + 1])
        except Exception:
            print("⚠️ Nieprawidłowa wartość parametru --port. Używam domyślnego portu 9000.")

    if command == "start":
        start_server(port)
    elif command in ("down", "stop"):
        stop_server()
    elif command == "restart":
        stop_server()
        time.sleep(0.5)
        start_server(port)
    elif command == "status":
        show_status()
    else:
        print(f"❌ Nieznane polecenie: {command}")
        print("Dozwolone polecenia: start, down, restart, status")
        sys.exit(1)

if __name__ == "__main__":
    main()

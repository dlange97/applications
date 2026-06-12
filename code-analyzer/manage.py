#!/usr/bin/env python3
"""
manage.py - Skrypt do zarządzania aplikacją Code Analyzer Pro
Umożliwia uruchamianie (start), zatrzymywanie (down/stop), restartowanie oraz sprawdzanie statusu (status).
Obsługuje dynamiczne wykrywanie zajętości portów i interaktywne proponowanie wolnych alternatyw.
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

PID_FILE = Path(__file__).resolve().parent / "code_analyzer.pid"
LOG_FILE = Path(__file__).resolve().parent / "code_analyzer.log"
APP_FILE = Path(__file__).resolve().parent / "app.py"

def get_python_executable() -> str:
    """Wyszukuje najlepszy interpreter Pythona (preferując lokalne środowisko wirtualne .venv)."""
    # Sprawdzamy .venv w katalogu nadrzędnym (root projektu)
    parent_venv = Path(__file__).resolve().parent.parent / ".venv"
    if parent_venv.exists():
        bin_path = parent_venv / "bin" / "python"
        if bin_path.exists():
            return str(bin_path)
        win_path = parent_venv / "Scripts" / "python.exe"
        if win_path.exists():
            return str(win_path)
            
    # Sprawdzamy .venv w katalogu lokalnym (wewnątrz code-analyzer/)
    local_venv = Path(__file__).resolve().parent / ".venv"
    if local_venv.exists():
        bin_path = local_venv / "bin" / "python"
        if bin_path.exists():
            return str(bin_path)
        win_path = local_venv / "Scripts" / "python.exe"
        if win_path.exists():
            return str(win_path)

    return sys.executable

def is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    """Sprawdza czy port jest aktualnie nasłuchiwany przez inny proces."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0

def find_free_port(start_port: int == 8000, host: str = "127.0.0.1") -> int | None:
    """Przeszukuje porty w górę w celu znalezienia wolnego portu do powiązania socketu."""
    port = start_port
    while port < 65535:
        if not is_port_in_use(port, host):
            return port
        port += 1
    return None

def is_process_running(pid: int) -> bool:
    """Sprawdza czy proces o podanym PID nadal działa w systemie operacyjnym."""
    try:
        os.kill(pid, 0)
        return True
    except OSError:
        return False

def get_running_details() -> dict | None:
    """Odczytuje szczegóły uruchomionego procesu z pliku PID i weryfikuje jego stan."""
    if not PID_FILE.exists():
        return None
    try:
        with open(PID_FILE, "r") as f:
            data = json.load(f)
            pid = int(data.get("pid"))
            port = int(data.get("port"))
            if is_process_running(pid):
                return {"pid": pid, "port": port}
    except Exception:
        pass
    return None

def start(port: int = 8000, host: str = "127.0.0.1"):
    """Uruchamia aplikację Flask w tle."""
    details = get_running_details()
    if details:
        print(f"ℹ️ Aplikacja Code Analyzer już działa na porcie {details['port']} (PID: {details['pid']}).")
        print(f"   Otwórz w przeglądarce: http://{host}:{details['port']}")
        return

    # Jeśli port docelowy jest zajęty, proponujemy nowy
    if is_port_in_use(port, host):
        print(f"⚠️ Port {port} jest zajęty przez inny proces.")
        free_port = find_free_port(port + 1, host)
        if not free_port:
            print("❌ Błąd: Nie znaleziono wolnego portu w systemie operacyjnym.")
            sys.exit(1)
        
        try:
            print(f"💡 Zaproponowano wolny port alternatywny: {free_port}")
            ans = input(f"Czy chcesz uruchomić aplikację Code Analyzer na porcie {free_port}? [Y/n]: ").strip().lower()
            if ans in ("", "y", "yes", "tak", "t"):
                port = free_port
            else:
                print("❌ Anulowano uruchomienie z powodu zajętości portu.")
                sys.exit(1)
        except (KeyboardInterrupt, EOFError):
            print("\n❌ Anulowano.")
            sys.exit(1)

    print(f"🚀 Uruchamianie aplikacji Code Analyzer na http://{host}:{port} ...")
    
    try:
        # Tworzenie lub dopisywanie logów
        log_f = open(LOG_FILE, "a", encoding="utf-8")
        
        # Pobieramy właściwy interpreter pythona ze środowiska wirtualnego
        python_exe = get_python_executable()
        
        # Uruchamiamy aplikację w nowej sesji, aby zapobiec jej zabiciu po zamknięciu terminala (daemon)
        try:
            process = subprocess.Popen(
                [python_exe, str(APP_FILE), "--port", str(port), "--host", host],
                stdout=log_f,
                stderr=log_f,
                start_new_session=True
            )
        except Exception:
            log_f.close()
            raise
        
        # Zapisujemy status w pliku PID
        with open(PID_FILE, "w") as f:
            json.dump({"pid": process.pid, "port": port, "time": time.time()}, f)
            
        # Dajemy Flaskowi krótki czas na zainicjowanie socketu i sprawdzamy czy nie crashnął
        time.sleep(1.2)
        if process.poll() is not None:
            print("❌ Błąd: Aplikacja zakończyła działanie tuż po uruchomieniu.")
            print(f"   Przeanalizuj logi błędów w pliku: {LOG_FILE}")
            if PID_FILE.exists():
                PID_FILE.unlink()
            sys.exit(1)
            
        print(f"✅ Sukces: Aplikacja została pomyślnie uruchomiona w tle!")
        print(f"   👉 URL: http://{host}:{port}")
        print(f"   👉 PID: {process.pid}")
        print(f"   👉 Plik logów: {LOG_FILE}")
    except Exception as e:
        print(f"❌ Wystąpił niespodziewany błąd podczas uruchamiania: {e}")
        sys.exit(1)

def down():
    """Zamyka działającą aplikację."""
    details = get_running_details()
    if not details:
        if PID_FILE.exists():
            try:
                PID_FILE.unlink()
            except OSError:
                pass
        print("ℹ️ Aplikacja Code Analyzer nie jest aktualnie uruchomiona.")
        return

    pid = details["pid"]
    port = details["port"]
    print(f"🛑 Zatrzymywanie aplikacji (PID: {pid}, port: {port})...")
    
    try:
        os.kill(pid, signal.SIGTERM)
        # Czekamy grzecznie na zamknięcie socketu i wątków
        for _ in range(12):
            if not is_process_running(pid):
                break
            time.sleep(0.5)
        else:
            print("⚠️ Proces nie odpowiada na SIGTERM. Wymuszanie natychmiastowego zamknięcia (SIGKILL)...")
            os.kill(pid, signal.SIGKILL)
            time.sleep(0.5)
    except OSError:
        pass

    if PID_FILE.exists():
        try:
            PID_FILE.unlink()
        except OSError:
            pass
            
    print("✅ Aplikacja została pomyślnie wyłączona.")

def restart(port: int = 8000, host: str = "127.0.0.1"):
    """Zatrzymuje, a następnie uruchamia ponownie aplikację."""
    details = get_running_details()
    # Jeśli aplikacja działała, restartujemy na tym samym porcie, na którym wisiała
    target_port = details["port"] if details else port
    
    print("🔄 Trwa restartowanie bazy aplikacji...")
    down()
    time.sleep(1.0)
    start(port=target_port, host=host)

def status():
    """Wyświetla aktualny status serwera."""
    details = get_running_details()
    if details:
        print(f"🟢 Status: URUCHOMIONA")
        print(f"   👉 PORT: {details['port']}")
        print(f"   👉 URL: http://127.0.0.1:{details['port']}")
        print(f"   👉 PID: {details['pid']}")
    else:
        print("🔴 Status: WYŁĄCZONA")

def main():
    if len(sys.argv) < 2:
        print("Opcje użycia: ")
        print("  python3 manage.py start [--port PORT]")
        print("  python3 manage.py down")
        print("  python3 manage.py restart")
        print("  python3 manage.py status")
        sys.exit(1)

    command = sys.argv[1].lower()
    
    port = 8000
    if "--port" in sys.argv:
        try:
            port_idx = sys.argv.index("--port")
            port = int(sys.argv[port_idx + 1])
        except (ValueError, IndexError):
            print("❌ Nieprawidłowy format parametru --port. Uruchamianie na domyślnym porcie 8000.")

    if command == "start":
        start(port=port)
    elif command in ("down", "stop"):
        down()
    elif command == "restart":
        restart(port=port)
    elif command == "status":
        status()
    else:
        print(f"❌ Nieznana komenda: {command}")
        print("Wybierz jedną z opcji: start, down, restart, status")
        sys.exit(1)

if __name__ == "__main__":
    main()

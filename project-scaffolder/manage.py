#!/usr/bin/env python3
import os
import sys
import json
import socket
import signal
import time
import subprocess

PID_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "project_scaffolder.pid"))
LOG_FILE = os.path.abspath(os.path.join(os.path.dirname(__file__), "project_scaffolder.log"))

def is_port_in_use(port, host="127.0.0.1"):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex((host, port)) == 0

def find_next_free_port(start_port, host="127.0.0.1", max_tries=50):
    current = start_port
    for _ in range(max_tries):
        if not is_port_in_use(current, host):
            return current
        current += 1
    return None

def get_python_executable():
    """
    Wyszukuje ścieżkę wirtualnego środowiska pythona, w którym zainstalowany jest Flask.
    """
    # Sprawdź lokalny folder .venv w workspace
    workspace_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    venv_python = os.path.join(workspace_root, ".venv", "bin", "python")
    
    if os.path.exists(venv_python):
        return venv_python
    
    # Fallback do systemowego/bieżącego interpretera
    return sys.executable

def get_running_details():
    if not os.path.exists(PID_FILE):
        return None
    try:
        with open(PID_FILE, "r", encoding="utf-8") as f:
            status_data = json.load(f)
        pid = status_data.get("pid")
        os.kill(pid, 0)
        return status_data
    except OSError:
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)
        return None
    except Exception:
        return None

def start_server(port=8500):
    details = get_running_details()
    if details:
        print(f"ℹ️ Aplikacja Project Scaffolder już działa na porcie {details['port']} (PID: {details['pid']}).")
        print("   Otwórz w przeglądarce: " + details.get('url', f"http://127.0.0.1:{details['port']}"))
        return

    print(f"🔍 Sprawdzanie dostępności portu {port}...")
    
    if is_port_in_use(port):
        print(f"⚠️ Port {port} jest już zajęty przez inną aplikację/usługę.")
        free_port = find_next_free_port(port + 1)
        if free_port:
            print(f"💡 Znaleziono wolny port: {free_port}")
            user_input = input(f"Czy chcesz automatycznie uruchomić aplikację na porcie {free_port}? [Y/n]: ").strip().lower()
            if user_input in ("", "y", "yes", "tak"):
                port = free_port
            else:
                print("❌ Przerwano uruchamianie z powodu zajętości portu.")
                sys.exit(1)
        else:
            print("❌ Brak wolnych wolnych portów w zakresie +50. Zamknij inne serwisy.")
            sys.exit(1)

    python_bin = get_python_executable()
    app_script = os.path.abspath(os.path.join(os.path.dirname(__file__), "app.py"))
    
    print(f"🚀 Uruchamianie Project Scaffolder Pro za pomocą: {python_bin}")
    print(f"📝 Szczegółowe logi będą zapisywane w: {LOG_FILE}")
    
    log_fd = open(LOG_FILE, "w", encoding="utf-8")
    
    # Detachowanie procesu przy użyciu start_new_session (działa jak demon systemowy UNIX)
    try:
        proc = subprocess.Popen(
            [python_bin, app_script, "--port", str(port), "--host", "127.0.0.1"],
            stdout=log_fd,
            stderr=log_fd,
            start_new_session=True,
            cwd=os.path.dirname(__file__)
        )
    except Exception as e:
        log_fd.close()
        print(f"❌ Nie udało się zainicjalizować demona: {str(e)}")
        sys.exit(1)

    time.sleep(1.2) # Chwila na zbindowanie portu
    
    # Sprawdzenie czy proces wciąż działa
    if proc.poll() is not None:
        print("❌ Serwer zakończył działanie tuż po starcie. Sprawdź plik logów:")
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
    if not os.path.exists(PID_FILE):
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
        print(f"🛑 Zatrzymywanie aplikacji Project Scaffolder (PID: {pid}, port: {port})...")
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

    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)
    return True

def show_status():
    if not os.path.exists(PID_FILE):
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
        if os.path.exists(PID_FILE):
            os.remove(PID_FILE)

def main():
    if len(sys.argv) < 2:
        print("Użycie: python manage.py [start|down|restart|status]")
        print("Dostępne opcje dodatkowe:")
        print("  --port PORT   Wymuś niestandardowy port startowy (domyślnie 8500)")
        sys.exit(1)

    command = sys.argv[1].lower()
    
    # Parser argumentów pomocniczych pod start
    port = 8500
    if "--port" in sys.argv:
        try:
            idx = sys.argv.index("--port")
            port = int(sys.argv[idx + 1])
        except Exception:
            print("⚠️ Nieprawidłowa wartość parametru --port. Używam domyślnego portu 8500.")

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

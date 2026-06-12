# Project Scaffolder Pro 🚀

Profesjonalna, w pełni lokalna aplikacja w Pythonie służąca do błyskawicznego bindowania i startowania nowych projektów w najpopularniejszych językach programowania oraz powiązanych frameworkach.

Posiada intuicyjny, ciemny, responsywny interfejs webowy (Tailwind CSS, FontAwesome) umożliwiający generowanie czystych, przetestowanych struktur projektów bezpośrednio we wskazanej ścieżce lokalnej systemu lub pobieranie ich jako skompresowane archiwum ZIP.

---

## 🌟 Główne Funkcje i Obsługiwane Środowiska

Projekt wspiera 5 wiodących języków programowania oraz ich flagowe frameworki:

1. **Python:**
   - **FastAPI:** Pełna integracja z pydantic, uvicorn, zdefiniowane endpoints API, router CORS, ustrukturyzowana konfiguracja.
   - **Flask:** Standardowy, minimalistyczny serwer REST z obsługą endpointów, filtrowaniem payloadów JSON.
   - **Django:** Minimalistyczna konfiguracja pojedynczego pliku bez zbędnego narzutu bazy na start.
2. **JavaScript / TypeScript:**
   - **React (Vite):** Skonfigurowany Vite, TypeScript, nowoczesny interfejs dashboardu w ciemnym motywie z interaktywnymi komponentami.
   - **Next.js:** Przygotowany App Router (`layout.tsx`, `page.tsx`, `globals.css`) zgodny z najnowszymi standardami NextJS 14+.
   - **Express.js:** Server API napisany w TypeScript, kompletne middleware CORS, obsługa środowisk `.env`.
   - **NestJS:** Czysty kod zintegrowany z modułami `@Module`, `@Controller` oraz `@Service`.
3. **PHP:**
   - **Laravel:** Minimalna struktura kontrolerów i tras zintegrowana z mapowaniem PSR-4 autoload.
   - **Symfony:** Szybki starter mikro-kontrolera oraz publicznych punktów bindowania.
4. **Java:**
   - **Spring Boot:** Struktura Maven (`pom.xml`, Maven wrapper), predefiniowany `HelloController` oraz klasy konfiguracyjne.
5. **Go (Golang):**
   - **Gin:** Szybki silnik routingu w Go wraz z obsługą CORS, mapowaniem JSON i testowym `/api/v1/health`.
   - **Fiber:** Szybki mikro-framework, przygotowany pod wydajne przetwarzanie w architekturze kontenerowej.

### ⚡ Dodatki Architektoniczne jako opcje w kreatorze:

- **Inicjalizacja GIT:** Wykonuje lokalne `git init`, przygotowuje `.gitignore` dopasowany do wybranego języka i tworzy predefiniowany `Initial commit`.
- **Docker & Docker Compose:** Tworzy zoptymalizowany wieloetapowy (multi-stage) plik `Dockerfile` z cache kompilacji oraz uniwersalny `docker-compose.yml`.
- **Integracja CI/CD:** Generuje gotowy workflow do automatycznych testów GitHub Actions (`.github/workflows/ci.yml`).
- **Standard Licencyjny:** Kompiluje plik `LICENSE` (MIT) dedykowany dla podanego w formularzu autora.

---

## 📂 Struktura Aplikacji

Aplikacja znajduje się w wyizolowanym folderze `project-scaffolder/`:

- `scaffolder.py` — Rdzeń silnika generującego (wszystkie szablony i logika zapisu).
- `app.py` — Lokalny serwer Flask obsługujący asynchroniczne punkty API oraz renderowanie UI.
- `manage.py` — Skrypt CLI do automatycznego daemonizowania procesów i detekcji kolizji portów.
- `tests/test_scaffolder.py` — Testy jednostkowe platformy.

---

## ⚙️ Jak Uruchomić i Zarządzać Usługą

Dla Twojej wygody przygotowano uniwersalny, zautomatyzowany skrypt `manage.py`, który dba o procesy i bindowanie odpowiedniego środowiska wirtualnego:

### Dostępne Komendy:

1. **Uruchomienie aplikacji w tle:**

   ```bash
   python project-scaffolder/manage.py start [--port PORT]
   ```

   _Domyślnie aplikacja nasłuchuje na porcie `8500`. Jeżeli port jest zajęty, skrypt automatycznie przeskanuje dostępne gniazda w górę, zaproponuje wolną alternatywę i po akceptacji podniesie serwer._

2. **Zatrzymanie aplikacji:**

   ```bash
   python project-scaffolder/manage.py down
   ```

   _Zamyka proces demona, zwalnia bindowany port i usuwa plik blokady PID._

3. **Sprawdzenie statusu:**

   ```bash
   python project-scaffolder/manage.py status
   ```

4. **Szybki restart:**
   ```bash
   python project-scaffolder/manage.py restart
   ```

---

## 🧪 Uruchamianie Testów Jednostkowych

Aby upewnić się, że generator poprawnie kompiluje wszystkie pliki systemowe, uruchom testy za pomoca komendy:

```bash
PYTHONPATH=project-scaffolder python -m unittest project-scaffolder/tests/test_scaffolder.py
```

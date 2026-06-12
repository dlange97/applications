# Code Analyzer Pro 🚀

Profesjonalna, modularna aplikacja w Pythonie do statycznej analizy jakości, metryk oraz potencjalnych podatności bezpieczeństwa (zgodna z wytycznymi OWASP Top 10) dla wszystkich popularnych języków programowania.

System posiada intuicyjny, w pełni responsywny interfejs webowy (frontend) zbudowany w technologii **Tailwind CSS** wraz z interaktywnymi wykresami **Chart.js** oraz opcjami pobierania szczegółowych raportów końcowych.

---

## 🌟 Główne Funkcje

1. **Wielojęzyczność:** Wsparcie dla wszystkich kluczowych języków:
   - **Python** (`.py`)
   - **JavaScript / TypeScript** (`.js`, `.jsx`, `.ts`, `.tsx`)
   - **PHP** (`.php`)
   - **Java** (`.java`)
   - **Go** (`.go`)
   - **C / C++** (`.c`, `.cpp`, `.h`, `.hpp`)
   - **Ruby** (`.rb`)
   - **HTML / CSS** (`.html`, `.css`)
   - **Shell Script** (`.sh`, `.bash`)
2. **Zaawansowana Statyczna Analiza:**
   - **Podatności bezpieczeństwa:** Wykrywanie hardcoded haseł/kluczy API, podatności na SQL Injection, Command Injection, Insecure Deserialization, DOM-based XSS, słabych algorytmów kryptograficznych (MD5, DES) itp.
   - **Jakość kodu / Dobre praktyki:** Pozostawione komentarze TODO/FIXME, zbyt skomplikowane i zagnieżdżone instrukcje warunkowe, debuggery (np. console.log, print) w kodzie produkcyjnym, ciche ignorowanie wyjątków, przestarzałe funkcje itp.
3. **Szczegółowe Metryki Kodu:**
   - Linie Kodu (LOC), puste linie, komentarze.
   - Szacowanie złożoności cyklomatycznej McCabe'a (McCabe Complexity indicator).
   - Liczba zdefiniowanych metod/funkcji oraz instancji klas w plikach.
4. **Intuicyjny Panel UI (Frontend):**
   - Wpisywanie absolutnej ścieżki i automatyczna walidacja jej istnienia pod kątem błędów (asynchroniczny walidator).
   - Multiselect wyboru języków z możliwością szybkiego zaznaczania/odznaczania.
   - Dynamiczne wykresy kołowe (rozkład severity) oraz interaktywne sortowanie/filtrowanie i wyszukiwanie problemów.
   - Podgląd podatnej linii kodu sformatowanej w ciemnym motywie monospace.
5. **Eksport i Pobieranie Raportów:**
   - **Pobierz pełny, niezależny Raport HTML:** Gotowy do otwarcia offline lub wydrukowania (wbudowane instrukcje dla druku PDF).
   - **Pobierz raport Markdown:** Idealny do wrzucenia do repozytorium GitHub/GitLab lub jako dokumentacja audytu.
   - **Eksport JSON:** Pełen zestaw danych i metryk do dalszego automatycznego przetwarzania.

---

## 📂 Struktura Projektu

Aplikacja została umieszczona w dedykowanym katalogu `code-analyzer/`, który pozostaje całkowicie niezależny i nie koliduje z innymi modułami projektu.

- `analyzer.py` — Rdzeń silnika analitycznego i zestaw setek prekompilowanych reguł dla badanych języków.
- `app.py` — Serwer webowy oparty na microframeworku Flask, serwujący dedykowane endpoints REST oraz pobieranie plików.
- `manage.py` — Skrypt CLI do wygodnego zarządzania instancją serwera (uruchamianie w tle, zatrzymywanie, sprawdzanie statusu, sprytne rozwiązywanie kolizji wolnych portów w locie).
- `templates/index.html` — Kompletny frontend z interfejsem Tailwind CSS, Chart.js oraz logiką JS.

---

## ⚙️ Jak Uruchomić i Zarządzać Aplikacją

Aplikacja posiada dedykowany skrypt zarządzający `manage.py` ułatwiający automatyzację z poziomu CLI (np. startowanie dedykowanego procesu w tle, zatrzymywanie lub statusowanie).

Wykrywa on automatycznie odpowiednie wirtualne środowisko Pythona (`.venv`) posiadające bibliotekę **Flask**, dzięki czemu nie musisz się martwić o ręczne bindowanie interpretatorów.

### Dostępne Polecenia Zarządzające:

1. **Uruchomienie serwera w tle (Start):**

   ```bash
   python code-analyzer/manage.py start [--port PORT]
   ```

   _Skrypt sprawdzi, czy wskazany port jest wolny. Jeżeli jest zajęty, przeskanuje porty w górę, zaproponuje wolne alternatywne gniazdo i zapyta Cię o zgodę na automatyczną relokację pod nowy adres._

2. **Zatrzymanie serwera (Zatrzymanie/Stop):**

   ```bash
   python code-analyzer/manage.py down
   ```

   _Zamyka instancję działającą w tle, dbając o czyszczenie gniazda portu i usuwając plik blokady PID._

3. **Status usługi (Status):**

   ```bash
   python code-analyzer/manage.py status
   ```

   _Pokazuje, czy usługa działa, na jakim porcie nasłuchuje, jaki ma URL oraz jaki jest jej systemowy identyfikator procesu (PID)._

4. **Restart usługi (Restart):**
   ```bash
   python code-analyzer/manage.py restart
   ```
   _Szybko zamyka aktualną instancję i stawia ją ponownie (pamiętając ostatnio używany port)._

---

## 🚀 Ręczne Uruchomienie Serwera (Opcjonalnie)

Jeżeli wolisz uruchomić serwer synchronicznie bezpośrednio w oknie terminala:

1. Przejdź do folderu `code-analyzer`:

   ```bash
   cd code-analyzer
   ```

2. Uruchom serwer za pomocą python:

   ```bash
   python app.py
   ```

   _W Twoim systemie macOS (Conda/Python Environment) zalecane jest użycie:_

   ```bash
   /Users/dlange/Desktop/my-dashboard-app/.venv/bin/python app.py
   ```

3. Otwórz przeglądarkę i przejdź pod adres:

   ```
   http://127.0.0.1:8000
   ```

4. W polu ścieżki wpisz dowolny katalog z kodem źródłowym, np.:
   - Cały workspace: `/Users/dlange/Desktop/my-dashboard-app`
   - Wybrany mikroserwis: `/Users/dlange/Desktop/my-dashboard-app/my-dashboard-backend/auth-service`
   - Aplikacja mobilna: `/Users/dlange/Desktop/my-dashboard-app/my-dashboard-mobile`

5. Kliknij **Uruchom Analizę Kodu** i ciesz się pięknym, czytelnym raportem!

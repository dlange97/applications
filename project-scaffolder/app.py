import os
import io
import json
import shutil
import tempfile
import zipfile
import argparse
from flask import Flask, jsonify, request, render_template_string, send_file
from scaffolder import ProjectScaffolder

app = Flask(__name__)
scaffolder = ProjectScaffolder()

# HTML Template zintegrowany ze stylowaniem Tailwind i dynamicznym widokiem kreatora (wizard)
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Project Scaffolder Pro — Kreator Nowych Projektów</title>
    <!-- Tailwind CSS -->
    <script src="https://cdn.tailwindcss.com"></script>
    <!-- FontAwesome Icons -->
    <link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.4.0/css/all.min.css">
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');
        body {
            font-family: 'Plus Jakarta Sans', sans-serif;
            background: radial-gradient(circle at 10% 20%, rgb(15, 23, 42) 0%, rgb(9, 13, 30) 90.1%);
        }
        .step-transition {
            transition: all 0.4s cubic-bezier(0.4, 0, 0.2, 1);
        }
    </style>
</head>
<body class="text-slate-100 min-h-screen flex flex-col">

    <!-- Header / Navbar -->
    <header class="border-b border-slate-800 bg-slate-900/80 backdrop-blur-md sticky top-0 z-50 px-6 py-4">
        <div class="max-w-7xl mx-auto flex items-center justify-between">
            <div class="flex items-center space-x-3">
                <div class="bg-blue-600 p-2.5 rounded-xl shadow-lg shadow-blue-500/20">
                    <i class="fa-solid fa-cubes-stacked text-xl text-white"></i>
                </div>
                <div>
                    <h1 class="text-xl font-bold tracking-tight text-white flex items-center gap-2">
                        Project Scaffolder <span class="text-xs bg-blue-500/10 text-blue-400 px-2 py-0.5 rounded-full border border-blue-500/30">LOCAL-PRO</span>
                    </h1>
                    <p class="text-xs text-slate-400">Generator nowoczesnych mikroserwisów i szkieletów aplikacji</p>
                </div>
            </div>
            <div class="flex items-center space-x-4 text-xs text-slate-400">
                <span class="flex items-center gap-1.5 bg-slate-800 px-3 py-1.5 rounded-lg border border-slate-700/50">
                    <span class="h-2 w-2 rounded-full bg-emerald-500 animate-pulse"></span>
                    Serwer lokalny aktywny
                </span>
            </div>
        </div>
    </header>

    <!-- Main Container -->
    <main class="flex-grow max-w-5xl w-full mx-auto p-4 md:p-8">

        <!-- Banner powitalny -->
        <div class="bg-gradient-to-r from-slate-900 via-slate-900/90 to-blue-900/10 border border-slate-800 rounded-2xl p-6 mb-8 shadow-xl">
            <h2 class="text-xl font-bold mb-2 text-white">Błyskawiczny start nowego projektu ⚡</h2>
            <p class="text-slate-400 text-sm max-w-2xl leading-relaxed">
                Wybierz interesujący Cię język programowania, dobierz jeden z najpopularniejszych frameworków, skonfiguruj opcje dodatkowe, a system przygotuje profesjonalną, czystą infrastrukturę (w tym Docker, Git, CI/CD) bezpośrednio we wskazanym folderze lokalnym lub jako paczkę do pobrania.
            </p>
        </div>

        <div class="grid grid-cols-1 lg:grid-cols-3 gap-8">
            
            <!-- Lewa kolumna: Formularz kreatora -->
            <div class="lg:col-span-2 space-y-6">
                <form id="scaffold-form" class="space-y-6 bg-slate-900/90 border border-slate-800 rounded-2xl p-6 md:p-8 shadow-2xl">
                    
                    <!-- Krok 1: Podstawowe informacje -->
                    <div>
                        <h3 class="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                            <span class="flex items-center justify-center h-7 w-7 text-xs bg-blue-500/20 text-blue-400 rounded-full font-bold">1</span>
                            Podstawowa Metryka Projektu
                        </h3>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label class="block text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1.5">Nazwa Projektu</label>
                                <input type="text" id="project-name" name="project-name" value="my-scaffolded-app" placeholder="np. auth-service-pro" 
                                    class="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-slate-100 placeholder-slate-600 focus:outline-none focus:border-blue-500 text-sm step-transition">
                            </div>
                            <div>
                                <label class="block text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1.5">Autor Projektu</label>
                                <input type="text" id="author" name="author" value="{{ author_name }}" placeholder="np. Developer" 
                                    class="w-full bg-slate-950 border border-slate-800 rounded-xl px-4 py-3 text-slate-100 placeholder-slate-600 focus:outline-none focus:border-blue-500 text-sm step-transition">
                            </div>
                        </div>
                    </div>

                    <hr class="border-slate-800/80">

                    <!-- Krok 2: Wybór Technologii -->
                    <div>
                        <h3 class="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                            <span class="flex items-center justify-center h-7 w-7 text-xs bg-blue-500/20 text-blue-400 rounded-full font-bold">2</span>
                            Wybór Języka oraz Frameworku
                        </h3>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                            <div>
                                <label class="block text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1.5">Wiodący Język</label>
                                <select id="language" name="language" 
                                    class="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-3 text-slate-100 focus:outline-none focus:border-blue-500 text-sm step-transition">
                                    <!-- Dynamiczne opcje -->
                                </select>
                            </div>
                            <div>
                                <label class="block text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1.5">Zalecany Framework</label>
                                <select id="framework" name="framework" 
                                    class="w-full bg-slate-950 border border-slate-800 rounded-xl px-3 py-3 text-slate-100 focus:outline-none focus:border-blue-500 text-sm step-transition">
                                    <!-- Dynamiczne opcje na bazie języka -->
                                </select>
                            </div>
                        </div>
                    </div>

                    <hr class="border-slate-800/80">

                    <!-- Krok 3: Wybór Ścieżki Zapisu -->
                    <div>
                        <h3 class="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                            <span class="flex items-center justify-center h-7 w-7 text-xs bg-blue-500/20 text-blue-400 rounded-full font-bold">3</span>
                            Lokalizacja oraz Miejsce zapisu
                        </h3>
                        <div>
                            <label class="block text-xs font-semibold text-slate-400 uppercase tracking-wide mb-1.5">Ścieżka do katalogu nadrzędnego (na serwerze)</label>
                            <div class="relative">
                                <input type="text" id="destination" name="destination" value="{{ default_workspace }}" placeholder="/absolute/path/to/parent/directory" 
                                    class="w-full bg-slate-950 border border-slate-800 rounded-xl pl-4 pr-12 py-3 text-slate-100 placeholder-slate-600 focus:outline-none focus:border-blue-500 text-sm step-transition">
                                <div id="validation-spinner" class="hidden absolute right-4 top-1/2 -translate-y-1/2 text-blue-500">
                                    <i class="fa-solid fa-spinner animate-spin"></i>
                                </div>
                                <div id="validation-success" class="hidden absolute right-4 top-1/2 -translate-y-1/2 text-emerald-500">
                                    <i class="fa-solid fa-circle-check"></i>
                                </div>
                                <div id="validation-warning" class="hidden absolute right-4 top-1/2 -translate-y-1/2 text-amber-500">
                                    <i class="fa-solid fa-triangle-exclamation"></i>
                                </div>
                            </div>
                            <p id="path-feedback-text" class="text-xs text-slate-400 mt-2">Domyślnie używany jest bieżący katalog workspace.</p>
                        </div>
                    </div>

                    <hr class="border-slate-800/80">

                    <!-- Krok 4: Konfiguracja modułów -->
                    <div>
                        <h3 class="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                            <span class="flex items-center justify-center h-7 w-7 text-xs bg-blue-500/20 text-blue-400 rounded-full font-bold">4</span>
                            Dodatki architektoniczne
                        </h3>
                        <div class="grid grid-cols-1 md:grid-cols-2 gap-y-3.5 gap-x-4">
                            
                            <!-- Inicjalizuj Git -->
                            <label class="flex items-start space-x-3 p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/50 hover:border-slate-700/80 cursor-pointer step-transition">
                                <input type="checkbox" id="git_init" name="git_init" checked class="mt-1 h-4 w-4 text-blue-600 bg-slate-900 border-slate-700 rounded focus:ring-blue-500">
                                <div class="text-xs">
                                    <p class="font-semibold text-white">Inicjalizuj lokalny GIT</p>
                                    <p class="text-slate-400">Wykonuje `git init` oraz wstępny commit z plikami.</p>
                                </div>
                            </label>

                            <!-- Generuj Dockerfile -->
                            <label class="flex items-start space-x-3 p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/50 hover:border-slate-700/80 cursor-pointer step-transition">
                                <input type="checkbox" id="docker" name="docker" checked class="mt-1 h-4 w-4 text-blue-600 bg-slate-900 border-slate-700 rounded focus:ring-blue-500">
                                <div class="text-xs">
                                    <p class="font-semibold text-white">Dodaj Dockerfile</p>
                                    <p class="text-slate-400">Tworzy minimalny wieloetapowy obraz Docker ze wsparciem cache.</p>
                                </div>
                            </label>

                            <!-- Docker Compose -->
                            <label class="flex items-start space-x-3 p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/50 hover:border-slate-700/80 cursor-pointer step-transition">
                                <input type="checkbox" id="docker_compose" name="docker_compose" checked class="mt-1 h-4 w-4 text-blue-600 bg-slate-900 border-slate-700 rounded focus:ring-blue-500">
                                <div class="text-xs">
                                    <p class="font-semibold text-white">Dodaj Docker Compose</p>
                                    <p class="text-slate-400">Generuje `docker-compose.yml` umożliwiający łatwy start serwisu.</p>
                                </div>
                            </label>

                            <!-- CI/CD GitHub Actions -->
                            <label class="flex items-start space-x-3 p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/50 hover:border-slate-700/80 cursor-pointer step-transition">
                                <input type="checkbox" id="github_actions" name="github_actions" checked class="mt-1 h-4 w-4 text-blue-600 bg-slate-900 border-slate-700 rounded focus:ring-blue-500">
                                <div class="text-xs">
                                    <p class="font-semibold text-white">Dodaj Pipeline GitHub Actions</p>
                                    <p class="text-slate-400">Konfiguracja `.github/workflows/ci.yml` do automatycznej weryfikacji.</p>
                                </div>
                            </label>

                            <!-- License MIT -->
                            <label class="flex items-start space-x-3 p-3.5 rounded-xl bg-slate-950/60 border border-slate-800/50 hover:border-slate-700/80 cursor-pointer step-transition">
                                <input type="checkbox" id="license" name="license" checked class="mt-1 h-4 w-4 text-blue-600 bg-slate-900 border-slate-700 rounded focus:ring-blue-500">
                                <div class="text-xs">
                                    <p class="font-semibold text-white">Dołącz licencję MIT</p>
                                    <p class="text-slate-400">Generuje standardowy plik LICENSE z prawami autorskimi.</p>
                                </div>
                            </label>

                            <!-- Nadpisywanie ścieżki -->
                            <label class="flex items-start space-x-3 p-3.5 rounded-xl bg-slate-950/60 border border-amber-900/30 hover:border-amber-800/60 cursor-pointer step-transition">
                                <input type="checkbox" id="overwrite" name="overwrite" class="mt-1 h-4 w-4 text-amber-600 bg-slate-900 border-slate-700 rounded focus:ring-amber-500">
                                <div class="text-xs">
                                    <p class="font-semibold text-white text-amber-400">Wymuś Nadpisanie katalogu</p>
                                    <p class="text-slate-400">Usuwa i zastępuje pliki bez ostrzeżeń, jeśli folder docelowy istnieje.</p>
                                </div>
                            </label>

                        </div>
                    </div>

                    <!-- Sekcja przycisków generujących -->
                    <div class="pt-4 flex flex-col sm:flex-row gap-4">
                        <button type="button" id="btn-generate-local"
                            class="flex-1 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 text-white rounded-xl py-3.5 px-6 font-bold text-sm shadow-xl shadow-blue-500/10 active:scale-[0.99] step-transition flex items-center justify-center gap-2">
                            <i class="fa-solid fa-code text-base"></i>
                            Stwórz Projekt Lokalnie
                        </button>
                        <button type="button" id="btn-download-zip"
                            class="flex-1 bg-indigo-950/80 hover:bg-indigo-900 border border-indigo-500/30 hover:border-indigo-400/50 text-indigo-300 rounded-xl py-3.5 px-6 font-semibold text-sm active:scale-[0.99] step-transition flex items-center justify-center gap-2">
                            <i class="fa-solid fa-file-zipper text-base"></i>
                            Pobierz jako Paczkę ZIP
                        </button>
                    </div>

                </form>
            </div>

            <!-- Prawa kolumna: Informacje o szablonie oraz Podgląd -->
            <div class="space-y-6">
                
                <!-- Informacja o strukturze -->
                <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-2xl">
                    <h4 class="text-sm font-bold text-slate-200 uppercase tracking-wider mb-4 flex items-center gap-2">
                        <i class="fa-solid fa-folder-tree text-blue-500 text-sm"></i>
                        Podgląd Drzewa Katalogów
                    </h4>
                    <div class="bg-slate-950 border border-slate-800 rounded-xl p-4 font-mono text-xs text-slate-400 leading-relaxed overflow-x-auto">
                        <div id="tree-preview">
                            <!-- Dynamiczny podgląd -->
                        </div>
                    </div>
                </div>

                <!-- Lista technologii i statystyka wbudowana -->
                <div class="bg-slate-900/90 border border-slate-800 rounded-2xl p-6 shadow-2xl">
                    <h4 class="text-sm font-bold text-slate-200 uppercase tracking-wider mb-3">
                        Dlaczego Project Scaffolder?
                    </h4>
                    <ul class="text-xs text-slate-400 space-y-2.5">
                        <li class="flex items-start gap-2">
                            <i class="fa-solid fa-circle-check text-emerald-500 mt-0.5"></i>
                            <span><strong>Czysta architektura:</strong> Brak ukrytych zależności i zbędnego kodu produkcyjnego.</span>
                        </li>
                        <li class="flex items-start gap-2">
                            <i class="fa-solid fa-circle-check text-emerald-500 mt-0.5"></i>
                            <span><strong>Prawidłowe .gitignore:</strong> Automatyczne ignorowanie vendorów, cache, baz oraz IDE.</span>
                        </li>
                        <li class="flex items-start gap-2">
                            <i class="fa-solid fa-circle-check text-emerald-500 mt-0.5"></i>
                            <span><strong>Gotowy do Chmury:</strong> Szablony Docker-compose oraz wieloetapowe kompilacje Dockerfile.</span>
                        </li>
                    </ul>
                </div>

            </div>

        </div>

    </main>

    <!-- Modal Statusu Powodzenia -->
    <div id="success-modal" class="hidden fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm p-4 animate-fade-in">
        <div class="bg-slate-900 border border-slate-800 rounded-2xl max-w-lg w-full p-6 md:p-8 text-center shadow-2xl">
            <div class="h-16 w-16 bg-emerald-500/10 border border-emerald-500/20 text-emerald-500 rounded-full flex items-center justify-center mx-auto mb-4 text-3xl">
                <i class="fa-solid fa-champagne-glasses"></i>
            </div>
            <h3 class="text-xl font-bold text-white mb-2">Projekt Wygenerowany Pomyślnie!</h3>
            <p id="modal-project-info" class="text-slate-400 text-sm mb-6 leading-relaxed">Projekt został zapisany we wskazanym folderze lokalnym.</p>
            
            <div class="bg-slate-950 border border-slate-800 rounded-xl p-4 mb-6 text-left">
                <p class="text-xs font-semibold text-slate-300 mb-2 uppercase tracking-wide">Szybki Start w Twoim Terminalu:</p>
                <pre id="cli-tips-box" class="font-mono text-xs text-blue-400 leading-relaxed overflow-x-auto whitespace-pre-wrap select-all bg-slate-900 px-3 py-2.5 rounded-lg border border-slate-800/80"></pre>
            </div>

            <button type="button" onclick="closeSuccessModal()"
                class="w-full bg-slate-800 hover:bg-slate-700 text-white rounded-xl py-3 font-semibold text-sm step-transition">
                Zamknij i Kontynuuj
            </button>
        </div>
    </div>

    <!-- Stopka -->
    <footer class="border-t border-slate-800 bg-slate-950 mt-12 py-6 text-center text-xs text-slate-500">
        <p>© 2026 Project Scaffolder Pro. Wszystkie prawa zastrzeżone.</p>
    </footer>

    <!-- Logic Script JS -->
    <script>
        const supported = {{ supported_map_json|safe }};
        const langSelect = document.getElementById("language");
        const frameworkSelect = document.getElementById("framework");
        const destinationInput = document.getElementById("destination");
        const treePreview = document.getElementById("tree-preview");

        // Drzewo podglądu dla każdego szablonu
        const previews = {
            "python:fastapi": "📁 my-scaffolded-app\\n ├── 📁 .github\\n │    └── 📁 workflows\\n │         └── ci.yml\\n ├── 📄 config.py\\n ├── 📄 main.py\\n ├── 📄 requirements.txt\\n ├── 📄 Dockerfile\\n ├── 📄 docker-compose.yml\\n ├── 📄 .gitignore\\n ├── 📄 LICENSE\\n └── 📄 README.md",
            "python:flask": "📁 my-scaffolded-app\\n ├── 📄 app.py\\n ├── 📄 requirements.txt\\n ├── 📄 Dockerfile\\n ├── 📄 docker-compose.yml\\n ├── 📄 .gitignore\\n ├── 📄 LICENSE\\n └── 📄 README.md",
            "python:django": "📁 my-scaffolded-app\\n ├── 📁 my_scaffolded_app\\n │    ├── 📄 __init__.py\\n │    ├── 📄 settings.py\\n │    ├── 📄 urls.py\\n │    └── 📄 wsgi.py\\n ├── 📄 manage.py\\n ├── 📄 requirements.txt\\n ├── 📄 .gitignore\\n └── 📄 README.md",
            "javascript:react": "📁 my-scaffolded-app\\n ├── 📁 src\\n │    ├── 📄 main.tsx\\n │    ├── 📄 App.tsx\\n │    └── 📄 index.css\\n ├── 📄 index.html\\n ├── 📄 package.json\\n ├── 📄 tsconfig.json\\n ├── 📄 vite.config.ts\\n ├── 📄 .gitignore\\n └── 📄 README.md",
            "javascript:nextjs": "📁 my-scaffolded-app\\n ├── 📁 src\\n │    └── 📁 app\\n │         ├── 📄 layout.tsx\\n │         ├── 📄 page.tsx\\n │         └── 📄 globals.css\\n ├── 📄 next.config.js\\n ├── 📄 package.json\\n ├── 📄 tsconfig.json\\n ├── 📄 .gitignore\\n └── 📄 README.md",
            "javascript:express": "📁 my-scaffolded-app\\n ├── 📁 src\\n │    └── 📄 index.ts\\n ├── 📄 package.json\\n ├── 📄 tsconfig.json\\n ├── 📄 .gitignore\\n └── 📄 README.md",
            "javascript:nestjs": "📁 my-scaffolded-app\\n ├── 📁 src\\n │    ├── 📄 main.ts\\n │    ├── 📄 app.module.ts\\n │    ├── 📄 app.controller.ts\\n │    └── 📄 app.service.ts\\n ├── 📄 nest-cli.json\\n ├── 📄 package.json\\n ├── 📄 tsconfig.json\\n ├── 📄 .gitignore\\n └── 📄 README.md",
            "php:laravel": "📁 my-scaffolded-app\\n ├── 📁 app\\n │    └── 📁 Http\\n │         └── 📁 Controllers\\n │              └── HomeController.php\\n ├── 📁 config\\n │    └── 📄 app.php\\n ├── 📁 public\\n │    └── 📄 index.php\\n ├── 📁 routes\\n │    └── 📄 web.php\\n ├── 📄 composer.json\\n ├── 📄 .gitignore\\n └── 📄 README.md",
            "php:symfony": "📁 my-scaffolded-app\\n ├── 📁 src\\n │    ├── 📁 Controller\\n │    │    └── HomeController.php\\n │    └── 📄 Kernel.php\\n ├── 📁 public\\n │    └── 📄 index.php\\n ├── 📁 config\\n │    └── 📄 routes.yaml\\n ├── 📄 composer.json\\n ├── 📄 .gitignore\\n └── 📄 README.md",
            "java:springboot": "📁 my-scaffolded-app\\n ├── 📁 src\\n │    ├── 📁 main\\n │    │    ├── 📁 java\\n │    │    │    └── 📁 com\\n │    │    │         └── 📁 example\\n │    │    │              └── 📁 demo\\n │    │    │                   ├── 📄 DemoApplication.java\\n │    │    │                   └── 📁 controller\\n │    │    │                        └── HelloController.java\\n │    │    └── 📁 resources\\n │    │         └── application.properties\\n ├── 📄 pom.xml\\n ├── 📄 .gitignore\\n └── 📄 README.md",
            "go:gin": "📁 my-scaffolded-app\\n ├── 📄 main.go\\n ├── 📄 go.mod\\n ├── 📄 .gitignore\\n ├── 📄 Dockerfile\\n └── 📄 README.md",
            "go:fiber": "📁 my-scaffolded-app\\n ├── 📄 main.go\\n ├── 📄 go.mod\\n ├── 📄 .gitignore\\n ├── 📄 Dockerfile\\n └── 📄 README.md"
        };

        // Inicjalizacja języków
        function initLanguages() {
            langSelect.innerHTML = "";
            for (const [langKey, langData] of Object.entries(supported)) {
                const opt = document.createElement("option");
                opt.value = langKey;
                opt.textContent = langData.name;
                langSelect.appendChild(opt);
            }
            updateFrameworks();
        }

        // Aktualizacja frameworków na podstawie wybranego języka
        function updateFrameworks() {
            const lang = langSelect.value;
            frameworkSelect.innerHTML = "";
            
            if (supported[lang]) {
                const frameworks = supported[lang].frameworks;
                for (const [fwKey, fwName] of Object.entries(frameworks)) {
                    const opt = document.createElement("option");
                    opt.value = fwKey;
                    opt.textContent = fwName;
                    frameworkSelect.appendChild(opt);
                }
            }
            updateTreePreview();
        }

        // Renderowanie podglądu drzewa
        function updateTreePreview() {
            const lang = langSelect.value;
            const fw = frameworkSelect.value;
            const key = `${lang}:${fw}`;
            let preview = previews[key] || "📁 Błąd wczytywania struktury podglądu";
            
            // Zamiana nazwy folderu głównego w podglądzie
            const projName = document.getElementById("project-name").value.trim() || "my-scaffolded-app";
            const safeName = projName.toLowerCase().replace(/[^a-z0-9_-]/g, "_");
            preview = preview.replaceAll("my-scaffolded-app", safeName);
            preview = preview.replaceAll("my_scaffolded_app", safeName.replaceAll("-", "_"));
            
            treePreview.textContent = preview;
        }

        langSelect.addEventListener("change", updateFrameworks);
        frameworkSelect.addEventListener("change", updateTreePreview);
        document.getElementById("project-name").addEventListener("input", updateTreePreview);

        // Zapytanie o walidację ścieżki w tle (asynchronicznie)
        let validationTimeout;
        destinationInput.addEventListener("input", function() {
            clearTimeout(validationTimeout);
            validationTimeout = setTimeout(validatePath, 450);
        });

        function validatePath() {
            const pathValue = destinationInput.value;
            const spinner = document.getElementById("validation-spinner");
            const success = document.getElementById("validation-success");
            const warning = document.getElementById("validation-warning");
            const feedback = document.getElementById("path-feedback-text");

            if (!pathValue.trim()) {
                spinner.classList.add("hidden");
                success.classList.add("hidden");
                warning.classList.add("hidden");
                feedback.textContent = "Podaj prawidłową ścieżkę absolutną.";
                return;
            }

            spinner.classList.remove("hidden");
            success.classList.add("hidden");
            warning.classList.add("hidden");

            fetch("/api/validate-path", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ path: pathValue })
            })
            .then(res => res.json())
            .then(data => {
                spinner.classList.add("hidden");
                if (data.exists) {
                    success.classList.remove("hidden");
                    feedback.innerHTML = `<span class="text-emerald-400">Katalog docelowy istnieje. Uprawnienia zapisu: <strong>${data.writable ? 'Tak' : 'Nie'}</strong>. Powierzchnia wolna: ${data.free_gb != 'Brak' ? data.free_gb + ' GB' : 'Wiele'}</span>`;
                } else {
                    warning.classList.remove("hidden");
                    feedback.innerHTML = `<span class="text-amber-400">Katalog nie istnieje. Zostanie automatycznie otworzony przy generowaniu.</span>`;
                }
            })
            .catch(() => {
                spinner.classList.add("hidden");
            });
        }

        // Akcja: Generuj Lokalnie
        document.getElementById("btn-generate-local").addEventListener("click", function() {
            const payload = getFormPayload();
            if (!payload.destination) {
                alert("Podaj pełną lokalizację docelową!");
                return;
            }

            const btn = document.getElementById("btn-generate-local");
            const originalContent = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = `<i class="fa-solid fa-spinner animate-spin"></i> Generowanie...`;

            fetch("/api/generate", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            })
            .then(res => res.json())
            .then(data => {
                btn.disabled = false;
                btn.innerHTML = originalContent;

                if (data.success) {
                    showSuccessModal(data);
                } else {
                    alert("Wystąpił błąd przy tworzeniu projektu: " + data.error);
                }
            })
            .catch(err => {
                btn.disabled = false;
                btn.innerHTML = originalContent;
                alert("Wystąpił nieoczekiwany błąd serwera.");
            });
        });

        // Akcja: Pobierz jako ZIP
        document.getElementById("btn-download-zip").addEventListener("click", function() {
            const payload = getFormPayload();
            
            const btn = document.getElementById("btn-download-zip");
            const originalContent = btn.innerHTML;
            btn.disabled = true;
            btn.innerHTML = `<i class="fa-solid fa-spinner animate-spin"></i> Pakowanie...`;

            fetch("/api/download-zip", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            })
            .then(res => {
                btn.disabled = false;
                btn.innerHTML = originalContent;
                if (!res.ok) {
                    return res.json().then(d => { throw new Error(d.error || "Wystąpił błąd"); });
                }
                return res.blob();
            })
            .then(blob => {
                const url = window.URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = `${payload.projectName || 'scaffolded-project'}.zip`;
                document.body.appendChild(a);
                a.click();
                a.remove();
            })
            .catch(err => {
                btn.disabled = false;
                btn.innerHTML = originalContent;
                alert("Błąd paczkowania: " + err.message);
            });
        });

        function getFormPayload() {
            return {
                projectName: document.getElementById("project-name").value.trim(),
                author: document.getElementById("author").value.trim(),
                language: langSelect.value,
                framework: frameworkSelect.value,
                destination: destinationInput.value.trim(),
                git_init: document.getElementById("git_init").checked,
                docker: document.getElementById("docker").checked,
                docker_compose: document.getElementById("docker_compose").checked,
                github_actions: document.getElementById("github_actions").checked,
                license: document.getElementById("license").checked,
                overwrite: document.getElementById("overwrite").checked
            };
        }

        // Kod porady CLI w modalu
        function showSuccessModal(data) {
            document.getElementById("modal-project-info").innerHTML = `
                Projekt <strong>${data.project_name}</strong> został pomyślnie wygenerowany! <br>
                Zapisano w: <span class="text-blue-400 font-mono text-xs break-all">${data.target_directory}</span>
            `;

            let startTips = "";
            const fw = frameworkSelect.value;
            const absoluteDir = data.target_directory;

            startTips += `cd "${absoluteDir}"\\n`;
            if (langSelect.value === "python") {
                startTips += `python -m venv .venv\\nsource .venv/bin/activate\\npip install -r requirements.txt\\n`;
                if (fw === "fastapi") {
                    startTips += `uvicorn main:app --reload`;
                } else if (fw === "flask") {
                    startTips += `python app.py`;
                } else if (fw === "django") {
                    startTips += `python manage.py runserver`;
                }
            } else if (langSelect.value === "javascript") {
                startTips += `npm install\\nnpm run dev`;
            } else if (langSelect.value === "go") {
                startTips += `go mod tidy\\ngo run main.go`;
            } else if (langSelect.value === "java") {
                startTips += `./mvnw spring-boot:run`;
            } else if (langSelect.value === "php") {
                startTips += `composer install\\nphp artisan serve`;
            }

            document.getElementById("cli-tips-box").textContent = startTips;
            document.getElementById("success-modal").classList.remove("hidden");
        }

        function closeSuccessModal() {
            document.getElementById("success-modal").classList.add("hidden");
        }

        // Start
        initLanguages();
        validatePath();
    </script>
</body>
</html>
"""

@app.route("/", methods=["GET"])
def index():
    default_workspace = os.path.abspath(os.path.join(os.getcwd()))
    author_name = "Developer"
    
    # Przekazanie wspieranych technologii
    supported_map_json = json.dumps(scaffolder.get_supported_map())
    
    return render_template_string(
        HTML_TEMPLATE,
        default_workspace=default_workspace,
        author_name=author_name,
        supported_map_json=supported_map_json
    )

@app.route("/api/validate-path", methods=["POST"])
def validate_path():
    data = request.get_json() or {}
    path = data.get("path", "").strip()
    
    if not path:
        return jsonify({"exists": False, "writable": False, "free_gb": "Brak"})
        
    resolved_path = os.path.abspath(path)
    exists = os.path.exists(resolved_path)
    
    writable = os.access(resolved_path, os.W_OK) if exists else os.access(os.path.dirname(resolved_path), os.W_OK)
    
    free_gb_val = "Brak"
    if exists:
        try:
            total, used, free = shutil.disk_usage(resolved_path)
            free_gb_val = f"{free / (2**30):.2f}"
        except Exception:
            pass
            
    return jsonify({
        "resolved_path": resolved_path,
        "exists": exists,
        "writable": writable,
        "free_gb": free_gb_val
    })

@app.route("/api/generate", methods=["POST"])
def generate_project():
    try:
        data = request.get_json() or {}
        lang = data.get("language")
        framework = data.get("framework")
        destination = data.get("destination", "").strip()
        project_name = data.get("projectName", "").strip()
        
        supported_map = scaffolder.get_supported_map()
        if not lang or lang not in supported_map:
            return jsonify({"success": False, "error": "Nieznany lub nieobsługiwany język."}), 400
        if not framework or framework not in supported_map[lang]["frameworks"]:
            return jsonify({"success": False, "error": "Nieznany lub nieobsługiwany framework dla wybranego języka."}), 400
            
        if not destination or not os.path.isabs(destination):
            # Fallback
            destination = os.getcwd()
            
        options = {
            "git_init": bool(data.get("git_init", True)),
            "docker": bool(data.get("docker", True)),
            "docker_compose": bool(data.get("docker_compose", True)),
            "github_actions": bool(data.get("github_actions", True)),
            "license": bool(data.get("license", True)),
            "overwrite": bool(data.get("overwrite", False)),
            "author": data.get("author", "Developer")
        }
        
        result = scaffolder.generate(lang, framework, destination, project_name, options)
        return jsonify(result)
        
    except FileExistsError as fe:
        return jsonify({"success": False, "error": str(fe)}), 400
    except Exception as e:
        return jsonify({"success": False, "error": f"Wystąpił nieoczekiwany błąd: {str(e)}"}), 500

@app.route("/api/download-zip", methods=["POST"])
def download_zip():
    try:
        data = request.get_json() or {}
        lang = data.get("language")
        framework = data.get("framework")
        project_name = data.get("projectName", "").strip() or "my-scaffolded-app"
        
        supported_map = scaffolder.get_supported_map()
        if not lang or lang not in supported_map:
            return jsonify({"success": False, "error": "Nieznany lub nieobsługiwany język."}), 400
        if not framework or framework not in supported_map[lang]["frameworks"]:
            return jsonify({"success": False, "error": "Nieznany lub nieobsługiwany framework dla wybranego języka."}), 400
            
        options = {
            "git_init": False, # W paczkach zip nie inicjalizujemy gita
            "docker": bool(data.get("docker", True)),
            "docker_compose": bool(data.get("docker_compose", True)),
            "github_actions": bool(data.get("github_actions", True)),
            "license": bool(data.get("license", True)),
            "overwrite": True, # W tempie możemy nadpisywać
            "author": data.get("author", "Developer")
        }
        
        # Sanitize project_name to prevent path traversal inside the ZIP archive
        safe_zip_name = "".join(c if c.isalnum() or c in "-_" else "_" for c in project_name).lower() or "my-scaffolded-app"

        # Wykorzystanie folderu tymczasowego
        with tempfile.TemporaryDirectory() as tmpdir:
            res = scaffolder.generate(lang, framework, tmpdir, project_name, options)
            target_directory = res["target_directory"]
            
            # Pakowanie do zip
            memory_file = io.BytesIO()
            with zipfile.ZipFile(memory_file, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for root, dirs, files in os.walk(target_directory):
                    for file in files:
                        file_path = os.path.join(root, file)
                        # Relatywna ścieżka do umieszczenia w zipie
                        arcname = os.path.relpath(file_path, target_directory)
                        # Umieszczenie pod sanityzowanym folderem głównym projektu
                        arcname_with_folder = os.path.join(safe_zip_name, arcname)
                        zip_file.write(file_path, arcname_with_folder)
            
            memory_file.seek(0)
            return send_file(
                memory_file,
                mimetype="application/zip",
                as_attachment=True,
                download_name=f"{safe_zip_name}.zip"
            )
            
    except Exception as e:
        return jsonify({"success": False, "error": f"Błąd tworzenia archiwum ZIP: {str(e)}"}), 500

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Uruchomienie serwera Project Scaffolder Pro.")
    parser.add_argument("--port", type=int, default=8500, help="Numer portu (domyślnie 8500).")
    parser.add_argument("--host", type=str, default="127.0.0.1", help="Adres hosta.")
    parser.add_argument("--debug", action="store_true", help="Tryb debugowania.")
    args = parser.parse_args()
    
    print(f"Starting Project Scaffolder Pro server on http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)

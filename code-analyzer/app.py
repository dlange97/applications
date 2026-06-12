#!/usr/bin/env python3
"""
app.py - Flask Web Application for Code Analyzer
Exposes APIs for scanning local folders and downloading reports.
"""

from __future__ import annotations
import os
import uuid
import json
import datetime
from pathlib import Path
from flask import Flask, request, jsonify, render_template, Response
from analyzer import CodeAnalyzer

app = Flask(__name__)

# Thread-safe in-memory cache for scan results
scans_cache = {}

@app.route("/")
def index():
    # Return index template
    return render_template("index.html")

@app.route("/api/validate", methods=["POST"])
def validate_dir():
    data = request.get_json() or {}
    target_dir = data.get("target_dir", "").strip()
    
    if not target_dir:
        return jsonify({"valid": False, "message": "Proszę podać ścieżkę do katalogu."})
        
    path = Path(target_dir)
    if not path.exists():
        return jsonify({"valid": False, "message": f"Ścieżka '{target_dir}' nie istnieje."})
    if not path.is_dir():
        return jsonify({"valid": False, "message": f"Ścieżka '{target_dir}' nie jest katalogiem."})
        
    return jsonify({"valid": True, "message": "Ścieżka jest prawidłowa."})

@app.route("/api/scan", methods=["POST"])
def scan_directory():
    data = request.get_json() or {}
    target_dir = data.get("target_dir", "").strip()
    languages = data.get("languages", [])

    if not target_dir:
        return jsonify({"success": False, "error": "Ścieżka do katalogu jest wymagana."}), 400

    path = Path(target_dir)
    if not path.exists() or not path.is_dir():
        return jsonify({"success": False, "error": f"Katalog '{target_dir}' nie istnieje lub nie jest prawidłowy."}), 400

    try:
        analyzer = CodeAnalyzer(target_dir, selected_languages=languages if languages else None)
        findings, metrics, summary = analyzer.scan()
        
        # Serialize scan result
        scan_id = str(uuid.uuid4())
        
        # Convert findings and metrics to serialize-friendly formats
        findings_serialized = []
        for f in findings:
            findings_serialized.append({
                "file_path": f.file_path,
                "line_number": f.line_number,
                "line_content": f.line_content,
                "severity": f.severity,
                "category": f.category,
                "rule_id": f.rule_id,
                "message": f.message,
                "remediation": f.remediation
            })
            
        metrics_serialized = {}
        for k, v in metrics.items():
            metrics_serialized[k] = {
                "file_path": v.file_path,
                "language": CodeAnalyzer.LANG_DISPLAY_NAMES.get(v.language, v.language),
                "loc": v.loc,
                "blank_lines": v.blank_lines,
                "comment_lines": v.comment_lines,
                "complexity": v.complexity,
                "functions_count": v.functions_count,
                "classes_count": v.classes_count
            }

        scans_cache[scan_id] = {
            "target_dir": target_dir,
            "scan_id": scan_id,
            "findings": findings_serialized,
            "metrics": metrics_serialized,
            "summary": summary
        }

        # Keep cache length manageable
        if len(scans_cache) > 20:
            oldest_key = list(scans_cache.keys())[0]
            del scans_cache[oldest_key]

        return jsonify({
            "success": True,
            "scan_id": scan_id,
            "findings": findings_serialized,
            "metrics": metrics_serialized,
            "summary": summary
        })

    except Exception as e:
        return jsonify({"success": False, "error": f"Błąd skanowania: {str(e)}"}), 500


@app.route("/api/download/<scan_id>/<export_format>", methods=["GET"])
def download_report(scan_id: str, export_format: str):
    if scan_id not in scans_cache:
        return "Identyfikator skanu wygasł lub jest niepoprawny. Wykonaj skan ponownie.", 404

    scan_data = scans_cache[scan_id]
    target_dir_name = Path(scan_data["target_dir"]).name or "workspace"

    if export_format == "json":
        json_content = json.dumps(scan_data, indent=2, ensure_ascii=False)
        return Response(
            json_content,
            mimetype="application/json",
            headers={"Content-disposition": f"attachment; filename=raport-analizy-{target_dir_name}.json"}
        )

    elif export_format == "markdown":
        md_content = generate_markdown_report_string(scan_data)
        return Response(
            md_content,
            mimetype="text/markdown",
            headers={"Content-disposition": f"attachment; filename=raport-analizy-{target_dir_name}.md"}
        )

    elif export_format == "html":
        html_content = generate_standalone_html_report(scan_data)
        return Response(
            html_content,
            mimetype="text/html",
            headers={"Content-disposition": f"attachment; filename=raport-analizy-{target_dir_name}.html"}
        )

    return "Niepoprawny format eksportu.", 400


def generate_markdown_report_string(scan_data: dict) -> str:
    summary = scan_data["summary"]
    findings = scan_data["findings"]
    metrics = scan_data["metrics"]
    target_dir = scan_data["target_dir"]

    md = []
    md.append(f"# Raport z Analizy Kodu: {Path(target_dir).name}")
    md.append(f"Katalog źródłowy: `{target_dir}`\n")
    md.append("## Podsumowanie Metryk\n")
    md.append(f"- **Skanowane pliki:** {summary['total_files']} (Pominięto large/binary: {summary['ignored_files']})")
    md.append(f"- **Wszystkie linie kodu (LOC):** {summary['total_loc']}")
    md.append(f"- **Linie komentarzy:** {summary['total_comments']}")
    md.append(f"- **Puste linie:** {summary['total_blanks']}\n")

    md.append("## Statystyki Podatności / Problemów\n")
    md.append(f"- **Wszystkie problemy:** {summary['total_findings']}")
    md.append(f"  - 🔴 Krytyczne: {summary['critical_findings']}")
    md.append(f"  - 🟠 Wysokie: {summary['high_findings']}")
    md.append(f"  - 🟡 Średnie: {summary['medium_findings']}")
    md.append(f"  - 🔵 Niskie: {summary['low_findings']}")
    md.append(f"  - ⚪ Info: {summary['info_findings']}\n")

    md.append("## Lista Wykrytych Problemów\n")
    if not findings:
        md.append("🎉 Nie wykryto żadnych problemów! Dobra robota.")
    else:
        # Sort findings: Critical, High, Medium, Low, Info
        sev_order = {"Critical": 1, "High": 2, "Medium": 3, "Low": 4, "Info": 5}
        sorted_findings = sorted(findings, key=lambda x: (sev_order.get(x["severity"], 10), x["file_path"], x["line_number"]))
        
        for idx, f in enumerate(sorted_findings, 1):
            severity_emoji = {"Critical": "🔴 CRITICAL", "High": "🟠 HIGH", "Medium": "🟡 MEDIUM", "Low": "🔵 LOW", "Info": "⚪ INFO"}.get(f["severity"], "⚪ INFO")
            md.append(f"### {idx}. [{severity_emoji}] {f['message']}")
            md.append(f"- **Lokalizacja:** `{f['file_path']}` (Linia {f['line_number']})")
            md.append(f"- **Kategoria:** {f['category']}")
            md.append(f"- **Kod reguły:** `{f['rule_id']}`")
            md.append("- **Kod źródłowy:**")
            md.append(f"  ```")
            md.append(f"  {f['line_content']}")
            md.append(f"  ```")
            md.append(f"- **Rekomendacja:** {f['remediation']}")
            md.append("")

    md.append("## Metryki Szczegółowe dla Plików\n")
    md.append("| Ścieżka pliku | Język | LOC | Komentarze | Puste linie | Złożoność | Metody | Klasy |")
    md.append("| :--- | :--- | :---: | :---: | :---: | :---: | :---: | :---: |")
    for file, m in sorted(metrics.items()):
        md.append(f"| `{m['file_path']}` | {m['language']} | {m['loc']} | {m['comment_lines']} | {m['blank_lines']} | {m['complexity']} | {m['functions_count']} | {m['classes_count']} |")

    return "\n".join(md)


def generate_standalone_html_report(scan_data: dict) -> str:
    summary = scan_data["summary"]
    findings = scan_data["findings"]
    metrics = scan_data["metrics"]
    target_dir = scan_data["target_dir"]
    target_name = Path(target_dir).name

    # Prepare findings table rows
    findings_rows = []
    sev_badge_classes = {
        "Critical": "bg-red-100 text-red-800 border-red-200 dark:bg-red-900/30 dark:text-red-400 dark:border-red-800",
        "High": "bg-orange-100 text-orange-850 border-orange-200 dark:bg-orange-900/30 dark:text-orange-400 dark:border-orange-800",
        "Medium": "bg-yellow-105 text-yellow-850 border-yellow-250 dark:bg-yellow-905/30 dark:text-yellow-400 dark:border-yellow-800",
        "Low": "bg-blue-100 text-blue-800 border-blue-200 dark:bg-blue-900/30 dark:text-blue-400 dark:border-blue-800",
        "Info": "bg-gray-100 text-gray-800 border-gray-200 dark:bg-gray-900/30 dark:text-gray-400 dark:border-gray-800"
    }

    # Sort findings in output html
    sev_order = {"Critical": 1, "High": 2, "Medium": 3, "Low": 4, "Info": 5}
    sorted_findings = sorted(findings, key=lambda x: (sev_order.get(x["severity"], 10), x["file_path"], x["line_number"]))

    for i, f in enumerate(sorted_findings, 1):
        badge = sev_badge_classes.get(f['severity'], "bg-gray-100 text-gray-800")
        safe_line = f['line_content'].replace("<", "&lt;").replace(">", "&gt;")
        findings_rows.append(f"""
        <div class="p-6 bg-white dark:bg-gray-800 rounded-lg border border-gray-100 dark:border-gray-700 shadow-sm flex flex-col gap-4">
            <div class="flex flex-wrap items-center justify-between gap-2">
                <div class="flex items-center gap-3">
                    <span class="inline-flex items-center px-3 py-1 text-sm font-semibold rounded-full border {badge}">
                        {f['severity'].upper()}
                    </span>
                    <h3 class="text-lg font-bold text-gray-900 dark:text-white">{f['message']}</h3>
                </div>
                <span class="text-xs text-mono text-gray-500 font-semibold">{f['rule_id']}</span>
            </div>
            <div class="text-sm space-y-2">
                <p class="text-gray-600 dark:text-gray-400"><strong class="text-gray-900 dark:text-white">Plik:</strong> <span class="text-indigo-600 dark:text-indigo-400 font-mono break-all">{f['file_path']}</span> : Linia {f['line_number']}</p>
                <p class="text-gray-650 dark:text-gray-405"><strong class="text-gray-900 dark:text-white">Kategoria:</strong> {f['category']}</p>
            </div>
            <div class="relative overflow-hidden rounded-md bg-gray-900 text-gray-100 p-4 font-mono text-xs max-h-40 overflow-y-auto">
                <pre><code>{safe_line}</code></pre>
            </div>
            <div class="text-sm p-4 bg-emerald-50 dark:bg-emerald-950/20 border border-emerald-100 dark:border-emerald-900/30 rounded-lg text-emerald-800 dark:text-emerald-300">
                <strong class="font-bold flex items-center gap-1.5 mb-1 text-emerald-900 dark:text-emerald-200">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z"></path></svg>
                    Zalecenie naprawcze
                </strong>
                {f['remediation']}
            </div>
        </div>
        """)

    if not findings:
        findings_html = """
        <div class="p-12 text-center bg-white dark:bg-gray-800 rounded-lg border border-dashed border-gray-200 dark:border-gray-700">
            <svg class="mx-auto h-12 w-12 text-emerald-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"></path>
            </svg>
            <h3 class="mt-4 text-lg font-medium text-gray-900 dark:text-white">Nie wykryto problemów</h3>
            <p class="mt-2 text-sm text-gray-500 dark:text-gray-400">Świetna jakość kodu! Nie znaleziono żadnych naruszeń ani luk bezpieczeństwa.</p>
        </div>
        """
    else:
        findings_html = "\n".join(findings_rows)

    # Prepare file metrics rows
    metrics_rows = []
    for file, m in sorted(metrics.items()):
        metrics_rows.append(f"""
        <tr class="border-b border-gray-100 dark:border-gray-700 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-50 dark:hover:bg-gray-700/50">
            <td class="px-4 py-3 font-mono break-all text-xs text-left max-w-xs">{m['file_path']}</td>
            <td class="px-4 py-3 font-medium">{m['language']}</td>
            <td class="px-4 py-3">{m['loc']}</td>
            <td class="px-4 py-3 text-gray-500">{m['comment_lines']}</td>
            <td class="px-4 py-3 text-gray-500">{m['blank_lines']}</td>
            <td class="px-4 py-3 font-bold {'text-amber-655' if m['complexity'] > 12 else 'text-emerald-600' if m['complexity'] < 6 else 'text-orange-500'}">{m['complexity']}</td>
            <td class="px-4 py-3">{m['functions_count']}</td>
            <td class="px-4 py-3">{m['classes_count']}</td>
        </tr>
        """)

    # Standard clean HTML template
    html = f"""<!DOCTYPE html>
<html lang="pl">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Raport z Analizy Kodu - {target_name}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600;700&display=swap');
        body {{
            font-family: 'Plus Jakarta Sans', sans-serif;
        }}
        .text-mono {{
            font-family: 'JetBrains Mono', monospace;
        }}
    </style>
</head>
<body class="bg-gray-50 dark:bg-gray-900 text-gray-950 dark:text-gray-50 min-h-screen">
    <div class="max-w-7xl mx-auto px-4 py-8 lg:py-12">
        <header class="mb-12 border-b border-gray-200 dark:border-gray-800 pb-8 flex flex-col md:flex-row md:items-center justify-between gap-6">
            <div>
                <span class="text-sm font-semibold tracking-wider text-indigo-650 dark:text-indigo-400 uppercase">Raport Statycznej Analizy Kodu</span>
                <h1 class="text-3xl lg:text-4xl font-extrabold text-gray-900 dark:text-white mt-1">{target_name}</h1>
                <p class="text-sm text-gray-500 dark:text-gray-400 mt-2">Ścieżka na dysku: <code class="bg-gray-100 dark:bg-gray-800 px-2 py-1 rounded text-gray-800 dark:text-gray-200 text-xs">{target_dir}</code></p>
            </div>
            <div class="flex items-center gap-3">
                <button onclick="window.print()" class="inline-flex items-center gap-2 bg-indigo-600 hover:bg-indigo-700 text-white font-semibold px-5 py-2.5 rounded-lg text-sm shadow-sm transition-all focus:outline-none focus:ring-4 focus:ring-indigo-300">
                    <svg class="w-4 h-4" fill="none" stroke="currentColor" stroke-width="2" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" d="M17 17h2a2 2 0 002-2v-4a2 2 0 00-2-2H5a2 2 0 00-2 2v4a2 2 0 002 2h2m2 4h10a2 2 0 002-2v-4a2 2 0 00-2-2H9a2 2 0 00-2 2v4a2 2 0 002 2zm8-12V5a2 2 0 00-2-2H9a2 2 0 00-2 2v4h10z"></path></svg>
                    Drukuj / Zapisz PDF
                </button>
            </div>
        </header>

        <!-- KPI SUMMARY -->
        <section class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
            <div class="p-6 bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700">
                <p class="text-xs font-semibold text-gray-400 uppercase tracking-wider">Przebadane pliki</p>
                <p class="text-2xl font-black mt-2 text-gray-900 dark:text-white">{summary['total_files']}</p>
                <p class="text-xs text-gray-400 mt-1">Pominięto {summary['ignored_files']} plików</p>
            </div>
            <div class="p-6 bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700">
                <p class="text-xs font-semibold text-gray-400 uppercase tracking-wider">Linie kodu (LOC)</p>
                <p class="text-2xl font-black mt-2 text-gray-900 dark:text-white">{summary['total_loc']}</p>
                <p class="text-xs text-gray-400 mt-1">{summary['total_comments']} linii komentarzy</p>
            </div>
            <div class="p-6 bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700">
                <p class="text-xs font-semibold text-gray-400 uppercase tracking-wider">Liczba problemów</p>
                <p class="text-2xl font-black mt-2 text-amber-600 dark:text-amber-400">{summary['total_findings']}</p>
                <p class="text-xs text-gray-400 mt-1">🔴 {summary['critical_findings']} krytycznych, 🟠 {summary['high_findings']} wysokich</p>
            </div>
            <div class="p-6 bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700">
                <p class="text-xs font-semibold text-gray-400 uppercase tracking-wider">Skanowane języki</p>
                <p class="text-2xl font-black mt-2 text-indigo-600 dark:text-indigo-400">{summary['languages_scanned']}</p>
                <p class="text-xs text-gray-400 mt-1">Dedykowane zasady analizy</p>
            </div>
        </section>

        <!-- SUB DETAILED SUMMARY -->
        <section class="mb-12 grid grid-cols-1 md:grid-cols-5 gap-4">
            <div class="md:col-span-3 bg-white dark:bg-gray-800 p-6 rounded-xl border border-gray-100 dark:border-gray-700 shadow-sm flex flex-col justify-between">
                <h2 class="text-lg font-bold text-gray-900 dark:text-white mb-4">Profil podatności</h2>
                <div class="space-y-3">
                    <div>
                        <div class="flex justify-between text-xs font-bold mb-1">
                            <span class="text-red-600">🔴 Krytyczne</span>
                            <span class="text-gray-900 dark:text-white">{summary['critical_findings']}</span>
                        </div>
                        <div class="w-full bg-gray-100 dark:bg-gray-700 rounded-full h-2">
                            <div class="bg-red-600 h-2 rounded-full" style="width: {min(100, (summary['critical_findings']/max(1, summary['total_findings']))*100)}%"></div>
                        </div>
                    </div>
                    <div>
                        <div class="flex justify-between text-xs font-bold mb-1">
                            <span class="text-orange-500 font-bold">🟠 Wysokie</span>
                            <span class="text-gray-900 dark:text-white">{summary['high_findings']}</span>
                        </div>
                        <div class="w-full bg-gray-100 dark:bg-gray-700 rounded-full h-2">
                            <div class="bg-orange-500 h-2 rounded-full" style="width: {min(100, (summary['high_findings']/max(1, summary['total_findings']))*100)}%"></div>
                        </div>
                    </div>
                    <div>
                        <div class="flex justify-between text-xs font-bold mb-1">
                            <span class="text-yellow-600">🟡 Średnie</span>
                            <span class="text-gray-900 dark:text-white">{summary['medium_findings']}</span>
                        </div>
                        <div class="w-full bg-gray-100 dark:bg-gray-700 rounded-full h-2">
                            <div class="bg-yellow-405 h-2 rounded-full" style="width: {min(100, (summary['medium_findings']/max(1, summary['total_findings']))*100)}%"></div>
                        </div>
                    </div>
                    <div>
                        <div class="flex justify-between text-xs font-bold mb-1">
                            <span class="text-blue-600">🔵 Niskie</span>
                            <span class="text-gray-900 dark:text-white">{summary['low_findings']}</span>
                        </div>
                        <div class="w-full bg-gray-100 dark:bg-gray-700 rounded-full h-2">
                            <div class="bg-blue-600 h-2 rounded-full" style="width: {min(100, (summary['low_findings']/max(1, summary['total_findings']))*100)}%"></div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="md:col-span-2 bg-indigo-50 dark:bg-indigo-950/20 p-6 rounded-xl border border-indigo-100 dark:border-indigo-900/40 shadow-sm flex flex-col justify-between">
                <div>
                    <h3 class="text-indigo-900 dark:text-indigo-200 font-bold text-lg">Podsumowanie jakości</h3>
                    <p class="text-xs text-indigo-700 dark:text-indigo-400 mt-1">Poziom zgodności oraz bezpieczeństwa bazy kodowej bazujący na liczbie wykrytych krytycznych anomalii statycznych.</p>
                </div>
                <div class="my-6">
                    <span class="text-5xl font-extrabold text-indigo-700 dark:text-indigo-400">
                        {max(0, 100 - (summary['critical_findings']*15 + summary['high_findings']*8 + summary['medium_findings']*3))} %
                    </span>
                    <span class="text-sm block text-indigo-600 dark:text-indigo-400 font-medium mt-1">Ogólny Score Bezpieczeństwa</span>
                </div>
                <div class="text-xs text-indigo-600 dark:text-indigo-300">
                    Skompilowano automatycznie dnia: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                </div>
            </div>
        </section>

        <!-- SECTIONS TABS -->
        <main class="space-y-12">
            <!-- FINDINGS SECTION -->
            <section>
                <div class="flex items-center gap-2 mb-6">
                    <h2 class="text-2xl font-bold text-gray-900 dark:text-white">Luki i Nieprawidłowości ({summary['total_findings']})</h2>
                </div>
                <div class="space-y-6">
                    {findings_html}
                </div>
            </section>

            <!-- METRICS TABLE SECTION -->
            <section class="pt-8 border-t border-gray-200 dark:border-gray-800">
                <h2 class="text-2xl font-bold text-gray-900 dark:text-white mb-6">Metryki Techniczne i Złożoność</h2>
                <div class="bg-white dark:bg-gray-800 rounded-xl shadow-sm border border-gray-100 dark:border-gray-700 overflow-hidden">
                    <div class="overflow-x-auto">
                        <table class="w-full text-center table-fixed md:table-auto">
                            <thead>
                                <tr class="bg-gray-50/75 dark:bg-gray-700/50 border-b border-gray-100 dark:border-gray-700 text-xs font-bold text-gray-500 dark:text-gray-450 uppercase tracking-wider">
                                    <th class="px-4 py-3 text-left w-1/3">Zasób / Ścieżka pliku</th>
                                    <th class="px-4 py-3">Język</th>
                                    <th class="px-4 py-3">LOC</th>
                                    <th class="px-4 py-3">Komentarze</th>
                                    <th class="px-4 py-3">Linie Puste</th>
                                    <th class="px-4 py-3">Złożoność</th>
                                    <th class="px-4 py-3">Funkcje</th>
                                    <th class="px-4 py-3">Klasy</th>
                                </tr>
                            </thead>
                            <tbody>
                                {"\n".join(metrics_rows)}
                            </tbody>
                        </table>
                    </div>
                </div>
            </section>
        </main>

        <footer class="mt-16 text-center text-xs text-gray-400 border-t border-gray-200 dark:border-gray-800 pt-8">
            <p>Generowane przez Code Analyzer App &copy; 2026. Wszystkie prawa zastrzeżone.</p>
        </footer>
    </div>
</body>
</html>
"""
    return html


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Code Analyzer Web App")
    parser.add_argument("-p", "--port", type=int, default=8000, help="Port to run on")
    parser.add_argument("-H", "--host", type=str, default="127.0.0.1", help="Host to run on")
    parser.add_argument("--debug", action="store_true", help="Enable Flask debug mode")
    args = parser.parse_args()
    
    app.run(host=args.host, port=args.port, debug=args.debug)

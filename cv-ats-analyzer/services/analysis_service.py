import datetime
import re

from services.profile_service import ATS_PROFILE


def run_ats_analysis(cv_text: str, job_description: str = "") -> dict:
    lower = cv_text.lower()
    jd_lower = job_description.lower().strip()

    def check(kws: list) -> tuple:
        found, missing = [], []
        for kw in kws:
            (found if kw.lower() in lower else missing).append(kw)
        return found, missing

    f_must, m_must = check(ATS_PROFILE["must_have"])
    f_nice, m_nice = check(ATS_PROFILE["nice_to_have"])
    f_soft, m_soft = check(ATS_PROFILE["soft_skills"])
    f_ai, m_ai = check(ATS_PROFILE["ai_mindset"])
    f_ht, m_ht = check(ATS_PROFILE["high_traffic"])
    f_senior, _ = check(ATS_PROFILE["seniority"])

    jd_focus_terms = []
    if jd_lower:
        keywords_pool = ATS_PROFILE["must_have"] + ATS_PROFILE["nice_to_have"]
        seen = set()
        for term in keywords_pool:
            low = term.lower()
            if low in jd_lower and low not in seen:
                seen.add(low)
                jd_focus_terms.append(term)

    f_jd, m_jd = check(jd_focus_terms) if jd_focus_terms else ([], [])

    def pct(found, pool):
        return len(found) / len(pool) if pool else 0

    match_rate = max(0, min(100, int(
        pct(f_must, ATS_PROFILE["must_have"]) * 55 +
        pct(f_nice, ATS_PROFILE["nice_to_have"]) * 20 +
        pct(f_soft, ATS_PROFILE["soft_skills"]) * 10 +
        pct(f_ai, ATS_PROFILE["ai_mindset"]) * 8 +
        pct(f_ht, ATS_PROFILE["high_traffic"]) * 7
    )))

    if jd_focus_terms:
        jd_alignment_bonus = int((pct(f_jd, jd_focus_terms) - 0.5) * 10)
        match_rate = max(0, min(100, match_rate + jd_alignment_bonus))

    if match_rate >= 80:
        rating_desc, rating_color = "Excellent — bardzo wysokie dopasowanie", "success"
    elif match_rate >= 60:
        rating_desc, rating_color = "Good — dobre dopasowanie, kilka braków do uzupełnienia", "primary"
    elif match_rate >= 40:
        rating_desc, rating_color = "Fair — umiarkowane dopasowanie, uzupełnij słowa kluczowe", "warning"
    else:
        rating_desc, rating_color = "Poor — CV wymaga znacznych poprawek pod to ogłoszenie", "danger"

    compliance = []
    words = len(cv_text.split())
    if words < 250:
        compliance.append({
            "severity": "critical",
            "issue": "CV zbyt krótkie",
            "description": f"Tylko {words} słów. ATS może odrzucić bardzo krótkie CV — minimum ~400 słów.",
        })
    if not re.search(r"\d{4}\s*[-–—]\s*(?:present|obecnie|nadal|\d{4})", cv_text, re.I):
        compliance.append({
            "severity": "warning",
            "issue": "Brak czytelnych dat",
            "description": "Daty w formacie 'RRRR – RRRR' lub 'RRRR – Obecnie' są wymagane przez parsery ATS.",
        })
    if re.search(r"[│┃╠╦╔═]", cv_text) or cv_text.count("|") > 15:
        compliance.append({
            "severity": "warning",
            "issue": "Prawdopodobne tabele lub ramki",
            "description": "Tabele ASCII / graficzne elementy mogą być źle parsowane. Zamień na proste listy.",
        })
    emails = re.findall(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", cv_text)
    if not emails:
        compliance.append({
            "severity": "critical",
            "issue": "Brak adresu email",
            "description": "Email to obowiązkowy element wykrywany przez ATS w sekcji kontaktowej.",
        })
    has_sections = any(
        sec in lower for sec in [
            "doświadczenie", "experience", "umiejętności", "skills", "wykształcenie", "education",
            "projekty", "projects", "about", "summary", "podsumowanie",
        ]
    )
    if not has_sections:
        compliance.append({
            "severity": "warning",
            "issue": "Brak standardowych nagłówków sekcji",
            "description": "ATS szuka nagłówków: Doświadczenie, Umiejętności, Wykształcenie.",
        })
    if not compliance:
        compliance.append({
            "severity": "info",
            "issue": "Brak krytycznych błędów formatowania",
            "description": "Struktura CV wygląda poprawnie dla systemów ATS.",
        })

    recommendations = []
    if "blackfire" not in lower:
        recommendations.append(
            "Dodaj profilowanie: Profilowanie aplikacji PHP przy użyciu BlackFire Profiler — identyfikacja wąskich gardeł wydajnościowych, redukcja czasu odpowiedzi o 30-40%."
        )
    if not any(kw.lower() in lower for kw in ["ai", "copilot", "chatgpt", "gpt", "claude"]):
        recommendations.append(
            "Podkreśl AI mindset: Na co dzień wykorzystuję GitHub Copilot i ChatGPT do przyspieszenia developmentu, generowania testów jednostkowych i automatyzacji code review."
        )
    if "akamai" not in lower:
        recommendations.append(
            "Wspomnij CDN: Doświadczenie z platformami high-traffic (50k+ concurrent users), konfiguracja Akamai CDN i Varnish cache dla redukcji obciążenia origin serverów."
        )
    if "rabbitmq" not in lower:
        recommendations.append(
            "Dodaj message broker: Implementacja asynchronicznych pipeline'ow z RabbitMQ (Dead Letter Exchanges, consumer groups, prefetch QoS, monitoring przez rabbitmq_management)."
        )
    if not any(ec.lower() in lower for ec in ["e-commerce", "ecommerce", "sklep"]):
        recommendations.append(
            "Zaznacz kontekst e-commerce: Rozwój platform e-commerce obsługujących tysiące transakcji dziennie — optymalizacja wydajności, bezpieczeństwo płatności, skalowalność."
        )
    if "elasticsearch" not in lower:
        recommendations.append(
            "Dodaj ElasticSearch: Projektowanie i optymalizacja indeksów ElasticSearch — full-text search, faceted navigation, agregacje dla platform e-commerce."
        )

    return {
        "match_rate": match_rate,
        "rating_description": rating_desc,
        "rating_color": rating_color,
        "seniority_signals": f_senior,
        "keywords": {
            "must_have": {"found": f_must, "missing": m_must},
            "nice_to_have": {"found": f_nice, "missing": m_nice},
        },
        "soft_skills": {
            "found": f_soft,
            "missing": m_soft,
            "ai_mindset": {"found": f_ai, "missing": m_ai},
            "high_traffic": {"found": f_ht, "missing": m_ht},
        },
        "job_context": {
            "provided": bool(job_description.strip()),
            "focus_terms": {"found": f_jd, "missing": m_jd},
        },
        "compliance": compliance,
        "recommendations": recommendations[:5],
        "cv_stats": {
            "words": len(cv_text.split()),
            "chars": len(cv_text),
            "emails": emails[:1],
        },
        "analyzed_at": datetime.datetime.now().isoformat(),
    }


def build_improvement_annotations(cv_text: str) -> list[dict]:
    annotations = []
    lines = cv_text.splitlines()
    weak_patterns = [
        (r"\bodpowiedzialn\w*\s+za\b", "Zamień ogólnik na konkretny rezultat i metrykę.", "medium"),
        (r"\buczestniczy\w*\b", "Użyj mocniejszych czasowników: wdrożyłem/zoptymalizowałem/zaprojektowałem.", "low"),
        (r"\bznajomo[śs]ć\b", "Zamiast 'znajomość' podaj poziom i efekt użycia technologii.", "low"),
        (r"\bteam player\b", "Dodaj konkretny przykład współpracy zespołowej.", "low"),
    ]

    for idx, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line:
            continue
        if len(annotations) >= 25:
            break
        if re.search(r"[│┃╠╦╔═]", line):
            annotations.append({
                "line_number": idx,
                "severity": "high",
                "reason": "Element tabelaryczny może utrudniać parserowi ATS odczyt CV.",
                "snippet": line,
            })
            continue
        if len(line) > 170:
            annotations.append({
                "line_number": idx,
                "severity": "medium",
                "reason": "Linia jest bardzo długa — skróć ją dla lepszej czytelności ATS.",
                "snippet": line,
            })
            continue
        if (
            any(word in line.lower() for word in ["wdro", "projekt", "system", "optymal", "api", "mikroserwis"])
            and not re.search(r"\d", line)
            and len(line.split()) >= 6
        ):
            annotations.append({
                "line_number": idx,
                "severity": "medium",
                "reason": "Dodaj mierzalny efekt (np. %, czas, skala), aby podbić ranking ATS.",
                "snippet": line,
            })
            continue
        for pattern, reason, severity in weak_patterns:
            if re.search(pattern, line, re.IGNORECASE):
                annotations.append({
                    "line_number": idx,
                    "severity": severity,
                    "reason": reason,
                    "snippet": line,
                })
                break

    return annotations


def build_text_summary(cv_text: str, analysis: dict, annotations: list[dict]) -> dict:
    lower = cv_text.lower()
    email = bool(re.search(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", cv_text))
    phone = bool(re.search(r"(?:\+\d{1,3}[\s\-]?)?\d[\d\s\-]{7,14}\d", cv_text))
    linkedin = "linkedin" in lower
    github = "github" in lower

    has_experience = any(k in lower for k in ["doświadczenie", "experience", "projekty", "project"])
    has_skills = any(k in lower for k in ["umiejętności", "skills", "stack", "technologie"])
    has_education = any(k in lower for k in ["wykształcenie", "education", "uczelnia"])

    must_found = analysis["keywords"]["must_have"]["found"]
    must_missing = analysis["keywords"]["must_have"]["missing"]
    recommendations = analysis.get("recommendations", [])

    severity_rank = {"high": 3, "critical": 3, "medium": 2, "warning": 2, "low": 1, "info": 0}
    top_issues = sorted(
        annotations,
        key=lambda x: severity_rank.get(str(x.get("severity", "low")).lower(), 1),
        reverse=True,
    )[:5]

    elements = [
        {
            "name": "Kontakt",
            "status": "good" if email and phone else "needs-work",
            "details": [
                f"Email: {'OK' if email else 'brak'}",
                f"Telefon: {'OK' if phone else 'brak'}",
                f"LinkedIn: {'OK' if linkedin else 'brak'}",
                f"GitHub: {'OK' if github else 'brak'}",
            ],
        },
        {
            "name": "Sekcje CV",
            "status": "good" if has_experience and has_skills else "needs-work",
            "details": [
                f"Doświadczenie: {'OK' if has_experience else 'brak wyraźnej sekcji'}",
                f"Umiejętności: {'OK' if has_skills else 'brak wyraźnej sekcji'}",
                f"Wykształcenie: {'OK' if has_education else 'do uzupełnienia'}",
            ],
        },
        {
            "name": "Dopasowanie techniczne",
            "status": "good" if len(must_found) >= max(6, len(must_missing) // 2) else "needs-work",
            "details": [
                f"Must-have znalezione: {len(must_found)}",
                f"Must-have brakujące: {len(must_missing)}",
                "Najmocniejsze słowa kluczowe: " + (", ".join(must_found[:6]) if must_found else "brak"),
            ],
        },
        {
            "name": "Krytyczne miejsca do poprawy",
            "status": "needs-work" if top_issues else "good",
            "details": [f"Linia {i['line_number']}: {i['reason']}" for i in top_issues] or ["Brak krytycznych uwag."],
        },
        {
            "name": "Szybkie poprawki",
            "status": "needs-work" if recommendations else "good",
            "details": recommendations[:3] or ["Brak pilnych rekomendacji."],
        },
    ]

    return {
        "overview": (
            f"Match Rate: {analysis.get('match_rate', 0)}%. "
            f"Znaleziono {len(must_found)} kluczowych technologii, brak {len(must_missing)}."
        ),
        "elements": elements,
    }

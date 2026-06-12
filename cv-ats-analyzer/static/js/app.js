/* ═══════════════════════════════════════════════════════════════════════════
   CV ATS Analyzer — Frontend Logic
   ═══════════════════════════════════════════════════════════════════════════ */

"use strict";

// PDF.js global
if (window.pdfjsLib) {
  window.pdfjsLib.GlobalWorkerOptions.workerSrc =
    "https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js";
}

let currentFilename = null;
let pdfDoc = null;
let currentPage = 1;
let currentScale = 1.3;
let lastAnalysis = null;
let lastPreviewText = "";
let lastMarkers = [];
let lastTextSummary = null;
let activePreviewFile = null;

// ── Initialisation ───────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  loadTemplates();
  loadHtmlPreviews();
  setupDropZone();
  const toggle = document.getElementById("highlightToggle");
  if (toggle) {
    toggle.addEventListener("change", () => {
      applyHighlightToggle();
    });
  }
});

// ── Drop Zone ────────────────────────────────────────────────────────────────
function setupDropZone() {
  const zone = document.getElementById("uploadZone");
  const input = document.getElementById("fileInput");

  zone.addEventListener("click", () => input.click());

  zone.addEventListener("dragover", (e) => {
    e.preventDefault();
    zone.classList.add("drag-over");
  });
  zone.addEventListener("dragleave", () => zone.classList.remove("drag-over"));
  zone.addEventListener("drop", (e) => {
    e.preventDefault();
    zone.classList.remove("drag-over");
    const f = e.dataTransfer.files[0];
    if (f) doUpload(f);
  });

  input.addEventListener("change", () => {
    if (input.files[0]) doUpload(input.files[0]);
  });
}

// ── Load Templates Dropdown ──────────────────────────────────────────────────
async function loadTemplates() {
  try {
    const res = await fetch("/api/templates");
    const data = await res.json();
    const html = data.templates
      .map((t) => `<option value="${t.id}">${t.name}</option>`)
      .join("");
    ["templateSelect", "templateSelect2"].forEach((id) => {
      const el = document.getElementById(id);
      if (el) el.innerHTML = html;
    });
  } catch (e) {
    console.error("Nie udało się załadować szablonów", e);
  }
}

// ── Upload ───────────────────────────────────────────────────────────────────
async function doUpload(file) {
  const allowed = [".pdf", ".docx", ".doc", ".txt", ".jpg", ".jpeg", ".png"];
  const ext = "." + file.name.split(".").pop().toLowerCase();
  if (!allowed.includes(ext)) {
    showToast(
      `Nieobsługiwany format: ${ext}. Dozwolone: PDF, DOCX, TXT, JPG, PNG`,
      "error",
    );
    return;
  }

  setStatus("Wgrywanie…");
  const fd = new FormData();
  fd.append("cv", file);

  try {
    const res = await fetch("/api/upload", { method: "POST", body: fd });
    const data = await res.json();
    if (!data.success) {
      showToast(data.error || "Błąd wgrywania", "error");
      setStatus("Błąd");
      return;
    }
    currentFilename = data.filename;
    showFileInfo(data);
    setStatus("Gotowy do analizy");
    showToast("CV wgrane pomyślnie!", "success");
  } catch (e) {
    showToast("Błąd połączenia z serwerem", "error");
    setStatus("Błąd sieci");
  }
}

async function convertCvTemplate() {
  if (!currentFilename) {
    showToast("Wgraj najpierw CV", "warning");
    return;
  }

  const outputFormat = (
    document.getElementById("convertFormatSelect")?.value || "html"
  ).trim();
  const btn = document.getElementById("convertBtn");
  if (btn) btn.disabled = true;

  setStatus("Konwersja 1:1 w toku…");
  showToast("Uruchamiam zaawansowaną konwersję 1:1…", "info");

  try {
    const res = await fetch("/api/convert-template", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        filename: currentFilename,
        output_format: outputFormat,
      }),
    });
    const data = await res.json();
    if (!data.success) {
      showToast(data.error || "Błąd konwersji", "error");
      setStatus("Konwersja nieudana");
      return;
    }

    if (!data.validation || !data.validation.passed) {
      showToast("Walidacja 1:1 nie przeszła", "error");
      setStatus("Walidacja nieudana");
      return;
    }

    await loadHtmlPreviews();

    // Optional UX: show links in improve box if analysis view is open.
    const box = document.getElementById("improveCvResult");
    if (box) {
      const imgs = (data.extracted_images || [])
        .map(
          (url) =>
            `<a class="btn btn-generate" href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">🖼 Wycięte zdjęcie</a>`,
        )
        .join(" ");
      box.innerHTML = `
        <div class="summary-overview">Konwersja 1:1 zakończona sukcesem (score: ${data.validation.score}%).</div>
        <div class="job-search-row">
          <button class="btn btn-generate" type="button" onclick="openHtmlPreviewModal('${escapeHtml(data.html_preview || "")}')">👁 Otwórz podgląd HTML</button>
          ${imgs}
        </div>
      `;
    }

    showToast(
      "Konwersja 1:1 zakończona. Podgląd dodany do historii HTML.",
      "success",
    );
    setStatus(`Konwersja OK · ${data.validation.score}%`);
  } catch (e) {
    showToast("Błąd połączenia przy konwersji", "error");
    setStatus("Błąd konwersji");
  } finally {
    if (btn) btn.disabled = false;
  }
}

async function loadHtmlPreviews() {
  const list = document.getElementById("htmlPreviewsList");
  if (!list) return;

  list.innerHTML =
    '<div class="preview-item preview-empty">Wczytywanie listy podglądów...</div>';
  try {
    const res = await fetch("/api/html-previews");
    const data = await res.json();
    if (!data.success) {
      list.innerHTML = `<div class="preview-item preview-empty">${escapeHtml(data.error || "Nie udało się pobrać listy")}</div>`;
      return;
    }

    const items = data.items || [];
    if (!items.length) {
      list.innerHTML =
        '<div class="preview-item preview-empty">Brak podglądów HTML w folderze html-previews.</div>';
      return;
    }

    list.innerHTML = items
      .map((item) => {
        const ts = formatDate(item.modified_at);
        const size = formatBytes(item.size || 0);
        const name = escapeHtml(item.filename || "preview.html");
        const rawName = item.filename || "preview.html";
        return `<div class="preview-row">
          <button type="button" class="preview-item" onclick="openHtmlPreviewModal('${name}')">
            <span class="preview-name">${name}</span>
            <span class="preview-meta">${ts} · ${size}</span>
          </button>
          <button type="button" class="preview-delete" title="Usuń podgląd i powiązane pliki"
            onclick="deleteHtmlPreview('${rawName}', event)">&#128465;</button>
        </div>`;
      })
      .join("");
  } catch (e) {
    list.innerHTML =
      '<div class="preview-item preview-empty">Błąd połączenia podczas ładowania listy.</div>';
  }
}

async function deleteHtmlPreview(filename, event) {
  if (event) {
    event.stopPropagation();
  }
  if (!filename) return;
  if (
    !confirm(`Usunąć "${filename}" wraz z powiązanym plikiem PDF i assetami?`)
  )
    return;
  try {
    const res = await fetch(
      `/api/html-preview/${encodeURIComponent(filename)}`,
      { method: "DELETE" },
    );
    const data = await res.json();
    if (data.success) {
      await loadHtmlPreviews();
    } else {
      alert("Błąd usuwania: " + (data.error || "nieznany błąd"));
    }
  } catch (e) {
    alert("Błąd połączenia podczas usuwania.");
  }
}

async function openHtmlPreviewModal(filename) {
  if (!filename) return;
  activePreviewFile = filename;

  const modal = document.getElementById("htmlPreviewModal");
  const frame = document.getElementById("htmlPreviewFrame");
  const title = document.getElementById("htmlModalTitle");
  const meta = document.getElementById("htmlModalMeta");
  const editor = document.getElementById("htmlEditorPanel");
  const textarea = document.getElementById("htmlEditorTextarea");
  const formatSelect = document.getElementById("htmlDownloadFormat");

  if (!modal || !frame || !title || !meta || !editor || !textarea) return;

  title.textContent = filename;
  meta.textContent = "Podgląd HTML z możliwością pobrania i edycji";
  frame.src = `/api/html-preview/${encodeURIComponent(filename)}?t=${Date.now()}`;
  if (formatSelect) formatSelect.value = "html";

  editor.classList.add("hidden");
  textarea.value = "";
  modal.classList.remove("hidden");
  modal.setAttribute("aria-hidden", "false");
}

function downloadActivePreview() {
  if (!activePreviewFile) {
    showToast("Brak aktywnego preview do pobrania", "warning");
    return;
  }

  const format = document.getElementById("htmlDownloadFormat")?.value || "html";
  const url = `/api/html-preview-export/${encodeURIComponent(activePreviewFile)}?format=${encodeURIComponent(format)}`;
  const a = document.createElement("a");
  a.href = url;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
}

function closeHtmlPreviewModal() {
  const modal = document.getElementById("htmlPreviewModal");
  const frame = document.getElementById("htmlPreviewFrame");
  const editor = document.getElementById("htmlEditorPanel");
  if (!modal || !frame || !editor) return;

  frame.src = "about:blank";
  editor.classList.add("hidden");
  modal.classList.add("hidden");
  modal.setAttribute("aria-hidden", "true");
}

async function toggleHtmlEditor() {
  if (!activePreviewFile) return;
  const panel = document.getElementById("htmlEditorPanel");
  const textarea = document.getElementById("htmlEditorTextarea");
  if (!panel || !textarea) return;

  const isHidden = panel.classList.contains("hidden");
  if (!isHidden) {
    panel.classList.add("hidden");
    return;
  }

  if (!textarea.value.trim()) {
    try {
      const res = await fetch(
        `/api/html-preview-content/${encodeURIComponent(activePreviewFile)}`,
      );
      const data = await res.json();
      if (!data.success) {
        showToast(
          data.error || "Nie udało się odczytać HTML do edycji",
          "error",
        );
        return;
      }
      textarea.value = data.content || "";
    } catch (e) {
      showToast("Błąd połączenia podczas ładowania edytora", "error");
      return;
    }
  }

  panel.classList.remove("hidden");
}

function wrapSelection(prefix, suffix) {
  const ta = document.getElementById("htmlEditorTextarea");
  if (!ta) return;
  const start = ta.selectionStart;
  const end = ta.selectionEnd;
  const value = ta.value;
  const selected = value.slice(start, end);
  ta.value =
    value.slice(0, start) + prefix + selected + suffix + value.slice(end);
  ta.focus();
  ta.selectionStart = start + prefix.length;
  ta.selectionEnd = end + prefix.length;
}

function convertLinesToList() {
  const ta = document.getElementById("htmlEditorTextarea");
  if (!ta) return;
  const start = ta.selectionStart;
  const end = ta.selectionEnd;
  const value = ta.value;
  const selected = value.slice(start, end).trim();
  if (!selected) return;
  const items = selected
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean)
    .map((line) => `  <li>${line}</li>`)
    .join("\n");
  const listHtml = `<ul>\n${items}\n</ul>`;
  ta.value = value.slice(0, start) + listHtml + value.slice(end);
}

function replaceAllInEditor() {
  const ta = document.getElementById("htmlEditorTextarea");
  const findText = document.getElementById("editorFindText")?.value || "";
  const replaceText = document.getElementById("editorReplaceText")?.value || "";
  if (!ta || !findText) {
    showToast("Podaj tekst do wyszukania", "warning");
    return;
  }
  ta.value = ta.value.split(findText).join(replaceText);
  showToast("Podmiana zakończona", "success");
}

function formatEditorHtml() {
  const ta = document.getElementById("htmlEditorTextarea");
  if (!ta) return;

  const lines = ta.value
    .replace(/>\s+</g, "><")
    .replace(/></g, ">\n<")
    .split("\n");

  let indent = 0;
  const out = [];
  for (const raw of lines) {
    const line = raw.trim();
    if (!line) continue;
    if (/^<\//.test(line)) indent = Math.max(0, indent - 1);
    out.push(`${"  ".repeat(indent)}${line}`);
    if (
      /^<[^!/][^>]*[^/]>$/.test(line) &&
      !/^<(meta|link|img|br|hr|input)/i.test(line)
    ) {
      indent += 1;
    }
  }
  ta.value = out.join("\n");
}

async function saveHtmlPreviewEdits() {
  if (!activePreviewFile) return;
  const ta = document.getElementById("htmlEditorTextarea");
  const frame = document.getElementById("htmlPreviewFrame");
  if (!ta || !frame) return;

  const content = ta.value;
  if (!content.trim()) {
    showToast("Treść HTML nie może być pusta", "warning");
    return;
  }

  try {
    const res = await fetch(
      `/api/html-preview-content/${encodeURIComponent(activePreviewFile)}`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content }),
      },
    );
    const data = await res.json();
    if (!data.success) {
      showToast(data.error || "Nie udało się zapisać zmian", "error");
      return;
    }

    frame.src = `/api/html-preview/${encodeURIComponent(activePreviewFile)}?t=${Date.now()}`;
    await loadHtmlPreviews();
    showToast("Zapisano zmiany HTML", "success");
  } catch (e) {
    showToast("Błąd połączenia podczas zapisu", "error");
  }
}

function showFileInfo(data) {
  const kb = Math.round(data.size / 1024);
  document.getElementById("fileName").textContent = data.original_name;
  document.getElementById("fileSize").textContent =
    `${kb} KB · wgrano pomyślnie`;
  document.getElementById("uploadZone").classList.add("hidden");
  document.getElementById("fileInfo").classList.remove("hidden");
  document.getElementById("actionButtons").classList.remove("hidden");
}

function clearFile() {
  currentFilename = null;
  lastAnalysis = null;
  lastPreviewText = "";
  lastMarkers = [];
  lastTextSummary = null;
  document.getElementById("uploadZone").classList.remove("hidden");
  document.getElementById("fileInfo").classList.add("hidden");
  document.getElementById("actionButtons").classList.add("hidden");
  document.getElementById("fileInput").value = "";
  document.getElementById("improvementMarkers").classList.add("hidden");
  setStatus("Ready");
}

// ── Analyse ──────────────────────────────────────────────────────────────────
async function analyzeCV() {
  if (!currentFilename) {
    showToast("Wgraj najpierw swoje CV", "warning");
    return;
  }
  const jobDescription = (
    document.getElementById("jobDescriptionInput")?.value || ""
  ).trim();

  // Switch panels
  document.getElementById("uploadPanel").classList.add("hidden");
  document.getElementById("analysisPanel").classList.remove("hidden");

  // Reset results area
  document.getElementById("analysisContent").innerHTML =
    `<div id="loadingSpinner" class="loading-box"><div class="spinner"></div><p>Analizuję CV…</p></div>`;

  document.getElementById("headerFileName").textContent = currentFilename;
  document.getElementById("matchBadge").classList.add("hidden");

  // Load preview
  loadCVPreview(currentFilename);

  setStatus("Analizuję…");
  try {
    const res = await fetch("/api/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        filename: currentFilename,
        job_description: jobDescription,
      }),
    });
    const data = await res.json();

    if (!data.success) {
      showAnalysisError(data.error || "Nieznany błąd");
      setStatus("Błąd analizy");
      return;
    }

    lastAnalysis = data.analysis;
    lastPreviewText = data.preview_text || "";
    lastMarkers = data.improvement_annotations || [];
    lastTextSummary = data.text_summary || null;
    renderAnalysis(data.analysis);
    renderImprovementMarkers();
    applyHighlightToggle();
    setStatus(`Analiza gotowa · ${data.analysis.match_rate}% dopasowania`);

    // Badge
    const badge = document.getElementById("matchBadge");
    badge.textContent = `${data.analysis.match_rate}% match`;
    badge.className = `match-badge ${data.analysis.rating_color}`;
    badge.classList.remove("hidden");
  } catch (e) {
    showAnalysisError("Błąd połączenia z serwerem");
    setStatus("Błąd");
  }
}

// ── Render Analysis ──────────────────────────────────────────────────────────
function renderAnalysis(a) {
  const ts = new Date(a.analyzed_at).toLocaleTimeString("pl-PL");
  document.getElementById("analysisTimestamp").textContent = `Analiza: ${ts}`;

  const colorMap = {
    success: "#3fb950",
    primary: "#58a6ff",
    warning: "#d29922",
    danger: "#f85149",
  };
  const matchColor = colorMap[a.rating_color] || "#58a6ff";

  const must_total =
    a.keywords.must_have.found.length + a.keywords.must_have.missing.length;
  const nice_total =
    a.keywords.nice_to_have.found.length +
    a.keywords.nice_to_have.missing.length;
  const must_pct = must_total
    ? ((a.keywords.must_have.found.length / must_total) * 100).toFixed(0)
    : 0;
  const nice_pct = nice_total
    ? ((a.keywords.nice_to_have.found.length / nice_total) * 100).toFixed(0)
    : 0;
  const soft_total = a.soft_skills.found.length + a.soft_skills.missing.length;
  const soft_pct = soft_total
    ? ((a.soft_skills.found.length / soft_total) * 100).toFixed(0)
    : 0;

  // SVG ring
  const R = 34,
    circ = 2 * Math.PI * R;
  const dash = ((a.match_rate / 100) * circ).toFixed(1);
  const gap = (circ - dash).toFixed(1);

  document.getElementById("analysisContent").innerHTML = `
<div class="analysis-sections">

  <!-- 1 ── Match Rate -->
  <div class="analysis-section">
    <div class="section-title"><span class="section-num">1</span> Ogólny Rating Dopasowania (Match Rate)</div>
    <div class="match-rate-wrap">
      <div class="match-ring">
        <svg width="84" height="84" viewBox="0 0 84 84">
          <circle class="match-ring-track" cx="42" cy="42" r="${R}" fill="none" stroke-width="7"/>
          <circle class="match-ring-fill"  cx="42" cy="42" r="${R}" fill="none" stroke-width="7"
            stroke="${matchColor}"
            stroke-dasharray="${dash} ${gap}" stroke-dashoffset="0"/>
        </svg>
        <div class="match-ring-label">
          <div class="match-ring-pct" style="color:${matchColor}">${a.match_rate}%</div>
          <div class="match-ring-sub">Match</div>
        </div>
      </div>
      <div class="match-info">
        <div class="match-desc" style="color:${matchColor}">${a.rating_description}</div>
        <div class="match-stats">
          <span class="stat-pill">📝 ${a.cv_stats.words} słów</span>
          <span class="stat-pill">📊 ${a.cv_stats.chars} znaków</span>
          ${a.cv_stats.emails.length ? `<span class="stat-pill">✉ ${a.cv_stats.emails[0]}</span>` : ""}
          ${a.seniority_signals.length ? `<span class="stat-pill">🎖 ${a.seniority_signals.slice(0, 2).join(", ")}</span>` : ""}
        </div>
        <div class="bar-rows">
          ${barRow("Must-Have Keywords", must_pct, `${a.keywords.must_have.found.length}/${must_total}`, matchColor)}
          ${barRow("Nice-to-Have", nice_pct, `${a.keywords.nice_to_have.found.length}/${nice_total}`, "#58a6ff")}
          ${barRow("Soft Skills", soft_pct, `${a.soft_skills.found.length}/${soft_total}`, "#bc8cff")}
        </div>
      </div>
    </div>
  </div>

  <!-- 2 ── Keywords -->
  <div class="analysis-section">
    <div class="section-title"><span class="section-num">2</span> Analiza Słów Kluczowych (Hard Skills)</div>

    <div class="kw-group">
      <div class="kw-group-lbl">🔧 Must-Have Technologie</div>
      <div class="kw-grid">
        <div>
          <div class="kw-col-title found-title">✅ Znalezione (${a.keywords.must_have.found.length})</div>
          <div class="kw-tags">
            ${a.keywords.must_have.found.map((k) => `<span class="kw-tag found">${k}</span>`).join("") || '<span class="kw-empty">Brak</span>'}
          </div>
        </div>
        <div>
          <div class="kw-col-title missing-title">❌ Brakujące (${a.keywords.must_have.missing.length})</div>
          <div class="kw-tags">
            ${a.keywords.must_have.missing.map((k) => `<span class="kw-tag missing">${k}</span>`).join("") || '<span class="kw-empty">Brak braków!</span>'}
          </div>
        </div>
      </div>
    </div>

    <div class="kw-group">
      <div class="kw-group-lbl">⭐ Nice-to-Have</div>
      <div class="kw-grid">
        <div>
          <div class="kw-col-title found-title">✅ Znalezione (${a.keywords.nice_to_have.found.length})</div>
          <div class="kw-tags">
            ${a.keywords.nice_to_have.found.map((k) => `<span class="kw-tag found nice">${k}</span>`).join("") || '<span class="kw-empty">Brak</span>'}
          </div>
        </div>
        <div>
          <div class="kw-col-title missing-title">❌ Brakujące (${a.keywords.nice_to_have.missing.length})</div>
          <div class="kw-tags">
            ${a.keywords.nice_to_have.missing
              .slice(0, 12)
              .map((k) => `<span class="kw-tag missing nice">${k}</span>`)
              .join("")}
            ${a.keywords.nice_to_have.missing.length > 12 ? `<span class="kw-more">+${a.keywords.nice_to_have.missing.length - 12} więcej</span>` : ""}
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- 3 ── Cultural Fit -->
  <div class="analysis-section">
    <div class="section-title"><span class="section-num">3</span> Dopasowanie Kulturowe i Miękkie</div>
    <div class="cultural-grid">
      <div class="cultural-card">
        <div class="cultural-icon">${a.soft_skills.ai_mindset.found.length > 0 ? "✅" : "⚠️"}</div>
        <div class="cultural-lbl">AI-Powered Mindset</div>
        <div class="cultural-tags">
          ${
            a.soft_skills.ai_mindset.found
              .map((k) => `<span class="kw-tag found small">${k}</span>`)
              .join("") ||
            '<span class="kw-tag missing small">Brak wzmianek AI</span>'
          }
        </div>
      </div>
      <div class="cultural-card">
        <div class="cultural-icon">${a.soft_skills.high_traffic.found.length > 0 ? "✅" : "⚠️"}</div>
        <div class="cultural-lbl">High-Traffic / E-commerce</div>
        <div class="cultural-tags">
          ${
            a.soft_skills.high_traffic.found
              .map((k) => `<span class="kw-tag found small">${k}</span>`)
              .join("") ||
            '<span class="kw-tag missing small">Brak high-traffic</span>'
          }
        </div>
      </div>
      <div class="cultural-card">
        <div class="cultural-icon">${a.soft_skills.found.length > 0 ? "✅" : "⚠️"}</div>
        <div class="cultural-lbl">Soft Skills / Teamwork</div>
        <div class="cultural-tags">
          ${
            a.soft_skills.found
              .map((k) => `<span class="kw-tag found small">${k}</span>`)
              .join("") ||
            '<span class="kw-tag missing small">Brak soft skills</span>'
          }
        </div>
      </div>
    </div>
  </div>

  <!-- 4 ── ATS Compliance -->
  <div class="analysis-section">
    <div class="section-title"><span class="section-num">4</span> Krytyczne Błędy Formatowania (ATS Compliance)</div>
    ${a.compliance
      .map(
        (c) => `
      <div class="compliance-item compliance-${c.severity}">
        <div class="ci-icon">${c.severity === "critical" ? "🚨" : c.severity === "warning" ? "⚠️" : "ℹ️"}</div>
        <div>
          <div class="ci-title">${c.issue}</div>
          <div class="ci-desc">${c.description}</div>
        </div>
      </div>`,
      )
      .join("")}
  </div>

  <!-- 5 ── Recommendations -->
  <div class="analysis-section">
    <div class="section-title"><span class="section-num">5</span> Rekomendacje — Gotowe Zdania do Wpisania</div>
    ${
      a.recommendations.length === 0
        ? '<p style="color:var(--green);font-size:13px">🎉 CV jest bardzo dobrze dopasowane — brak krytycznych rekomendacji.</p>'
        : a.recommendations
            .map(
              (rec, i) => `
        <div class="rec-item">
          <div class="rec-num">${i + 1}</div>
          <div>
            <div class="rec-text">${escapeHtml(rec)}</div>
            <button class="btn-copy" onclick="copyText(${JSON.stringify(rec)})">📋 Kopiuj</button>
          </div>
        </div>`,
            )
            .join("")
    }
  </div>

  <!-- 6 ── Internet Job Search -->
  <div class="analysis-section">
    <div class="section-title"><span class="section-num">6</span> Oferty z Internetu Pasujące do Profilu</div>
    <div class="job-search-row">
      <button class="btn btn-generate" onclick="searchMatchingJobs()">🌐 Szukaj ofert (na żądanie)</button>
      <span class="job-search-hint">Wyszukiwanie legalne: publiczne wyniki wyszukiwarki i linki do popularnych portali.</span>
    </div>
    <div id="jobSearchResults" class="job-results"></div>
  </div>

  <!-- 7 ── Text Summary -->
  <div class="analysis-section">
    <div class="section-title"><span class="section-num">7</span> Podsumowanie Tekstowe CV (sekcja po sekcji)</div>
    ${renderTextSummarySection()}
  </div>

  <!-- 8 ── Improve CV -->
  <div class="analysis-section">
    <div class="section-title"><span class="section-num">8</span> Aktualizuj Podane CV</div>
    <div class="job-search-row">
      <select id="improveFormatSelect" class="template-select small" style="min-width:220px">
        <option value="">Taki sam jak wejściowy</option>
        <option value="pdf">PDF</option>
        <option value="docx">DOCX</option>
        <option value="html">HTML</option>
        <option value="canva">Canva (HTML do importu)</option>
      </select>
      <button class="btn btn-analyze" style="width:auto;padding:10px 14px" onclick="improveCurrentCV()">✨ Aktualizuj podane CV</button>
      <span class="job-search-hint">Tworzona jest poprawiona wersja CV na podstawie wykrytych braków i rekomendacji.</span>
    </div>
    <div id="improveCvResult" class="summary-box"></div>
  </div>

</div>`;
}

function renderTextSummarySection() {
  if (!lastTextSummary || !Array.isArray(lastTextSummary.elements)) {
    return '<p class="job-search-hint">Podsumowanie pojawi się po pełnej analizie CV.</p>';
  }

  const overview = escapeHtml(lastTextSummary.overview || "");
  const elements = lastTextSummary.elements
    .map((el) => {
      const status = el.status === "good" ? "good" : "needs-work";
      const statusLabel = status === "good" ? "OK" : "Do poprawy";
      const details = (el.details || [])
        .map((d) => `<li>${escapeHtml(d)}</li>`)
        .join("");
      return `
      <div class="summary-item ${status}">
        <div class="summary-head">
          <span class="summary-title">${escapeHtml(el.name || "Sekcja")}</span>
          <span class="summary-status ${status}">${statusLabel}</span>
        </div>
        <ul class="summary-list">${details}</ul>
      </div>
    `;
    })
    .join("");

  return `
    <div class="summary-box">
      <div class="summary-overview">${overview}</div>
      ${elements}
    </div>
  `;
}

// ── Helper: bar row HTML ─────────────────────────────────────────────────────
function barRow(label, pct, count, color) {
  return `
    <div class="bar-row">
      <span class="bar-row-label">${label}</span>
      <div class="bar"><div class="bar-fill" style="width:${pct}%;background:${color}"></div></div>
      <span class="bar-row-count">${count}</span>
    </div>`;
}

// ── PDF Preview ──────────────────────────────────────────────────────────────
async function loadCVPreview(filename) {
  const ext = filename.split(".").pop().toLowerCase();

  if (ext === "pdf" && window.pdfjsLib) {
    document.getElementById("pdfCanvas").classList.remove("hidden");
    document.getElementById("textPreview").classList.add("hidden");
    document.getElementById("pdfControls").classList.remove("hidden");

    try {
      pdfDoc = await window.pdfjsLib.getDocument(`/api/cv/${filename}`).promise;
      currentPage = 1;
      await renderPDFPage(1);
    } catch (e) {
      console.error("PDF load error", e);
      showTextFallback(filename);
    }
  } else {
    showTextFallback(filename);
  }
}

async function showTextFallback(filename) {
  document.getElementById("pdfCanvas").classList.add("hidden");
  document.getElementById("textPreview").classList.remove("hidden");
  document.getElementById("pdfControls").classList.add("hidden");

  try {
    const res = await fetch(`/api/cv/${filename}`);
    const text = await res.text();
    const slice = text.slice(0, 8000);
    lastPreviewText = slice;
    document.getElementById("textPreview").textContent = slice;
    applyHighlightToggle();
  } catch {
    document.getElementById("textPreview").textContent =
      "[Nie udało się załadować podglądu]";
  }
}

async function renderPDFPage(pageNum) {
  if (!pdfDoc) return;
  const page = await pdfDoc.getPage(pageNum);
  const canvas = document.getElementById("pdfCanvas");
  const ctx = canvas.getContext("2d");
  const viewport = page.getViewport({ scale: currentScale });

  canvas.width = viewport.width;
  canvas.height = viewport.height;

  await page.render({ canvasContext: ctx, viewport }).promise;
  currentPage = pageNum;
  document.getElementById("pageInfo").textContent =
    `${pageNum} / ${pdfDoc.numPages}`;
}

function prevPage() {
  if (currentPage > 1) renderPDFPage(currentPage - 1);
}
function nextPage() {
  if (pdfDoc && currentPage < pdfDoc.numPages) renderPDFPage(currentPage + 1);
}
function zoomIn() {
  currentScale = Math.min(currentScale + 0.2, 3.0);
  renderPDFPage(currentPage);
}
function zoomOut() {
  currentScale = Math.max(currentScale - 0.2, 0.6);
  renderPDFPage(currentPage);
}

// ── Template Generation ──────────────────────────────────────────────────────
async function generateTemplate() {
  if (!currentFilename) {
    showToast("Wgraj najpierw swoje CV", "warning");
    return;
  }
  const type = document.getElementById("templateSelect").value;
  await doGenerateTemplate(type, document.getElementById("generateBtn"));
}

async function generateTemplateFromAnalysis() {
  if (!currentFilename) {
    showToast("Brak wgranego CV", "warning");
    return;
  }
  const type = document.getElementById("templateSelect2").value;
  await doGenerateTemplate(type, null);
}

async function doGenerateTemplate(templateType, btnEl) {
  if (btnEl) btnEl.disabled = true;
  showToast("Generowanie szablonu PDF…", "info");
  setStatus("Generuję szablon…");

  try {
    const res = await fetch("/api/generate-template", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        filename: currentFilename,
        template_type: templateType,
      }),
    });
    const data = await res.json();

    if (!data.success) {
      showToast(data.error || "Błąd generowania", "error");
      return;
    }

    // Trigger download
    const a = document.createElement("a");
    a.href = `/api/download/${data.download_filename}`;
    a.download = data.download_filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);

    showToast(`✅ Szablon „${data.template_name}" pobrany!`, "success");
    setStatus("Szablon gotowy");
  } catch (e) {
    showToast("Błąd połączenia z serwerem", "error");
  } finally {
    if (btnEl) btnEl.disabled = false;
  }
}

// ── Navigation ───────────────────────────────────────────────────────────────
function backToUpload() {
  document.getElementById("uploadPanel").classList.remove("hidden");
  document.getElementById("analysisPanel").classList.add("hidden");
  setStatus(currentFilename ? "Gotowy do analizy" : "Ready");
}

function applyHighlightToggle() {
  const toggle = document.getElementById("highlightToggle");
  const textPreview = document.getElementById("textPreview");
  const markersBox = document.getElementById("improvementMarkers");
  if (!toggle || !textPreview) return;

  const isOn = toggle.checked;
  if (markersBox) {
    if (!lastMarkers.length || !isOn) {
      markersBox.classList.add("hidden");
    } else {
      markersBox.classList.remove("hidden");
    }
  }

  if (!isOn || !lastPreviewText || !lastMarkers.length) {
    textPreview.textContent = lastPreviewText || textPreview.textContent;
    return;
  }

  const markedLines = new Map();
  lastMarkers.forEach((m) => {
    markedLines.set(m.line_number, m.severity || "medium");
  });

  const html = (lastPreviewText || "")
    .split("\n")
    .map((line, idx) => {
      const lineNo = idx + 1;
      const sev = markedLines.get(lineNo);
      if (!sev) return escapeHtml(line);
      return `<span class="text-highlight-${sev}">${escapeHtml(line)}</span>`;
    })
    .join("\n");

  textPreview.innerHTML = html;
}

function renderImprovementMarkers() {
  const box = document.getElementById("improvementMarkers");
  if (!box) return;

  if (!lastMarkers.length) {
    box.classList.add("hidden");
    box.innerHTML = "";
    return;
  }

  box.classList.remove("hidden");
  const shown = lastMarkers.slice(0, 15);
  box.innerHTML = `
    <div class="improvement-markers-title">Miejsca do poprawy w CV (${lastMarkers.length})</div>
    ${shown
      .map(
        (m) => `
      <div class="marker-item">
        <div class="marker-head">Linia ${m.line_number} · ${m.severity}</div>
        <div class="marker-reason">${escapeHtml(m.reason)}</div>
        <div class="marker-snippet">${escapeHtml(m.snippet || "")}</div>
      </div>
    `,
      )
      .join("")}
  `;
}

async function searchMatchingJobs() {
  const container = document.getElementById("jobSearchResults");
  if (!container) return;

  if (!currentFilename) {
    showToast("Najpierw wgraj CV", "warning");
    return;
  }

  const jobDescription = (
    document.getElementById("jobDescriptionInput")?.value || ""
  ).trim();
  container.innerHTML =
    '<div class="loading-box" style="padding:20px"><div class="spinner"></div><p>Szukam ofert w popularnych serwisach…</p></div>';

  try {
    const res = await fetch("/api/search-jobs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        filename: currentFilename,
        job_description: jobDescription,
      }),
    });
    const data = await res.json();
    if (!data.success) {
      container.innerHTML = `<div class="error-box"><span>❌</span><p>${escapeHtml(data.error || "Błąd wyszukiwania")}</p></div>`;
      return;
    }

    const jobs = data.jobs || [];
    if (!jobs.length) {
      container.innerHTML =
        '<p class="job-search-hint">Brak wyników. Spróbuj dodać bardziej szczegółową treść ogłoszenia.</p>';
      return;
    }

    container.innerHTML = jobs
      .map(
        (job) => `
      <div class="job-result-card">
        <a class="job-result-title" href="${escapeHtml(job.url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(job.title)}</a>
        <div class="job-result-meta">${escapeHtml(job.source)} · ${escapeHtml(job.domain || "")}</div>
        <div class="job-result-snippet">${escapeHtml(job.snippet || "")}</div>
      </div>
    `,
      )
      .join("");
  } catch (e) {
    container.innerHTML =
      '<div class="error-box"><span>❌</span><p>Błąd połączenia podczas wyszukiwania ofert.</p></div>';
  }
}

async function improveCurrentCV() {
  const box = document.getElementById("improveCvResult");
  if (!box) return;
  if (!currentFilename) {
    showToast("Najpierw wgraj CV", "warning");
    return;
  }

  const jobDescription = (
    document.getElementById("jobDescriptionInput")?.value || ""
  ).trim();
  const outputFormat = (
    document.getElementById("improveFormatSelect")?.value || ""
  ).trim();
  box.innerHTML =
    '<div class="loading-box" style="padding:20px"><div class="spinner"></div><p>Aktualizuję CV…</p></div>';

  try {
    const res = await fetch("/api/improve-cv", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        filename: currentFilename,
        job_description: jobDescription,
        output_format: outputFormat,
      }),
    });
    const data = await res.json();
    if (!data.success) {
      box.innerHTML = `<div class="error-box"><span>❌</span><p>${escapeHtml(data.error || "Błąd aktualizacji")}</p></div>`;
      return;
    }

    const fmt = (data.output_format || "").toUpperCase() || "PLIK";
    box.innerHTML = `
      <div class="summary-overview">Wygenerowano poprawioną wersję CV.</div>
      <div class="job-search-row" style="margin-top:8px">
        <a class="btn btn-generate" href="/api/download/${encodeURIComponent(data.download_filename)}" download>📥 Pobierz poprawione CV (${fmt})</a>
        ${data.html_preview_url ? `<a class="btn btn-generate" href="${escapeHtml(data.html_preview_url)}" target="_blank" rel="noopener noreferrer">👁 Podgląd HTML tej próby</a>` : ""}
      </div>
      ${data.output_format === "html" ? '<div class="job-search-hint">Wybrano HTML lub Canva: pobierasz/otwierasz wersję HTML do dalszej edycji i importu.</div>' : ""}
      <pre class="improved-preview">${escapeHtml(data.improved_preview || "")}</pre>
    `;
    showToast("Poprawione CV gotowe do pobrania", "success");
  } catch (e) {
    box.innerHTML =
      '<div class="error-box"><span>❌</span><p>Błąd połączenia podczas aktualizacji CV.</p></div>';
  }
}

// ── Utilities ────────────────────────────────────────────────────────────────
function setStatus(text) {
  document.getElementById("appStatus").textContent = text;
}

function formatDate(iso) {
  if (!iso) return "-";
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString("pl-PL");
}

function formatBytes(bytes) {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function showAnalysisError(msg) {
  document.getElementById("analysisContent").innerHTML =
    `<div class="error-box"><span style="font-size:22px">❌</span><p>${escapeHtml(msg)}</p></div>`;
}

function escapeHtml(str) {
  return String(str)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function copyText(text) {
  navigator.clipboard
    .writeText(text)
    .then(() => showToast("Skopiowano do schowka!", "success"))
    .catch(() => showToast("Nie udało się skopiować", "error"));
}

function showToast(msg, type = "info") {
  const t = document.getElementById("toast");
  t.textContent = msg;
  t.className = `toast toast-${type}`;
  t.classList.remove("hidden");
  clearTimeout(t._timer);
  t._timer = setTimeout(() => t.classList.add("hidden"), 3500);
}

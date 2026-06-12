from collections import defaultdict
from pathlib import Path


def extract_text(filepath: Path) -> str:
    ext = filepath.suffix.lower()

    if ext == ".pdf":
        try:
            import pdfplumber
            text = ""
            with pdfplumber.open(str(filepath)) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            return text
        except ImportError:
            return "[ERROR: pdfplumber not installed — pip install pdfplumber]"
        except Exception as e:
            return f"[ERROR extracting PDF: {e}]"

    if ext in (".docx", ".doc"):
        try:
            from docx import Document
            doc = Document(str(filepath))
            return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
        except ImportError:
            return "[ERROR: python-docx not installed — pip install python-docx]"
        except Exception as e:
            return f"[ERROR extracting DOCX: {e}]"

    if ext == ".txt":
        try:
            return filepath.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            return f"[ERROR reading TXT: {e}]"

    return ""


def extract_pdf_layout(filepath: Path) -> list[dict]:
    import pdfplumber

    pages_layout = []
    with pdfplumber.open(str(filepath)) as pdf:
        for page in pdf.pages:
            words = page.extract_words(use_text_flow=True) or []
            line_groups = defaultdict(list)

            for word in words:
                y_key = int(round(float(word["top"]) / 3.0) * 3)
                line_groups[y_key].append(word)

            lines = []
            for y_key in sorted(line_groups.keys()):
                row = sorted(line_groups[y_key], key=lambda x: float(x["x0"]))
                text = " ".join(item["text"] for item in row).strip()
                if not text:
                    continue
                x0 = min(float(item["x0"]) for item in row)
                x1 = max(float(item["x1"]) for item in row)
                top = min(float(item["top"]) for item in row)
                bottom = max(float(item["bottom"]) for item in row)
                font_size = max(9.0, min(14.0, bottom - top + 2))
                lines.append({
                    "text": text,
                    "x": x0,
                    "top": top,
                    "width": max(50.0, x1 - x0),
                    "font_size": font_size,
                })

            pages_layout.append({
                "width": float(page.width),
                "height": float(page.height),
                "lines": lines,
            })
    return pages_layout


def extract_rich_pdf_layout(filepath: Path) -> list[dict]:
    """
    Extract rich PDF layout using PyMuPDF: filled background rects, embedded images,
    and text spans with exact position, font size, bold/italic, and color.

    Each element dict has:
      type  : "rect" | "image" | "text"
      x, top, x1, bottom  (PDF points, origin top-left)
      -- rect  : color (hex), opacity
      -- image : image_data (bytes), image_ext (str)
      -- text  : text, font_size, bold, italic, color (hex), font_family
    """
    try:
        import fitz
    except ImportError as exc:
        raise RuntimeError("PyMuPDF jest wymagany — pip install pymupdf") from exc

    def _font_family(name: str) -> str:
        n = name.lower()
        if any(x in n for x in ("arial", "helvetica")):
            return "Arial, Helvetica, sans-serif"
        if any(x in n for x in ("times", "roman")):
            return "'Times New Roman', Times, serif"
        if any(x in n for x in ("courier", "mono")):
            return "'Courier New', Courier, monospace"
        if "calibri" in n:
            return "Calibri, Arial, sans-serif"
        if "verdana" in n:
            return "Verdana, Arial, sans-serif"
        if "georgia" in n:
            return "Georgia, serif"
        return "Arial, Helvetica, sans-serif"

    pages_layout = []
    doc = fitz.open(str(filepath))

    for page_idx in range(doc.page_count):
        page = doc.load_page(page_idx)
        elements = []

        # ── Layer 1: filled background shapes ──────────────────────────────
        try:
            for drawing in page.get_drawings():
                fill = drawing.get("fill")
                if not fill:
                    continue
                r, g, b = float(fill[0]), float(fill[1]), float(fill[2])
                if r > 0.93 and g > 0.93 and b > 0.93:
                    continue
                opacity = float(drawing.get("fill_opacity") or 1.0)
                if opacity < 0.05:
                    continue
                rect = drawing.get("rect")
                if not rect:
                    continue
                rw = float(rect.x1 - rect.x0)
                rh = float(rect.y1 - rect.y0)
                if rw < 4 or rh < 1:
                    continue
                ri, gi, bi = int(r * 255), int(g * 255), int(b * 255)
                elements.append({
                    "type": "rect",
                    "x": float(rect.x0),
                    "top": float(rect.y0),
                    "x1": float(rect.x1),
                    "bottom": float(rect.y1),
                    "color": f"#{ri:02x}{gi:02x}{bi:02x}",
                    "opacity": round(opacity, 3),
                })
        except Exception:
            pass

        # ── Layer 2: embedded images (e.g. profile photo) ──────────────────
        try:
            for img_item in page.get_images(full=True):
                xref = img_item[0]
                try:
                    rects = page.get_image_rects(xref)
                    base_img = doc.extract_image(xref)
                    img_bytes = base_img.get("image", b"")
                    img_ext = base_img.get("ext", "png")
                    if img_bytes and rects:
                        ir = rects[0]
                        elements.append({
                            "type": "image",
                            "x": float(ir.x0),
                            "top": float(ir.y0),
                            "x1": float(ir.x1),
                            "bottom": float(ir.y1),
                            "image_data": img_bytes,
                            "image_ext": img_ext,
                        })
                except Exception:
                    pass
        except Exception:
            pass

        # ── Layer 3: text spans with full styling ──────────────────────────
        text_dict = page.get_text("dict")
        for block in text_dict.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                for span in line.get("spans", []):
                    text = span.get("text", "")
                    if not text.strip():
                        continue
                    bbox = span.get("bbox", (0, 0, 0, 0))
                    span_flags = span.get("flags", 0)
                    color_int = span.get("color", 0)
                    cr = (color_int >> 16) & 0xFF
                    cg = (color_int >> 8) & 0xFF
                    cb = color_int & 0xFF
                    elements.append({
                        "type": "text",
                        "text": text,
                        "x": float(bbox[0]),
                        "top": float(bbox[1]),
                        "x1": float(bbox[2]),
                        "bottom": float(bbox[3]),
                        "font_size": float(span.get("size", 11)),
                        "bold": bool(span_flags & 16),
                        "italic": bool(span_flags & 2),
                        "color": f"#{cr:02x}{cg:02x}{cb:02x}",
                        "font_family": _font_family(span.get("font", "")),
                    })

        pages_layout.append({
            "width": float(page.rect.width),
            "height": float(page.rect.height),
            "elements": elements,
        })

    doc.close()
    return pages_layout

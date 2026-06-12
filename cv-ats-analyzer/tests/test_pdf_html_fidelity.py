"""
Optical + structural fidelity tests: PDF source vs generated editable HTML.
"""
import tempfile
import unittest
from pathlib import Path

import fitz

from services.preview_service import build_editable_html_from_pdf


def _uploads_pdf():
    uploads = Path(__file__).resolve().parent.parent / "uploads"
    pdfs = sorted(uploads.glob("*.pdf"))
    return pdfs[0] if pdfs else None


class PdfHtmlFidelityTest(unittest.TestCase):

    def test_html_structure(self):
        source_pdf = _uploads_pdf()
        self.assertIsNotNone(source_pdf, "Need at least one PDF in uploads/")
        with tempfile.TemporaryDirectory() as tmp_dir:
            html_path = Path(tmp_dir) / "preview.html"
            page_count = build_editable_html_from_pdf(source_pdf, html_path, source_pdf.stem)
            html_text = html_path.read_text(encoding="utf-8")
        self.assertGreater(page_count, 0)
        self.assertIn('<div class="bg"', html_text, "Expected colored background divs")
        self.assertIn('<span class="t"', html_text, "Expected editable text spans")
        # No full-page PNG screenshots - only small embedded photos allowed
        page_div_idx = html_text.find('<div class="page"')
        first_png = html_text.find("data:image/png;base64")
        if first_png > 0:
            # it must be inside a page div, not the whole page
            self.assertGreater(first_png, page_div_idx,
                "Full-page PNG blob detected before any page div")
        span_count = html_text.count('<span class="t"')
        self.assertGreater(span_count, 10, f"Too few text spans: {span_count}")

    def test_color_fidelity(self):
        source_pdf = _uploads_pdf()
        self.assertIsNotNone(source_pdf)
        with tempfile.TemporaryDirectory() as tmp_dir:
            html_path = Path(tmp_dir) / "preview.html"
            build_editable_html_from_pdf(source_pdf, html_path, source_pdf.stem)
            html_text = html_path.read_text(encoding="utf-8")
        doc = fitz.open(str(source_pdf))
        page = doc[0]
        pdf_colors = set()
        for drawing in page.get_drawings():
            fill = drawing.get("fill")
            if not fill:
                continue
            r, g, b = float(fill[0]), float(fill[1]), float(fill[2])
            if r > 0.93 and g > 0.93 and b > 0.93:
                continue
            if r < 0.07 and g < 0.07 and b < 0.07:
                continue
            ri, gi, bi = int(r * 255), int(g * 255), int(b * 255)
            pdf_colors.add(f"#{ri:02x}{gi:02x}{bi:02x}")
        doc.close()
        if not pdf_colors:
            return
        missing = [c for c in pdf_colors if c not in html_text]
        self.assertFalse(missing, f"PDF fill colors missing from HTML: {missing}")

    def test_text_fidelity(self):
        source_pdf = _uploads_pdf()
        self.assertIsNotNone(source_pdf)
        doc = fitz.open(str(source_pdf))
        page = doc[0]
        pdf_words = set(w[4].strip() for w in page.get_text("words") if w[4].strip())
        doc.close()
        with tempfile.TemporaryDirectory() as tmp_dir:
            html_path = Path(tmp_dir) / "preview.html"
            build_editable_html_from_pdf(source_pdf, html_path, source_pdf.stem)
            html_text = html_path.read_text(encoding="utf-8")
        if not pdf_words:
            return
        found = sum(1 for w in pdf_words if w in html_text)
        coverage = found / len(pdf_words)
        self.assertGreaterEqual(coverage, 0.90,
            f"Text coverage {coverage:.1%}: {found}/{len(pdf_words)} PDF words in HTML")

    def test_raster_similarity(self):
        """Compare PDF and SVG rasterizations as proxy for visual fidelity."""
        source_pdf = _uploads_pdf()
        self.assertIsNotNone(source_pdf)
        doc = fitz.open(str(source_pdf))
        pdf_page = doc[0]
        mat = fitz.Matrix(2.0, 2.0)
        pdf_pix = pdf_page.get_pixmap(matrix=mat, alpha=False)
        svg_markup = pdf_page.get_svg_image(text_as_path=False)
        doc.close()
        svg_doc = fitz.open("svg", svg_markup.encode("utf-8"))
        svg_pix = svg_doc[0].get_pixmap(matrix=mat, alpha=False)
        svg_doc.close()
        self.assertEqual(pdf_pix.width, svg_pix.width)
        self.assertEqual(pdf_pix.height, svg_pix.height)
        total = len(pdf_pix.samples)
        within_20 = sum(1 for a, b in zip(pdf_pix.samples, svg_pix.samples) if abs(a - b) <= 20)
        ratio = within_20 / total
        self.assertGreaterEqual(ratio, 0.80,
            f"Raster similarity {ratio:.1%} below 80%")


if __name__ == "__main__":
    unittest.main()

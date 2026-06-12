from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
UPLOAD_DIR = BASE_DIR / "uploads"
GENERATED_DIR = BASE_DIR / "generated"
HTML_PREVIEW_DIR = GENERATED_DIR / "html-previews"
CONVERSION_ASSETS_DIR = GENERATED_DIR / "conversion-assets"
EXTRACTED_IMAGES_DIR = GENERATED_DIR / "extracted-images"

ALLOWED_EXTENSIONS = {".pdf", ".docx", ".doc", ".txt", ".jpg", ".jpeg", ".png"}


def ensure_directories() -> None:
    UPLOAD_DIR.mkdir(exist_ok=True)
    GENERATED_DIR.mkdir(exist_ok=True)
    HTML_PREVIEW_DIR.mkdir(parents=True, exist_ok=True)
    CONVERSION_ASSETS_DIR.mkdir(parents=True, exist_ok=True)
    EXTRACTED_IMAGES_DIR.mkdir(parents=True, exist_ok=True)

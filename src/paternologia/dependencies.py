# ABOUTME: Shared dependencies for Paternologia FastAPI application.
# ABOUTME: Provides storage and templates instances for dependency injection.

from pathlib import Path

from fastapi.templating import Jinja2Templates

from paternologia.storage import Storage

BASE_DIR = Path(__file__).resolve().parent.parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
DATA_DIR = BASE_DIR / "data"

_storage: Storage | None = None
_templates: Jinja2Templates | None = None


def get_storage() -> Storage:
    """Get or create storage instance."""
    global _storage
    if _storage is None:
        _storage = Storage(data_dir=DATA_DIR)
        _storage._ensure_dirs()
    return _storage


def get_templates() -> Jinja2Templates:
    """Get or create templates instance."""
    global _templates
    if _templates is None:
        _templates = Jinja2Templates(directory=TEMPLATES_DIR)
    return _templates

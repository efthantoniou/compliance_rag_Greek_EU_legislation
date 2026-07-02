import sys
from pathlib import Path

_REPO_ROOT = str(Path(__file__).resolve().parent.parent)


def repo_root_on_path() -> None:
    """Ensure the repo root (where config.py etc. live) is importable."""
    if _REPO_ROOT not in sys.path:
        sys.path.insert(0, _REPO_ROOT)

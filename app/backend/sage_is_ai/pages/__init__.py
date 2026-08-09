"""No-build server-rendered pages. See router.py for why they exist."""

from pathlib import Path

# Islands and the shared stylesheet. They live beside the routes that reference
# them rather than in the frontend build output, because nothing here is built.
ASSETS_DIR = Path(__file__).parent / "assets"

__all__ = ["ASSETS_DIR"]

from pathlib import Path

# --- Core Library Structure ---
LIBRARY_DIR = Path("./WebParts.lplib")
WEBPARTS_DIR = LIBRARY_DIR / "webparts"
PKG_DIR = LIBRARY_DIR / "pkg"
SYM_DIR = LIBRARY_DIR / "sym"
CMP_DIR = LIBRARY_DIR / "cmp"
DEV_DIR = LIBRARY_DIR / "dev"

# --- Standard Filenames ---
FILENAME_HERO_IMAGE = "hero.png"
FILENAME_CONVERSION_LOG = "conversion.log"
FILENAME_PACKAGE_LP = "package.lp"
FILENAME_SYMBOL_LP = "symbol.lp"
FILENAME_PART_MANIFEST = "part.wp"
FILENAME_SOURCE_JSON = "source.json"
FILENAME_FOOTPRINT_WP = "footprint.wp" # Example for element manifests

# --- Status & Workflow ---
STATUS_APPROVED = "approved"
STATUS_NEEDS_REVIEW = "needs_review"
STATUS_ERROR = "error"
STATUS_UNAVAILABLE = "unavailable"

STATUS_ICON_MAP = {
    STATUS_APPROVED: "✔",
    STATUS_NEEDS_REVIEW: "⏳",
    STATUS_ERROR: "✘",
    STATUS_UNAVAILABLE: "❓",
}

# Maps UI workflow step names to the internal element type names
WORKFLOW_MAPPING = {
    'footprint': 'pkg',
    'symbol': 'sym',
    'assembly': 'cmp',
    'finalize': 'dev',
}

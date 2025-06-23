from enum import Enum
from pathlib import Path

# --- Core Library Structure ---
LIBRARY_DIR = Path("./WebParts.lplib")
WEBPARTS_DIR = LIBRARY_DIR / "webparts"
CACHE_DIR = Path("image_cache")


# --- WebParts Internal Filenames ---
class WebPartsFilename(Enum):
    """Filenames used internally by the WebParts application."""

    HERO_IMAGE = "hero.png"
    CONVERSION_LOG = "conversion.log"
    PART_MANIFEST = "part.wp"
    SOURCE_JSON = "source.json"
    FOOTPRINT_MANIFEST = "footprint.wp"
    FOOTPRINT_PNG = "footprint.png"
    SYMBOL_PNG = "symbol.png"
    FOOTPRINT_SVG = "footprint.svg"
    SYMBOL_SVG = "symbol.svg"
    RENDERED_SVG = "rendered.svg"
    RENDERED_PNG = "rendered.png"

# --- Status & Workflow ---
WORKFLOW_MAPPING = {
    'footprint': 'footprint',
    'symbol': 'symbol',
    'assembly': 'component',
    'finalize': 'device',
}

# --- API & Network ---
USER_AGENT = "WebParts v0.1"


# --- UI Text ---
class UIText(Enum):
    LOADING = "Loading..."
    NO_IMAGE = "No Image"
    IMAGE_NOT_AVAILABLE = "Image Not Available"
    SELECT_PART = "Select a part to view details"


# --- Executables ---
LIBREPCB_CLI_PATH = "/Users/fred/LibrePCB/build/apps/librepcb-cli/librepcb-cli.app/Contents/MacOS/librepcb-cli"

# --- Default Metadata ---
DEFAULT_VERSION = "0.1"
DEFAULT_AUTHOR = "Fred Turkington"

IMAGE_DIMENSIONS = 3200

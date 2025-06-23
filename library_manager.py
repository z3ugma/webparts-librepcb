import logging
import json
import shutil
from pathlib import Path
from typing import Dict, Optional, Union

from PySide6.QtCore import QObject, Signal

from models.library_part import LibraryPart
from models.search_result import SearchResult
from models.status import StatusValue
from models.elements import LibrePCBElement
from constants import WebPartsFilename, WEBPARTS_DIR
from workers.footprint_converter import generate_footprint

logger = logging.getLogger(__name__)


class LibraryManager(QObject):
    """A class to manage all library operations."""

    addPartFinished = Signal(object)  # Will emit LibraryPart or None

    def __init__(self, parent=None):
        """Initializes the LibraryManager."""
        super().__init__(parent)

    def setup_conversion_logging(self, part_uuid: str) -> Optional[logging.FileHandler]:
        """
        Creates a dedicated log file for a conversion process.
        """
        if not part_uuid:
            return None
        log_dir = WEBPARTS_DIR / part_uuid
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file_path = log_dir / WebPartsFilename.CONVERSION_LOG.value
        file_handler = logging.FileHandler(log_file_path, mode="w", encoding="utf-8")
        formatter = logging.Formatter(
            "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
        )
        file_handler.setFormatter(formatter)
        logging.getLogger().addHandler(file_handler)
        logger.info(f"Conversion log started at: {log_file_path}")
        return file_handler

    def cleanup_conversion_logging(self, handler: Optional[logging.FileHandler]):
        """Removes and closes a specific log handler."""
        if handler:
            logger.info("Ending conversion log.")
            handler.close()
            logging.getLogger().removeHandler(handler)

    def part_exists(self, part_uuid: str) -> bool:
        """Checks if a part manifest already exists in the library."""
        if not part_uuid:
            return False
        manifest_path = WEBPARTS_DIR / part_uuid / WebPartsFilename.PART_MANIFEST.value
        return manifest_path.exists()

    def add_part_from_search_result(self, search_result: SearchResult):
        """
        Converts a SearchResult, saves it, and emits a finished signal.
        """
        try:
            logger.info(f"Starting import of '{search_result.lcsc_id}'...")
            library_part = self._map_search_result_to_library_part(search_result)
            logger.info(f"  Mapped to Library Part UUID: {library_part.uuid}")

            part_pkg_dir = LibrePCBElement.PACKAGE.dir / library_part.footprint.uuid

            logger.info("Creating library directories...")
            (WEBPARTS_DIR / library_part.uuid).mkdir(parents=True, exist_ok=True)
            part_pkg_dir.mkdir(parents=True, exist_ok=True)
            part_sym_dir = LibrePCBElement.SYMBOL.dir / library_part.symbol.uuid
            part_sym_dir.mkdir(parents=True, exist_ok=True)
            logger.info("  OK.")

            logger.info("Copying assets...")
            self._copy_assets_and_get_new_paths(
                search_result,
                part_pkg_dir,
                part_sym_dir,
                (WEBPARTS_DIR / library_part.uuid),
            )
            logger.info("  OK.")

            logger.info("Saving footprint source JSON...")
            self._save_footprint_source_json(search_result, part_pkg_dir)
            logger.info("  OK.")

            logger.info("Saving symbol source JSON...")
            self._save_symbol_source_json(search_result, part_sym_dir)
            logger.info("  OK.")

            logger.info("--- Starting Footprint Generation ---")
            if generate_footprint(search_result.raw_cad_data, str(part_pkg_dir)):
                logger.info("--- Footprint Generation Succeeded ---")
            else:
                logger.error("--- Footprint Generation Failed ---")

            logger.info("Creating manifests...")
            self._create_manifests(library_part, part_pkg_dir)
            logger.info("  OK.")

            logger.info("Hydrating final asset paths...")
            self._hydrate_asset_paths(library_part)
            logger.info("  OK.")

            logger.info("\nImport complete.")
            self.addPartFinished.emit(library_part)
        except Exception as e:
            logger.error(f"\n[ERROR] An exception occurred: {e}", exc_info=True)
            self.addPartFinished.emit(None)

    def get_all_parts(self) -> list[LibraryPart]:
        """Scans the library and returns a list of all parts."""
        parts = []
        if not WEBPARTS_DIR.exists():
            return parts

        for part_dir in WEBPARTS_DIR.iterdir():
            if part_dir.is_dir():
                manifest_path = part_dir / WebPartsFilename.PART_MANIFEST.value
                if manifest_path.exists():
                    try:
                        with open(manifest_path, "r") as f:
                            part_data = json.load(f)
                            part = LibraryPart.model_validate(part_data)

                            # Status is determined ONLY from individual element manifests
                            # to maintain single source of truth
                            part.status.footprint = self._get_element_status(
                                LibrePCBElement.PACKAGE, part.footprint.uuid
                            )
                            part.status.symbol = self._get_element_status(
                                LibrePCBElement.SYMBOL, part.symbol.uuid
                            )
                            part.status.component = self._get_element_status(
                                LibrePCBElement.COMPONENT, part.component.uuid
                            )
                            part.status.device = self._get_element_status(
                                LibrePCBElement.DEVICE, part.uuid
                            )

                            # Hydrate asset paths
                            self._hydrate_asset_paths(part)

                            parts.append(part)
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.error(
                            f"❌ Failed to load part from {manifest_path}: {e}"
                        )

        return parts

    def _hydrate_asset_paths(self, part: LibraryPart):
        """
        Dynamically constructs and adds absolute paths for a part's assets.
        """
        # Hero image
        hero_image_path = WEBPARTS_DIR / part.uuid / WebPartsFilename.HERO_IMAGE.value
        if hero_image_path.exists():
            part.image.url = str(hero_image_path.resolve())

        # Symbol images
        if part.symbol and part.symbol.uuid:
            sym_dir = LibrePCBElement.SYMBOL.dir / part.symbol.uuid
            symbol_png_path = sym_dir / WebPartsFilename.SYMBOL_PNG.value
            symbol_svg_path = sym_dir / WebPartsFilename.SYMBOL_SVG.value
            if symbol_png_path.exists():
                part.symbol.png_path = str(symbol_png_path.resolve())
            if symbol_svg_path.exists():
                part.symbol.svg_path = str(symbol_svg_path.resolve())

        # Footprint images
        if part.footprint and part.footprint.uuid:
            pkg_dir = LibrePCBElement.PACKAGE.dir / part.footprint.uuid
            footprint_png_path = pkg_dir / WebPartsFilename.FOOTPRINT_PNG.value
            footprint_svg_path = pkg_dir / WebPartsFilename.FOOTPRINT_SVG.value
            if footprint_png_path.exists():
                part.footprint.png_path = str(footprint_png_path.resolve())
            if footprint_svg_path.exists():
                part.footprint.svg_path = str(footprint_svg_path.resolve())

    def _get_element_status(
        self, element: LibrePCBElement, element_uuid: str
    ) -> StatusValue:
        """Reads the status from a given element's .wp manifest."""
        if not element_uuid:
            return StatusValue.UNAVAILABLE

        # Use the new helper properties to get paths
        lp_path = element.get_lp_path(element_uuid)
        wp_path = element.get_wp_path(element_uuid)

        if not wp_path.exists():
            # If the .wp file doesn't exist, but the .lp file does, it's an error.
            if lp_path.exists():
                return StatusValue.ERROR
            # If neither exist, it's simply unavailable.
            return StatusValue.UNAVAILABLE

        # If the .wp manifest exists, but the .lp file doesn't, it needs review.
        if not lp_path.exists():
            return StatusValue.NEEDS_REVIEW

        try:
            with open(wp_path, "r") as f:
                data = json.load(f)
                status_value = data.get("status", "unknown")
                return StatusValue(status_value)
        except (json.JSONDecodeError, IOError, ValueError) as e:
            logger.error(f"Error reading status manifest {wp_path}: {e}")
            return StatusValue.ERROR

    def _map_search_result_to_library_part(
        self, search_result: SearchResult
    ) -> LibraryPart:
        """Performs a one-way mapping from a search result to a library part."""
        search_dict = search_result.model_dump()
        if not search_dict.get("uuid"):
            search_dict["uuid"] = (
                search_result.uuid or f"search-{search_result.lcsc_id}"
            )
        return LibraryPart.model_validate(search_dict)

    def _copy_assets_and_get_new_paths(
        self,
        search_result: SearchResult,
        pkg_dir: Path,
        sym_dir: Path,
        webparts_dir: Path,
    ) -> Dict[str, str]:
        """Copies assets and returns a dict of the new, permanent paths."""
        new_paths = {}
        # Footprint assets
        if search_result.footprint_png_cache_path:
            new_paths["footprint_png_cache_path"] = self._copy_asset(
                search_result.footprint_png_cache_path,
                pkg_dir,
                WebPartsFilename.FOOTPRINT_PNG.value,
            )
        if search_result.footprint_svg_cache_path:
            self._copy_asset(
                search_result.footprint_svg_cache_path,
                pkg_dir,
                WebPartsFilename.FOOTPRINT_SVG.value,
            )
        # Symbol assets
        if search_result.symbol_png_cache_path:
            new_paths["symbol_png_cache_path"] = self._copy_asset(
                search_result.symbol_png_cache_path,
                sym_dir,
                WebPartsFilename.SYMBOL_PNG.value,
            )
        if search_result.symbol_svg_cache_path:
            self._copy_asset(
                search_result.symbol_svg_cache_path,
                sym_dir,
                WebPartsFilename.SYMBOL_SVG.value,
            )
        # Other assets
        if search_result.hero_image_cache_path:
            new_paths["hero_image_cache_path"] = self._copy_asset(
                search_result.hero_image_cache_path,
                webparts_dir,
                WebPartsFilename.HERO_IMAGE.value,
            )
        return new_paths

    def _save_footprint_source_json(self, search_result: SearchResult, pkg_dir: Path):
        """Saves the packageDetail portion of the raw CAD data."""
        if search_result.raw_cad_data:
            if package_detail := search_result.raw_cad_data.get("packageDetail"):
                source_json_path = pkg_dir / WebPartsFilename.SOURCE_JSON.value
                with open(source_json_path, "w") as f:
                    json.dump(package_detail, f, indent=2)

    def _save_symbol_source_json(self, search_result: SearchResult, sym_dir: Path):
        """Saves the symbol portion of the raw CAD data."""
        if search_result.raw_cad_data:
            if symbol_detail := search_result.raw_cad_data.get("dataStr"):
                source_json_path = sym_dir / WebPartsFilename.SOURCE_JSON.value
                with open(source_json_path, "w") as f:
                    json.dump(symbol_detail, f, indent=2)

    def _copy_asset(self, src_path_str: str, dest_dir: Path, dest_filename: str) -> str:
        """Copies a single asset from cache to library and returns its new path."""
        src_path = Path(src_path_str)
        if src_path.exists():
            dest_path = dest_dir / dest_filename
            shutil.copy2(src_path, dest_path)
            return str(dest_path.resolve())
        return src_path_str

    def _create_manifests(self, library_part: LibraryPart, pkg_dir: Path):
        """Creates the central part.wp and element manifests."""
        manifest_dir = WEBPARTS_DIR / library_part.uuid
        manifest_path = manifest_dir / WebPartsFilename.PART_MANIFEST.value
        with open(manifest_path, "w") as f:
            f.write(library_part.model_dump_json(indent=2))

        def create_element_manifest(element: LibrePCBElement, uuid: str):
            manifest_path = element.get_wp_path(uuid)
            manifest_data = {
                "version": 1,
                "status": StatusValue.NEEDS_REVIEW.value,
                "validation": {"errors": [], "warnings": []},
            }
            with open(manifest_path, "w") as f:
                json.dump(manifest_data, f, indent=2)

        create_element_manifest(LibrePCBElement.PACKAGE, library_part.footprint.uuid)
        create_element_manifest(LibrePCBElement.SYMBOL, library_part.symbol.uuid)

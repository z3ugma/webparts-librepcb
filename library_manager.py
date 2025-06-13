import json
import logging
import shutil
from pathlib import Path
from typing import Dict, Optional

from PySide6.QtCore import QObject, Signal

from models.library_part import LibraryPart
from models.search_result import SearchResult

LIBRARY_DIR = Path("./WebParts.lplib")
logger = logging.getLogger(__name__)


class LibraryManager(QObject):
    """A class to manage all library operations."""

    addPartFinished = Signal(object)  # Will emit LibraryPart or None

    def __init__(self, library_path: Path = LIBRARY_DIR, parent=None):
        """Initializes the LibraryManager."""
        super().__init__(parent)
        self.library_path = library_path
        self.webparts_dir = self.library_path / "webparts"
        self.pkg_dir = self.library_path / "pkg"

    def setup_conversion_logging(self, part_uuid: str) -> Optional[logging.FileHandler]:
        """
        Creates a dedicated log file for a conversion process.

        Args:
            part_uuid: The UUID of the part being converted.

        Returns:
            The configured FileHandler, or None if the UUID is invalid.
        """
        if not part_uuid:
            return None

        log_dir = self.webparts_dir / part_uuid
        log_dir.mkdir(parents=True, exist_ok=True)
        log_file_path = log_dir / "conversion.log"

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
        manifest_path = self.webparts_dir / part_uuid / "part.wp"
        return manifest_path.exists()

    def add_part_from_search_result(self, search_result: SearchResult):
        """
        Converts a SearchResult, saves it, and emits a finished signal.
        """
        try:
            logger.info(f"Starting import of '{search_result.lcsc_id}'...")
            library_part = self._map_search_result_to_library_part(search_result)
            logger.info(f"  Mapped to Library Part UUID: {library_part.uuid}")

            part_webparts_dir = self.webparts_dir / library_part.uuid
            part_pkg_dir = self.pkg_dir / library_part.footprint.uuid

            logger.info("Creating library directories...")
            part_webparts_dir.mkdir(parents=True, exist_ok=True)
            part_pkg_dir.mkdir(parents=True, exist_ok=True)
            logger.info("  OK.")

            logger.info("Copying assets...")
            self._copy_assets_and_get_new_paths(
                search_result, part_pkg_dir, part_webparts_dir
            )
            logger.info("  OK.")

            logger.info("Saving footprint source JSON...")
            self._save_footprint_source_json(search_result, part_pkg_dir)
            logger.info("  OK.")

            logger.info("Creating manifests...")
            self._create_manifests(library_part, part_pkg_dir)
            logger.info("  OK.")

            logger.info("\nImport complete.")
            self.addPartFinished.emit(library_part)
        except Exception as e:
            logger.error(f"\n[ERROR] An exception occurred: {e}", exc_info=True)
            self.addPartFinished.emit(None)

    def get_all_parts(self) -> list[LibraryPart]:
        """Scans the library and returns a list of all parts."""
        parts = []
        if not self.webparts_dir.exists():
            return parts

        for part_dir in self.webparts_dir.iterdir():
            if part_dir.is_dir():
                manifest_path = part_dir / "part.wp"
                if manifest_path.exists():
                    try:
                        with open(manifest_path, "r") as f:
                            part_data = json.load(f)
                            part = LibraryPart.model_validate(part_data)

                            part.status.footprint = self._get_element_status(
                                "pkg", part.footprint.uuid, "footprint"
                            )
                            part.status.symbol = self._get_element_status(
                                "sym", part.symbol.uuid, "symbol"
                            )
                            part.status.component = self._get_element_status(
                                "cmp", part.component.uuid, "component"
                            )
                            part.status.device = self._get_element_status(
                                "dev", part.uuid, "device"
                            )

                            parts.append(part)
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.error(
                            f"Error loading part manifest {manifest_path}: {e}"
                        )
        return parts

    def _get_element_status(
        self, element_dir_name: str, element_uuid: str, element_type: str
    ) -> str:
        """Reads the status from a given element's .wp manifest."""
        if not element_uuid:
            return "unavailable"

        element_dir = self.library_path / element_dir_name / element_uuid
        manifest_path = element_dir / f"{element_uuid}.{element_type}.wp"

        if not manifest_path.exists():
            return "needs_review"

        try:
            with open(manifest_path, "r") as f:
                data = json.load(f)
                return data.get("status", "unknown")
        except (json.JSONDecodeError, IOError):
            return "error"

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
        self, search_result: SearchResult, pkg_dir: Path, webparts_dir: Path
    ) -> Dict[str, str]:
        """Copies assets and returns a dict of the new, permanent paths."""
        new_paths = {}
        if search_result.footprint_png_cache_path:
            new_paths["footprint_png_cache_path"] = self._copy_asset(
                search_result.footprint_png_cache_path, pkg_dir, "footprint.png"
            )
        if search_result.footprint_svg_cache_path:
            self._copy_asset(
                search_result.footprint_svg_cache_path, pkg_dir, "footprint.svg"
            )
        if search_result.hero_image_cache_path:
            new_paths["hero_image_cache_path"] = self._copy_asset(
                search_result.hero_image_cache_path, webparts_dir, "hero.png"
            )
        return new_paths

    def _save_footprint_source_json(self, search_result: SearchResult, pkg_dir: Path):
        """Saves the packageDetail portion of the raw CAD data."""
        if search_result.raw_cad_data:
            if package_detail := search_result.raw_cad_data.get("packageDetail"):
                source_json_path = pkg_dir / "source.json"
                with open(source_json_path, "w") as f:
                    json.dump(package_detail, f, indent=2)

    def _copy_asset(self, src_path_str: str, dest_dir: Path, dest_filename: str) -> str:
        """Copies a single asset from cache to library and returns its new path."""
        src_path = Path(src_path_str)
        if src_path.exists():
            dest_path = dest_dir / dest_filename
            shutil.copy2(src_path, dest_path)
            return str(dest_path.resolve())
        return src_path_str

    def _create_manifests(self, library_part: LibraryPart, pkg_dir: Path):
        """Creates the central part.wp and the footprint element manifest."""
        manifest_dir = self.webparts_dir / library_part.uuid
        manifest_path = manifest_dir / "part.wp"
        with open(manifest_path, "w") as f:
            f.write(library_part.model_dump_json(indent=2))

        footprint_manifest_path = (
            pkg_dir / f"{library_part.footprint.uuid}.footprint.wp"
        )
        footprint_manifest = {
            "version": 1,
            "status": "needs_review",
            "validation": {"errors": [], "warnings": []},
        }
        with open(footprint_manifest_path, "w") as f:
            json.dump(footprint_manifest, f, indent=2)

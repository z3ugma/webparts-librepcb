"""
Manages the local WebParts.lplib library.

This module is responsible for converting SearchResult objects into permanent
LibraryPart objects and saving them to the .lplib directory structure.
"""

import json
import shutil
from pathlib import Path
from typing import Dict

from models.library_part import LibraryPart
from models.search_result import SearchResult

LIBRARY_DIR = Path("./WebParts.lplib")


class LibraryManager:
    """A class to manage all library operations."""

    def __init__(self, library_path: Path = LIBRARY_DIR):
        """Initializes the LibraryManager."""
        self.library_path = library_path
        self.webparts_dir = self.library_path / "webparts"
        self.pkg_dir = self.library_path / "pkg"

    def part_exists(self, part_uuid: str) -> bool:
        """Checks if a part manifest already exists in the library."""
        if not part_uuid:
            return False
        manifest_path = self.webparts_dir / part_uuid / "part.wp"
        return manifest_path.exists()

    def add_part_from_search_result(self, search_result: SearchResult) -> LibraryPart:
        """
        Converts a SearchResult, saves it, and returns the LibraryPart object.
        """
        library_part = self._map_search_result_to_library_part(search_result)

        part_webparts_dir = self.webparts_dir / library_part.uuid
        part_pkg_dir = self.pkg_dir / library_part.footprint.uuid
        
        part_webparts_dir.mkdir(parents=True, exist_ok=True)
        part_pkg_dir.mkdir(parents=True, exist_ok=True)

        new_paths = self._copy_assets_and_get_new_paths(search_result, part_pkg_dir, part_webparts_dir)
        self._save_footprint_source_json(search_result, part_pkg_dir)
        self._create_manifests(library_part, part_pkg_dir)

        print(f"Successfully added part {library_part.lcsc_id} to library.")
        return library_part

    def _map_search_result_to_library_part(self, search_result: SearchResult) -> LibraryPart:
        """Performs a one-way mapping from a search result to a library part."""
        return LibraryPart.model_validate(search_result.model_dump())

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
            new_paths["footprint_svg_cache_path"] = self._copy_asset(
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

        footprint_manifest_path = pkg_dir / f"{library_part.footprint.uuid}.footprint.wp"
        footprint_manifest = {
            "version": 1,
            "status": "needs_review",
            "validation": {"errors": [], "warnings": []},
        }
        with open(footprint_manifest_path, "w") as f:
            json.dump(footprint_manifest, f, indent=2)

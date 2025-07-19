import copy
import json
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Optional

from PySide6.QtCore import QObject

from constants import WEBPARTS_DIR, WebPartsFilename
from models.elements import LibrePCBElement
from models.library_part import LibraryPart
from models.search_result import SearchResult
from models.status import (
    ElementManifest,
    StatusValue,
    ValidationMessage,
    ValidationSource,
)

logger = logging.getLogger(__name__)


class LibraryManager(QObject):
    """A class to manage all library operations."""

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
        # Use a temporary part object to get the manifest path
        temp_part = LibraryPart(
            uuid=part_uuid,
            vendor="",
            part_name="",
            lcsc_id="",
            manufacturer="",
            mfr_part_number="",
            description="",
            full_description="",
        )
        manifest_path = temp_part.manifest_path
        return manifest_path.exists()

    def add_part_from_search_result(self, search_result: SearchResult):
        """
        Adds a new part to the library based on a search result.
        """
        try:
            from workers.element_renderer import render_and_check_element
            from workers.footprint_converter import process_footprint_complete
            from workers.symbol_converter import generate_symbol

            logger.info(f"Starting import of '{search_result.lcsc_id}'...")
            library_part = self._map_search_result_to_library_part(search_result)

            # --- Create Directories ---
            library_part.create_library_dirs()
            logger.info(f"Created library directories for part {library_part.uuid}")

            # Get directory paths from properties for later use
            part_pkg_dir = library_part.footprint.dir_path
            part_sym_dir = library_part.symbol.dir_path
            part_dir = library_part.dir_path

            # --- Save Source Data and Assets ---
            self._copy_assets_and_get_new_paths(
                search_result, part_pkg_dir, part_sym_dir, part_dir
            )
            logger.info("  OK.")

            logger.info("Saving footprint source JSON...")
            self._save_footprint_source_json(search_result, part_pkg_dir)
            logger.info("  OK.")

            logger.info("Saving symbol source JSON...")
            self._save_symbol_source_json(search_result, part_sym_dir)
            logger.info("  OK.")

            # --- Process Footprint (Generate, Render, Check, Align) ---
            process_footprint_complete(
                copy.deepcopy(search_result.raw_cad_data), library_part, part_pkg_dir
            )

            # --- Process Symbol (Generate, Render, Check) ---
            logger.info("--- Starting Symbol Generation ---")
            if generate_symbol(
                copy.deepcopy(search_result.raw_cad_data), str(part_sym_dir)
            ):
                logger.info(
                    "--- Symbol Generation Succeeded, now rendering and checking ---"
                )
                _, issues = render_and_check_element(
                    library_part, LibrePCBElement.SYMBOL
                )
                self._update_element_manifest(
                    LibrePCBElement.SYMBOL, library_part.symbol.uuid, issues
                )
            else:
                logger.error("--- Symbol Generation Failed ---")

            # # --- Process Component (Generate, Render, Check) ---
            # logger.info("--- Starting Component Generation ---")
            # process_component_complete(
            #     copy.deepcopy(search_result.raw_cad_data), library_part
            # )

            # # --- Process Device (Generate, Render, Check) ---
            # logger.info("--- Starting Device Generation ---")
            # process_device_complete(
            #     copy.deepcopy(search_result.raw_cad_data), library_part
            # )

            # --- Finalize: Create Part Manifest ---
            part_manifest_path = library_part.manifest_path
            with open(part_manifest_path, "w") as f:
                f.write(library_part.model_dump_json(indent=2))

            logger.info(f"✅ Successfully added '{library_part.part_name}' to library.")
            return library_part

        except Exception as e:
            logger.error(f"❌ Failed to add part to library: {e}", exc_info=True)
            # Re-raise the exception to be caught by the worker
            raise e

    def get_all_parts(self) -> list[LibraryPart]:
        """Scans the library and returns a list of all parts."""
        parts = []
        if not WEBPARTS_DIR.exists():
            return parts

        for part_dir in WEBPARTS_DIR.iterdir():
            if part_dir.is_dir():
                # Construct the expected manifest path to check for existence
                # We need a dummy part to get the path structure
                temp_part = LibraryPart(
                    uuid=part_dir.name,
                    vendor="",
                    part_name="",
                    lcsc_id="",
                    manufacturer="",
                    mfr_part_number="",
                    description="",
                    full_description="",
                )
                manifest_path = temp_part.manifest_path
                if manifest_path.exists():
                    try:
                        with open(manifest_path, "r") as f:
                            part_data = json.load(f)
                            part = LibraryPart.model_validate(part_data)

                            # Status is determined ONLY from individual element manifests
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

                            # Hydrate remaining metadata and paths
                            self._hydrate_part_info(part)

                            parts.append(part)
                    except (json.JSONDecodeError, TypeError) as e:
                        logger.error(
                            f"❌ Failed to load part from {manifest_path}: {e}"
                        )

        return parts

    def get_part_by_uuid(self, uuid: str) -> Optional[LibraryPart]:
        """Retrieves a single, fully hydrated library part by its UUID."""
        if not uuid:
            return None

        # This is inefficient as it iterates all parts, but it's simple.
        # For a large library, a direct lookup would be better.
        all_parts = self.get_all_parts()
        for part in all_parts:
            if part.uuid == uuid:
                return part
        return None

    def _hydrate_part_info(self, part: LibraryPart):
        """
        Dynamically constructs and adds asset paths and names for a part.
        This is for parts being loaded from the library, not during creation.
        """
        # Hero image
        hero_image_path = WEBPARTS_DIR / part.uuid / WebPartsFilename.HERO_IMAGE.value
        if hero_image_path.exists():
            part.image.url = str(hero_image_path.resolve())

        # Symbol info
        if part.symbol and part.symbol.uuid:
            symbol_name = LibrePCBElement.SYMBOL.get_element_name(part.symbol.uuid)
            if symbol_name:
                part.symbol.name = symbol_name

        # Footprint info
        if part.footprint and part.footprint.uuid:
            footprint_name = LibrePCBElement.PACKAGE.get_element_name(
                part.footprint.uuid
            )
            if footprint_name:
                part.footprint.name = footprint_name

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

    def set_footprint_manifest_status(
        self, library_part: LibraryPart, new_status: StatusValue
    ) -> None:
        """Update the approval status of a footprint and save it to its manifest."""
        manifest_path = LibrePCBElement.PACKAGE.get_wp_path(library_part.footprint.uuid)
        if not manifest_path or not manifest_path.exists():
            logger.error(
                f"Manifest for footprint {library_part.footprint.uuid} not found."
            )
            return

        try:
            manifest = ElementManifest.model_validate_json(manifest_path.read_text())
            manifest.status = new_status
            manifest_path.write_text(manifest.model_dump_json(indent=2))
            logger.info(
                f"Updated footprint {library_part.footprint.uuid} status to {new_status.name}."
            )
        except Exception as e:
            logger.error(
                f"Failed to update manifest for footprint {library_part.footprint.uuid}: {e}"
            )

    def set_symbol_manifest_status(
        self, library_part: LibraryPart, new_status: StatusValue
    ) -> None:
        """Update the approval status of a symbol and save it to its manifest."""
        manifest_path = LibrePCBElement.SYMBOL.get_wp_path(library_part.symbol.uuid)
        if not manifest_path or not manifest_path.exists():
            logger.error(f"Manifest for symbol {library_part.symbol.uuid} not found.")
            return

        try:
            manifest = ElementManifest.model_validate_json(manifest_path.read_text())
            manifest.status = new_status
            manifest_path.write_text(manifest.model_dump_json(indent=2))
            logger.info(
                f"Updated symbol {library_part.symbol.uuid} status to {new_status.name}."
            )
        except Exception as e:
            logger.error(
                f"Failed to update manifest for symbol {library_part.symbol.uuid}: {e}"
            )

    def _map_search_result_to_library_part(
        self, search_result: SearchResult
    ) -> LibraryPart:
        """Performs a one-way mapping from a search result to a library part."""
        import uuid as uuid_module

        from adapters.librepcb.librepcb_uuid import create_derived_uuidv4

        search_dict = search_result.model_dump()
        if not search_dict.get("uuid"):
            search_dict["uuid"] = (
                search_result.uuid or f"search-{search_result.lcsc_id}"
            )

        # Generate UUIDs from the main part UUID
        if search_dict.get("uuid"):
            main_uuid_str = search_dict["uuid"]
            # Convert string to UUID object
            main_uuid = uuid_module.UUID(main_uuid_str)
            search_dict["component"]["uuid"] = str(
                create_derived_uuidv4(main_uuid, "component")
            )
            # Device UUID is the same as the main part UUID
            search_dict["device"]["uuid"] = main_uuid_str

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
            self._copy_asset(
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
            self._copy_asset(
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
            self._copy_asset(
                search_result.hero_image_cache_path,
                webparts_dir,
                WebPartsFilename.HERO_IMAGE.value,
            )
        if search_result.footprint_model_3d_step_cache_path:
            self._copy_asset(
                search_result.footprint_model_3d_step_cache_path,
                pkg_dir,
                f"{search_result.footprint.model_3d_uuid}.step",
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

    def _update_element_manifest(
        self, element: LibrePCBElement, uuid: str, new_issues: List[ValidationMessage]
    ):
        """
        Runs checks for an element and updates its .wp manifest file with
        reconciled validation messages.
        """
        manifest_path = element.get_wp_path(uuid)

        # Step 1: Read existing manifest
        existing_manifest = ElementManifest()
        if manifest_path.exists():
            try:
                existing_manifest = ElementManifest.model_validate_json(
                    manifest_path.read_text()
                )
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(
                    f"Could not parse existing manifest {manifest_path}: {e}"
                )

        # Step 2: Preserve internal (WebParts) messages
        preserved_webparts_messages = [
            msg
            for msg in existing_manifest.validation
            if msg.source == ValidationSource.WEBPARTS
        ]

        # Step 3: Combine preserved internal messages with all new external ones
        reconciled_messages = preserved_webparts_messages + new_issues

        # Step 4: Write updated manifest, preserving original human-set status
        new_manifest = ElementManifest(
            validation=reconciled_messages, status=existing_manifest.status
        )
        with open(manifest_path, "w") as f:
            f.write(new_manifest.model_dump_json(indent=2))
        logger.info(
            f"Updated manifest for {element.value} {uuid} with {len(reconciled_messages)} issues and status {existing_manifest.status.value}."
        )

    def update_footprint_approval_status(
        self, part: LibraryPart, msg_index: int, is_approved: bool
    ) -> None:
        """
        Handles the state change of an approval checkbox for a footprint.
        """
        manifest_path = LibrePCBElement.PACKAGE.get_wp_path(part.footprint.uuid)
        try:
            if manifest_path.exists():
                manifest = ElementManifest.model_validate_json(
                    manifest_path.read_text()
                )
            else:
                logger.error(f"Manifest not found at {manifest_path}")
                return
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse manifest {manifest_path}: {e}")
            return

        if not (0 <= msg_index < len(manifest.validation)):
            logger.error(f"Cannot update approval for invalid index {msg_index}")
            return

        manifest.validation[msg_index].is_approved = is_approved

        try:
            manifest_path.write_text(manifest.model_dump_json(indent=2))
            logger.info(
                f"Updated approval for message {msg_index} to {'Approved' if is_approved else 'Not Approved'}."
            )
        except Exception as e:
            logger.error(f"Error writing footprint manifest {manifest_path}: {e}")

    def update_symbol_approval_status(
        self, part: LibraryPart, msg_index: int, is_approved: bool
    ) -> None:
        """
        Handles the state change of an approval checkbox for a symbol.
        """
        manifest_path = LibrePCBElement.SYMBOL.get_wp_path(part.symbol.uuid)
        try:
            if manifest_path.exists():
                manifest = ElementManifest.model_validate_json(
                    manifest_path.read_text()
                )
            else:
                logger.error(f"Manifest not found at {manifest_path}")
                return
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse manifest {manifest_path}: {e}")
            return

        if not (0 <= msg_index < len(manifest.validation)):
            logger.error(f"Cannot update approval for invalid index {msg_index}")
            return

        manifest.validation[msg_index].is_approved = is_approved

        try:
            with open(manifest_path, "w") as f:
                f.write(manifest.model_dump_json(indent=2))
            logger.info(
                f"Successfully persisted symbol approval state for message {msg_index} to {is_approved}."
            )
        except IOError as e:
            logger.error(
                f"Error writing symbol manifest {manifest_path}: {e}", exc_info=True
            )

        """
        Handles the state change of an approval checkbox.
        """
        manifest_path = LibrePCBElement.PACKAGE.get_wp_path(part.footprint.uuid)
        try:
            if manifest_path.exists():
                manifest = ElementManifest.model_validate_json(
                    manifest_path.read_text()
                )
            else:
                logger.error(f"Manifest not found at {manifest_path}")
                return
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse manifest {manifest_path}: {e}")
            return

        if not (0 <= msg_index < len(manifest.validation)):
            logger.error(f"Cannot update approval for invalid index {msg_index}")
            return

        # Update the in-memory manifest
        manifest.validation[msg_index].is_approved = is_approved

        # Write the entire, updated manifest back to disk
        try:
            with open(manifest_path, "w") as f:
                f.write(manifest.model_dump_json(indent=2))
            logger.info(
                f"Successfully persisted approval state for message {msg_index} to {is_approved}."
            )
        except IOError as e:
            logger.error(f"Error writing manifest {manifest_path}: {e}", exc_info=True)

import json
import logging
import shutil
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from PySide6.QtCore import QObject, Signal

from constants import WEBPARTS_DIR, WebPartsFilename
from models.elements import LibrePCBElement
from models.library_part import LibraryPart
from models.search_result import SearchResult
from models.status import (
    ElementManifest,
    StatusValue,
    ValidationMessage,
    ValidationSeverity,
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
            from workers.footprint_converter import process_footprint_complete
            from workers.symbol_converter import generate_symbol
            from workers.element_renderer import render_and_check_element

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
                search_result.raw_cad_data, library_part, part_pkg_dir
            )

            # --- Process Symbol (Generate, Render, Check) ---
            logger.info("--- Starting Symbol Generation ---")
            if generate_symbol(search_result.raw_cad_data, str(part_sym_dir)):
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
        self, element: LibrePCBElement, uuid: str, issues: List[Tuple[str, str, int]]
    ):
        """
        Runs checks for an element and updates its .wp manifest file with
        reconciled validation messages.
        """
        manifest_path = element.get_wp_path(uuid)

        # Step 1: Read existing manifest
        existing_messages = {}
        if manifest_path.exists():
            try:
                manifest = ElementManifest.model_validate_json(
                    manifest_path.read_text()
                )
                for msg in manifest.validation:
                    existing_messages[(msg.message, msg.severity)] = msg
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning(
                    f"Could not parse existing manifest {manifest_path}: {e}"
                )

        # Step 2: Reconcile messages
        reconciled_messages = []
        for msg_text, severity_str, count in issues:
            key = (msg_text, ValidationSeverity(severity_str))

            # Create the new message object based on the latest results
            new_msg = ValidationMessage(
                message=msg_text,
                severity=key[1],
                count=count,
            )

            # If the same message existed before, check if we should preserve approval
            if key in existing_messages:
                old_msg = existing_messages[key]
                # CRUCIAL: Preserve approval ONLY if the count has NOT changed.
                if old_msg.is_approved and old_msg.count == new_msg.count:
                    new_msg.is_approved = True

            reconciled_messages.append(new_msg)

        # Step 3: Determine status - preserve existing human review status or set default
        existing_status = StatusValue.NEEDS_REVIEW  # Default for new elements
        if manifest_path.exists():
            try:
                existing_manifest = ElementManifest.model_validate_json(
                    manifest_path.read_text()
                )
                existing_status = existing_manifest.status
            except (json.JSONDecodeError, ValueError):
                pass  # Use default if can't read existing

        # Step 4: Write updated manifest (preserve human review status)
        new_manifest = ElementManifest(
            validation=reconciled_messages, status=existing_status
        )
        with open(manifest_path, "w") as f:
            f.write(new_manifest.model_dump_json(indent=2))
        logger.info(
            f"Updated manifest for {element.value} {uuid} with {len(reconciled_messages)} issues and status {existing_status.value}."
        )

    def reconcile_and_save_footprint_manifest(
        self, part: LibraryPart, issues: list
    ) -> ElementManifest:
        """
        Reconciles new issues with the existing manifest and saves it.
        Approval is invalidated if the message count changes.
        """
        manifest_path = LibrePCBElement.PACKAGE.get_wp_path(part.footprint.uuid)
        try:
            if manifest_path.exists():
                manifest = ElementManifest.model_validate_json(
                    manifest_path.read_text()
                )
            else:
                manifest = ElementManifest()
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse manifest {manifest_path}: {e}")
            manifest = ElementManifest()

        existing_messages = {
            (msg.message, msg.severity): msg for msg in manifest.validation
        }
        reconciled_messages = []

        for msg_text, severity_str, count in issues:
            key = (msg_text, ValidationSeverity(severity_str))

            # Create the new message object based on the latest results
            new_msg = ValidationMessage(
                message=msg_text,
                severity=key[1],
                count=count,
            )

            # If the same message existed before, check if we should preserve approval
            if key in existing_messages:
                old_msg = existing_messages[key]
                # CRUCIAL: Preserve approval ONLY if the count has NOT changed.
                if old_msg.is_approved and old_msg.count == new_msg.count:
                    new_msg.is_approved = True

            reconciled_messages.append(new_msg)

        manifest.validation = reconciled_messages

        try:
            with open(manifest_path, "w") as f:
                f.write(manifest.model_dump_json(indent=2))
            logger.info("Successfully persisted reconciled manifest.")
        except IOError as e:
            logger.error(f"Error writing manifest {manifest_path}: {e}", exc_info=True)
        return manifest

    def reconcile_and_save_symbol_manifest(
        self, part: LibraryPart, issues: list
    ) -> ElementManifest:
        """
        Reconciles new issues with the existing symbol manifest and saves it.
        """
        manifest_path = LibrePCBElement.SYMBOL.get_wp_path(part.symbol.uuid)
        try:
            if manifest_path.exists():
                manifest = ElementManifest.model_validate_json(
                    manifest_path.read_text()
                )
            else:
                manifest = ElementManifest()
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(f"Failed to parse manifest {manifest_path}: {e}")
            manifest = ElementManifest()

        existing_messages = {
            (msg.message, msg.severity): msg for msg in manifest.validation
        }
        reconciled_messages = []

        for msg_text, severity_str, count in issues:
            key = (msg_text, ValidationSeverity(severity_str))
            new_msg = ValidationMessage(
                message=msg_text,
                severity=key[1],
                count=count,
            )
            if key in existing_messages:
                old_msg = existing_messages[key]
                if old_msg.is_approved and old_msg.count == new_msg.count:
                    new_msg.is_approved = True
            reconciled_messages.append(new_msg)

        manifest.validation = reconciled_messages

        try:
            with open(manifest_path, "w") as f:
                f.write(manifest.model_dump_json(indent=2))
            logger.info("Successfully persisted reconciled symbol manifest.")
        except IOError as e:
            logger.error(
                f"Error writing symbol manifest {manifest_path}: {e}", exc_info=True
            )
        return manifest

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

import logging
from PySide6.QtCore import QObject, Signal, Slot, Slot, Slot, Slot, Slot, Slot

from adapters.search_engine import Vendor
from models.search_result import SearchResult

logger = logging.getLogger(__name__)

# --- UI-Facing Workers ---


class SearchWorker(QObject):
    """Handles background searching for components."""

    search_completed = Signal(list)
    search_failed = Signal(str)

    def __init__(self, api_service):
        super().__init__()
        self.api_service = api_service

    def start_search(self, vendor: Vendor, search_term: str):
        try:
            self.search_completed.emit(self.api_service.search(vendor, search_term))
        except Exception as e:
            logger.error(f"SearchWorker failed: {e}", exc_info=True)
            self.search_failed.emit(str(e))


class ImageWorker(QObject):
    """Handles background downloading of images for the UI."""

    image_loaded = Signal(bytes, str, str)
    image_failed = Signal(str, str)

    def __init__(self, api_service):
        super().__init__()
        self.api_service = api_service

    def load_image(self, vendor: Vendor, image_url: str, image_type: str):
        try:
            result = self.api_service.download_image_from_url(vendor, image_url)
            if result:
                image_data, cache_path = result
                self.image_loaded.emit(image_data, image_type, cache_path)
            else:
                self.image_failed.emit("Failed to download image", image_type)
        except Exception as e:
            logger.error(f"ImageWorker failed: {e}", exc_info=True)
            self.image_failed.emit(str(e), image_type)


class ComponentWorker(QObject):
    """Handles background fetching of full component data (hydration)."""

    hydration_completed = Signal(SearchResult)
    hydration_failed = Signal(str)

    def __init__(self, api_service):
        super().__init__()
        self.api_service = api_service

    def hydrate_search_result(self, result: SearchResult):
        try:
            self.hydration_completed.emit(
                self.api_service.get_fully_hydrated_search_result(result)
            )
        except Exception as e:
            logger.error(f"ComponentWorker failed: {e}", exc_info=True)
            self.hydration_failed.emit(str(e))

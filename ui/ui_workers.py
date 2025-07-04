# ui/ui_workers.py
import logging
from PySide6.QtCore import QObject, Signal, Slot

from models.search_result import SearchResult
from search import Search
from models.library_part import LibraryPart
from library_manager import LibraryManager
from workers.element_renderer import render_and_check_element


class ElementUpdateWorker(QObject):
    """
    A worker to refresh an element's rendered image and validation checks.
    """

    finished = Signal()
    update_complete = Signal(str, list)
    update_failed = Signal(str)

    def __init__(self, part: LibraryPart, element_type):
        super().__init__()
        self._part = part
        self._element_type = element_type

    @Slot()
    def run(self):
        """
        Performs the long-running render and check operation.
        """
        logger.info(
            f"ElementUpdateWorker started for {self._part.part_name} - {self._element_type.value}"
        )
        try:
            png_path, issues = render_and_check_element(self._part, self._element_type)
            if png_path:
                self.update_complete.emit(png_path, issues)
            else:
                # Still emit issues even if rendering fails
                self.update_complete.emit("", issues)
                self.update_failed.emit("Rendering failed, but checks may have run.")
        except Exception as e:
            logger.error(
                f"An exception occurred in ElementUpdateWorker: {e}", exc_info=True
            )
            self.update_failed.emit(str(e))
        finally:
            self.finished.emit()
            logger.info("ElementUpdateWorker finished.")


logger = logging.getLogger(__name__)


class SearchWorker(QObject):
    """
    A QObject worker for performing searches in a separate thread.
    """

    search_completed = Signal(list)
    search_failed = Signal(str)

    def __init__(self, api_service: Search):
        super().__init__()
        self._api_service = api_service

    @Slot(object, str)
    def start_search(self, vendor, search_term):
        try:
            results = self._api_service.search(vendor, search_term)
            self.search_completed.emit(results)
        except Exception as e:
            self.search_failed.emit(str(e))


class ImageWorker(QObject):
    """
    A QObject worker for loading images in a separate thread.
    """

    image_loaded = Signal(bytes, str, str)
    image_failed = Signal(str, str)

    def __init__(self, api_service: Search):
        super().__init__()
        self._api_service = api_service

    @Slot(object, str, str)
    def load_image(self, vendor, image_url, image_type):
        try:
            image_data, cache_path = self._api_service.download_image_from_url(
                vendor, image_url
            )
            self.image_loaded.emit(image_data, image_type, cache_path)
        except Exception as e:
            self.image_failed.emit(str(e), image_type)


class ComponentWorker(QObject):
    """
    A QObject worker for hydrating search results in a separate thread.
    """

    hydration_completed = Signal(object)
    hydration_failed = Signal(str)

    def __init__(self, api_service: Search):
        super().__init__()
        self._api_service = api_service

    @Slot(object)
    def hydrate_search_result(self, search_result):
        try:
            hydrated_result = self._api_service.get_fully_hydrated_search_result(
                search_result
            )
            self.hydration_completed.emit(hydrated_result)
        except Exception as e:
            self.hydration_failed.emit(str(e))


class AddPartWorker(QObject):
    """
    A QObject worker for adding a library part in a separate thread.
    """

    add_part_succeeded = Signal(LibraryPart)
    add_part_failed = Signal(str)
    log_message = Signal(str)

    def __init__(self, search_result: SearchResult):
        super().__init__()
        self._search_result = search_result
        self._manager = LibraryManager()

    @Slot()
    def run(self):
        """
        Performs the long-running add-part operation.
        """
        # Set up a log handler that emits signals
        handler = self.SignalLogHandler(self.log_message)
        logging.getLogger().addHandler(handler)

        logger.info(f"Worker started for part {self._search_result.lcsc_id}")
        try:
            # Note: The manager's method might need to be adjusted to not
            # return the part, as it will be emitted via signal.
            library_part = self._manager.add_part_from_search_result(
                self._search_result
            )
            if library_part:
                self.add_part_succeeded.emit(library_part)
            else:
                # This handles cases where the manager returns None without an exception
                self.add_part_failed.emit("Add part operation returned no result.")

        except Exception as e:
            logger.error(
                f"An exception occurred in the worker thread: {e}", exc_info=True
            )
            self.add_part_failed.emit(str(e))
        finally:
            logging.getLogger().removeHandler(handler)
            logger.info("Worker finished.")

    class SignalLogHandler(logging.Handler):
        """A logging handler that emits a Qt signal."""

        def __init__(self, log_signal: Signal):
            super().__init__()
            self.log_signal = log_signal
            self.setFormatter(logging.Formatter("%(message)s"))

        def emit(self, record):
            msg = self.format(record)
            self.log_signal.emit(msg)

import logging
import os
import signal
import sys
from typing import List

from PySide6.QtCore import QObject, QThread, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QApplication, QStackedWidget, QWidget

from adapters.search_engine import Vendor
from library_manager import LibraryManager
from models.library_part import LibraryPart
from models.search_result import SearchResult
from search import Search

from .custom_widgets import ClickableLabel
from .footprint_review_page import FootprintReviewPage
from .hero_image_widget import HeroImageWidget
from .page_library import LibraryPage
from .page_library_element import LibraryElementPage
from .page_search import SearchPage
from .part_info_widget import PartInfoWidget
from .symbol_review_page import SymbolReviewPage

# Ensure SIGINT (Ctrl+C) quits the app properly
signal.signal(signal.SIGINT, signal.SIG_DFL)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class SearchWorker(QObject):
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


class WorkbenchController(QObject):
    request_search = Signal(Vendor, str)
    request_hydration = Signal(SearchResult)
    request_image = Signal(Vendor, str, str)

    def __init__(self, window):
        super().__init__()
        self.window = window
        self.api_service = Search()
        self.library_manager = LibraryManager()
        self.current_search_result = None
        self.is_adding_to_library = False
        self._setup_workers()
        self._find_widgets()
        self._connect_signals()
        self.go_to_library()

    def _setup_workers(self):
        self.search_thread = QThread()
        self.search_worker = SearchWorker(self.api_service)
        self.search_worker.moveToThread(self.search_thread)
        self.search_worker.search_completed.connect(self.on_search_completed)
        self.search_worker.search_failed.connect(self.on_search_failed)
        self.request_search.connect(self.search_worker.start_search)
        self.search_thread.start()

        self.image_thread = QThread()
        self.image_worker = ImageWorker(self.api_service)
        self.image_worker.moveToThread(self.image_thread)
        self.image_worker.image_loaded.connect(self.on_image_loaded)
        self.image_worker.image_failed.connect(self.on_image_failed)
        self.request_image.connect(self.image_worker.load_image)
        self.image_thread.start()

        self.component_thread = QThread()
        self.component_worker = ComponentWorker(self.api_service)
        self.component_worker.moveToThread(self.component_thread)
        self.component_worker.hydration_completed.connect(self.on_hydration_completed)
        self.component_worker.hydration_failed.connect(self.on_hydration_failed)
        self.request_hydration.connect(self.component_worker.hydrate_search_result)
        self.component_thread.start()

    def _find_widgets(self):
        self.main_stack = self.window.findChild(QStackedWidget, "mainStackedWidget")
        self.page_Library: LibraryPage = self.window.findChild(QWidget, "page_Library")
        self.page_Search: SearchPage = self.window.findChild(QWidget, "page_Search")
        self.page_LibraryElement: LibraryElementPage = self.window.findChild(
            QWidget, "page_LibraryElement"
        )
        self.pages = {
            "library": self.page_Library,
            "search": self.page_Search,
            "library_element": self.page_LibraryElement,
        }

    def _connect_signals(self):
        # Library page signals
        self.page_Library.go_to_search_requested.connect(self.go_to_search)
        self.page_Library.edit_part_requested.connect(self.on_library_edit_requested)

        # Search page signals
        self.page_Search.search_requested.connect(self.run_search)
        self.page_Search.item_selected.connect(self.on_search_item_selected)
        self.page_Search.part_added_to_library.connect(self.on_part_added_to_library)
        self.page_Search.request_image.connect(self.on_request_image)
        self.page_Search.back_to_library_requested.connect(self.go_to_library)

        # Library element page signals
        if hasattr(self.page_LibraryElement, "back_to_library_requested"):
            self.page_LibraryElement.back_to_library_requested.connect(
                self.go_to_library
            )

    def on_part_added_to_library(self, library_part: LibraryPart):
        """
        Handles the successful addition of a part to the library.
        """
        if library_part:
            self.window.statusBar().showMessage(
                f"Successfully added '{library_part.part_name}' to library!", 4000
            )
            # Refresh the library page to show the new part
            if hasattr(self.page_Library, "refresh_library"):
                self.page_Library.refresh_library()
            # Navigate to the new part's element page
            self.on_library_edit_requested(library_part)
        else:
            self.window.statusBar().showMessage("Failed to add part to library.", 5000)

    def go_to_library(self):
        self.main_stack.setCurrentWidget(self.pages["library"])
        self.window.statusBar().showMessage("Library", 2000)

    def go_to_search(self):
        self.main_stack.setCurrentWidget(self.pages["search"])
        self.window.statusBar().showMessage("Search", 2000)

    def go_to_library_element(self):
        if hasattr(self.page_LibraryElement, "cleanup"):
            self.page_LibraryElement.cleanup()
        # Simply switch to the LibraryElementPage; details have been set by on_library_review_requested
        self.main_stack.setCurrentWidget(self.pages["library_element"])
        self.window.statusBar().showMessage("Entering review workflow", 2000)

    def on_library_edit_requested(self, part: LibraryPart):
        """
        Handle edit request from LibraryPage: switch to LibraryElementPage with the given part.
        """
        if not part:
            logger.warning("Edit requested for a null part.")
            self.window.statusBar().showMessage(
                "Cannot edit a non-existent part.", 3000
            )
            return

        try:
            self.page_LibraryElement.set_component(part)
            self.main_stack.setCurrentWidget(self.pages["library_element"])
            self.window.statusBar().showMessage(f"Editing {part.part_name}", 2000)
        except Exception as e:
            logger.error(
                f"Error opening edit page for part {getattr(part, 'part_name', 'unknown')}: {e}",
                exc_info=True,
            )
            self.window.statusBar().showMessage(f"Error opening edit page: {e}", 5000)

    def run_search(self, search_term: str):
        self.page_Search.set_search_button_enabled(False)
        self.page_Search.set_search_button_text("Searching...")
        self.window.statusBar().showMessage(f"Searching for '{search_term}'...")
        self.request_search.emit(Vendor.LCSC, search_term)

    def on_search_completed(self, results: List[SearchResult]):
        self.page_Search.update_search_results(results)
        self.window.statusBar().showMessage(f"Found {len(results)} results.", 3000)
        self.page_Search.set_search_button_enabled(True)
        self.page_Search.set_search_button_text("Search")

    def on_search_failed(self, error_message):
        self.window.statusBar().showMessage(f"Search failed: {error_message}", 5000)
        self.page_Search.set_search_button_enabled(True)
        self.page_Search.set_search_button_text("Search")

    def on_request_image(self, vendor: Vendor, image_url: str, image_type: str):
        self.request_image.emit(vendor, image_url, image_type)

    def on_image_loaded(self, image_data: bytes, image_type: str, cache_path: str):
        pixmap = QPixmap()
        pixmap.loadFromData(image_data)
        if image_type == "hero":
            if self.page_Search.hero_image_widget:
                self.page_Search.hero_image_widget.show_pixmap(pixmap)
            if self.current_search_result:
                self.current_search_result.hero_image_cache_path = cache_path

    def on_image_failed(self, error_message: str, image_type: str):
        if image_type == "hero" and self.page_Search.hero_image_widget:
            self.page_Search.hero_image_widget.show_image_not_available()

    def on_hydration_completed(self, result: SearchResult):
        if not result:
            logger.error("Hydration completed with an empty result.")
            self.on_hydration_failed("Received no data.")
            return

        self.current_search_result = result
        self.page_Search.set_symbol_image(
            QPixmap(result.symbol_png_cache_path)
            if result.symbol_png_cache_path
            else QPixmap()
        )
        self.page_Search.set_footprint_image(
            QPixmap(result.footprint_png_cache_path)
            if result.footprint_png_cache_path
            else QPixmap()
        )
        assets_loaded = (
            result.symbol_png_cache_path is not None
            and result.footprint_png_cache_path is not None
        )
        self.page_Search.add_to_library_button.setEnabled(assets_loaded)
        if not assets_loaded:
            self.window.statusBar().showMessage(
                "Cannot add to library: missing assets.", 3000
            )

    def on_hydration_failed(self, error_message: str):
        logger.error(f"Hydration failed: {error_message}")
        self.page_Search.set_symbol_error("Hydration Failed")
        self.page_Search.set_footprint_error("Hydration Failed")
        self.window.statusBar().showMessage(f"Error: {error_message}", 5000)

    def on_search_item_selected(self, result: SearchResult):
        if result and isinstance(result.vendor, str):
            result.vendor = Vendor(result.vendor)

        self.current_search_result = result
        self.page_Search.clear_images()
        self.page_Search.add_to_library_button.setEnabled(False)
        if result:
            self.page_Search.set_details(result)
            self.page_Search.set_symbol_loading(True)
            self.page_Search.set_footprint_loading(True)
            self.request_hydration.emit(result)

    def cleanup(self):
        for thread in [self.search_thread, self.component_thread, self.image_thread]:
            if thread.isRunning():
                thread.quit()
                thread.wait()


def main():
    app = QApplication(sys.argv)
    loader = QUiLoader()
    loader.registerCustomWidget(LibraryPage)
    loader.registerCustomWidget(SearchPage)
    loader.registerCustomWidget(LibraryElementPage)
    loader.registerCustomWidget(PartInfoWidget)
    loader.registerCustomWidget(HeroImageWidget)
    loader.registerCustomWidget(FootprintReviewPage)
    loader.registerCustomWidget(SymbolReviewPage)
    loader.registerCustomWidget(ClickableLabel)
    ui_file_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), "workbench.ui"
    )
    window = loader.load(ui_file_path, None)
    if not window:
        sys.exit(1)

    controller = WorkbenchController(window)
    window.show()
    app.aboutToQuit.connect(controller.cleanup)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()

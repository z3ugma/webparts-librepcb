import logging
import os
import sys
from functools import partial
from typing import List

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QCursor, QPixmap, QFont, QAction
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPixmapItem,
    QGraphicsTextItem,
    QLabel,
    QPushButton,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
    QMenu,
)

from models.search_result import SearchResult
from search import Search
from .page_search import SearchPage
from .footprint_review_page import FootprintReviewPage
from .symbol_review_page import SymbolReviewPage

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger(__name__)


class SearchWorker(QObject):
    search_completed = Signal(list)
    search_failed = Signal(str)

    def __init__(self, api_service):
        super().__init__()
        self.api_service = api_service

    def start_search(self, vendor, search_term):
        try:
            results = self.api_service.search(vendor, search_term)
            self.search_completed.emit(results)
        except Exception as e:
            logger.error(f"SearchWorker failed: {e}", exc_info=True)
            self.search_failed.emit(str(e))


class ImageWorker(QObject):
    image_loaded = Signal(bytes, str)
    image_failed = Signal(str, str)

    def __init__(self, api_service):
        super().__init__()
        self.api_service = api_service

    def load_image(self, vendor: str, image_url: str, image_type: str):
        try:
            image_data = self.api_service.download_image_from_url(vendor, image_url)
            if image_data:
                self.image_loaded.emit(image_data, image_type)
            else:
                self.image_failed.emit("Failed to download image", image_type)
        except Exception as e:
            logger.error(f"ImageWorker failed for {image_url}: {e}", exc_info=True)
            self.image_failed.emit(str(e), image_type)


class ComponentWorker(QObject):
    hydration_completed = Signal(SearchResult)
    hydration_failed = Signal(str)

    def __init__(self, api_service):
        super().__init__()
        self.api_service = api_service

    def hydrate_search_result(self, result: SearchResult):
        try:
            hydrated_result = self.api_service.get_fully_hydrated_search_result(result)
            self.hydration_completed.emit(hydrated_result)
        except Exception as e:
            logger.error(f"ComponentWorker hydration encountered an exception: {e}", exc_info=True)
            self.hydration_failed.emit(str(e))


class ClickableLabel(QLabel):
    clicked = Signal()
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setCursor(QCursor(Qt.PointingHandCursor))
    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)


class WorkbenchController(QObject):
    request_search = Signal(str, str)  # vendor, search_term
    request_image = Signal(str, str, str)  # vendor, url, type
    request_hydration = Signal(SearchResult)

    def __init__(self, window):
        super().__init__()
        self.window = window
        self.api_service = Search()
        self.current_search_result = None
        self.current_step_index = 0
        self._setup_workers()
        self._find_widgets()
        self._connect_signals()
        self.go_to_step(0)

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
        self.button_PreviousStep = self.window.findChild(QPushButton, "button_PreviousStep")
        self.button_NextStep = self.window.findChild(QPushButton, "button_NextStep")
        self.context_frame = self.window.findChild(QFrame, "contextFrame")
        self.label_LcscId = self.window.findChild(QLabel, "label_LcscId")
        self.label_PartTitle = self.window.findChild(QLabel, "label_PartTitle")
        self.mfn_value = self.window.findChild(QLabel, "mfn_value")
        self.mfn_part_value = self.window.findChild(QLabel, "mfn_part_value")
        self.description_value = self.window.findChild(QLabel, "description_value")
        self.hero_view = self.window.findChild(QGraphicsView, "image_hero_view")
        self.page_Search: SearchPage = self.window.findChild(QWidget, "page_Search")
        self.page_FootprintReview: FootprintReviewPage = self.window.findChild(QWidget, "page_FootprintReview")
        self.page_SymbolReview: SymbolReviewPage = self.window.findChild(QWidget, "page_SymbolReview")
        self.pages = [
            self.page_Search,
            self.page_FootprintReview,
            self.page_SymbolReview,
            self.window.findChild(QWidget, "page_ComponentAssembly"),
            self.window.findChild(QWidget, "page_FinalSummary"),
        ]
        self.step_labels = []
        self._promote_step_labels()
        self._setup_hero_image()
        self.on_search_item_selected(None)
        self._enable_text_selection()

    def _enable_text_selection(self):
        selectable_labels = [
            self.label_LcscId, self.label_PartTitle, self.mfn_value,
            self.mfn_part_value, self.description_value,
        ]
        for label in selectable_labels:
            if label:
                label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
                label.setContextMenuPolicy(Qt.CustomContextMenu)
                label.customContextMenuRequested.connect(
                    lambda pos, lbl=label: self._show_label_context_menu(pos, lbl)
                )
                label.setToolTip("Right-click to copy, or select text with mouse")
    
    def _show_label_context_menu(self, position, label):
        menu = QMenu(self.window)
        copy_selected_action = QAction("Copy Selected", self.window)
        copy_selected_action.triggered.connect(lambda: self._copy_label_text(label, selected_only=True))
        copy_selected_action.setEnabled(label.hasSelectedText())
        menu.addAction(copy_selected_action)
        copy_all_action = QAction("Copy All", self.window)
        copy_all_action.triggered.connect(lambda: self._copy_label_text(label, selected_only=False))
        copy_all_action.setEnabled(bool(label.text().strip()))
        menu.addAction(copy_all_action)
        select_all_action = QAction("Select All", self.window)
        select_all_action.triggered.connect(lambda: self._select_all_label_text(label))
        select_all_action.setEnabled(bool(label.text().strip()))
        menu.addAction(select_all_action)
        if any(action.isEnabled() for action in menu.actions()):
            menu.exec(label.mapToGlobal(position))
    
    def _copy_label_text(self, label, selected_only=True):
        if selected_only and label.hasSelectedText():
            text = label.selectedText()
        else:
            text = label.text()
        if text.strip():
            QApplication.clipboard().setText(text)
            self.window.statusBar().showMessage(f"Copied: {text[:50]}...", 2000)

    def _select_all_label_text(self, label):
        if hasattr(label, 'setSelection'):
            label.setSelection(0, len(label.text()))
        else:
            text = label.text()
            if text.strip():
                QApplication.clipboard().setText(text)
                self.window.statusBar().showMessage(f"Copied all: {text[:50]}...", 2000)

    def _setup_hero_image(self):
        self.hero_scene = QGraphicsScene()
        self.hero_view.setScene(self.hero_scene)
        self.hero_pixmap_item = QGraphicsPixmapItem()
        self.hero_scene.addItem(self.hero_pixmap_item)
        self.hero_text_item = QGraphicsTextItem()
        font = QFont(); font.setPointSize(12); self.hero_text_item.setFont(font)
        self.hero_text_item.setDefaultTextColor(Qt.gray)
        self.hero_scene.addItem(self.hero_text_item)
        self._set_hero_text("No Image")

    def _set_hero_text(self, text: str):
        self.hero_text_item.setPlainText(text); self.hero_text_item.setVisible(True)
        self.hero_pixmap_item.setVisible(False); self.hero_view.resetTransform()
        self.hero_view.centerOn(self.hero_text_item)

    def _set_hero_pixmap(self, pixmap: QPixmap):
        self.hero_pixmap_item.setPixmap(pixmap); self.hero_pixmap_item.setVisible(True)
        self.hero_text_item.setVisible(False)
        if pixmap.isNull() or self.hero_view.width() == 0: return
        scale_w = (1.5 * self.hero_view.width()) / pixmap.width()
        scale_h = (1.5 * self.hero_view.height()) / pixmap.height()
        scale_factor = max(scale_w, scale_h)
        self.hero_view.resetTransform(); self.hero_view.scale(scale_factor, scale_factor)
        self.hero_view.centerOn(self.hero_pixmap_item)

    def _connect_signals(self):
        self.page_Search.search_requested.connect(self.run_search)
        self.page_Search.item_selected.connect(self.on_search_item_selected)
        self.page_Search.item_double_clicked.connect(self.next_step)
        if self.button_PreviousStep: self.button_PreviousStep.clicked.connect(self.previous_step)
        if self.button_NextStep: self.button_NextStep.clicked.connect(self.next_step)
        if self.page_FootprintReview:
             approve_button = self.page_FootprintReview.findChild(QPushButton, "button_ApproveFootprint")
             if approve_button: approve_button.clicked.connect(self.next_step)

    def _promote_step_labels(self):
        step_names = ["step1_Status", "step2_Status", "step3_Status", "step4_Status", "step5_Status"]
        layout = self.context_frame.layout()
        if not layout: return
        for i, name in enumerate(step_names):
            old_label = self.window.findChild(QLabel, name)
            if old_label:
                new_label = ClickableLabel(old_label.text())
                new_label.setToolTip(old_label.toolTip())
                new_label.setObjectName(old_label.objectName())
                index = layout.indexOf(old_label)
                layout.insertWidget(index, new_label)
                layout.removeWidget(old_label)
                old_label.deleteLater()
                new_label.clicked.connect(partial(self.go_to_step, i))
                self.step_labels.append(new_label)

    def go_to_step(self, index):
        if not (0 <= index < len(self.pages) and self.pages[index] is not None): return
        if self.pages[index] == self.page_FootprintReview:
            footprint_pixmap = self.page_Search.get_footprint_pixmap()
            if self.page_FootprintReview and footprint_pixmap:
                self.page_FootprintReview.set_footprint_image(footprint_pixmap)
        self.current_step_index = index
        self.main_stack.setCurrentWidget(self.pages[index])
        for i, label in enumerate(self.step_labels):
            font = label.font(); font.setBold(i == index); label.setFont(font)
        self.button_PreviousStep.setEnabled(index > 0)
        self.button_NextStep.setEnabled(index < len(self.pages) - 1 and self.current_search_result is not None)
        self.window.statusBar().showMessage(f"Step {index + 1}: {self.step_labels[index].text()[3:]}", 2000)

    def next_step(self, item_data=None):
        if self.current_search_result or item_data:
            if self.current_step_index < len(self.pages) - 1:
                self.go_to_step(self.current_step_index + 1)

    def previous_step(self):
        self.go_to_step(self.current_step_index - 1)

    def run_search(self, search_term: str):
        self.page_Search.set_search_button_enabled(False)
        self.page_Search.set_search_button_text("Searching...")
        self.window.statusBar().showMessage(f"Searching for '{search_term}'...")
        self.request_search.emit("LCSC", search_term)

    def on_search_completed(self, results: List[SearchResult]):
        self.page_Search.update_search_results(results)
        self.window.statusBar().showMessage(f"Found {len(results)} results.", 3000)
        self.page_Search.set_search_button_enabled(True)
        self.page_Search.set_search_button_text("Search")

    def on_search_failed(self, error_message):
        self.window.statusBar().showMessage(f"Search failed: {error_message}", 5000)
        self.page_Search.set_search_button_enabled(True)
        self.page_Search.set_search_button_text("Search")

    def on_image_loaded(self, image_data: bytes, image_type: str):
        pixmap = QPixmap()
        pixmap.loadFromData(image_data)
        if image_type == "hero":
            self._set_hero_pixmap(pixmap)

    def on_image_failed(self, error_message: str, image_type: str):
        if image_type == "hero":
            self._set_hero_text("Image Not Available")

    def on_hydration_completed(self, result: SearchResult):
        self.current_search_result = result
        if result.symbol_png_path:
            pixmap = QPixmap(result.symbol_png_path)
            self.page_Search.set_symbol_image(pixmap)
        else:
            self.page_Search.set_symbol_error("Symbol not available")
        if result.footprint_png_path:
            pixmap = QPixmap(result.footprint_png_path)
            self.page_Search.set_footprint_image(pixmap)
        else:
            self.page_Search.set_footprint_error("Footprint not available")

    def on_hydration_failed(self, error_message: str):
        logger.error(f"An unexpected error occurred during hydration: {error_message}")
        self.page_Search.set_symbol_error("Hydration Failed")
        self.page_Search.set_footprint_error("Hydration Failed")
        self.window.statusBar().showMessage(f"Error: {error_message}", 5000)

    def on_search_item_selected(self, result: SearchResult):
        self.current_search_result = result
        self._set_hero_text("No Image")
        self.page_Search.clear_images()
        if result:
            self.label_LcscId.setText(f"LCSC ID: {result.lcsc_id}")
            self.label_PartTitle.setText(result.part_name)
            self.mfn_value.setText(result.manufacturer)
            self.mfn_part_value.setText(result.mfr_part_number)
            self.description_value.setText(result.description)
            if result.image_url:
                self._set_hero_text("Loading...")
                self.request_image.emit(result.vendor, result.image_url, "hero")
            else:
                self._set_hero_text("Image Not Available")
            self.page_Search.set_symbol_loading(True)
            self.page_Search.set_footprint_loading(True)
            self.request_hydration.emit(result)
        else:
            self.label_LcscId.setText("LCSC ID: -")
            self.label_PartTitle.setText("No Part Loaded")
            self.mfn_value.setText("(select a part)")
            self.mfn_part_value.setText("")
            self.description_value.setText("")
        self.button_NextStep.setEnabled(result is not None)

    def cleanup(self):
        for thread in [self.search_thread, self.image_thread, self.component_thread]:
            if thread.isRunning():
                thread.quit()
                thread.wait()

def main():
    app = QApplication(sys.argv)
    loader = QUiLoader()
    loader.registerCustomWidget(SearchPage)
    loader.registerCustomWidget(FootprintReviewPage)
    loader.registerCustomWidget(SymbolReviewPage)
    ui_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "workbench.ui")
    window = loader.load(ui_file_path, None)
    if not window:
        sys.exit(1)
    controller = WorkbenchController(window)
    window.show()
    app.aboutToQuit.connect(controller.cleanup)
    sys.exit(app.exec())

if __name__ == "__main__":
    main()

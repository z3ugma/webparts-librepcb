import os
import logging
from functools import partial

from PySide6.QtCore import QObject, Qt, QThread, Signal, QTimer
from PySide6.QtGui import QPixmap, QFont
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QFrame,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPixmapItem,
    QGraphicsTextItem,
    QLabel,
    QStackedWidget,
    QPushButton,
    QSplitter,
)

from models.library_part import LibraryPart
from models.status import StatusValue
from models.elements import LibrePCBElement
from adapters.search_engine import Vendor
from search import Search
from .footprint_review_page import FootprintReviewPage
from .symbol_review_page import SymbolReviewPage
from .part_info_widget import PartInfoWidget
from .custom_widgets import ClickableLabel, ZoomPanGraphicsView
from constants import UIText, WebPartsFilename, WORKFLOW_MAPPING

logger = logging.getLogger(__name__)


class ImageWorker(QObject):
    image_loaded = Signal(bytes, str)
    image_failed = Signal(str, str)

    def __init__(self, api_service):
        super().__init__()
        self.api_service = api_service

    def load_image(self, vendor: str, image_url: str, image_type: str):
        try:
            result = self.api_service.download_image_from_url(vendor, image_url)
            if result:
                image_data, cache_path = result
                self.image_loaded.emit(image_data, image_type)
            else:
                self.image_failed.emit("Failed to download image", image_type)
        except Exception as e:
            logger.error(f"ImageWorker failed: {e}", exc_info=True)
            self.image_failed.emit(str(e), image_type)


class LibraryElementPage(QWidget):
    request_image = Signal(Vendor, str, str)
    back_to_library_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        loader = QUiLoader()
        loader.registerCustomWidget(ClickableLabel)
        loader.registerCustomWidget(PartInfoWidget)
        loader.registerCustomWidget(FootprintReviewPage)
        loader.registerCustomWidget(SymbolReviewPage)
        ui_file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "page_library_element.ui"
        )

        # Load the UI file but don't parent it to self yet
        self.ui_content = loader.load(ui_file_path, None)

        self._find_widgets()

        # Create a QSplitter as the main layout mechanism
        self.main_splitter = QSplitter(Qt.Horizontal)
        self.main_splitter.setHandleWidth(5)
        self.main_splitter.addWidget(self.context_frame)
        self.main_splitter.addWidget(self.review_stack)
        self.main_splitter.setStretchFactor(0, 1)  # Sidebar
        self.main_splitter.setStretchFactor(1, 3)  # Main content

        # Set the main layout for this widget
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.main_splitter)

        # Set initial splitter sizes programmatically to a 1:4 ratio
        self.main_splitter.setSizes([200, 800])

        self.api_service = Search()
        self._setup_workers()
        self._connect_signals()

    def _find_widgets(self):
        # Find widgets from the loaded UI content
        self.context_frame = self.ui_content.findChild(QFrame, "contextFrame")
        self.review_stack = self.ui_content.findChild(
            QStackedWidget, "reviewStackedWidget"
        )
        self.part_info_widget = self.context_frame.findChild(
            PartInfoWidget, "part_info_widget"
        )

        # Replace hero image placeholder with ZoomPanGraphicsView
        hero_view_placeholder = self.context_frame.findChild(
            QGraphicsView, "image_hero_view"
        )
        if hero_view_placeholder:
            self.hero_scene = QGraphicsScene(self)
            self.hero_view = ZoomPanGraphicsView(self.hero_scene, self)
            parent_layout = hero_view_placeholder.parent().layout()
            if parent_layout:
                parent_layout.replaceWidget(hero_view_placeholder, self.hero_view)
                hero_view_placeholder.deleteLater()
            else:
                logger.error("Could not find parent layout for hero view placeholder.")
                self.hero_view = hero_view_placeholder  # Fallback
        else:
            logger.error("Could not find 'image_hero_view' placeholder in UI.")
            self.hero_view = QGraphicsView()  # Dummy widget

        self.back_to_library_button = self.context_frame.findChild(
            QPushButton, "back_to_library_button"
        )
        self.button_PreviousStep = self.context_frame.findChild(
            QPushButton, "button_PreviousStep"
        )
        self.button_NextStep = self.context_frame.findChild(
            QPushButton, "button_NextStep"
        )
        self.page_FootprintReview: FootprintReviewPage = self.review_stack.findChild(
            QWidget, "page_FootprintReview"
        )
        self.page_SymbolReview: SymbolReviewPage = self.review_stack.findChild(
            QWidget, "page_SymbolReview"
        )
        self._setup_hero_image()

    def _setup_hero_image(self):
        self.hero_pixmap_item = QGraphicsPixmapItem()
        self.hero_scene.addItem(self.hero_pixmap_item)
        self.hero_text_item = QGraphicsTextItem()
        font = QFont()
        font.setPointSize(12)
        self.hero_text_item.setFont(font)
        self.hero_text_item.setDefaultTextColor(Qt.gray)
        self.hero_scene.addItem(self.hero_text_item)
        self._set_hero_text(UIText.NO_IMAGE.value)

    def _set_hero_pixmap(self, pixmap: QPixmap):
        if pixmap and not pixmap.isNull():
            self.hero_pixmap_item.setPixmap(pixmap)
            self.hero_pixmap_item.setVisible(True)
            self.hero_text_item.setVisible(False)
            QTimer.singleShot(0, self._fit_and_zoom_hero)
        else:
            self._set_hero_text(UIText.IMAGE_NOT_AVAILABLE.value)

    def _fit_and_zoom_hero(self):
        self.hero_view.fitInView(self.hero_pixmap_item, Qt.KeepAspectRatio)
        self.hero_view.scale(1.5, 1.5)

    def _setup_workers(self):
        self.image_thread = QThread()
        self.image_worker = ImageWorker(self.api_service)
        self.image_worker.moveToThread(self.image_thread)
        self.image_worker.image_loaded.connect(self.on_image_loaded)
        self.image_worker.image_failed.connect(self.on_image_failed)
        self.request_image.connect(self.image_worker.load_image)
        self.image_thread.start()

    def _connect_signals(self):
        """Find and connect signals for workflow steps and navigation buttons."""
        logger.debug("Connecting signals for LibraryElementPage...")
        self.step_labels = [
            self.context_frame.findChild(ClickableLabel, f"step{i + 1}_Status")
            for i in range(4)
        ]
        self.step_label_text = [label.text() for label in self.step_labels if label]
        logger.debug(f"Found {len(self.step_labels)} workflow step labels.")

        if self.button_PreviousStep:
            self.button_PreviousStep.clicked.connect(self.previous_step)
            logger.debug("Connected 'Previous' button.")
        else:
            logger.warning("'button_PreviousStep' not found.")

        if self.button_NextStep:
            self.button_NextStep.clicked.connect(self.next_step)
            logger.debug("Connected 'Next' button.")
        else:
            logger.warning("'button_NextStep' not found.")

        if self.back_to_library_button:
            self.back_to_library_button.clicked.connect(self.back_to_library_requested)
            logger.debug("Connected 'Back to Library' button.")
        else:
            logger.warning("'back_to_library_button' not found.")

        for i, label in enumerate(self.step_labels):
            if label:
                label.clicked.connect(partial(self.go_to_step, i))
        logger.debug("Connected clickable step labels.")

    def set_component(self, component):
        self.component = component
        if self.part_info_widget:
            self.part_info_widget.set_component(component)

        if hasattr(component, "image_url"):
            self._set_hero_text(UIText.LOADING.value)
            try:
                vendor_enum = Vendor(component.vendor)
                self.request_image.emit(vendor_enum, component.image_url, "hero")
            except ValueError:
                self._set_hero_text(UIText.IMAGE_NOT_AVAILABLE.value)
        else:
            hero_path = (
                LibrePCBElement.PACKAGE.dir.parent
                / "webparts"
                / component.uuid
                / WebPartsFilename.HERO_IMAGE.value
            )
            if hero_path.exists():
                self._set_hero_pixmap(QPixmap(str(hero_path)))
            else:
                self._set_hero_text(UIText.IMAGE_NOT_AVAILABLE.value)

        footprint_pixmap = (
            QPixmap(component.footprint.png_path)
            if hasattr(component, "footprint") and component.footprint.png_path
            else QPixmap()
        )
        self.page_FootprintReview.set_footprint_image(footprint_pixmap)
        self.page_FootprintReview.set_library_part(component)

        rendered_footprint_pixmap = (
            QPixmap(component.footprint.rendered_png_path)
            if hasattr(component, "footprint") and component.footprint.rendered_png_path
            else QPixmap()
        )
        self.page_FootprintReview.set_librepcb_footprint_image(
            rendered_footprint_pixmap
        )

        symbol_pixmap = (
            QPixmap(component.symbol.png_path)
            if hasattr(component, "symbol") and component.symbol.png_path
            else QPixmap()
        )
        self.page_SymbolReview.set_symbol_image(symbol_pixmap)
        self.page_SymbolReview.set_library_part(component)

        rendered_symbol_pixmap = (
            QPixmap(component.symbol.rendered_png_path)
            if hasattr(component, "symbol") and component.symbol.rendered_png_path
            else QPixmap()
        )
        self.page_SymbolReview.set_librepcb_symbol_image(rendered_symbol_pixmap)

        self._update_workflow_status(component.status)
        self.go_to_step(0)

    def _update_workflow_status(self, status):
        """Update the workflow status icons based on the component's status."""
        workflow_status_labels = {
            "footprint": self.context_frame.findChild(QLabel, "label_step1_status"),
            "symbol": self.context_frame.findChild(QLabel, "label_step2_status"),
            "assembly": self.context_frame.findChild(QLabel, "label_step3_status"),
            "finalize": self.context_frame.findChild(QLabel, "label_step4_status"),
        }

        for label_key, status_key in WORKFLOW_MAPPING.items():
            label_widget = workflow_status_labels.get(label_key)
            if label_widget:
                status_value = getattr(status, status_key, StatusValue.UNAVAILABLE)
                label_widget.setText(status_value.icon)

    def on_image_loaded(self, image_data: bytes, image_type: str):
        pixmap = QPixmap()
        pixmap.loadFromData(image_data)
        if image_type == "hero":
            self._set_hero_pixmap(pixmap)

    def on_image_failed(self, error_message: str, image_type: str):
        if image_type == "hero":
            self._set_hero_text(UIText.IMAGE_NOT_AVAILABLE.value)

    def go_to_step(self, index):
        """Navigate to a specific step in the review workflow."""
        logger.debug(f"Attempting to navigate to step {index + 1}.")
        if self.review_stack and 0 <= index < self.review_stack.count():
            self.review_stack.setCurrentIndex(index)
            logger.info(
                f"Navigated to workflow step {index + 1}: '{self.step_label_text[index]}'."
            )

            # Enable/disable navigation buttons
            if self.button_PreviousStep:
                self.button_PreviousStep.setEnabled(index > 0)
            if self.button_NextStep:
                self.button_NextStep.setEnabled(index < self.review_stack.count() - 1)

            # Update label styles
            for i, label in enumerate(self.step_labels):
                if label:
                    is_active_step = i == index
                    new_text = (
                        f"<b>{self.step_label_text[i]}</b>"
                        if is_active_step
                        else self.step_label_text[i]
                    )
                    if label.text() != new_text:
                        label.setText(new_text)
                        logger.debug(
                            f"Set step {i + 1} label to '{'bold' if is_active_step else 'plain'}'."
                        )
        else:
            logger.warning(
                f"Could not navigate to step {index + 1}: Index out of range or review_stack not found."
            )

    def next_step(self):
        if self.review_stack:
            self.go_to_step(self.review_stack.currentIndex() + 1)

    def previous_step(self):
        if self.review_stack:
            self.go_to_step(self.review_stack.currentIndex() - 1)

    def cleanup(self):
        if hasattr(self, "image_thread") and self.image_thread.isRunning():
            self.image_thread.quit()
            self.image_thread.wait()

    def _set_hero_text(self, text: str):
        self.hero_text_item.setPlainText(text)
        self.hero_text_item.setVisible(True)
        self.hero_pixmap_item.setVisible(False)
        self.hero_view.resetTransform()
        self.hero_view.centerOn(self.hero_text_item)

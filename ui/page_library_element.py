import os
import logging
from typing import List
from functools import partial

from PySide6.QtCore import QObject, Qt, QThread, Signal
from PySide6.QtGui import QPixmap, QFont, QCursor
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QApplication,
    QFrame,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPixmapItem,
    QGraphicsTextItem,
    QLabel,
    QStackedWidget,
    QWidget,
    QPushButton,
    QVBoxLayout,
)

from models.search_result import SearchResult
from models.library_part import LibraryPart
from models.status import StatusValue
from models.elements import LibrePCBElement
from adapters.search_engine import Vendor
from search import Search
from .footprint_review_page import FootprintReviewPage
from .symbol_review_page import SymbolReviewPage
from .part_info_widget import PartInfoWidget
from constants import UIText, WebPartsFilename, WORKFLOW_MAPPING

logger = logging.getLogger(__name__)

class ClickableLabel(QLabel):
    clicked = Signal()
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.setCursor(QCursor(Qt.PointingHandCursor))
    def mousePressEvent(self, event):
        self.clicked.emit()
        super().mousePressEvent(event)

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
    request_image = Signal(Vendor, str, str)  # vendor_enum, image_url, image_type
    back_to_library_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        loader = QUiLoader()
        loader.registerCustomWidget(ClickableLabel)
        loader.registerCustomWidget(PartInfoWidget)
        ui_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "page_library_element.ui")
        self.ui = loader.load(ui_file_path, self)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0,0,0,0)
        layout.addWidget(self.ui)
        
        self.api_service = Search()
        self._setup_workers()
        self._find_widgets()
        self._connect_signals()

    def _setup_workers(self):
        self.image_thread = QThread()
        self.image_worker = ImageWorker(self.api_service)
        self.image_worker.moveToThread(self.image_thread)
        self.image_worker.image_loaded.connect(self.on_image_loaded)
        self.image_worker.image_failed.connect(self.on_image_failed)
        self.request_image.connect(self.image_worker.load_image)
        self.image_thread.start()

    def _find_widgets(self):
        self.context_frame = self.ui.findChild(QFrame, "contextFrame")
        self.part_info_widget = self.ui.findChild(PartInfoWidget, "part_info_widget")
        self.hero_view = self.ui.findChild(QGraphicsView, "image_hero_view")
        self.review_stack = self.ui.findChild(QStackedWidget, "reviewStackedWidget")
        self.button_PreviousStep = self.ui.findChild(QPushButton, "button_PreviousStep")
        self.button_NextStep = self.ui.findChild(QPushButton, "button_NextStep")
        self.back_to_library_button = self.ui.findChild(QPushButton, "back_to_library_button")

        self.workflow_status_labels = {
            'footprint': self.ui.findChild(QLabel, 'label_step1_status'),
            'symbol': self.ui.findChild(QLabel, 'label_step2_status'),
            'assembly': self.ui.findChild(QLabel, 'label_step3_status'),
            'finalize': self.ui.findChild(QLabel, 'label_step4_status'),
        }

        self.step_labels = [
            self.ui.findChild(ClickableLabel, "step1_Status"),
            self.ui.findChild(ClickableLabel, "step2_Status"),
            self.ui.findChild(ClickableLabel, "step3_Status"),
            self.ui.findChild(ClickableLabel, "step4_Status"),
        ]

        self.page_FootprintReview: FootprintReviewPage = self.ui.findChild(QWidget, "page_FootprintReview")
        self.page_SymbolReview: SymbolReviewPage = self.ui.findChild(QWidget, "page_SymbolReview")
        self.page_Assembly: QWidget = self.ui.findChild(QWidget, "page_ComponentAssembly")
        self.page_Finalize: QWidget = self.ui.findChild(QWidget, "page_FinalSummary")

        self.review_pages = [self.page_FootprintReview, self.page_SymbolReview, self.page_Assembly, self.page_Finalize]
        self.current_step_index = 0
        self._setup_hero_image()
        
    def _setup_hero_image(self):
        self.hero_scene = QGraphicsScene()
        self.hero_view.setScene(self.hero_scene)
        self.hero_pixmap_item = QGraphicsPixmapItem()
        self.hero_scene.addItem(self.hero_pixmap_item)
        self.hero_text_item = QGraphicsTextItem()
        font = QFont(); font.setPointSize(12); self.hero_text_item.setFont(font)
        self.hero_text_item.setDefaultTextColor(Qt.gray)
        self.hero_scene.addItem(self.hero_text_item)
        self._set_hero_text(UIText.NO_IMAGE.value)

    def _set_hero_text(self, text: str):
        self.hero_text_item.setPlainText(text); self.hero_text_item.setVisible(True)
        self.hero_pixmap_item.setVisible(False); self.hero_view.resetTransform()
        self.hero_view.centerOn(self.hero_text_item)

    def _set_hero_pixmap(self, pixmap: QPixmap):
        self.hero_pixmap_item.setPixmap(pixmap); self.hero_pixmap_item.setVisible(True)
        self.hero_text_item.setVisible(False)
        if pixmap.isNull() or self.hero_view.width() == 0: return
        scale = max((1.5 * self.hero_view.width()) / pixmap.width(), (1.5 * self.hero_view.height()) / pixmap.height())
        self.hero_view.resetTransform(); self.hero_view.scale(scale, scale)
        self.hero_view.centerOn(self.hero_pixmap_item)

    def _connect_signals(self):
        self.button_PreviousStep.clicked.connect(self.previous_step)
        self.button_NextStep.clicked.connect(self.next_step)
        if self.back_to_library_button:
            self.back_to_library_button.clicked.connect(self.back_to_library_requested)
        
        for i, label in enumerate(self.step_labels):
            if label:
                label.clicked.connect(partial(self.go_to_step, i))

    def set_component(self, component):
        """Set component data - handles both SearchResult and LibraryPart objects"""
        self.component = component
        
        if hasattr(component, 'image_url'):
            self._set_component_searchresult(component)
        else:
            self._set_component_librarypart(component)
        
        self.go_to_step(0)
    
    def _set_component_searchresult(self, component):
        """Handle SearchResult objects"""
        if self.part_info_widget:
            self.part_info_widget.set_component(component)
        
        if component.image_url:
            self._set_hero_text(UIText.LOADING.value)
            # Convert string vendor to Vendor enum
            try:
                vendor_enum = Vendor(component.vendor)
                self.request_image.emit(vendor_enum, component.image_url, "hero")
            except ValueError:
                logger.warning(f"Unknown vendor: {component.vendor}")
                self._set_hero_text(UIText.IMAGE_NOT_AVAILABLE.value)
        else:
            self._set_hero_text(UIText.IMAGE_NOT_AVAILABLE.value)
            
        self.page_FootprintReview.set_footprint_image(
            QPixmap(component.footprint_png_path) if component.footprint_png_path else QPixmap()
        )
        self.page_SymbolReview.set_symbol_image(
            QPixmap(component.symbol_png_path) if component.symbol_png_path else QPixmap()
        )
    
    def _set_component_librarypart(self, part):
        """Handle LibraryPart objects"""
        if self.part_info_widget:
            self.part_info_widget.set_component(part)
        
        hero_path = LibrePCBElement.PACKAGE.dir.parent / "webparts" / part.uuid / WebPartsFilename.HERO_IMAGE.value
        if hero_path.exists():
            pixmap = QPixmap(str(hero_path))
            if not pixmap.isNull():
                self._set_hero_pixmap(pixmap)
            else:
                self._set_hero_text(UIText.IMAGE_NOT_AVAILABLE.value)
        else:
            self._set_hero_text(UIText.IMAGE_NOT_AVAILABLE.value)
        
        footprint_path = LibrePCBElement.PACKAGE.dir / part.footprint.uuid / WebPartsFilename.FOOTPRINT_PNG.value
        symbol_path = LibrePCBElement.PACKAGE.dir.parent / "webparts" / part.uuid / WebPartsFilename.SYMBOL_PNG.value
        
        self.page_FootprintReview.set_footprint_image(
            QPixmap(str(footprint_path)) if footprint_path.exists() else QPixmap()
        )
        self.page_SymbolReview.set_symbol_image(
            QPixmap(str(symbol_path)) if symbol_path.exists() else QPixmap()
        )

        self._update_workflow_status(part)

    def _update_workflow_status(self, part: LibraryPart):
        """Update the workflow status indicators in the sidebar."""
        for label_key, status_key in WORKFLOW_MAPPING.items():
            if self.workflow_status_labels[label_key]:
                status_value: StatusValue = getattr(part.status, status_key, StatusValue.UNAVAILABLE)
                self.workflow_status_labels[label_key].setText(status_value.icon)

    def on_image_loaded(self, image_data: bytes, image_type: str):
        pixmap = QPixmap()
        pixmap.loadFromData(image_data)
        if image_type == "hero": self._set_hero_pixmap(pixmap)

    def on_image_failed(self, error_message: str, image_type: str):
        if image_type == "hero": self._set_hero_text(UIText.IMAGE_NOT_AVAILABLE.value)

    def go_to_step(self, index):
        if 0 <= index < len(self.review_pages):
            self.current_step_index = index
            self.review_stack.setCurrentIndex(index)
            self.button_PreviousStep.setEnabled(index > 0)
            self.button_NextStep.setEnabled(index < len(self.review_pages) - 1)
            
            for i, label in enumerate(self.step_labels):
                font = label.font()
                font.setBold(i == index)
                label.setFont(font)

    def next_step(self):
        self.go_to_step(self.current_step_index + 1)

    def previous_step(self):
        self.go_to_step(self.current_step_index - 1)

    def cleanup(self):
        if hasattr(self, 'image_thread') and self.image_thread.isRunning():
            self.image_thread.quit()
            self.image_thread.wait()

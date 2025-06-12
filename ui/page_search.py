import logging
import os
from typing import List

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from models.search_result import SearchResult

from .hero_image_widget import HeroImageWidget
from .part_info_widget import PartInfoWidget

logger = logging.getLogger(__name__)


class SearchPage(QWidget):
    search_requested = Signal(str)
    item_selected = Signal(object)
    add_to_library_requested = Signal()
    request_image = Signal(str, str, str)
    back_to_library_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        # Store original pixmaps for rescaling
        self._original_symbol_pixmap = None
        self._original_footprint_pixmap = None

        loader = QUiLoader()
        loader.registerCustomWidget(PartInfoWidget)
        loader.registerCustomWidget(HeroImageWidget)
        ui_file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "page_search.ui"
        )
        loaded_ui = loader.load(ui_file_path, self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(loaded_ui)

        # Find widgets
        self.search_input = self.findChild(QLineEdit, "searchInput")
        self.search_button = self.findChild(QPushButton, "button_Search")
        self.add_to_library_button = self.findChild(
            QPushButton, "add_to_library_button"
        )
        self.back_to_library_button = self.findChild(
            QPushButton, "back_to_library_button"
        )
        self.results_tree = self.findChild(QTreeWidget, "searchResultsTree")
        self.symbol_image_label = self.findChild(QLabel, "image_symbol")
        self.footprint_image_label = self.findChild(QLabel, "image_footprint")

        self.part_info_widget = self.findChild(PartInfoWidget, "part_info_widget")
        self.hero_image_widget = self.findChild(HeroImageWidget, "hero_image_widget")
        self.label_3dModelStatus = self.findChild(QLabel, "label_3dModelStatus")
        self.datasheetLink = self.findChild(QLabel, "datasheetLink")

        for label in [self.symbol_image_label, self.footprint_image_label]:
            if label:
                label.setAlignment(Qt.AlignCenter)
                label.setWordWrap(True)

        self._connect_signals()
        self.clear_images()

    def resizeEvent(self, event):
        """Handle resize events to rescale images to fit the new size."""
        super().resizeEvent(event)
        self._rescale_images()

    def showEvent(self, event):
        """Handle show events to ensure images are properly scaled when first displayed."""
        super().showEvent(event)
        # Use a single shot timer to rescale after the layout is complete
        from PySide6.QtCore import QTimer

        QTimer.singleShot(0, self._rescale_images)

    def _rescale_images(self):
        """Internal method to rescale both symbol and footprint images to current container sizes."""
        # Rescale symbol image
        if (
            self._original_symbol_pixmap
            and not self._original_symbol_pixmap.isNull()
            and self.symbol_image_label
        ):
            w = self.symbol_image_label.width()
            h = self.symbol_image_label.height()
            # Use a minimum size to ensure good scaling even if container reports small size
            w = max(w, 250)
            h = max(h, 250)
            logger.debug(f"Symbol label dimensions: {w}x{h}")
            if w > 0 and h > 0:
                scaled_pixmap = self._original_symbol_pixmap.scaled(
                    w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self.symbol_image_label.setPixmap(scaled_pixmap)

        # Rescale footprint image
        if (
            self._original_footprint_pixmap
            and not self._original_footprint_pixmap.isNull()
            and self.footprint_image_label
        ):
            w = self.footprint_image_label.width()
            h = self.footprint_image_label.height()
            # Use a minimum size to ensure good scaling even if container reports small size
            w = max(w, 250)
            h = max(h, 250)
            logger.debug(f"Footprint label dimensions: {w}x{h}")
            if w > 0 and h > 0:
                scaled_pixmap = self._original_footprint_pixmap.scaled(
                    w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self.footprint_image_label.setPixmap(scaled_pixmap)
                logger.debug(
                    f"Scaled footprint pixmap to: {scaled_pixmap.width()}x{scaled_pixmap.height()}"
                )

    def _connect_signals(self):
        if self.search_button:
            self.search_button.clicked.connect(self.on_search_button_clicked)
        if self.search_input:
            self.search_input.returnPressed.connect(self.on_search_button_clicked)
        if self.results_tree:
            self.results_tree.currentItemChanged.connect(self.on_tree_item_selected)
        if self.add_to_library_button:
            self.add_to_library_button.clicked.connect(self.add_to_library_requested)
        if self.back_to_library_button:
            self.back_to_library_button.clicked.connect(self.back_to_library_requested)

    def clear_images(self):
        # Clear stored pixmaps
        self._original_symbol_pixmap = None
        self._original_footprint_pixmap = None

        if self.symbol_image_label:
            self.symbol_image_label.clear()
            self.symbol_image_label.setText("Select a component to see its symbol")
        if self.footprint_image_label:
            self.footprint_image_label.clear()
            self.footprint_image_label.setText(
                "Select a component to see its footprint"
            )
        if self.hero_image_widget:
            self.hero_image_widget.clear()
        if self.part_info_widget:
            self.part_info_widget.clear()
        self.label_3dModelStatus.setText("3D Model: (Not found)")
        self.datasheetLink.setText('Datasheet: <a href="#">(Not available)</a>')

    def on_search_button_clicked(self):
        search_term = self.search_input.text().strip()
        if search_term:
            self.search_requested.emit(search_term)

    def on_tree_item_selected(self, current, previous):
        if current:
            self.item_selected.emit(current.data(0, Qt.UserRole))
        else:
            self.item_selected.emit(None)

    def update_search_results(self, results: List[SearchResult]):
        if self.results_tree:
            self.results_tree.currentItemChanged.disconnect(self.on_tree_item_selected)
            self.results_tree.clear()
            if not results:
                item = QTreeWidgetItem(["No results found."])
                item.setDisabled(True)
                self.results_tree.addTopLevelItem(item)
            else:
                for result in results:
                    item = QTreeWidgetItem(
                        [
                            result.manufacturer,
                            result.part_name,
                            result.lcsc_id,
                            result.description,
                        ]
                    )
                    item.setData(0, Qt.UserRole, result)
                    self.results_tree.addTopLevelItem(item)
            self.results_tree.currentItemChanged.connect(self.on_tree_item_selected)

    def set_symbol_loading(self, loading: bool):
        if loading and self.symbol_image_label:
            self.symbol_image_label.setText("Loading...")

    def set_footprint_loading(self, loading: bool):
        if loading and self.footprint_image_label:
            self.footprint_image_label.setText("Loading...")

    def set_symbol_error(self, message: str):
        if self.symbol_image_label:
            self.symbol_image_label.setText(f"Error:\n{message}")

    def set_footprint_error(self, message: str):
        if self.footprint_image_label:
            self.footprint_image_label.setText(f"Error:\n{message}")

    def set_symbol_image(self, pixmap: QPixmap):
        if self.symbol_image_label:
            if not pixmap.isNull():
                # Store the original for future rescaling
                self._original_symbol_pixmap = pixmap

                # Get the current label dimensions
                w = self.symbol_image_label.width()
                h = self.symbol_image_label.height()

                # If dimensions aren't available yet, use the minimum size from UI
                if w <= 0 or h <= 0:
                    w = self.symbol_image_label.minimumWidth() or 250
                    h = self.symbol_image_label.minimumHeight() or 250

                # Use a minimum size to ensure good scaling
                w = max(w, 250)
                h = max(h, 250)

                scaled_pixmap = pixmap.scaled(
                    w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self.symbol_image_label.setPixmap(scaled_pixmap)
            else:
                self._original_symbol_pixmap = None
                self.symbol_image_label.setText("Symbol Not Available")

    def set_footprint_image(self, pixmap: QPixmap):
        if self.footprint_image_label:
            if not pixmap.isNull():
                # Store the original for future rescaling
                self._original_footprint_pixmap = pixmap

                # Get the current label dimensions
                w = self.footprint_image_label.width()
                h = self.footprint_image_label.height()

                # If dimensions aren't available yet, use the minimum size from UI
                if w <= 0 or h <= 0:
                    w = self.footprint_image_label.minimumWidth() or 250
                    h = self.footprint_image_label.minimumHeight() or 250

                scaled_pixmap = pixmap.scaled(
                    w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self.footprint_image_label.setPixmap(scaled_pixmap)
            else:
                self._original_footprint_pixmap = None
                self.footprint_image_label.setText("Footprint Not Available")

    def get_footprint_pixmap(self) -> QPixmap:
        if self.footprint_image_label and self.footprint_image_label.pixmap():
            return self.footprint_image_label.pixmap()
        return None

    def set_search_button_enabled(self, enabled: bool):
        if self.search_button:
            self.search_button.setEnabled(enabled)

    def set_search_button_text(self, text: str):
        if self.search_button:
            self.search_button.setText(text)

    def set_details(self, result: SearchResult):
        if self.part_info_widget:
            self.part_info_widget.set_component(result)

        if self.hero_image_widget:
            if result.image.url:
                self.hero_image_widget.show_loading()
                self.request_image.emit(result.vendor, result.image.url, "hero")
            elif result.hero_image_cache_path:
                self.hero_image_widget.show_pixmap(
                    QPixmap(result.hero_image_cache_path)
                )
            else:
                self.hero_image_widget.show_image_not_available()

        if result.has_3d_model:
            self.label_3dModelStatus.setText("3D Model: Found")
        else:
            self.label_3dModelStatus.setText("3D Model: Not Found")

        if result.datasheet_url:
            self.datasheetLink.setText(
                f'<a href="{result.datasheet_url}">Open Datasheet</a>'
            )
        else:
            self.datasheetLink.setText("Datasheet: Not Available")

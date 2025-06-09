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
    QWidget,
    QVBoxLayout
)

from models.search_result import SearchResult

logger = logging.getLogger(__name__)

class SearchPage(QWidget):
    search_requested = Signal(str)
    item_selected = Signal(object)
    item_double_clicked = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)
        loader = QUiLoader()
        ui_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "page_search.ui")
        loaded_ui = loader.load(ui_file_path, self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(loaded_ui)

        # Find widgets
        self.search_input = loaded_ui.findChild(QLineEdit, "searchInput")
        self.search_button = loaded_ui.findChild(QPushButton, "button_Search")
        self.results_tree = loaded_ui.findChild(QTreeWidget, "searchResultsTree")
        self.symbol_image_label = loaded_ui.findChild(QLabel, "image_symbol")
        self.footprint_image_label = loaded_ui.findChild(QLabel, "image_footprint")

        # Configure widgets for text display
        for label in [self.symbol_image_label, self.footprint_image_label]:
            label.setAlignment(Qt.AlignCenter)
            label.setWordWrap(True)

        self._connect_signals()
        self.clear_images()

    def _connect_signals(self):
        self.search_button.clicked.connect(self.on_search_button_clicked)
        self.search_input.returnPressed.connect(self.on_search_button_clicked)
        self.results_tree.currentItemChanged.connect(self.on_tree_item_selected)
        self.results_tree.itemDoubleClicked.connect(self.on_tree_item_double_clicked)

    def clear_images(self):
        """Clears both image panes and resets their text."""
        self.symbol_image_label.clear() # Clears both text and pixmap
        self.footprint_image_label.clear()
        self.symbol_image_label.setText("Select a component to see its symbol")
        self.footprint_image_label.setText("Select a component to see its footprint")

    def on_search_button_clicked(self):
        search_term = self.search_input.text().strip()
        if search_term:
            self.search_requested.emit(search_term)

    def on_tree_item_selected(self, current, previous):
        self.item_selected.emit(current.data(0, Qt.UserRole) if current else None)

    def on_tree_item_double_clicked(self, item, column):
        self.item_double_clicked.emit(item.data(0, Qt.UserRole) if item else None)

    def update_search_results(self, results: List[SearchResult]):
        self.results_tree.currentItemChanged.disconnect(self.on_tree_item_selected)
        try:
            self.results_tree.clear()
            if not results:
                self.results_tree.addTopLevelItem(QTreeWidgetItem(["No results found."]))
                return
            for result in results:
                item = QTreeWidgetItem([result.manufacturer, result.part_name, result.lcsc_id, result.description])
                item.setData(0, Qt.UserRole, result)
                self.results_tree.addTopLevelItem(item)
        finally:
            self.results_tree.currentItemChanged.connect(self.on_tree_item_selected)

    def set_symbol_loading(self, loading: bool):
        if loading:
            self.symbol_image_label.setText("Loading...")

    def set_footprint_loading(self, loading: bool):
        if loading:
            self.footprint_image_label.setText("Loading...")

    def set_symbol_error(self, message: str):
        self.symbol_image_label.setText(f"Error:\n{message}")

    def set_footprint_error(self, message: str):
        self.footprint_image_label.setText(f"Error:\n{message}")

    def set_symbol_image(self, pixmap: QPixmap):
        if not pixmap.isNull():
            self.symbol_image_label.setPixmap(pixmap.scaled(self.symbol_image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.symbol_image_label.setText("Symbol Not Available")

    def set_footprint_image(self, pixmap: QPixmap):
        if not pixmap.isNull():
            self.footprint_image_label.setPixmap(pixmap.scaled(self.footprint_image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.footprint_image_label.setText("Footprint Not Available")

    def get_footprint_pixmap(self) -> QPixmap:
        if self.footprint_image_label.pixmap():
            return self.footprint_image_label.pixmap()
        return None

    def set_search_button_enabled(self, enabled: bool):
        self.search_button.setEnabled(enabled)

    def set_search_button_text(self, text: str):
        self.search_button.setText(text)

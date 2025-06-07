
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
    # Signals to communicate with the main controller
    search_requested = Signal(str)
    item_selected = Signal(object)
    item_double_clicked = Signal(object)

    def __init__(self, parent=None):
        super().__init__(parent)

        # Load the UI from the .ui file
        loader = QUiLoader()
        ui_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "search_page.ui")
        loaded_ui = loader.load(ui_file_path, self)

        # Add the loaded UI to this widget's layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(loaded_ui)

        # Find widgets from the loaded UI tree
        self.search_input = loaded_ui.findChild(QLineEdit, "searchInput")
        self.search_button = loaded_ui.findChild(QPushButton, "button_Search")
        self.results_tree = loaded_ui.findChild(QTreeWidget, "searchResultsTree")
        self.symbol_image_label = loaded_ui.findChild(QLabel, "image_symbol")
        self.footprint_image_label = loaded_ui.findChild(QLabel, "image_footprint")

        self._connect_signals()

    def _connect_signals(self):
        """Connects widget signals to handler methods."""
        self.search_button.clicked.connect(self.on_search_button_clicked)
        self.search_input.returnPressed.connect(self.on_search_button_clicked)
        self.results_tree.currentItemChanged.connect(self.on_tree_item_selected)
        self.results_tree.itemDoubleClicked.connect(self.on_tree_item_double_clicked)

    def on_search_button_clicked(self):
        search_term = self.search_input.text().strip()
        if search_term:
            self.search_requested.emit(search_term)

    def on_tree_item_selected(self, current_item: QTreeWidgetItem, previous_item: QTreeWidgetItem):
        if current_item:
            result = current_item.data(0, Qt.UserRole)
            self.item_selected.emit(result)
        else:
            self.item_selected.emit(None)

    def on_tree_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        if item:
            result = item.data(0, Qt.UserRole)
            self.item_double_clicked.emit(result)

    def update_search_results(self, results: List[SearchResult]):
        """Populates the tree widget with search results."""
        # --- FIX: Disconnect signal to prevent a "signal storm" during model update ---
        self.results_tree.currentItemChanged.disconnect(self.on_tree_item_selected)
        try:
            self.results_tree.clear()
            if not results:
                item = QTreeWidgetItem(["No results found."])
                self.results_tree.addTopLevelItem(item)
                return
            for result in results:
                item = QTreeWidgetItem([result.manufacturer, result.part_name, result.lcsc_id, result.description])
                item.setData(0, Qt.UserRole, result)
                self.results_tree.addTopLevelItem(item)
        finally:
            # --- Reconnect signal after the model is updated ---
            self.results_tree.currentItemChanged.connect(self.on_tree_item_selected)

    def set_symbol_image(self, pixmap: QPixmap):
        if not pixmap.isNull():
            # Use the label's size for scaling, which is now fixed
            self.symbol_image_label.setPixmap(pixmap.scaled(self.symbol_image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.symbol_image_label.setText("Symbol N/A")

    def set_footprint_image(self, pixmap: QPixmap):
        if not pixmap.isNull():
            self.footprint_image_label.setPixmap(pixmap.scaled(self.footprint_image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.footprint_image_label.setText("Footprint N/A")

    def get_footprint_pixmap(self) -> QPixmap:
        """Returns the current footprint pixmap."""
        if self.footprint_image_label:
            return self.footprint_image_label.pixmap()
        return None

    def set_search_button_enabled(self, enabled: bool):
        self.search_button.setEnabled(enabled)

    def set_search_button_text(self, text: str):
        self.search_button.setText(text)

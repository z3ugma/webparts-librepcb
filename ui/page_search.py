import logging
import os
from typing import List

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QFont
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QLabel,
    QLineEdit,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QWidget,
    QVBoxLayout,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPixmapItem,
    QGraphicsTextItem
)

from models.search_result import SearchResult

logger = logging.getLogger(__name__)

class SearchPage(QWidget):
    search_requested = Signal(str)
    item_selected = Signal(object)
    add_to_library_requested = Signal()
    request_image = Signal(str, str, str)
    back_to_library_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        loader = QUiLoader()
        ui_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "page_search.ui")
        loaded_ui = loader.load(ui_file_path, self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(loaded_ui)

        # Find widgets
        self.search_input = self.findChild(QLineEdit, "searchInput")
        self.search_button = self.findChild(QPushButton, "button_Search")
        self.add_to_library_button = self.findChild(QPushButton, "add_to_library_button")
        self.back_to_library_button = self.findChild(QPushButton, "back_to_library_button")
        self.results_tree = self.findChild(QTreeWidget, "searchResultsTree")
        self.symbol_image_label = self.findChild(QLabel, "image_symbol")
        self.footprint_image_label = self.findChild(QLabel, "image_footprint")
        
        self.label_LcscId = self.findChild(QLabel, "label_LcscId")
        self.label_PartTitle = self.findChild(QLabel, "label_PartTitle")
        self.mfn_value = self.findChild(QLabel, "mfn_value")
        self.mfn_part_value = self.findChild(QLabel, "mfn_part_value")
        self.description_value = self.findChild(QLabel, "description_value")
        self.hero_view = self.findChild(QGraphicsView, "image_hero_view")
        self.label_3dModelStatus = self.findChild(QLabel, "label_3dModelStatus")
        self.datasheetLink = self.findChild(QLabel, "datasheetLink")

        for label in [self.symbol_image_label, self.footprint_image_label]:
            if label:
                label.setAlignment(Qt.AlignCenter)
                label.setWordWrap(True)
        
        self._setup_hero_image()
        self._connect_signals()
        self.clear_images()

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
        self.hero_view.resetTransform()
        self.hero_pixmap_item.setPixmap(pixmap)
        self.hero_pixmap_item.setVisible(True)
        self.hero_text_item.setVisible(False)
        if pixmap.isNull() or self.hero_view.width() == 0:
            return
        scale = min((1.5 * self.hero_view.width()) / pixmap.width(), (1.5 * self.hero_view.height()) / pixmap.height())
        self.hero_view.scale(scale, scale)
        self.hero_view.centerOn(self.hero_pixmap_item)

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
        if self.symbol_image_label:
            self.symbol_image_label.clear()
            self.symbol_image_label.setText("Select a component to see its symbol")
        if self.footprint_image_label:
            self.footprint_image_label.clear()
            self.footprint_image_label.setText("Select a component to see its footprint")
        self._set_hero_text("No Image")
        self.label_LcscId.setText("LCSC ID: -")
        self.label_PartTitle.setText("No Part Loaded")
        self.mfn_value.setText("(select a part)")
        self.mfn_part_value.setText("")
        self.description_value.setText("")
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
                    item = QTreeWidgetItem([result.manufacturer, result.part_name, result.lcsc_id, result.description])
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
                self.symbol_image_label.setPixmap(pixmap.scaled(self.symbol_image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                self.symbol_image_label.setText("Symbol Not Available")

    def set_footprint_image(self, pixmap: QPixmap):
        if self.footprint_image_label:
            if not pixmap.isNull():
                self.footprint_image_label.setPixmap(pixmap.scaled(self.footprint_image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
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
        self.label_LcscId.setText(f"LCSC ID: {result.lcsc_id}")
        self.label_PartTitle.setText(result.part_name)
        self.mfn_value.setText(result.manufacturer)
        self.mfn_part_value.setText(result.mfr_part_number)
        self.description_value.setText(result.description)
        
        if result.image.url:
            self._set_hero_text("Loading...")
            self.request_image.emit(result.vendor, result.image.url, "hero")
        elif result.hero_image_cache_path:
            # If we have a cached path, load from there directly
            self._set_hero_pixmap(QPixmap(result.hero_image_cache_path))
        else:
            self._set_hero_text("Image Not Available")

        if result.has_3d_model:
            self.label_3dModelStatus.setText("3D Model: Found")
        else:
            self.label_3dModelStatus.setText("3D Model: Not Found")

        if result.datasheet_url:
            self.datasheetLink.setText(f'<a href="{result.datasheet_url}">Open Datasheet</a>')
        else:
            self.datasheetLink.setText("Datasheet: Not Available")

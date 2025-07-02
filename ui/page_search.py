import logging
import os
from pathlib import Path
from typing import List

from PySide6.QtCore import QObject, Qt, Signal, Slot, QThread
from PySide6.QtGui import QClipboard, QPixmap
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from adapters.search_engine import Vendor
from library_manager import LibraryManager
from models.library_part import LibraryPart
from models.search_result import SearchResult
from .hero_image_widget import HeroImageWidget
from .part_info_widget import PartInfoWidget
import constants as const

from .ui_workers import AddPartWorker

logger = logging.getLogger(__name__)


# --- Add to Library Dialog ---
class AddToLibraryDialog(QDialog):
    """
    Modal dialog to display add-to-library progress, with file and UI logging.
    """

    part_added_to_library = Signal(object)

    def __init__(self, search_result: SearchResult, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Adding {search_result.lcsc_id} to Library")
        self.setMinimumSize(700, 500)
        self.setModal(True)

        layout = QVBoxLayout(self)
        self.log_view = QPlainTextEdit(self)
        self.log_view.setReadOnly(True)
        self.log_view.setLineWrapMode(QPlainTextEdit.WidgetWidth)
        font = self.log_view.font()
        font.setFamily("monospace")
        self.log_view.setFont(font)
        layout.addWidget(self.log_view)

        button_box = QDialogButtonBox(self)
        self.copy_button = button_box.addButton(
            "Copy to Clipboard", QDialogButtonBox.ActionRole
        )
        self.ok_button = button_box.addButton(QDialogButtonBox.Ok)
        self.ok_button.setEnabled(False)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        self.copy_button.clicked.connect(self._on_copy_to_clipboard)
        layout.addWidget(button_box)

        self.library_part = None

        # --- Worker Setup ---
        self._thread = QThread(self)
        self._worker = AddPartWorker(search_result)
        self._worker.moveToThread(self._thread)

        # --- Connections ---
        self._worker.log_message.connect(self.log_view.appendPlainText)
        self._worker.add_part_succeeded.connect(self._on_add_part_succeeded)
        self._worker.add_part_failed.connect(self._on_add_part_failed)
        self._thread.started.connect(self._worker.run)
        self._thread.finished.connect(self._worker.deleteLater)
        self.finished.connect(self._thread.quit)  # Clean up thread when dialog closes

        self._thread.start()

    @Slot(object)
    def _on_add_part_succeeded(self, library_part):
        self.library_part = library_part
        self.log_view.appendPlainText("\n✅ Success!")
        self.ok_button.setEnabled(True)
        self._thread.quit()

    @Slot(str)
    def _on_add_part_failed(self, error_message):
        self.library_part = None
        self.log_view.appendPlainText(f"\n❌ Failed: {error_message}")
        self.ok_button.setEnabled(True)
        self._thread.quit()

    def accept(self):
        """
        Overrides QDialog.accept() to emit the part signal only when OK is clicked.
        """
        if self.library_part:
            self.part_added_to_library.emit(self.library_part)
        super().accept()

    @Slot()
    def _on_copy_to_clipboard(self):
        QApplication.clipboard().setText(self.log_view.toPlainText())
        logger.info("Log content copied to clipboard.")

    def done(self, result):
        if self._thread and self._thread.isRunning():
            self._thread.quit()
            self._thread.wait(1000)
        super().done(result)


class SearchPage(QWidget):
    search_requested = Signal(str)
    item_selected = Signal(object)
    part_added_to_library = Signal(object)
    request_image = Signal(Vendor, str, str)  # vendor_enum, image_url, image_type
    back_to_library_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._original_symbol_pixmap = None
        self._original_footprint_pixmap = None
        self._current_search_result = None
        self.library_manager = LibraryManager()
        self._load_ui()
        self._find_widgets()
        self._connect_signals()
        self.clear_images()

    def _load_ui(self):
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

    def _find_widgets(self):
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

    def _connect_signals(self):
        self.search_button.clicked.connect(self.on_search_button_clicked)
        self.search_input.returnPressed.connect(self.on_search_button_clicked)
        self.results_tree.currentItemChanged.connect(self.on_tree_item_selected)
        self.add_to_library_button.clicked.connect(self._on_add_to_library_clicked)
        self.back_to_library_button.clicked.connect(self.back_to_library_requested)

    def _on_add_to_library_clicked(self):
        if not self._current_search_result:
            logger.warning("Add to library clicked but no item selected.")
            return

        part_uuid = (
            self._current_search_result.uuid
            or f"search-{self._current_search_result.lcsc_id}"
        )
        if self.library_manager.part_exists(part_uuid):
            reply = QMessageBox.question(
                self,
                "Confirm Overwrite",
                f"The part '{self._current_search_result.part_name}' already exists in your library. Do you want to overwrite it?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if reply == QMessageBox.No:
                return

        dialog = AddToLibraryDialog(self._current_search_result, self)
        dialog.part_added_to_library.connect(self.part_added_to_library)
        dialog.show()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._rescale_images()

    def showEvent(self, event):
        super().showEvent(event)
        from PySide6.QtCore import QTimer

        QTimer.singleShot(0, self._rescale_images)

    def _rescale_images(self):
        if (
            self._original_symbol_pixmap
            and not self._original_symbol_pixmap.isNull()
            and self.symbol_image_label
        ):
            w = self.symbol_image_label.width()
            h = self.symbol_image_label.height()
            w = max(w, 250)
            h = max(h, 250)
            if w > 0 and h > 0:
                self.symbol_image_label.setPixmap(
                    self._original_symbol_pixmap.scaled(
                        w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                )
        if (
            self._original_footprint_pixmap
            and not self._original_footprint_pixmap.isNull()
            and self.footprint_image_label
        ):
            w = self.footprint_image_label.width()
            h = self.footprint_image_label.height()
            w = max(w, 250)
            h = max(h, 250)
            if w > 0 and h > 0:
                self.footprint_image_label.setPixmap(
                    self._original_footprint_pixmap.scaled(
                        w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation
                    )
                )

    def clear_images(self):
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
            self._current_search_result = current.data(0, Qt.UserRole)
            self.item_selected.emit(self._current_search_result)
        else:
            self._current_search_result = None
            self.item_selected.emit(None)

    def update_search_results(self, results: List[SearchResult]):
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
                self._original_symbol_pixmap = pixmap
                w = self.symbol_image_label.width()
                h = self.symbol_image_label.height()
                w = max(w, 250)
                h = max(h, 250)
                self.symbol_image_label.setPixmap(
                    pixmap.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
            else:
                self._original_symbol_pixmap = None
                self.symbol_image_label.setText(const.UIText.IMAGE_NOT_AVAILABLE.value)

    def set_footprint_image(self, pixmap: QPixmap):
        if self.footprint_image_label:
            if not pixmap.isNull():
                self._original_footprint_pixmap = pixmap
                w = self.footprint_image_label.width()
                h = self.footprint_image_label.height()
                w = max(w, 250)
                h = max(h, 250)
                self.footprint_image_label.setPixmap(
                    pixmap.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                )
            else:
                self._original_footprint_pixmap = None
                self.footprint_image_label.setText(
                    const.UIText.IMAGE_NOT_AVAILABLE.value
                )

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
                # Convert string vendor to Vendor enum
                try:
                    vendor_enum = Vendor(result.vendor)
                    self.request_image.emit(vendor_enum, result.image.url, "hero")
                except ValueError:
                    logger.warning(f"Unknown vendor: {result.vendor}")
                    self.hero_image_widget.show_image_not_available()
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

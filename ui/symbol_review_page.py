# ui/symbol_review_page.py
import json
import logging
import os
from typing import List, Tuple

from PySide6.QtCore import Qt, QThread
from PySide6.QtGui import QPixmap
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QCheckBox,
    QHeaderView,
    QPushButton,
)

from models.elements import LibrePCBElement
from models.status import ElementManifest, ValidationSeverity, ValidationMessage
from models.library_part import LibraryPart
from library_manager import LibraryManager
from .library_element_image_widget import LibraryElementImageWidget
from .ui_workers import SymbolUpdateWorker

logger = logging.getLogger(__name__)


class SymbolReviewPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.library_part = None
        self.manifest = None
        self.library_manager = LibraryManager()

        loader = QUiLoader()
        loader.registerCustomWidget(LibraryElementImageWidget)
        ui_file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "symbol_review_page.ui"
        )
        self.ui = loader.load(ui_file_path, self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ui)

        self.vertical_splitter = self.ui.findChild(QSplitter, "vertical_splitter")
        if self.vertical_splitter:
            self.vertical_splitter.setSizes([300, 100])

        self.symbol_splitter = self.ui.findChild(QSplitter, "symbol_splitter")
        if self.symbol_splitter:
            self.symbol_splitter.setSizes([200, 200])

        self.easyeda_preview = self.ui.findChild(
            LibraryElementImageWidget, "easyedaSymbolView"
        )
        self.librepcb_preview = self.ui.findChild(
            LibraryElementImageWidget, "librepcbSymbolView"
        )
        self.symbol_message_list = self.ui.findChild(
            QTreeWidget, "symbolMessageList"
        )

        if self.symbol_message_list:
            self.symbol_message_list.setColumnCount(3)
            self.symbol_message_list.setHeaderLabels(
                ["Approved", "Severity", "Message"]
            )
            header = self.symbol_message_list.header()
            header.setSectionResizeMode(2, QHeaderView.Stretch)
            self.symbol_message_list.setColumnWidth(0, 80)
            self.symbol_message_list.setColumnWidth(1, 60)
            self.symbol_message_list.setHeaderHidden(False)
        else:
            logger.error("Could not find 'symbolMessageList' widget.")

        self.refresh_button = self.ui.findChild(QPushButton, "button_RefreshSymbol")
        if self.refresh_button:
            self.refresh_button.clicked.connect(self._on_refresh_checks_clicked)
        else:
            logger.error("Could not find 'button_RefreshSymbol' widget.")

    def set_library_part(self, part: LibraryPart):
        self.library_part = part
        manifest_path = LibrePCBElement.SYMBOL.get_wp_path(part.symbol.uuid)
        if manifest_path.exists():
            try:
                self.manifest = ElementManifest.model_validate_json(
                    manifest_path.read_text()
                )
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to parse symbol manifest {manifest_path}: {e}")
                self.manifest = None
        else:
            logger.warning(f"Symbol manifest not found at {manifest_path}")
            self.manifest = None
        self._load_validation_messages()

    def set_symbol_image(self, pixmap: QPixmap):
        if self.easyeda_preview:
            self.easyeda_preview.show_pixmap(pixmap)

    def set_librepcb_symbol_image(self, pixmap: QPixmap):
        if self.librepcb_preview:
            self.librepcb_preview.show_pixmap(pixmap)

    def _on_refresh_checks_clicked(self):
        if not self.library_part:
            return
        self.refresh_button.setEnabled(False)
        self.refresh_button.setText("Refreshing...")

        self.refresh_thread = QThread(self)
        self.refresh_worker = SymbolUpdateWorker(self.library_part)
        self.refresh_worker.moveToThread(self.refresh_thread)
        self.refresh_worker.update_complete.connect(self._on_update_complete)
        self.refresh_worker.update_failed.connect(self._on_update_failed)
        self.refresh_thread.started.connect(self.refresh_worker.run)
        self.refresh_worker.finished.connect(self.refresh_thread.quit)
        self.refresh_thread.finished.connect(self.refresh_thread.deleteLater)
        self.refresh_worker.finished.connect(self.refresh_worker.deleteLater)
        self.refresh_thread.start()

    def _on_update_complete(self, png_path: str, issues: list):
        if png_path:
            self.set_librepcb_symbol_image(QPixmap(png_path))
        self.manifest = self.library_manager.reconcile_and_save_symbol_manifest(
            self.library_part, issues
        )
        self._load_validation_messages()
        self.refresh_button.setEnabled(True)
        self.refresh_button.setText("Refresh Checks")

    def _on_update_failed(self, error_message: str):
        logger.error(f"Symbol update failed: {error_message}")
        self.refresh_button.setEnabled(True)
        self.refresh_button.setText("Refresh Checks")

    def _load_validation_messages(self):
        if not self.library_part or not self.symbol_message_list:
            return
        self.symbol_message_list.clear()
        if not self.manifest:
            return

        for index, msg in enumerate(self.manifest.validation):
            item = QTreeWidgetItem(self.symbol_message_list)
            item.setData(0, Qt.UserRole, index)
            item.setText(1, self._get_icon_for_severity(msg.severity))
            item.setTextAlignment(1, Qt.AlignCenter)
            msg_text = msg.message
            if msg.count > 1:
                msg_text += f" ({msg.count} occurrences)"
            item.setText(2, msg_text)

            checkbox = QCheckBox()
            checkbox.setChecked(msg.is_approved)
            checkbox.stateChanged.connect(
                lambda state, idx=index: self._on_approval_changed(state, idx)
            )
            container = QWidget()
            layout = QHBoxLayout(container)
            layout.addWidget(checkbox)
            layout.setAlignment(Qt.AlignCenter)
            layout.setContentsMargins(0, 0, 0, 0)
            self.symbol_message_list.setItemWidget(item, 0, container)

    def _on_approval_changed(self, state: int, msg_index: int):
        if not self.manifest or not (0 <= msg_index < len(self.manifest.validation)):
            return
        is_checked = state == Qt.CheckState.Checked.value
        self.library_manager.update_symbol_approval_status(
            self.library_part, msg_index, is_checked
        )
        self.manifest.validation[msg_index].is_approved = is_checked

    def _get_icon_for_severity(self, severity: ValidationSeverity) -> str:
        if severity == ValidationSeverity.WARNING:
            return "⚠️"
        if severity == ValidationSeverity.HINT:
            return "💡"
        if severity == ValidationSeverity.ERROR:
            return "❌"
        return ""

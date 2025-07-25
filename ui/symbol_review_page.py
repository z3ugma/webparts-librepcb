# ui/symbol_review_page.py
import json
import logging
import os
import subprocess
import sys
from typing import List, Tuple

from PySide6.QtCore import Qt, QThread, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QPixmap
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
    QLabel,
)

from models.elements import LibrePCBElement
from models.status import (
    ElementManifest,
    ValidationSeverity,
    ValidationMessage,
    StatusValue,
    ValidationSource,
)
from models.library_part import LibraryPart
from library_manager import LibraryManager
from .library_element_image_widget import LibraryElementImageWidget
from .ui_workers import ElementUpdateWorker

logger = logging.getLogger(__name__)


class SymbolReviewPage(QWidget):
    status_changed = Signal()

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
        self.symbol_message_list = self.ui.findChild(QTreeWidget, "symbolMessageList")

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
            self.symbol_message_list.setStyleSheet(
                """
                QCheckBox:disabled {
                    color: #909090;
                }
                QCheckBox::indicator:disabled {
                    background-color: #e0e0e0;
                    border: 1px solid #c0c0c0;
                }
            """
            )
        else:
            logger.error("Could not find 'symbolMessageList' widget.")

        self.refresh_button = self.ui.findChild(QPushButton, "button_RefreshSymbol")
        if self.refresh_button:
            self.refresh_button.clicked.connect(self._on_refresh_checks_clicked)
        else:
            logger.error("Could not find 'button_RefreshSymbol' widget.")

        self.approve_button = self.ui.findChild(QPushButton, "button_ApproveSymbol")
        if self.approve_button:
            self.approve_button.clicked.connect(self._on_approve_clicked)
        else:
            logger.error("Could not find 'button_ApproveSymbol' widget.")

        # Find header and UUID labels
        self.header_label = self.ui.findChild(QLabel, "label_SymbolHeader")
        self.uuid_label = self.ui.findChild(QLabel, "label_SymbolUUID")
        if self.uuid_label:
            self.uuid_label.linkActivated.connect(self._on_uuid_clicked)
        else:
            logger.error("Could not find 'label_SymbolUUID' widget.")

    def _on_approve_clicked(self):
        if not self.library_part or not self.manifest:
            logger.warning("Approve clicked but no library part or manifest is set.")
            return

        current_status = self.manifest.status
        new_status = (
            StatusValue.NEEDS_REVIEW
            if current_status == StatusValue.APPROVED
            else StatusValue.APPROVED
        )

        self.library_manager.set_symbol_manifest_status(self.library_part, new_status)
        self.manifest.status = new_status
        self._update_button_state()
        self.status_changed.emit()

    def _update_button_state(self):
        if not self.manifest or not self.approve_button:
            return

        if self.manifest.status == StatusValue.APPROVED:
            self.approve_button.setText("Reject")
            self.approve_button.setStyleSheet("background-color: #e6b8b8;")
        else:
            self.approve_button.setText("Approve")
            self.approve_button.setStyleSheet("")

    def _on_uuid_clicked(self, link: str):
        """Opens the symbol folder in Finder when UUID link is clicked."""
        logger.info(f"UUID link clicked: {link}")
        if not self.library_part or not self.library_part.symbol:
            logger.warning("No library part or symbol set")
            return

        sym_dir_absolute = LibrePCBElement.SYMBOL.get_element_dir_absolute(
            self.library_part.symbol.uuid
        )

        if not sym_dir_absolute:
            logger.error(
                f"Symbol directory not found for UUID: {self.library_part.symbol.uuid}"
            )
            return

        logger.info(f"Opening symbol directory: {sym_dir_absolute}")

        # Use Qt's cross-platform method with absolute path
        url = QUrl.fromLocalFile(str(sym_dir_absolute))
        success = QDesktopServices.openUrl(url)

        if not success:
            logger.warning("QDesktopServices failed, trying platform-specific method")
            # Fall back to platform-specific method
            try:
                if sys.platform == "darwin":  # macOS
                    subprocess.run(["open", str(sym_dir_absolute)], check=True)
                elif sys.platform == "win32":  # Windows
                    subprocess.run(["explorer", str(sym_dir_absolute)], check=True)
                else:  # Linux and others
                    subprocess.run(["xdg-open", str(sym_dir_absolute)], check=True)
                logger.info(
                    f"Successfully opened folder using platform-specific method"
                )
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to open folder: {e}")
        else:
            logger.info(f"Successfully opened folder using QDesktopServices")

    def set_library_part(self, part: LibraryPart):
        self.library_part = part

        # Update header with symbol name (hydrated from symbol.lp file)
        if self.header_label and part.symbol:
            symbol_name = part.symbol.name or "Unknown Symbol"
            self.header_label.setText(f"<h1>{symbol_name}</h1>")

        # Update UUID label with clickable link
        if self.uuid_label and part.symbol:
            uuid_str = str(part.symbol.uuid)
            self.uuid_label.setText(f'<a href="#">{uuid_str}</a>')

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
        self._update_button_state()

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
        self.refresh_worker = ElementUpdateWorker(
            self.library_part, LibrePCBElement.SYMBOL
        )
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
        self.library_manager._update_element_manifest(
            LibrePCBElement.SYMBOL, self.library_part.symbol.uuid, issues
        )
        # We need to re-load the manifest from disk to get the latest changes
        manifest_path = LibrePCBElement.SYMBOL.get_wp_path(
            self.library_part.symbol.uuid
        )
        if manifest_path.exists():
            self.manifest = ElementManifest.model_validate_json(
                manifest_path.read_text()
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
            logger.warning("Cannot load messages: manifest not loaded.")
            return

        for index, msg in enumerate(self.manifest.validation):
            item = QTreeWidgetItem(self.symbol_message_list)
            item.setData(0, Qt.UserRole, index)
            item.setText(1, self._get_icon_for_severity(msg.severity))
            item.setTextAlignment(1, Qt.AlignCenter)
            item.setText(2, msg.message)

            checkbox = QCheckBox()
            checkbox.setChecked(msg.is_approved)

            # Disable checkbox for read-only (LibrePCB) messages
            is_readonly = msg.source == ValidationSource.LIBREPCB
            if is_readonly:
                checkbox.setEnabled(False)
                item.setToolTip(
                    2, "This check is from LibrePCB and cannot be approved here."
                )
            else:
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

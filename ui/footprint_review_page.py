import json
import logging
import os
import subprocess
import sys

from PySide6.QtCore import Qt, QThread, QUrl, Signal
from PySide6.QtGui import QDesktopServices, QPixmap
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QCheckBox,
    QGraphicsView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QSplitter,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)

from library_manager import LibraryManager
from models.elements import LibrePCBElement
from models.library_part import LibraryPart
from models.status import (
    ElementManifest,
    StatusValue,
    ValidationSeverity,
    ValidationSource,
)

from .library_element_image_widget import LibraryElementImageWidget
from .ui_workers import ElementUpdateWorker

logger = logging.getLogger(__name__)


class FootprintReviewPage(QWidget):
    """
    A custom widget that encapsulates the footprint review page functionality.
    """

    status_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.library_part = None
        self.manifest = None
        self.library_manager = LibraryManager()

        loader = QUiLoader()
        # Register the custom widget for promotion
        loader.registerCustomWidget(LibraryElementImageWidget)
        ui_file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "footprint_review_page.ui"
        )
        self.ui = loader.load(ui_file_path, self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ui)

        self.vertical_splitter = self.ui.findChild(QSplitter, "vertical_splitter")
        if self.vertical_splitter:
            # Set initial size ratio to 3:1 (images:messages)
            self.vertical_splitter.setSizes([300, 100])
        else:
            logger.error("Could not find 'vertical_splitter' in the UI.")

        self.footprint_splitter = self.ui.findChild(QSplitter, "footprint_splitter")
        if self.footprint_splitter:
            # Set initial size ratio to 1:1 (left:right)
            self.footprint_splitter.setSizes([200, 200])
        else:
            logger.error("Could not find 'footprint_splitter' in the UI.")

        self._setup_easyeda_preview()

        # The generated preview is now a custom widget promoted from the UI file
        self.footprint_message_list = self.ui.findChild(
            QTreeWidget, "footprintMessageList"
        )
        if self.footprint_message_list:
            self.footprint_message_list.setColumnCount(3)
            self.footprint_message_list.setHeaderLabels(
                ["Approved", "Severity", "Message"]
            )
            header = self.footprint_message_list.header()
            header.setSectionResizeMode(2, QHeaderView.Stretch)
            self.footprint_message_list.setColumnWidth(0, 80)  # Approved
            self.footprint_message_list.setColumnWidth(1, 60)  # Severity
            self.footprint_message_list.setHeaderHidden(False)
            self.footprint_message_list.setStyleSheet("""
                QCheckBox:disabled {
                    color: #909090;
                }
                QCheckBox::indicator:disabled {
                    background-color: #e0e0e0;
                 
                }
            """)
        else:
            logger.error("Could not find 'footprintMessageList' widget.")

        self.librepcb_preview = self.ui.findChild(
            LibraryElementImageWidget, "librepcbFootprintView"
        )
        if self.librepcb_preview:
            self.librepcb_preview.show_text("Loading...")
        else:
            logger.error("Could not find 'librepcbFootprintView' widget.")

        self.refresh_button = self.ui.findChild(QPushButton, "button_RefreshFootprint")
        if self.refresh_button:
            self.refresh_button.clicked.connect(self._on_refresh_checks_clicked)
        else:
            logger.error("Could not find 'button_RefreshFootprint' widget.")

        # Find header and UUID labels
        self.header_label = self.ui.findChild(QLabel, "label_FootprintHeader")
        self.uuid_label = self.ui.findChild(QLabel, "label_FootprintUUID")
        if self.uuid_label:
            self.uuid_label.linkActivated.connect(self._on_uuid_clicked)
        else:
            logger.error("Could not find 'label_FootprintUUID' widget.")

        self.approve_button = self.ui.findChild(QPushButton, "button_ApproveFootprint")
        if self.approve_button:
            self.approve_button.clicked.connect(self._on_approve_clicked)
        else:
            logger.error("Could not find 'button_ApproveFootprint' widget.")

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

        self.library_manager.set_footprint_manifest_status(
            self.library_part, new_status
        )
        self.manifest.status = new_status  # Update in-memory manifest
        self._update_button_state()
        self.status_changed.emit()

    def _update_button_state(self):
        if not self.manifest or not self.approve_button:
            return

        if self.manifest.status == StatusValue.APPROVED:
            self.approve_button.setText("Reject")
            # You can also add styling here, e.g., for a "rejection" state
            self.approve_button.setStyleSheet("background-color: #e6b8b8;")
        else:
            self.approve_button.setText("Approve")
            self.approve_button.setStyleSheet("")  # Reset to default stylesheet

    def _on_uuid_clicked(self, link: str):
        """Opens the package folder in Finder when UUID link is clicked."""
        logger.info(f"UUID link clicked: {link}")
        if not self.library_part or not self.library_part.footprint:
            logger.warning("No library part or footprint set")
            return

        pkg_dir_absolute = LibrePCBElement.PACKAGE.get_element_dir_absolute(
            self.library_part.footprint.uuid
        )

        if not pkg_dir_absolute:
            logger.error(
                f"Package directory not found for UUID: {self.library_part.footprint.uuid}"
            )
            return

        logger.info(f"Opening package directory: {pkg_dir_absolute}")

        # Use Qt's cross-platform method with absolute path
        url = QUrl.fromLocalFile(str(pkg_dir_absolute))
        success = QDesktopServices.openUrl(url)

        if not success:
            logger.warning("QDesktopServices failed, trying platform-specific method")
            # Fall back to platform-specific method
            try:
                if sys.platform == "darwin":  # macOS
                    subprocess.run(["open", str(pkg_dir_absolute)], check=True)
                elif sys.platform == "win32":  # Windows
                    subprocess.run(["explorer", str(pkg_dir_absolute)], check=True)
                else:  # Linux and others
                    subprocess.run(["xdg-open", str(pkg_dir_absolute)], check=True)
                logger.info("Successfully opened folder using platform-specific method")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to open folder: {e}")
        else:
            logger.info("Successfully opened folder using QDesktopServices")

    def _on_refresh_checks_clicked(self):
        if not self.library_part:
            logger.warning("Refresh clicked but no library part is set.")
            return

        self.refresh_button.setEnabled(False)
        self.refresh_button.setText("Refreshing...")

        self.refresh_thread = QThread(self)
        self.refresh_worker = ElementUpdateWorker(
            self.library_part, LibrePCBElement.PACKAGE
        )
        self.refresh_worker.moveToThread(self.refresh_thread)

        # Connections
        self.refresh_worker.update_complete.connect(self._on_update_complete)
        self.refresh_worker.update_failed.connect(self._on_update_failed)
        self.refresh_thread.started.connect(self.refresh_worker.run)

        # Cleanup: When the worker is done, it tells the thread to quit.
        self.refresh_worker.finished.connect(self.refresh_thread.quit)
        # When the thread is finished, schedule both for deletion.
        self.refresh_thread.finished.connect(self.refresh_thread.deleteLater)
        self.refresh_worker.finished.connect(self.refresh_worker.deleteLater)

        self.refresh_thread.start()

    def _on_update_complete(self, png_path: str, issues: list):
        logger.info("Footprint update complete. Refreshing UI.")
        if png_path:
            self.set_librepcb_footprint_image(QPixmap(png_path))

        # Reconcile and update the manifest
        self.library_manager._update_element_manifest(
            LibrePCBElement.PACKAGE, self.library_part.footprint.uuid, issues
        )
        # We need to re-load the manifest from disk to get the latest changes
        manifest_path = LibrePCBElement.PACKAGE.get_wp_path(
            self.library_part.footprint.uuid
        )
        if manifest_path.exists():
            self.manifest = ElementManifest.model_validate_json(
                manifest_path.read_text()
            )

        # Reload messages into the UI
        self._load_validation_messages()

        self.refresh_button.setEnabled(True)
        self.refresh_button.setText("Refresh Checks")

    def _on_update_failed(self, error_message: str):
        logger.error(f"Footprint update failed: {error_message}")
        self.refresh_button.setEnabled(True)
        self.refresh_button.setText("Refresh Checks")

    def _on_approval_changed(self, state: int, msg_index: int):
        """
        Handles the state change of an approval checkbox.
        """
        if not self.manifest or not (0 <= msg_index < len(self.manifest.validation)):
            logger.error(f"Cannot update approval for invalid index {msg_index}")
            return

        is_checked = state == Qt.CheckState.Checked.value
        self.library_manager.update_footprint_approval_status(
            self.library_part, msg_index, is_checked
        )
        # Update the in-memory manifest to reflect the change immediately
        self.manifest.validation[msg_index].is_approved = is_checked
        logger.info(
            f"Delegated approval state change for message {msg_index} to {is_checked}."
        )

    def set_library_part(self, part: LibraryPart):
        """
        Sets the library part, loads its manifest, and populates the page.
        """
        self.library_part = part

        # Update header with footprint name (hydrated from package.lp file)
        if self.header_label and part.footprint:
            footprint_name = part.footprint.name or "Unknown Footprint"
            self.header_label.setText(f"<h1>{footprint_name}</h1>")

        # Update UUID label with clickable link
        if self.uuid_label and part.footprint:
            uuid_str = str(part.footprint.uuid)
            self.uuid_label.setText(f'<a href="#">{uuid_str}</a>')

        manifest_path = LibrePCBElement.PACKAGE.get_wp_path(
            self.library_part.footprint.uuid
        )
        if manifest_path.exists():
            try:
                self.manifest = ElementManifest.model_validate_json(
                    manifest_path.read_text()
                )
            except (json.JSONDecodeError, ValueError) as e:
                logger.error(f"Failed to parse manifest {manifest_path}: {e}")
                self.manifest = None
        else:
            logger.warning(f"Footprint manifest not found at {manifest_path}")
            self.manifest = None

        self._load_validation_messages()
        self._update_button_state()

    def _load_validation_messages(self):
        """
        Populates the tree widget from the in-memory manifest.
        """
        if not self.library_part or not self.footprint_message_list:
            return

        self.footprint_message_list.clear()

        if not self.manifest:
            logger.warning("Cannot load messages: manifest not loaded.")
            return

        for index, msg in enumerate(self.manifest.validation):
            item = QTreeWidgetItem(self.footprint_message_list)
            item.setData(0, Qt.UserRole, index)  # Store index on first column

            # Column 1: Severity Icon (centered)
            item.setText(1, self._get_icon_for_severity(msg.severity))
            item.setTextAlignment(1, Qt.AlignCenter)

            # Column 2: Message Text (left-aligned by default)
            item.setText(2, msg.message)

            # Column 0: Approved Checkbox (centered)
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

            # To center the checkbox, we place it inside a container widget with a centered layout
            container = QWidget()
            layout = QHBoxLayout(container)
            layout.addWidget(checkbox)
            layout.setAlignment(Qt.AlignCenter)
            layout.setContentsMargins(0, 0, 0, 0)
            self.footprint_message_list.setItemWidget(item, 0, container)

    def _get_icon_for_severity(self, severity: ValidationSeverity) -> str:
        if severity == ValidationSeverity.WARNING:
            return "⚠️"
        if severity == ValidationSeverity.HINT:
            return "💡"
        if severity == ValidationSeverity.ERROR:
            return "❌"
        return ""

    def _setup_easyeda_preview(self):
        """Configures the left-side image viewer for the EasyEDA footprint."""
        placeholder_view = self.ui.findChild(QGraphicsView, "footprint_image_container")
        if not placeholder_view:
            logger.error("Could not find 'footprint_image_container' in the UI.")
            return

        self.footprint_image_view = LibraryElementImageWidget(self)
        parent_layout = placeholder_view.parent().layout()
        if parent_layout:
            parent_layout.replaceWidget(placeholder_view, self.footprint_image_view)
            placeholder_view.deleteLater()
        else:
            logger.error("Could not find parent layout for EasyEDA preview.")

    def set_footprint_image(self, pixmap: QPixmap):
        """
        Sets the EasyEDA footprint image in the left-side container.
        """
        if hasattr(self, "footprint_image_view"):
            self.footprint_image_view.show_pixmap(pixmap)

    def set_librepcb_footprint_image(self, pixmap: QPixmap):
        """
        Sets the generated LibrePCB footprint image in the right-side container.
        """
        if hasattr(self, "librepcb_preview"):
            self.librepcb_preview.show_pixmap(pixmap)

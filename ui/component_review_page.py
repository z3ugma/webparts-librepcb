import os
import logging
from typing import Optional

from PySide6.QtCore import QObject, Qt, QThread, Signal, Slot
from PySide6.QtGui import QDesktopServices, QFont
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QWidget,
    QTreeWidgetItem,
    QTableWidgetItem,
    QCheckBox,
    QHeaderView,
)
from PySide6.QtCore import QUrl

from models.library_part import LibraryPart
from models.status import StatusValue, ValidationMessage, ValidationSeverity
from models.elements import LibrePCBElement
from library_manager import LibraryManager

logger = logging.getLogger(__name__)


class DeviceUpdateWorker(QObject):
    finished = Signal()
    error = Signal(str)

    def __init__(self, library_part: LibraryPart):
        super().__init__()
        self.library_part = library_part

    @Slot()
    def run(self):
        try:
            from workers.element_renderer import render_and_check_element

            logger.info("Re-rendering and checking device...")

            # Re-render and check the device
            _, issues = render_and_check_element(
                self.library_part, LibrePCBElement.DEVICE
            )

            # Update the manifest with validation results
            manager = LibraryManager()
            manager._update_element_manifest(
                LibrePCBElement.DEVICE, self.library_part.uuid, issues
            )

            logger.info("Device refresh complete.")
            self.finished.emit()

        except Exception as e:
            logger.error(f"Device refresh failed: {e}", exc_info=True)
            self.error.emit(str(e))


class ComponentUpdateWorker(QObject):
    finished = Signal()
    error = Signal(str)

    def __init__(self, library_part: LibraryPart):
        super().__init__()
        self.library_part = library_part

    @Slot()
    def run(self):
        try:
            from workers.element_renderer import render_and_check_element

            logger.info("Re-rendering and checking component...")

            # Re-render and check the component
            _, issues = render_and_check_element(
                self.library_part, LibrePCBElement.COMPONENT
            )

            # Update the manifest with validation results
            manager = LibraryManager()
            manager._update_element_manifest(
                LibrePCBElement.COMPONENT, self.library_part.component.uuid, issues
            )

            logger.info("Component refresh complete.")
            self.finished.emit()

        except Exception as e:
            logger.error(f"Component refresh failed: {e}", exc_info=True)
            self.error.emit(str(e))


class ComponentReviewPage(QWidget):
    status_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.library_part: Optional[LibraryPart] = None
        self.library_manager = LibraryManager()

        # Load UI
        loader = QUiLoader()
        ui_file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "component_review_page.ui"
        )
        self.ui_content = loader.load(ui_file_path, self)

        # Find widgets
        self._find_widgets()

        # Setup UI
        self._setup_ui()

        # Connect signals
        self._connect_signals()

    def _find_widgets(self):
        """Find and store references to UI widgets."""
        self.label_component_name = self.findChild(QWidget, "label_component_name")
        self.label_component_uuid = self.findChild(QWidget, "label_component_uuid")
        self.component_validation_tree = self.findChild(
            QWidget, "component_validation_tree"
        )
        self.device_validation_tree = self.findChild(QWidget, "device_validation_tree")
        self.button_refresh_component_checks = self.findChild(
            QWidget, "button_refresh_component_checks"
        )
        self.button_refresh_device_checks = self.findChild(
            QWidget, "button_refresh_device_checks"
        )

    def _setup_ui(self):
        """Setup the UI components."""
        # Setup component validation tree columns
        if self.component_validation_tree:
            self.component_validation_tree.setHeaderLabels(
                ["Approval", "Severity", "Message"]
            )
            header = self.component_validation_tree.header()
            header.setSectionResizeMode(
                0, QHeaderView.ResizeToContents
            )  # Approval column
            header.setSectionResizeMode(
                1, QHeaderView.ResizeToContents
            )  # Severity column
            header.setSectionResizeMode(2, QHeaderView.Stretch)  # Message column

            # Center-align the first two columns
            header.setDefaultAlignment(Qt.AlignCenter)

        # Setup device validation tree columns
        if self.device_validation_tree:
            self.device_validation_tree.setHeaderLabels(
                ["Approval", "Severity", "Message"]
            )
            header = self.device_validation_tree.header()
            header.setSectionResizeMode(
                0, QHeaderView.ResizeToContents
            )  # Approval column
            header.setSectionResizeMode(
                1, QHeaderView.ResizeToContents
            )  # Severity column
            header.setSectionResizeMode(2, QHeaderView.Stretch)  # Message column

            # Center-align the first two columns
            header.setDefaultAlignment(Qt.AlignCenter)

    def _connect_signals(self):
        """Connect widget signals to slots."""
        if self.button_refresh_component_checks:
            self.button_refresh_component_checks.clicked.connect(
                self._on_refresh_component_checks_clicked
            )
        if self.button_refresh_device_checks:
            self.button_refresh_device_checks.clicked.connect(
                self._on_refresh_device_checks_clicked
            )
        if self.label_component_uuid:
            self.label_component_uuid.linkActivated.connect(self._on_uuid_clicked)

    def set_library_part(self, library_part: LibraryPart):
        """Set the library part to display."""
        self.library_part = library_part
        self._load_component_info()
        self._load_component_validation_messages()
        self._load_device_validation_messages()

    def _load_component_info(self):
        """Load and display component information."""
        if not self.library_part or not self.library_part.component:
            return

        # Set component name
        if self.label_component_name:
            component_name = LibrePCBElement.COMPONENT.get_element_name(
                self.library_part.component.uuid
            )
            if component_name:
                self.label_component_name.setText(component_name)
            else:
                self.label_component_name.setText(self.library_part.part_name)

        # Set UUID link
        if self.label_component_uuid:
            self.label_component_uuid.setText(
                f'<a href="#">{self.library_part.component.uuid}</a>'
            )

    def _load_component_validation_messages(self):
        """Load and display component validation messages."""
        if not self.component_validation_tree or not self.library_part:
            return

        self.component_validation_tree.clear()

        # Read validation messages from component manifest
        manifest_path = LibrePCBElement.COMPONENT.get_wp_path(
            self.library_part.component.uuid
        )
        if not manifest_path or not manifest_path.exists():
            logger.warning("Cannot load component messages: manifest not loaded.")
            return

        try:
            from models.status import ElementManifest

            manifest = ElementManifest.model_validate_json(manifest_path.read_text())

            for msg in manifest.validation:
                self._add_validation_message_to_tree(
                    msg, self.component_validation_tree
                )

        except Exception as e:
            logger.error(f"Failed to load component validation messages: {e}")

    def _load_device_validation_messages(self):
        """Load and display device validation messages."""
        if not self.device_validation_tree or not self.library_part:
            return

        self.device_validation_tree.clear()

        # Read validation messages from device manifest (device uses main part UUID)
        manifest_path = LibrePCBElement.DEVICE.get_wp_path(self.library_part.uuid)
        if not manifest_path or not manifest_path.exists():
            logger.warning("Cannot load device messages: manifest not loaded.")
            return

        try:
            from models.status import ElementManifest

            manifest = ElementManifest.model_validate_json(manifest_path.read_text())

            for msg in manifest.validation:
                self._add_validation_message_to_tree(msg, self.device_validation_tree)

        except Exception as e:
            logger.error(f"Failed to load device validation messages: {e}")

    def _add_validation_message_to_tree(self, msg: ValidationMessage, tree_widget):
        """Add a validation message to the specified tree widget."""
        item = QTreeWidgetItem(tree_widget)

        # Create approval checkbox
        checkbox = QCheckBox()
        checkbox.setChecked(msg.is_approved)
        # Disable if this is a read-only message from LibrePCB
        if msg.source.name == "LIBREPCB":
            checkbox.setEnabled(False)
        checkbox.stateChanged.connect(
            lambda state, m=msg: self._on_approval_changed(m, state == Qt.Checked)
        )
        tree_widget.setItemWidget(item, 0, checkbox)

        # Set severity icon
        item.setText(1, msg.severity.icon)

        # Set message text
        item.setText(2, msg.message)

        # Store the message object for later reference
        item.setData(0, Qt.UserRole, msg)

    def _on_approval_changed(self, msg: ValidationMessage, is_approved: bool):
        """Handle approval checkbox state change."""
        msg.is_approved = is_approved
        logger.info(
            f"Updated approval for message '{msg.message[:50]}...' to {is_approved}"
        )

        # Save both component and device validation messages since we don't know which tree the message belongs to
        self._save_component_validation_messages()
        self._save_device_validation_messages()

    def _save_device_validation_messages(self):
        """Save device validation messages back to the manifest file."""
        if not self.library_part or not self.device_validation_tree:
            return

        manifest_path = LibrePCBElement.DEVICE.get_wp_path(self.library_part.uuid)
        if not manifest_path:
            return

        try:
            from models.status import ElementManifest

            # Collect all validation messages from the device tree
            messages = []
            for i in range(self.device_validation_tree.topLevelItemCount()):
                item = self.device_validation_tree.topLevelItem(i)
                msg = item.data(0, Qt.UserRole)
                if msg:
                    messages.append(msg)

            # Update the manifest
            manifest = ElementManifest.model_validate_json(manifest_path.read_text())
            manifest.validation = messages
            manifest_path.write_text(manifest.model_dump_json(indent=2))

            logger.info("Device validation messages saved to manifest.")

        except Exception as e:
            logger.error(f"Failed to save device validation messages: {e}")

    def _save_component_validation_messages(self):
        """Save component validation messages back to the manifest file."""
        if not self.library_part or not self.component_validation_tree:
            return

        manifest_path = LibrePCBElement.COMPONENT.get_wp_path(
            self.library_part.component.uuid
        )
        if not manifest_path:
            return

        try:
            from models.status import ElementManifest

            # Collect all validation messages from the component tree
            messages = []
            for i in range(self.component_validation_tree.topLevelItemCount()):
                item = self.component_validation_tree.topLevelItem(i)
                msg = item.data(0, Qt.UserRole)
                if msg:
                    messages.append(msg)

            # Update the manifest
            manifest = ElementManifest.model_validate_json(manifest_path.read_text())
            manifest.validation = messages
            manifest_path.write_text(manifest.model_dump_json(indent=2))

            logger.info("Component validation messages saved to manifest.")

        except Exception as e:
            logger.error(f"Failed to save component validation messages: {e}")

    @Slot()
    def _on_refresh_component_checks_clicked(self):
        """Handle refresh component checks button click."""
        if not self.library_part:
            return

        logger.info("Refreshing component checks...")
        self.button_refresh_component_checks.setEnabled(False)
        self.button_refresh_component_checks.setText("Refreshing...")

        # Start worker in thread
        self.refresh_thread = QThread(self)
        self.refresh_worker = ComponentUpdateWorker(self.library_part)
        self.refresh_worker.moveToThread(self.refresh_thread)

        # Connect signals
        self.refresh_thread.started.connect(self.refresh_worker.run)
        self.refresh_worker.finished.connect(self._on_refresh_component_finished)
        self.refresh_worker.error.connect(self._on_refresh_component_error)

        # Start
        self.refresh_thread.start()

    @Slot()
    def _on_refresh_device_checks_clicked(self):
        """Handle refresh device checks button click."""
        if not self.library_part:
            return

        logger.info("Refreshing device checks...")
        self.button_refresh_device_checks.setEnabled(False)
        self.button_refresh_device_checks.setText("Refreshing...")

        # Start worker in thread
        self.refresh_device_thread = QThread(self)
        self.refresh_device_worker = DeviceUpdateWorker(self.library_part)
        self.refresh_device_worker.moveToThread(self.refresh_device_thread)

        # Connect signals
        self.refresh_device_thread.started.connect(self.refresh_device_worker.run)
        self.refresh_device_worker.finished.connect(self._on_refresh_device_finished)
        self.refresh_device_worker.error.connect(self._on_refresh_device_error)

        # Start
        self.refresh_device_thread.start()

    @Slot()
    def _on_refresh_device_finished(self):
        """Handle device refresh completion."""
        self.button_refresh_device_checks.setEnabled(True)
        self.button_refresh_device_checks.setText("Refresh Device Checks")

        # Reload device validation messages
        self._load_device_validation_messages()

        # Clean up thread
        if hasattr(self, "refresh_device_thread"):
            self.refresh_device_thread.quit()
            self.refresh_device_thread.wait()
            self.refresh_device_thread.deleteLater()

        # Emit signal that status may have changed
        self.status_changed.emit()

    @Slot(str)
    def _on_refresh_device_error(self, error_msg: str):
        """Handle device refresh error."""
        self.button_refresh_device_checks.setEnabled(True)
        self.button_refresh_device_checks.setText("Refresh Device Checks")
        logger.error(f"Device refresh failed: {error_msg}")

        # Clean up thread
        if hasattr(self, "refresh_device_thread"):
            self.refresh_device_thread.quit()
            self.refresh_device_thread.wait()
            self.refresh_device_thread.deleteLater()

    @Slot()
    def _on_refresh_component_finished(self):
        """Handle component refresh completion."""
        self.button_refresh_component_checks.setEnabled(True)
        self.button_refresh_component_checks.setText("Refresh Component Checks")

        # Reload component validation messages
        self._load_component_validation_messages()

        # Clean up thread
        if hasattr(self, "refresh_thread"):
            self.refresh_thread.quit()
            self.refresh_thread.wait()
            self.refresh_thread.deleteLater()

        # Emit signal that status may have changed
        self.status_changed.emit()

    @Slot(str)
    def _on_refresh_component_error(self, error_msg: str):
        """Handle component refresh error."""
        self.button_refresh_component_checks.setEnabled(True)
        self.button_refresh_component_checks.setText("Refresh Component Checks")
        logger.error(f"Component refresh failed: {error_msg}")

        # Clean up thread
        if hasattr(self, "refresh_thread"):
            self.refresh_thread.quit()
            self.refresh_thread.wait()
            self.refresh_thread.deleteLater()

    @Slot(str)
    def _on_uuid_clicked(self, link: str):
        """Handle UUID link click to open component directory."""
        if not self.library_part or not self.library_part.component:
            return

        component_dir = self.library_part.component.dir_path
        if component_dir and component_dir.exists():
            QDesktopServices.openUrl(QUrl.fromLocalFile(str(component_dir.absolute())))
        else:
            logger.warning(f"Component directory does not exist: {component_dir}")

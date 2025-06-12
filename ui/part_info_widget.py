import logging

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QFrame, QLabel, QVBoxLayout, QWidget

logger = logging.getLogger(__name__)


class PartInfoWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        # Create the layout and widgets programmatically to ensure proper ownership
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        # Create title label
        self.label_PartTitle = QLabel("No Part Selected")
        font = QFont()
        font.setPointSize(14)
        font.setBold(True)
        self.label_PartTitle.setFont(font)
        self.label_PartTitle.setWordWrap(True)
        self.label_PartTitle.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.label_PartTitle)

        # Create LCSC ID label
        self.label_LcscId = QLabel("LCSC ID: -")
        self.label_LcscId.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.label_LcscId)

        # Add separator line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        # Create manufacturer section
        mfn_label = QLabel("Manufacturer:")
        mfn_label.setFont(QFont("", -1, QFont.Bold))
        layout.addWidget(mfn_label)

        self.mfn_value = QLabel("(select a part)")
        self.mfn_value.setWordWrap(True)
        self.mfn_value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.mfn_value)

        # Create part number section
        mfn_part_label = QLabel("Mfr. Part Number:")
        mfn_part_label.setFont(QFont("", -1, QFont.Bold))
        layout.addWidget(mfn_part_label)

        self.mfn_part_value = QLabel("")
        self.mfn_part_value.setWordWrap(True)
        self.mfn_part_value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.mfn_part_value)

        # Create description section
        description_label = QLabel("Description:")
        description_label.setFont(QFont("", -1, QFont.Bold))
        layout.addWidget(description_label)

        self.description_value = QLabel("")
        self.description_value.setWordWrap(True)
        self.description_value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        layout.addWidget(self.description_value)

        logger.info("PartInfoWidget created with programmatic widgets")

    def set_component(self, component):
        """Populates the widget with data from a LibraryPart or SearchResult."""

        if not component:
            self.clear()
            return

        try:
            if self.label_PartTitle:
                part_name = getattr(component, "part_name", "N/A")
                logger.info(f"Setting part_name: {part_name}")
                self.label_PartTitle.setText(part_name)
            if self.label_LcscId:
                lcsc_id = getattr(component, "lcsc_id", "-")
                self.label_LcscId.setText(f"LCSC ID: {lcsc_id}")
            if self.mfn_value:
                manufacturer = getattr(component, "manufacturer", "N/A")
                self.mfn_value.setText(manufacturer)
            if self.mfn_part_value:
                mfr_part = getattr(component, "mfr_part_number", "N/A")
                self.mfn_part_value.setText(mfr_part)
            if self.description_value:
                description = getattr(component, "description", "N/A")
                self.description_value.setText(description)
            logger.info("PartInfoWidget.set_component completed successfully")
        except RuntimeError as e:
            logger.error(f"RuntimeError in set_component: {e}")
        except Exception as e:
            logger.error(f"Unexpected error in set_component: {e}")

    def clear(self):
        """Resets the widget to its default, empty state."""
        try:
            if self.label_PartTitle:
                self.label_PartTitle.setText("No Part Selected")
            if self.label_LcscId:
                self.label_LcscId.setText("LCSC ID: -")
            if self.mfn_value:
                self.mfn_value.setText("(select a part)")
            if self.mfn_part_value:
                self.mfn_part_value.setText("")
            if self.description_value:
                self.description_value.setText("")
        except RuntimeError:
            # Widget already deleted by C++, ignore
            pass

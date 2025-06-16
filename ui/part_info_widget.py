import logging
import os

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QFrame, QLabel, QVBoxLayout, QWidget, QToolButton, QHBoxLayout
)

logger = logging.getLogger(__name__)


class PartInfoWidget(QWidget):
    hide_requested = Signal()
    # This widget is now created programmatically, not from a .ui file.
    # This is necessary because it's used as a promoted widget (`native="true"`).
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.hide_sidebar_button = None
        self._setup_ui()
        logger.info("PartInfoWidget created programmatically.")

    def _setup_ui(self):
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(9, 9, 9, 9)

        # Top row with title and hide button
        top_row_layout = QHBoxLayout()
        self.label_PartTitle = QLabel("No Part Selected")
        font = QFont(); font.setPointSize(14); font.setBold(True)
        self.label_PartTitle.setFont(font)
        self.label_PartTitle.setWordWrap(True)
        self.label_PartTitle.setTextInteractionFlags(Qt.TextSelectableByMouse)
        top_row_layout.addWidget(self.label_PartTitle)
        
        main_layout.addLayout(top_row_layout)
        
        self.label_LcscId = QLabel("LCSC ID: -")
        self.label_LcscId.setTextInteractionFlags(Qt.TextSelectableByMouse)
        main_layout.addWidget(self.label_LcscId)

        line = QFrame(); line.setFrameShape(QFrame.HLine); line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)

        # Manufacturer
        mfn_label = QLabel("Manufacturer:"); mfn_label.setFont(QFont("", -1, QFont.Bold))
        main_layout.addWidget(mfn_label)
        self.mfn_value = QLabel("(select a part)"); self.mfn_value.setWordWrap(True); self.mfn_value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        main_layout.addWidget(self.mfn_value)

        # Mfr. Part Number
        mfn_part_label = QLabel("Mfr. Part Number:"); mfn_part_label.setFont(QFont("", -1, QFont.Bold))
        main_layout.addWidget(mfn_part_label)
        self.mfn_part_value = QLabel(""); self.mfn_part_value.setWordWrap(True); self.mfn_part_value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        main_layout.addWidget(self.mfn_part_value)

        # Description
        description_label = QLabel("Description:"); description_label.setFont(QFont("", -1, QFont.Bold))
        main_layout.addWidget(description_label)
        self.description_value = QLabel(""); self.description_value.setWordWrap(True); self.description_value.setTextInteractionFlags(Qt.TextSelectableByMouse)
        main_layout.addWidget(self.description_value)

    def set_component(self, component):
        if not component:
            self.clear()
            return
        self.label_PartTitle.setText(getattr(component, "part_name", "N/A"))
        self.label_LcscId.setText(f"LCSC ID: {getattr(component, 'lcsc_id', '-')}")
        self.mfn_value.setText(getattr(component, "manufacturer", "N/A"))
        self.mfn_part_value.setText(getattr(component, "mfr_part_number", "N/A"))
        self.description_value.setText(getattr(component, "description", "N/A"))

    def clear(self):
        self.label_PartTitle.setText("No Part Selected")
        self.label_LcscId.setText("LCSC ID: -")
        self.mfn_value.setText("(select a part)")
        self.mfn_part_value.setText("")
        self.description_value.setText("")

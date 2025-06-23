import os
import logging
from PySide6.QtCore import QObject, Qt, Signal, QTimer
from PySide6.QtGui import QPixmap, QFont
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QFrame,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPixmapItem,
    QGraphicsTextItem,
    QPushButton,
)

from models.library_part import LibraryPart
from models.elements import LibrePCBElement
from constants import UIText, WebPartsFilename
from .part_info_widget import PartInfoWidget

logger = logging.getLogger(__name__)


class LibraryElementSidebar(QWidget):
    back_to_library_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)

        loader = QUiLoader()
        loader.registerCustomWidget(PartInfoWidget)
        ui_file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "page_library_element.ui"
        )

        # Load the full UI to extract the contextFrame
        full_ui = loader.load(ui_file_path, None)
        self.context_frame = full_ui.findChild(QFrame, "contextFrame")

        if self.context_frame:
            self.context_frame.setParent(self)

            layout = QVBoxLayout(self)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.addWidget(self.context_frame)

            self.part_info_widget = self.context_frame.findChild(
                PartInfoWidget, "part_info_widget"
            )
            self.hero_view = self.context_frame.findChild(
                QGraphicsView, "image_hero_view"
            )
            self.back_to_library_button = self.context_frame.findChild(
                QPushButton, "back_to_library_button"
            )

            if self.back_to_library_button:
                self.back_to_library_button.clicked.connect(
                    self.back_to_library_requested
                )

            self._setup_hero_image()
        else:
            logger.error("Could not find 'contextFrame' in the UI file.")

    def _setup_hero_image(self):
        self.hero_scene = QGraphicsScene()
        self.hero_view.setScene(self.hero_scene)
        self.hero_pixmap_item = QGraphicsPixmapItem()
        self.hero_scene.addItem(self.hero_pixmap_item)
        self.hero_text_item = QGraphicsTextItem()
        font = QFont()
        font.setPointSize(12)
        self.hero_text_item.setFont(font)
        self.hero_text_item.setDefaultTextColor(Qt.gray)
        self.hero_scene.addItem(self.hero_text_item)
        self._set_hero_text(UIText.NO_IMAGE.value)

    def set_component(self, part: LibraryPart):
        if self.part_info_widget:
            self.part_info_widget.set_component(part)

        hero_path = (
            LibrePCBElement.PACKAGE.dir.parent
            / "webparts"
            / part.uuid
            / WebPartsFilename.HERO_IMAGE.value
        )
        if hero_path.exists():
            pixmap = QPixmap(str(hero_path))
            self._set_hero_pixmap(pixmap)
        else:
            self._set_hero_text(UIText.IMAGE_NOT_AVAILABLE.value)

    def _set_hero_text(self, text: str):
        self.hero_text_item.setPlainText(text)
        self.hero_text_item.setVisible(True)
        self.hero_pixmap_item.setVisible(False)
        self.hero_view.centerOn(self.hero_text_item)

    def _set_hero_pixmap(self, pixmap: QPixmap):
        if not pixmap.isNull():
            self.hero_pixmap_item.setPixmap(pixmap)
            self.hero_pixmap_item.setVisible(True)
            self.hero_text_item.setVisible(False)
            QTimer.singleShot(
                0,
                lambda: self.hero_view.fitInView(
                    self.hero_pixmap_item, Qt.KeepAspectRatio
                ),
            )
        else:
            self._set_hero_text(UIText.IMAGE_NOT_AVAILABLE.value)

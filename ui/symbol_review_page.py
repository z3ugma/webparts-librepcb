import logging
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QVBoxLayout,
    QWidget,
)

logger = logging.getLogger(__name__)


class SymbolReviewPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self._original_symbol_pixmap = None

        loader = QUiLoader()
        ui_file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "symbol_review_page.ui"
        )
        loaded_ui = loader.load(ui_file_path, self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(loaded_ui)

        self.easyeda_view = self.findChild(QGraphicsView, "easyedaSymbolView")
        self.librepcb_view = self.findChild(QGraphicsView, "librepcbSymbolView")

        if not self.easyeda_view or not self.librepcb_view:
            logger.error("Could not find symbol views in the UI.")
            return

        self.easyeda_scene = QGraphicsScene(self)
        self.easyeda_view.setScene(self.easyeda_scene)
        self.easyeda_view.setAlignment(Qt.AlignCenter)

        self.easyeda_item = QGraphicsPixmapItem()
        self.easyeda_scene.addItem(self.easyeda_item)

        self.easyeda_text_item = QGraphicsTextItem()
        self.easyeda_scene.addItem(self.easyeda_text_item)

        self.show_message("Loading Symbol...")

    def show_message(self, message: str):
        """Display a text message in the center of the easyeda_view."""
        if not self.easyeda_text_item:
            return
        self.easyeda_item.setVisible(False)
        self.easyeda_text_item.setPlainText(message)
        font = QFont()
        font.setPointSize(14)
        self.easyeda_text_item.setFont(font)
        self.easyeda_text_item.setVisible(True)
        self._rescale_contents()

    def set_symbol_image(self, pixmap: QPixmap | None):
        """Sets the pixmap to be displayed, or shows a message if pixmap is None."""
        if not self.easyeda_item:
            return

        if pixmap and not pixmap.isNull():
            self._original_symbol_pixmap = pixmap
            self.easyeda_text_item.setVisible(False)
            self.easyeda_item.setVisible(True)
            self.easyeda_item.setPixmap(pixmap)
        else:
            self._original_symbol_pixmap = None
            self.show_message("Symbol Not Available")
        self._rescale_contents()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._rescale_contents()

    def showEvent(self, event):
        """Handle show events to ensure image is properly scaled when first displayed."""
        super().showEvent(event)
        self._rescale_contents()

    def _rescale_contents(self):
        if self._original_symbol_pixmap and not self._original_symbol_pixmap.isNull():
            self.easyeda_view.fitInView(self.easyeda_item, Qt.KeepAspectRatio)
        elif self.easyeda_text_item and self.easyeda_text_item.isVisible():
            # For text, we just need to ensure the scene is still centered
            self.easyeda_view.centerOn(self.easyeda_text_item)

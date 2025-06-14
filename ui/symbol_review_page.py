import logging
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QPixmap
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QGraphicsPixmapItem,
    QGraphicsScene,
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
        self.easyeda_item = QGraphicsPixmapItem()
        self.easyeda_scene.addItem(self.easyeda_item)

    def set_symbol_image(self, pixmap: QPixmap):
        if not self.easyeda_item:
            return
        if not pixmap.isNull():
            self._original_symbol_pixmap = pixmap
            self.easyeda_item.setPixmap(pixmap)
            self.easyeda_view.fitInView(self.easyeda_item, Qt.KeepAspectRatio)
        else:
            self._original_symbol_pixmap = None
            self.easyeda_item.setPixmap(QPixmap())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self._original_symbol_pixmap and not self._original_symbol_pixmap.isNull():
            self.easyeda_view.fitInView(self.easyeda_item, Qt.KeepAspectRatio)

import logging
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QResizeEvent
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QGraphicsView,
    QGraphicsScene,
    QGraphicsPixmapItem,
)

from .custom_widgets import ZoomPanGraphicsView

logger = logging.getLogger(__name__)


class SymbolReviewPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        self._initial_fit_done = False

        loader = QUiLoader()
        ui_file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "symbol_review_page.ui"
        )
        self.ui = loader.load(ui_file_path, self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ui)

        placeholder_view = self.ui.findChild(QGraphicsView, "easyedaSymbolView")

        if placeholder_view:
            self.symbol_scene = QGraphicsScene(self)
            self.symbol_pixmap_item = QGraphicsPixmapItem()
            self.symbol_scene.addItem(self.symbol_pixmap_item)

            self.symbol_image_view = ZoomPanGraphicsView(self.symbol_scene, self)

            parent_layout = placeholder_view.parent().layout()
            if parent_layout:
                parent_layout.replaceWidget(placeholder_view, self.symbol_image_view)
                placeholder_view.deleteLater()
            else:
                logger.error(
                    "Could not find parent layout to replace placeholder view."
                )
        else:
            logger.error("Could not find 'easyedaSymbolView' in the UI.")

    def set_symbol_image(self, pixmap: QPixmap):
        if hasattr(self, "symbol_pixmap_item"):
            self._initial_fit_done = False  # Reset flag for new images
            if pixmap and not pixmap.isNull():
                self.symbol_pixmap_item.setPixmap(pixmap)
            else:
                self.symbol_pixmap_item.setPixmap(QPixmap())

    def resizeEvent(self, event: QResizeEvent):
        """
        Handle resize events to perform the initial fit-in-view.
        """
        super().resizeEvent(event)
        if not self._initial_fit_done:
            if self.symbol_image_view.viewport().size().width() > 0:
                logger.info(
                    f"Performing initial fit for symbol image with viewport size: {self.symbol_image_view.viewport().size()}"
                )
                self.symbol_image_view.fitInView(
                    self.symbol_pixmap_item, Qt.KeepAspectRatio
                )
                self._initial_fit_done = True

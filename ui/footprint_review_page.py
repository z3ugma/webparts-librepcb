import logging
import os

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene, 
    QGraphicsPixmapItem
)

from .custom_widgets import ZoomPanGraphicsView

logger = logging.getLogger(__name__)


class FootprintReviewPage(QWidget):
    """
    A custom widget that encapsulates the footprint review page functionality.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        
        loader = QUiLoader()
        ui_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "footprint_review_page.ui")
        self.ui = loader.load(ui_file_path, self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ui)

        placeholder_view = self.ui.findChild(QGraphicsView, "footprint_image_container")
        
        if placeholder_view:
            self.footprint_scene = QGraphicsScene(self)
            self.footprint_pixmap_item = QGraphicsPixmapItem()
            self.footprint_scene.addItem(self.footprint_pixmap_item)

            self.footprint_image_view = ZoomPanGraphicsView(self.footprint_scene, self)
            
            parent_layout = placeholder_view.parent().layout()
            if parent_layout:
                parent_layout.replaceWidget(placeholder_view, self.footprint_image_view)
                placeholder_view.deleteLater()
            else:
                logger.error("Could not find parent layout to replace placeholder view.")
        else:
            logger.error("Could not find 'footprint_image_container' in the UI.")

    def set_footprint_image(self, pixmap: QPixmap):
        """
        Sets the footprint image in the container and scales it appropriately.
        """
        if hasattr(self, 'footprint_pixmap_item'):
            if pixmap and not pixmap.isNull():
                self.footprint_pixmap_item.setPixmap(pixmap)
                # Use a timer to ensure the view has its final size before fitting
                QTimer.singleShot(0, lambda: self.footprint_image_view.fitInView(self.footprint_pixmap_item, Qt.KeepAspectRatio))
            else:
                self.footprint_pixmap_item.setPixmap(QPixmap()) # Clear if pixmap is null

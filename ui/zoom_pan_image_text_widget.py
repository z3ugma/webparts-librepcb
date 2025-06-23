import logging
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QGraphicsScene,
    QGraphicsPixmapItem,
    QStackedWidget,
    QLabel,
)
from PySide6.QtGui import QPixmap
from PySide6.QtCore import Qt, QTimer
from .custom_widgets import ZoomPanGraphicsView

logger = logging.getLogger(__name__)


class ZoomPanImageAndTextWidget(QWidget):
    def __init__(self, parent=None, zoom_factor=1.0):
        super().__init__(parent)
        self.zoom_factor = zoom_factor

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.stack = QStackedWidget(self)

        self.scene = QGraphicsScene()
        self.view = ZoomPanGraphicsView(self.scene, self)
        self.view.setToolTip("Pan by dragging, zoom with scroll wheel.")
        self.view.setAlignment(Qt.AlignHCenter | Qt.AlignTop)
        self.item = QGraphicsPixmapItem()
        self.scene.addItem(self.item)
        self.stack.addWidget(self.view)

        self.text_label = QLabel()
        self.text_label.setAlignment(Qt.AlignCenter)
        self.text_label.setWordWrap(True)
        self.stack.addWidget(self.text_label)

        layout.addWidget(self.stack)

    def show_text(self, text: str):
        self.text_label.setText(text)
        self.stack.setCurrentWidget(self.text_label)

    def show_pixmap(self, pixmap: QPixmap):
        if pixmap.isNull():
            self.show_text("Image Not Available")
            return

        self.item.setPixmap(pixmap)
        self.scene.setSceneRect(self.item.boundingRect())
        self.stack.setCurrentWidget(self.view)

        QTimer.singleShot(0, self._fit_and_zoom)

    def _fit_and_zoom(self):
        self.view.fitInView(self.item, Qt.KeepAspectRatio)
        if self.zoom_factor != 1.0:
            self.view.scale(self.zoom_factor, self.zoom_factor)

    def clear(self, default_text=""):
        self.show_text(default_text)
        if not self.item.pixmap().isNull():
            self.item.setPixmap(QPixmap())

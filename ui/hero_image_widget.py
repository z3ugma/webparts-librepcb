import logging
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QGraphicsScene,
    QGraphicsPixmapItem,
    QGraphicsTextItem,
)
from PySide6.QtGui import QPixmap, QFont
from PySide6.QtCore import Qt, QTimer
import constants as const
from .custom_widgets import ZoomPanGraphicsView

logger = logging.getLogger(__name__)


class HeroImageWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.hero_scene = QGraphicsScene()
        self.hero_view = ZoomPanGraphicsView(self.hero_scene, self)
        self.hero_view.setToolTip("Pan by dragging, zoom with scroll wheel.")
        self.hero_view.setMinimumHeight(250)
        layout.addWidget(self.hero_view)

        self.hero_item = QGraphicsPixmapItem()
        self.hero_scene.addItem(self.hero_item)

        self.hero_text = QGraphicsTextItem()
        font = QFont()
        font.setPointSize(12)
        self.hero_text.setFont(font)
        self.hero_scene.addItem(self.hero_text)

        self.show_text(const.UIText.SELECT_PART.value)

        logger.info("HeroImageWidget created with programmatic widgets")

    def show_text(self, text: str):
        self.hero_text.setPlainText(text)
        self.hero_text.setVisible(True)
        self.hero_item.setVisible(False)
        self.hero_view.resetTransform()
        self.hero_view.centerOn(self.hero_text)

    def show_pixmap(self, pixmap: QPixmap):
        if pixmap.isNull():
            self.show_text(const.UIText.NO_IMAGE.value)
            return

        self.hero_item.setPixmap(pixmap)
        self.hero_item.setVisible(True)
        self.hero_text.setVisible(False)

        # Use a timer to ensure the view is sized correctly before we zoom
        QTimer.singleShot(0, self._fit_and_zoom)

    def _fit_and_zoom(self):
        self.hero_view.fitInView(self.hero_item, Qt.KeepAspectRatio)
        self.hero_view.scale(1.5, 1.5)

    def show_loading(self):
        self.show_text(const.UIText.LOADING.value)

    def show_no_image(self):
        self.show_text(const.UIText.NO_IMAGE.value)

    def show_image_not_available(self):
        self.show_text(const.UIText.IMAGE_NOT_AVAILABLE.value)

    def clear(self):
        self.show_text(const.UIText.SELECT_PART.value)

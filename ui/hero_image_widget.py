import logging
from PySide6.QtWidgets import QWidget, QVBoxLayout, QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsTextItem
from PySide6.QtGui import QPixmap, QFont
from PySide6.QtCore import Qt

logger = logging.getLogger(__name__)


class HeroImageWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Create the layout programmatically to ensure proper ownership
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Create the graphics view
        self.hero_view = QGraphicsView()
        self.hero_view.setToolTip("Pan by dragging, zoom with scroll wheel.")
        self.hero_view.setMinimumHeight(250)
        self.hero_view.setDragMode(QGraphicsView.ScrollHandDrag)
        layout.addWidget(self.hero_view)
        
        # Set up the graphics scene and items
        self.hero_scene = QGraphicsScene()
        self.hero_view.setScene(self.hero_scene)
        
        # Create pixmap item for images
        self.hero_item = QGraphicsPixmapItem()
        self.hero_scene.addItem(self.hero_item)
        
        # Create text item for messages
        self.hero_text = QGraphicsTextItem()
        font = QFont()
        font.setPointSize(12)
        self.hero_text.setFont(font)
        self.hero_scene.addItem(self.hero_text)
        
        # Start with default text
        self.show_text("Select a part to view details")
        
        logger.info("HeroImageWidget created with programmatic widgets")

    def show_text(self, text: str):
        """Display text message (e.g., 'Loading...', 'No Image', etc.)"""
        self.hero_text.setPlainText(text)
        self.hero_text.setVisible(True)
        self.hero_item.setVisible(False)
        self.hero_view.resetTransform()
        self.hero_view.centerOn(self.hero_text)

    def show_pixmap(self, pixmap: QPixmap):
        """Display an image pixmap with automatic scaling"""
        if pixmap.isNull():
            self.show_text("No Image")
            return
            
        self.hero_item.setPixmap(pixmap)
        self.hero_item.setVisible(True)
        self.hero_text.setVisible(False)
        self.hero_view.resetTransform()
        
        # Scale to fit view with 1.5x zoom for better visibility
        view_rect = self.hero_view.viewport().rect()
        if view_rect.width() > 0 and view_rect.height() > 0:
            scale_factor = min(
                (view_rect.width() * 1.5) / pixmap.width(),
                (view_rect.height() * 1.5) / pixmap.height()
            )
            self.hero_view.scale(scale_factor, scale_factor)
        
        self.hero_view.centerOn(self.hero_item)

    def show_loading(self):
        """Show loading message"""
        self.show_text("Loading...")

    def show_no_image(self):
        """Show no image available message"""
        self.show_text("No Image")

    def show_image_not_available(self):
        """Show image not available message"""
        self.show_text("Image Not Available")

    def clear(self):
        """Reset to default state"""
        self.show_text("Select a part to view details")
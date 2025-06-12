import logging
import os

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel

logger = logging.getLogger(__name__)


class FootprintReviewPage(QWidget):
    """
    A custom widget that encapsulates the footprint review page functionality.
    It loads its own UI from footprint_review_page.ui.
    """
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Store the original pixmap for rescaling
        self._original_pixmap = None

        # Load the UI from the .ui file
        loader = QUiLoader()
        ui_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "footprint_review_page.ui")
        loaded_ui = loader.load(ui_file_path, self)

        # Add the loaded UI to this widget's layout
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(loaded_ui)

        # Find the image container widget
        self.footprint_image_container = self.findChild(QLabel, "footprint_image_container")
        if self.footprint_image_container:
            self.footprint_image_container.setAlignment(Qt.AlignCenter)
            self.footprint_image_container.setWordWrap(True)
        else:
            logger.error("Could not find 'footprint_image_container' in the UI.")

    def resizeEvent(self, event):
        """Handle resize events to rescale the image to fit the new size."""
        super().resizeEvent(event)
        self._rescale_image()

    def set_footprint_image(self, pixmap: QPixmap):
        """
        Sets the footprint image in the container.
        """
        if self.footprint_image_container:
            if not pixmap.isNull():
                # Store the original for future rescaling
                self._original_pixmap = pixmap
                
                # Get the current label dimensions
                w = self.footprint_image_container.width()
                h = self.footprint_image_container.height()
                
                # If dimensions aren't available yet, use the minimum size from UI
                if w <= 0 or h <= 0:
                    w = self.footprint_image_container.minimumWidth() or 250
                    h = self.footprint_image_container.minimumHeight() or 250
                
                # Scale pixmap to fit the label dimensions while keeping aspect ratio
                scaled_pixmap = pixmap.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.footprint_image_container.setPixmap(scaled_pixmap)
            else:
                self._original_pixmap = None
                self.footprint_image_container.setText("Footprint Not Available")

    def showEvent(self, event):
        """Handle show events to ensure image is properly scaled when first displayed."""
        super().showEvent(event)
        # Use a single shot timer to rescale after the layout is complete
        if self._original_pixmap and not self._original_pixmap.isNull():
            from PySide6.QtCore import QTimer
            QTimer.singleShot(0, self._rescale_image)
    
    def _rescale_image(self):
        """Internal method to rescale the image to current container size."""
        if self._original_pixmap and not self._original_pixmap.isNull() and self.footprint_image_container:
            w = self.footprint_image_container.width()
            h = self.footprint_image_container.height()
            if w > 0 and h > 0:  # Make sure we have valid dimensions
                scaled_pixmap = self._original_pixmap.scaled(w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.footprint_image_container.setPixmap(scaled_pixmap)

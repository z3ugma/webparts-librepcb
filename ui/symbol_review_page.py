import logging
import os

from PySide6.QtCore import Qt, Slot
from PySide6.QtGui import QPixmap
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

logger = logging.getLogger(__name__)


class SymbolReviewPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        # Store the original pixmap for rescaling
        self._original_symbol_pixmap = None

        loader = QUiLoader()
        ui_file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "symbol_review_page.ui"
        )
        loaded_ui = loader.load(ui_file_path, self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(loaded_ui)

        self.image_label = self.findChild(QLabel, "image_symbol")
        if self.image_label:
            self.image_label.setAlignment(Qt.AlignCenter)
            self.image_label.setWordWrap(True)
        else:
            logger.error("Could not find 'image_symbol' in the UI.")

        self.setupUi()

    def resizeEvent(self, event):
        """Handle resize events to rescale the image to fit the new size."""
        super().resizeEvent(event)
        self._rescale_image()

    def showEvent(self, event):
        """Handle show events to ensure image is properly scaled when first displayed."""
        super().showEvent(event)
        # Use a single shot timer to rescale after the layout is complete
        from PySide6.QtCore import QTimer

        QTimer.singleShot(0, self._rescale_image)

    def _rescale_image(self):
        """Internal method to rescale the image to current container size."""
        if (
            self._original_symbol_pixmap
            and not self._original_symbol_pixmap.isNull()
            and self.image_label
        ):
            w = self.image_label.width()
            h = self.image_label.height()
            # Use a minimum size to ensure good scaling even if container reports small size
            w = max(w, 250)
            h = max(h, 250)
            if w > 0 and h > 0:  # Make sure we have valid dimensions
                scaled_pixmap = self._original_symbol_pixmap.scaled(
                    w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self.image_label.setPixmap(scaled_pixmap)

    def setupUi(self) -> None:
        pass
        # self.button_ApproveSymbol.clicked.connect(self.approve_and_continue)

    def set_symbol_image(self, pixmap: QPixmap):
        if self.image_label:
            if not pixmap.isNull():
                # Store the original for future rescaling
                self._original_symbol_pixmap = pixmap

                # Get the current label dimensions
                w = self.image_label.width()
                h = self.image_label.height()

                # If dimensions aren't available yet, use the minimum size from UI
                if w <= 0 or h <= 0:
                    w = self.image_label.minimumWidth() or 250
                    h = self.image_label.minimumHeight() or 250

                # Use a minimum size to ensure good scaling
                w = max(w, 250)
                h = max(h, 250)

                scaled_pixmap = pixmap.scaled(
                    w, h, Qt.KeepAspectRatio, Qt.SmoothTransformation
                )
                self.image_label.setPixmap(scaled_pixmap)
            else:
                self._original_symbol_pixmap = None
                self.image_label.setText("Symbol Not Available")

    @Slot()
    def approve_and_continue(self):
        # TODO: Implement this
        pass

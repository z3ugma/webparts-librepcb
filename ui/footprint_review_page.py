import logging
import os

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QGraphicsView,
    QSplitter,
)

from .custom_widgets import ZoomPanGraphicsView
from .library_element_image_widget import LibraryElementImageWidget


logger = logging.getLogger(__name__)


class FootprintReviewPage(QWidget):
    """
    A custom widget that encapsulates the footprint review page functionality.
    """

    def __init__(self, parent=None):
        super().__init__(parent)

        loader = QUiLoader()
        # Register the custom widget for promotion
        loader.registerCustomWidget(LibraryElementImageWidget)
        ui_file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "footprint_review_page.ui"
        )
        self.ui = loader.load(ui_file_path, self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.ui)

        self.vertical_splitter = self.ui.findChild(QSplitter, "vertical_splitter")
        if self.vertical_splitter:
            # Set initial size ratio to 3:1 (images:messages)
            self.vertical_splitter.setSizes([300, 100])
        else:
            logger.error("Could not find 'vertical_splitter' in the UI.")

        self.footprint_splitter = self.ui.findChild(QSplitter, "footprint_splitter")
        if self.footprint_splitter:
            # Set initial size ratio to 1:1 (left:right)
            self.footprint_splitter.setSizes([200, 200])
        else:
            logger.error("Could not find 'footprint_splitter' in the UI.")

        self._setup_easyeda_preview()

        # The generated preview is now a custom widget promoted from the UI file
        self.librepcb_preview = self.ui.findChild(
            LibraryElementImageWidget, "librepcbFootprintView"
        )
        if self.librepcb_preview:
            self.librepcb_preview.show_text("Not Implemented")
        else:
            logger.error("Could not find 'librepcbFootprintView' widget.")

    def _setup_easyeda_preview(self):
        """Configures the left-side image viewer for the EasyEDA footprint."""
        placeholder_view = self.ui.findChild(QGraphicsView, "footprint_image_container")
        if not placeholder_view:
            logger.error("Could not find 'footprint_image_container' in the UI.")
            return

        self.footprint_image_view = LibraryElementImageWidget(self)
        parent_layout = placeholder_view.parent().layout()
        if parent_layout:
            parent_layout.replaceWidget(placeholder_view, self.footprint_image_view)
            placeholder_view.deleteLater()
        else:
            logger.error("Could not find parent layout for EasyEDA preview.")

    def set_footprint_image(self, pixmap: QPixmap):
        """
        Sets the EasyEDA footprint image in the left-side container.
        """
        if hasattr(self, "footprint_image_view"):
            self.footprint_image_view.show_pixmap(pixmap)

    def set_librepcb_footprint_image(self, pixmap: QPixmap):
        """
        Sets the generated LibrePCB footprint image in the right-side container.
        """
        if hasattr(self, "librepcb_preview"):
            self.librepcb_preview.show_pixmap(pixmap)


import logging
import os

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
        if not self.footprint_image_container:
            logger.error("Could not find 'footprint_image_container' in the UI.")

    def set_footprint_image(self, pixmap):
        """
        Sets the footprint image in the container.
        """
        if self.footprint_image_container:
            self.footprint_image_container.setPixmap(pixmap)

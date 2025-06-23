import logging
import os

from PySide6.QtGui import QPixmap
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QWidget, QVBoxLayout, QSplitter

from .library_element_image_widget import LibraryElementImageWidget

logger = logging.getLogger(__name__)


class SymbolReviewPage(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        loader = QUiLoader()
        loader.registerCustomWidget(LibraryElementImageWidget)
        ui_file_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "symbol_review_page.ui"
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

        self.symbol_splitter = self.ui.findChild(QSplitter, "symbol_splitter")
        if self.symbol_splitter:
            # Set initial size ratio to 1:1 (left:right)
            self.symbol_splitter.setSizes([200, 200])
        else:
            logger.error("Could not find 'symbol_splitter' in the UI.")

        self.easyeda_preview = self.ui.findChild(
            LibraryElementImageWidget, "easyedaSymbolView"
        )
        self.librepcb_preview = self.ui.findChild(
            LibraryElementImageWidget, "librepcbSymbolView"
        )

        if self.easyeda_preview:
            self.easyeda_preview.clear("Symbol Not Available")
        else:
            logger.error("Could not find 'easyedaSymbolView' widget.")

        if self.librepcb_preview:
            self.librepcb_preview.show_text("Not Implemented")
        else:
            logger.error("Could not find 'librepcbSymbolView' widget.")

    def set_symbol_image(self, pixmap: QPixmap):
        if self.easyeda_preview:
            self.easyeda_preview.show_pixmap(pixmap)

    def set_librepcb_symbol_image(self, pixmap: QPixmap):
        if self.librepcb_preview:
            self.librepcb_preview.show_pixmap(pixmap)

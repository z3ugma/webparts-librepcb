import os

from PySide6.QtCore import Slot, Qt
from PySide6.QtGui import QPixmap
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QVBoxLayout, QWidget, QLabel


class SymbolReviewPage(QWidget):
    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
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

        self.setupUi()

    def setupUi(self) -> None:
        pass
        # self.button_ApproveSymbol.clicked.connect(self.approve_and_continue)
        
    def set_symbol_image(self, pixmap: QPixmap):
        if self.image_label:
            if not pixmap.isNull():
                self.image_label.setPixmap(pixmap.scaled(self.image_label.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                self.image_label.setText("Symbol Not Available")

    @Slot()
    def approve_and_continue(self):
        # TODO: Implement this
        pass

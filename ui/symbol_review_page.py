import os

from PySide6.QtCore import Slot
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QVBoxLayout, QWidget


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

        self.setupUi()

    def setupUi(self) -> None:
        pass
        # self.button_ApproveSymbol.clicked.connect(self.approve_and_continue)

    @Slot()
    def approve_and_continue(self):
        # TODO: Implement this
        pass

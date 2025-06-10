import os
from PySide6.QtWidgets import QWidget, QPushButton, QVBoxLayout
from PySide6.QtUiTools import QUiLoader
from PySide6.QtCore import Signal

class LibraryPage(QWidget):
    go_to_search_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        loader = QUiLoader()
        ui_file_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "page_library.ui")
        loaded_ui = loader.load(ui_file_path, self)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(loaded_ui)

        self.go_to_search_button = self.findChild(QPushButton, "go_to_search_button")
        if self.go_to_search_button:
            self.go_to_search_button.clicked.connect(self.go_to_search_requested)

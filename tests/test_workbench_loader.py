import os

import pytest
from PySide6.QtUiTools import QUiLoader
from PySide6.QtWidgets import QStackedWidget, QWidget

from ui.footprint_review_page import FootprintReviewPage

# Import the custom widget classes that should be promoted
from ui.page_search import SearchPage
from ui.symbol_review_page import SymbolReviewPage

# Get the absolute path to the UI file
UI_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ui", "workbench.ui"
)


@pytest.fixture
def workbench_ui(qtbot):
    """
    Loads the workbench.ui file and registers custom widgets.
    Returns the loaded window object.
    """
    loader = QUiLoader()

    # Register all custom widgets that are expected in the UI file
    # This is crucial for the loader to know how to instantiate them
    loader.registerCustomWidget(SearchPage)
    loader.registerCustomWidget(FootprintReviewPage)
    loader.registerCustomWidget(SymbolReviewPage)

    window = loader.load(UI_FILE, None)
    assert window is not None, (
        f"Failed to load UI file: {UI_FILE}\\n{loader.errorString()}"
    )
    qtbot.addWidget(window)
    return window


def test_workbench_loads_main_stack(workbench_ui):
    """Test if the main QStackedWidget is loaded correctly."""
    main_stack = workbench_ui.findChild(QStackedWidget, "mainStackedWidget")
    assert main_stack is not None
    assert isinstance(main_stack, QStackedWidget)


def test_search_page_is_loaded_and_promoted(workbench_ui):
    """Test if the SearchPage is correctly loaded and promoted."""
    search_page = workbench_ui.findChild(QWidget, "page_Search")
    assert search_page is not None
    assert isinstance(search_page, SearchPage), (
        f"Widget page_Search is not of type SearchPage, but {type(search_page)}"
    )


def test_footprint_review_page_is_loaded_and_promoted(workbench_ui):
    """Test if the FootprintReviewPage is correctly loaded and promoted."""
    footprint_page = workbench_ui.findChild(QWidget, "page_FootprintReview")
    assert footprint_page is not None
    assert isinstance(footprint_page, FootprintReviewPage), (
        f"Widget page_FootprintReview is not of type FootprintReviewPage, but {type(footprint_page)}"
    )


def test_symbol_review_page_is_loaded_and_promoted(workbench_ui):
    """Test if the SymbolReviewPage is correctly loaded and promoted."""
    symbol_page = workbench_ui.findChild(QWidget, "page_SymbolReview")
    assert symbol_page is not None
    assert isinstance(symbol_page, SymbolReviewPage), (
        f"Widget page_SymbolReview is not of type SymbolReviewPage, but {type(symbol_page)}"
    )

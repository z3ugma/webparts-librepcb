import pytest
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap

from ui.page_search import SearchPage


# The pytest.mark.ui is optional but good practice to tag UI tests
@pytest.mark.ui
def test_search_page_initial_state(qtbot):
    """
    Tests the initial state of the SearchPage widget upon creation.
    """
    # 1. Create the widget under test
    search_page = SearchPage()

    # 2. Register the widget with qtbot. This ensures it's properly closed after
    #    the test and provides a way to interact with it.
    qtbot.addWidget(search_page)

    # 3. Assert that key widgets exist and are not None
    assert search_page.search_input is not None, "Search input should exist"
    assert search_page.search_button is not None, "Search button should exist"
    assert search_page.results_tree is not None, "Results tree should exist"

    # 4. Assert initial properties of the widgets
    assert search_page.search_input.placeholderText() == "e.g., C2040 or ESP32-C6", (
        "Incorrect placeholder text"
    )
    assert search_page.search_button.isEnabled(), (
        "Search button should be enabled by default"
    )
    assert search_page.results_tree.topLevelItemCount() == 0, (
        "Results tree should be empty initially"
    )


@pytest.mark.ui
def test_search_interaction(qtbot):
    """
    Tests user interaction: typing in the search box and clicking the search button.
    """
    search_page = SearchPage()
    qtbot.addWidget(search_page)

    # We want to check if the `search_requested` signal is emitted
    # when the button is clicked.

    # Define the search term
    search_term = "DS2411"

    # Use qtbot to simulate typing into the search input
    qtbot.keyClicks(search_page.search_input, search_term)

    # Assert that the text was entered correctly
    assert search_page.search_input.text() == search_term

    # Use qtbot.wait_signal to wait for the 'search_requested' signal to be emitted.
    # The 'with' block will fail if the signal is not emitted within a timeout (default 1 sec).
    with qtbot.wait_signal(search_page.search_requested, raising=True) as blocker:
        # Simulate a click on the search button
        qtbot.mouseClick(search_page.search_button, Qt.LeftButton)

    # The signal was emitted! Now we can check the arguments it was emitted with.
    # The signal from the `with` block is available as `blocker.args`.
    assert blocker.args == [search_term]


@pytest.mark.ui
class TestImageDisplayStates:
    """Test suite for the state changes of the image display labels."""

    @pytest.fixture
    def search_page(self, qtbot):
        """Fixture to create a SearchPage instance for each test."""
        page = SearchPage()
        qtbot.addWidget(page)
        return page

    def test_initial_image_state(self, search_page):
        """Test the initial text on the image labels."""
        assert search_page.symbol_image_label.text() == "Select a component to see its symbol"
        assert search_page.footprint_image_label.text() == "Select a component to see its footprint"
        assert search_page.symbol_image_label.pixmap().isNull()
        assert search_page.footprint_image_label.pixmap().isNull()

    def test_set_loading_state(self, search_page):
        """Test setting the loading message."""
        search_page.set_symbol_loading(True)
        search_page.set_footprint_loading(True)
        assert search_page.symbol_image_label.text() == "Loading..."
        assert search_page.footprint_image_label.text() == "Loading..."

    def test_set_error_state(self, search_page):
        """Test setting an error message."""
        error_msg = "Image not found"
        search_page.set_symbol_error(error_msg)
        search_page.set_footprint_error(error_msg)
        assert "Error:" in search_page.symbol_image_label.text()
        assert error_msg in search_page.symbol_image_label.text()
        assert "Error:" in search_page.footprint_image_label.text()
        assert error_msg in search_page.footprint_image_label.text()

    def test_set_image_state(self, search_page):
        """Test setting a pixmap image correctly clears text."""
        # Create a dummy pixmap (10x10, solid red)
        pixmap = QPixmap(10, 10)
        pixmap.fill(Qt.red)

        search_page.set_symbol_image(pixmap)
        search_page.set_footprint_image(pixmap)

        # The pixmap should be set
        assert search_page.symbol_image_label.pixmap() is not None
        assert search_page.footprint_image_label.pixmap() is not None
        
        # The label should no longer display any text
        assert search_page.symbol_image_label.text() == ""
        assert search_page.footprint_image_label.text() == ""

    def test_clear_images(self, search_page):
        """Test the clear_images method resets the state."""
        # First, set an image
        pixmap = QPixmap(10, 10)
        pixmap.fill(Qt.red)
        search_page.set_symbol_image(pixmap)
        search_page.set_footprint_image(pixmap)
        
        # Now, clear them
        search_page.clear_images()
        
        # Verify they are back to the initial state
        assert search_page.symbol_image_label.text() == "Select a component to see its symbol"
        assert search_page.footprint_image_label.text() == "Select a component to see its footprint"
        assert search_page.symbol_image_label.pixmap().isNull()
        assert search_page.footprint_image_label.pixmap().isNull()


# /Users/fred/librepcb_search/tests/test_search_page.py

import pytest
from PySide6.QtCore import Qt
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
    assert search_page.search_input.placeholderText() == "e.g., C2040 or ESP32-C6", "Incorrect placeholder text"
    assert search_page.search_button.isEnabled(), "Search button should be enabled by default"
    assert search_page.results_tree.topLevelItemCount() == 0, "Results tree should be empty initially"

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

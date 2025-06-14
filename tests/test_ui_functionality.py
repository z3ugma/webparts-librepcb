from unittest.mock import Mock, patch
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage
from pytestqt.qtbot import QtBot
import pytest

from models.search_result import SearchResult
from adapters.search_engine import Vendor
from ui.page_search import SearchPage
from ui.page_library import LibraryPage
from ui.page_library_element import LibraryElementPage

# --- Fixtures ---

@pytest.fixture
def search_page(qtbot: QtBot) -> SearchPage:
    """Create a SearchPage instance for testing."""
    widget = SearchPage()
    qtbot.addWidget(widget)
    return widget
    
# --- Tests for SearchPage ---

class TestSearchPageBehavior:
    def test_search_page_init(self, search_page: SearchPage):
        """Test that the SearchPage and its sidebar widgets initialize correctly."""
        assert search_page.search_input is not None
        assert search_page.search_button is not None
        assert search_page.add_to_library_button is not None
        assert search_page.results_tree is not None
        assert search_page.symbol_image_label is not None
        assert search_page.footprint_image_label is not None
        assert search_page.part_info_widget is not None
        assert search_page.hero_image_widget is not None
        assert search_page.label_3dModelStatus is not None
        assert search_page.datasheetLink is not None

    def test_search_requested_signal(self, search_page: SearchPage, qtbot: QtBot):
        """Test that the search_requested signal is emitted with the correct term."""
        search_term = "ESP32"
        with qtbot.wait_signal(search_page.search_requested) as blocker:
            search_page.search_input.setText(search_term)
            qtbot.mouseClick(search_page.search_button, Qt.LeftButton)
        assert blocker.args == [search_term]

    def test_item_selected_signal(self, search_page: SearchPage, qtbot: QtBot):
        """Test that item_selected signal emits the correct SearchResult object."""
        result = SearchResult(vendor="LCSC", part_name="Test Part", lcsc_id="C123", description="Desc", manufacturer="Mfr", mfr_part_number="TP-01", full_description="Full Desc")
        search_page.update_search_results([result])
        
        with qtbot.wait_signal(search_page.item_selected) as blocker:
            search_page.results_tree.setCurrentItem(search_page.results_tree.topLevelItem(0))
        assert blocker.args == [result]

    def test_set_details(self, search_page: SearchPage, qtbot: QtBot):
        """Test that component details are correctly displayed in the sidebar."""
        from models.common_info import ImageInfo
        
        result = SearchResult(
            vendor="LCSC", part_name="Test Part", lcsc_id="C123",
            description="Desc", manufacturer="Mfr", mfr_part_number="TP-01",
            full_description="Full Desc", has_3d_model=True,
            datasheet_url="http://example.com/datasheet.pdf",
            image=ImageInfo(url="http://example.com/image.png")
        )
        
        with qtbot.wait_signal(search_page.request_image) as blocker:
            search_page.set_details(result)

        assert search_page.part_info_widget.label_PartTitle.text() == "Test Part"
        assert search_page.part_info_widget.label_LcscId.text() == "LCSC ID: C123"
        assert search_page.part_info_widget.mfn_value.text() == "Mfr"
        assert search_page.label_3dModelStatus.text() == "3D Model: Found"
        assert 'href="http://example.com/datasheet.pdf"' in search_page.datasheetLink.text()
        assert blocker.args == [Vendor.LCSC, "http://example.com/image.png", "hero"]


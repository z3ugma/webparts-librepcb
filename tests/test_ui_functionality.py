from unittest.mock import Mock, patch
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QImage
from pytestqt.qtbot import QtBot
import pytest

from models.search_result import SearchResult
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
        assert search_page.label_LcscId is not None
        assert search_page.label_PartTitle is not None
        assert search_page.mfn_value is not None
        assert search_page.mfn_part_value is not None
        assert search_page.description_value is not None
        assert search_page.hero_view is not None
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
        result = SearchResult(
            vendor="LCSC", part_name="Test Part", lcsc_id="C123",
            description="Desc", manufacturer="Mfr", mfr_part_number="TP-01",
            full_description="Full Desc", has_3d_model=True,
            datasheet_url="http://example.com/datasheet.pdf",
            image_url="http://example.com/image.png"
        )
        
        with qtbot.wait_signal(search_page.request_image) as blocker:
            search_page.set_details(result)

        assert search_page.label_PartTitle.text() == "Test Part"
        assert search_page.label_LcscId.text() == "LCSC ID: C123"
        assert search_page.mfn_value.text() == "Mfr"
        assert search_page.label_3dModelStatus.text() == "3D Model: Found"
        assert 'href="http://example.com/datasheet.pdf"' in search_page.datasheetLink.text()
        assert blocker.args == ["LCSC", "http://example.com/image.png", "hero"]
        
class TestSearchPageHeroImage:
    def test_set_hero_text_displays_message(self, search_page: SearchPage):
        """Test that _set_hero_text properly displays a text message."""
        search_page._set_hero_text("Loading...")
        assert search_page.hero_text_item.toPlainText() == "Loading..."
        assert search_page.hero_text_item.isVisible()
        assert not search_page.hero_pixmap_item.isVisible()

    def test_set_hero_pixmap_displays_image(self, search_page: SearchPage):
        """Test that _set_hero_pixmap properly displays an image and hides text."""
        pixmap = QPixmap.fromImage(QImage(100, 100, QImage.Format_RGB32))
        search_page._set_hero_pixmap(pixmap)
        assert not search_page.hero_text_item.isVisible()
        assert search_page.hero_pixmap_item.isVisible()
        assert search_page.hero_pixmap_item.pixmap().size() == pixmap.size()

    def test_set_hero_pixmap_handles_null_pixmap(self, search_page: SearchPage, mocker):
        """Test that _set_hero_pixmap handles null/invalid pixmaps gracefully."""
        mocker.patch.object(search_page.hero_view, 'resetTransform')
        search_page._set_hero_pixmap(QPixmap())
        assert search_page.hero_view.resetTransform.called

    def test_set_hero_pixmap_handles_zero_view_width(self, search_page: SearchPage, mocker):
        """Test that _set_hero_pixmap handles zero view width gracefully."""
        mocker.patch.object(search_page.hero_view, 'resetTransform')
        pixmap = QPixmap.fromImage(QImage(100, 100, QImage.Format_RGB32))
        search_page.hero_view.width = Mock(return_value=0)
        search_page._set_hero_pixmap(pixmap)
        assert search_page.hero_view.resetTransform.called
        
    @pytest.mark.parametrize("img_w, img_h, view_w, view_h, expected_scale", [
        (200, 100, 300, 300, 2.25),  # Wide image, constrained by width
        (100, 200, 300, 300, 2.25),  # Tall image, constrained by height
        (100, 100, 300, 300, 4.5),   # Square image
    ])
    def test_scaling_calculation(self, search_page: SearchPage, mocker, img_w, img_h, view_w, view_h, expected_scale):
        """Test the hero image scaling calculation for various aspect ratios."""
        mocker.patch.object(search_page.hero_view, 'width', return_value=view_w)
        mocker.patch.object(search_page.hero_view, 'height', return_value=view_h)
        mocker.patch.object(search_page.hero_view, 'scale')

        pixmap = QPixmap(img_w, img_h)
        search_page._set_hero_pixmap(pixmap)
        
        search_page.hero_view.scale.assert_called_once_with(expected_scale, expected_scale)


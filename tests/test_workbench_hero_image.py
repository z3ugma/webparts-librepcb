import os
import sys
import pytest
from unittest.mock import Mock, patch

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QGraphicsView, QGraphicsScene, QGraphicsPixmapItem, QGraphicsTextItem

from models.search_result import SearchResult


class MockWorkbenchController:
    """Simplified mock of WorkbenchController for testing hero image behavior."""
    
    def __init__(self):
        # Mock the graphics components
        self.hero_view = Mock(spec=QGraphicsView)
        self.hero_view.width.return_value = 200
        self.hero_view.height.return_value = 200
        
        self.hero_scene = Mock(spec=QGraphicsScene)
        self.hero_pixmap_item = Mock(spec=QGraphicsPixmapItem)
        self.hero_text_item = Mock(spec=QGraphicsTextItem)
        
        # Import the actual methods we want to test
        from ui.workbench import WorkbenchController
        self._set_hero_text = WorkbenchController._set_hero_text.__get__(self)
        self._set_hero_pixmap = WorkbenchController._set_hero_pixmap.__get__(self)
        self.on_image_loaded = WorkbenchController.on_image_loaded.__get__(self)
        self.on_image_failed = WorkbenchController.on_image_failed.__get__(self)
        
        # Mock other dependencies
        self.page_Search = Mock()
        self.page_Search.set_symbol_image = Mock()
        self.page_Search.set_symbol_error = Mock()


@pytest.mark.ui
class TestHeroImageBehavior:
    """Test suite for hero image loading states and behavior."""
    
    @pytest.fixture
    def controller(self):
        """Create a mock controller for testing."""
        return MockWorkbenchController()
    
    def test_set_hero_text_displays_message(self, controller):
        """Test that _set_hero_text properly displays a text message."""
        test_message = "Loading..."
        
        controller._set_hero_text(test_message)
        
        controller.hero_text_item.setPlainText.assert_called_with(test_message)
        controller.hero_text_item.setVisible.assert_called_with(True)
        controller.hero_pixmap_item.setVisible.assert_called_with(False)
        controller.hero_view.resetTransform.assert_called()
        controller.hero_view.centerOn.assert_called_with(controller.hero_text_item)
    
    def test_set_hero_pixmap_displays_image(self, controller):
        """Test that _set_hero_pixmap properly displays an image."""
        pixmap = Mock(spec=QPixmap)
        pixmap.isNull.return_value = False
        pixmap.width.return_value = 100
        pixmap.height.return_value = 100
        
        controller._set_hero_pixmap(pixmap)
        
        controller.hero_pixmap_item.setPixmap.assert_called_with(pixmap)
        controller.hero_pixmap_item.setVisible.assert_called_with(True)
        controller.hero_text_item.setVisible.assert_called_with(False)
        controller.hero_view.resetTransform.assert_called()
        controller.hero_view.scale.assert_called()
        controller.hero_view.centerOn.assert_called_with(controller.hero_pixmap_item)
    
    def test_set_hero_pixmap_handles_null_pixmap(self, controller):
        """Test that _set_hero_pixmap handles null/invalid pixmaps gracefully."""
        pixmap = Mock(spec=QPixmap)
        pixmap.isNull.return_value = True
        
        controller._set_hero_pixmap(pixmap)
        
        controller.hero_pixmap_item.setPixmap.assert_called_with(pixmap)
        assert controller.hero_view.scale.call_count == 0
    
    def test_set_hero_pixmap_handles_zero_view_width(self, controller):
        """Test that _set_hero_pixmap handles zero view width gracefully."""
        controller.hero_view.width.return_value = 0
        pixmap = Mock(spec=QPixmap)
        pixmap.isNull.return_value = False
        pixmap.width.return_value = 100
        
        controller._set_hero_pixmap(pixmap)
        
        assert controller.hero_view.scale.call_count == 0
    
    def test_on_image_loaded_hero_type(self, controller):
        """Test that hero images are properly loaded and displayed."""
        image_data = b"fake_image_data"
        with patch('ui.workbench.QPixmap') as mock_pixmap_class:
            mock_pixmap = Mock(spec=QPixmap)
            mock_pixmap_class.return_value = mock_pixmap
            controller.on_image_loaded(image_data, "hero")
            mock_pixmap.loadFromData.assert_called_with(image_data)
            controller.hero_pixmap_item.setPixmap.assert_called_with(mock_pixmap)
    
    def test_on_image_failed_hero_type(self, controller):
        """Test that hero image failures are properly handled."""
        controller.on_image_failed("Network error", "hero")
        controller.hero_text_item.setPlainText.assert_called_with("Image Not Available")

@pytest.mark.ui
class TestHeroImageScaling:
    """Test suite for hero image scaling logic."""
    
    @pytest.fixture
    def controller(self):
        """Create a mock controller for testing."""
        return MockWorkbenchController()
    
    def test_scaling_calculation_wide_image(self, controller):
        """Test scaling calculation for a wide image."""
        pixmap = Mock(spec=QPixmap)
        pixmap.isNull.return_value = False
        pixmap.width.return_value = 300
        pixmap.height.return_value = 150
        controller._set_hero_pixmap(pixmap)
        controller.hero_view.scale.assert_called_with(2.0, 2.0)
    
    def test_scaling_calculation_tall_image(self, controller):
        """Test scaling calculation for a tall image."""
        pixmap = Mock(spec=QPixmap)
        pixmap.isNull.return_value = False
        pixmap.width.return_value = 150
        pixmap.height.return_value = 300
        controller._set_hero_pixmap(pixmap)
        controller.hero_view.scale.assert_called_with(2.0, 2.0)
    
    def test_scaling_calculation_square_image(self, controller):
        """Test scaling calculation for a square image."""
        pixmap = Mock(spec=QPixmap)
        pixmap.isNull.return_value = False
        pixmap.width.return_value = 100
        pixmap.height.return_value = 100
        controller._set_hero_pixmap(pixmap)
        controller.hero_view.scale.assert_called_with(3.0, 3.0)

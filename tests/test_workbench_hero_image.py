import pytest
from unittest.mock import Mock, patch
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
        
        # Verify text is set and visible
        controller.hero_text_item.setPlainText.assert_called_with(test_message)
        controller.hero_text_item.setVisible.assert_called_with(True)
        
        # Verify pixmap is hidden
        controller.hero_pixmap_item.setVisible.assert_called_with(False)
        
        # Verify view is reset and centered
        controller.hero_view.resetTransform.assert_called()
        controller.hero_view.centerOn.assert_called_with(controller.hero_text_item)
    
    def test_set_hero_pixmap_displays_image(self, controller):
        """Test that _set_hero_pixmap properly displays an image."""
        # Create a mock pixmap
        pixmap = Mock(spec=QPixmap)
        pixmap.isNull.return_value = False
        pixmap.width.return_value = 100
        pixmap.height.return_value = 100
        
        controller._set_hero_pixmap(pixmap)
        
        # Verify pixmap is set and visible
        controller.hero_pixmap_item.setPixmap.assert_called_with(pixmap)
        controller.hero_pixmap_item.setVisible.assert_called_with(True)
        
        # Verify text is hidden
        controller.hero_text_item.setVisible.assert_called_with(False)
        
        # Verify scaling logic is applied
        controller.hero_view.resetTransform.assert_called()
        controller.hero_view.scale.assert_called()
        controller.hero_view.centerOn.assert_called_with(controller.hero_pixmap_item)
    
    def test_set_hero_pixmap_handles_null_pixmap(self, controller):
        """Test that _set_hero_pixmap handles null/invalid pixmaps gracefully."""
        # Create a null pixmap
        pixmap = Mock(spec=QPixmap)
        pixmap.isNull.return_value = True
        
        controller._set_hero_pixmap(pixmap)
        
        # Verify pixmap is still set (even if null)
        controller.hero_pixmap_item.setPixmap.assert_called_with(pixmap)
        controller.hero_pixmap_item.setVisible.assert_called_with(True)
        controller.hero_text_item.setVisible.assert_called_with(False)
        
        # Verify scaling is NOT attempted for null pixmap
        assert controller.hero_view.scale.call_count == 0
    
    def test_set_hero_pixmap_handles_zero_view_width(self, controller):
        """Test that _set_hero_pixmap handles zero view width gracefully."""
        # Set view width to 0
        controller.hero_view.width.return_value = 0
        
        # Create a valid pixmap
        pixmap = Mock(spec=QPixmap)
        pixmap.isNull.return_value = False
        pixmap.width.return_value = 100
        pixmap.height.return_value = 100
        
        controller._set_hero_pixmap(pixmap)
        
        # Verify pixmap is still set
        controller.hero_pixmap_item.setPixmap.assert_called_with(pixmap)
        controller.hero_pixmap_item.setVisible.assert_called_with(True)
        controller.hero_text_item.setVisible.assert_called_with(False)
        
        # Verify scaling is NOT attempted when view width is 0
        assert controller.hero_view.scale.call_count == 0
    
    def test_on_image_loaded_hero_type(self, controller):
        """Test that hero images are properly loaded and displayed."""
        # Mock image data
        image_data = b"fake_image_data"
        
        # Mock QPixmap creation
        with patch('ui.workbench.QPixmap') as mock_pixmap_class:
            mock_pixmap = Mock(spec=QPixmap)
            mock_pixmap_class.return_value = mock_pixmap
            
            controller.on_image_loaded(image_data, "hero")
            
            # Verify pixmap was created and loaded
            mock_pixmap_class.assert_called_once()
            mock_pixmap.loadFromData.assert_called_with(image_data)
            
            # Verify pixmap was set (checking the method calls)
            controller.hero_pixmap_item.setPixmap.assert_called_with(mock_pixmap)
    
    def test_on_image_loaded_symbol_type(self, controller):
        """Test that symbol images are handled correctly."""
        # Mock image data
        image_data = b"fake_image_data"
        
        # Mock QPixmap creation
        with patch('ui.workbench.QPixmap') as mock_pixmap_class:
            mock_pixmap = Mock(spec=QPixmap)
            mock_pixmap_class.return_value = mock_pixmap
            
            controller.on_image_loaded(image_data, "symbol")
            
            # Verify pixmap was created and loaded
            mock_pixmap_class.assert_called_once()
            mock_pixmap.loadFromData.assert_called_with(image_data)
            
            # Verify the symbol image was handled by the search page
            controller.page_Search.set_symbol_image.assert_called_with(mock_pixmap)
            
            # Verify hero image was NOT touched
            controller.hero_pixmap_item.setPixmap.assert_not_called()
    
    def test_on_image_failed_hero_type(self, controller):
        """Test that hero image failures are properly handled."""
        error_message = "Network error"
        
        controller.on_image_failed(error_message, "hero")
        
        # Verify "Image Not Available" is shown
        controller.hero_text_item.setPlainText.assert_called_with("Image Not Available")
        controller.hero_text_item.setVisible.assert_called_with(True)
        controller.hero_pixmap_item.setVisible.assert_called_with(False)
    
    def test_on_image_failed_symbol_type(self, controller):
        """Test that symbol image failures are handled correctly."""
        error_message = "Network error"
        
        controller.on_image_failed(error_message, "symbol")
        
        # Verify the symbol error was handled by the search page
        controller.page_Search.set_symbol_error.assert_called_with(error_message)
        
        # Verify hero image was NOT touched
        controller.hero_text_item.setPlainText.assert_not_called()


@pytest.mark.ui
class TestHeroImageStates:
    """Test suite for different hero image states."""
    
    @pytest.fixture
    def controller(self):
        """Create a mock controller for testing."""
        return MockWorkbenchController()
    
    def test_loading_state(self, controller):
        """Test that loading state displays 'Loading...' message."""
        controller._set_hero_text("Loading...")
        
        controller.hero_text_item.setPlainText.assert_called_with("Loading...")
        controller.hero_text_item.setVisible.assert_called_with(True)
        controller.hero_pixmap_item.setVisible.assert_called_with(False)
    
    def test_no_image_state(self, controller):
        """Test that no image state displays 'No Image' message."""
        controller._set_hero_text("No Image")
        
        controller.hero_text_item.setPlainText.assert_called_with("No Image")
        controller.hero_text_item.setVisible.assert_called_with(True)
        controller.hero_pixmap_item.setVisible.assert_called_with(False)
    
    def test_error_state(self, controller):
        """Test that error state displays 'Image Not Available' message."""
        controller._set_hero_text("Image Not Available")
        
        controller.hero_text_item.setPlainText.assert_called_with("Image Not Available")
        controller.hero_text_item.setVisible.assert_called_with(True)
        controller.hero_pixmap_item.setVisible.assert_called_with(False)
    
    def test_image_loaded_state(self, controller):
        """Test that image loaded state displays the pixmap."""
        pixmap = Mock(spec=QPixmap)
        pixmap.isNull.return_value = False
        pixmap.width.return_value = 100
        pixmap.height.return_value = 100
        
        controller._set_hero_pixmap(pixmap)
        
        controller.hero_pixmap_item.setPixmap.assert_called_with(pixmap)
        controller.hero_pixmap_item.setVisible.assert_called_with(True)
        controller.hero_text_item.setVisible.assert_called_with(False)


@pytest.mark.ui
class TestHeroImageScaling:
    """Test suite for hero image scaling logic."""
    
    @pytest.fixture
    def controller(self):
        """Create a mock controller for testing."""
        return MockWorkbenchController()
    
    def test_scaling_calculation_wide_image(self, controller):
        """Test scaling calculation for a wide image."""
        # Set up view size (200x200)
        controller.hero_view.width.return_value = 200
        controller.hero_view.height.return_value = 200
        
        # Create a wide pixmap (300x150)
        pixmap = Mock(spec=QPixmap)
        pixmap.isNull.return_value = False
        pixmap.width.return_value = 300
        pixmap.height.return_value = 150
        
        controller._set_hero_pixmap(pixmap)
        
        # For a 200x200 view and 300x150 image:
        # scale_w = (1.5 * 200) / 300 = 1.0
        # scale_h = (1.5 * 200) / 150 = 2.0
        # Should use max(1.0, 2.0) = 2.0
        controller.hero_view.scale.assert_called_with(2.0, 2.0)
    
    def test_scaling_calculation_tall_image(self, controller):
        """Test scaling calculation for a tall image."""
        # Set up view size (200x200)
        controller.hero_view.width.return_value = 200
        controller.hero_view.height.return_value = 200
        
        # Create a tall pixmap (150x300)
        pixmap = Mock(spec=QPixmap)
        pixmap.isNull.return_value = False
        pixmap.width.return_value = 150
        pixmap.height.return_value = 300
        
        controller._set_hero_pixmap(pixmap)
        
        # For a 200x200 view and 150x300 image:
        # scale_w = (1.5 * 200) / 150 = 2.0
        # scale_h = (1.5 * 200) / 300 = 1.0
        # Should use max(2.0, 1.0) = 2.0
        controller.hero_view.scale.assert_called_with(2.0, 2.0)
    
    def test_scaling_calculation_square_image(self, controller):
        """Test scaling calculation for a square image."""
        # Set up view size (200x200)
        controller.hero_view.width.return_value = 200
        controller.hero_view.height.return_value = 200
        
        # Create a square pixmap (100x100)
        pixmap = Mock(spec=QPixmap)
        pixmap.isNull.return_value = False
        pixmap.width.return_value = 100
        pixmap.height.return_value = 100
        
        controller._set_hero_pixmap(pixmap)
        
        # For a 200x200 view and 100x100 image:
        # scale_w = (1.5 * 200) / 100 = 3.0
        # scale_h = (1.5 * 200) / 100 = 3.0
        # Should use max(3.0, 3.0) = 3.0
        controller.hero_view.scale.assert_called_with(3.0, 3.0)
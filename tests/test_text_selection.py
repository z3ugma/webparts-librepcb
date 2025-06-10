import os
import sys
import pytest
from unittest.mock import Mock, patch

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QLabel, QApplication

from ui.workbench import WorkbenchController


@pytest.mark.ui
class TestTextSelectionFeature:
    """Test suite for text selection functionality in sidebar labels."""
    
    def test_enable_text_selection_sets_correct_flags(self, qtbot):
        """Test that text selection is properly enabled on labels."""
        # Create a simple label to test
        label = QLabel("Test Label Content")
        qtbot.addWidget(label)
        
        # Enable text selection
        label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        label.setContextMenuPolicy(Qt.CustomContextMenu)
        label.setToolTip("Right-click to copy, or select text with mouse")
        
        # Verify the flags are set correctly
        flags = label.textInteractionFlags()
        assert flags & Qt.TextSelectableByMouse
        assert flags & Qt.TextSelectableByKeyboard
        
        # Verify context menu policy
        assert label.contextMenuPolicy() == Qt.CustomContextMenu
        
        # Verify tooltip
        assert "Right-click to copy" in label.toolTip()
    
    def test_label_text_selection_works(self, qtbot):
        """Test that text selection flags can be set on a label."""
        label = QLabel("LCSC ID: C123456")
        qtbot.addWidget(label)
        
        # Enable text selection
        label.setTextInteractionFlags(Qt.TextSelectableByMouse | Qt.TextSelectableByKeyboard)
        
        # Verify the text interaction flags are set
        flags = label.textInteractionFlags()
        assert flags & Qt.TextSelectableByMouse
        assert flags & Qt.TextSelectableByKeyboard
        
    def test_copy_label_text_function(self):
        """Test the copy functionality for labels."""
        mock_window = Mock()
        mock_window.statusBar.return_value = Mock()
        label = Mock(spec=QLabel)
        label.text.return_value = "ESP32-C6-WROOM-1-N8"
        label.hasSelectedText.return_value = False
        label.selectedText.return_value = ""
        
        with patch('ui.workbench.QApplication.clipboard') as mock_clipboard:
            mock_clipboard_instance = Mock()
            mock_clipboard.return_value = mock_clipboard_instance
            controller = Mock()
            controller.window = mock_window
            copy_method = WorkbenchController._copy_label_text.__get__(controller)
            copy_method(label, selected_only=False)
            mock_clipboard_instance.setText.assert_called_with("ESP32-C6-WROOM-1-N8")
            mock_window.statusBar().showMessage.assert_called()
    
    def test_copy_selected_text_only(self):
        """Test copying only selected text."""
        label = Mock(spec=QLabel)
        label.text.return_value = "LCSC ID: C123456"
        label.hasSelectedText.return_value = True
        label.selectedText.return_value = "C123456"
        mock_window = Mock()
        mock_window.statusBar.return_value = Mock()
        
        with patch('ui.workbench.QApplication.clipboard') as mock_clipboard:
            mock_clipboard_instance = Mock()
            mock_clipboard.return_value = mock_clipboard_instance
            controller = Mock()
            controller.window = mock_window
            copy_method = WorkbenchController._copy_label_text.__get__(controller)
            copy_method(label, selected_only=True)
            mock_clipboard_instance.setText.assert_called_with("C123456")
    
    def test_empty_text_handling(self):
        """Test that empty text is handled gracefully."""
        label = Mock(spec=QLabel)
        label.text.return_value = ""
        label.hasSelectedText.return_value = False
        label.selectedText.return_value = ""
        mock_window = Mock()
        mock_window.statusBar.return_value = Mock()
        
        with patch('ui.workbench.QApplication.clipboard') as mock_clipboard:
            mock_clipboard_instance = Mock()
            mock_clipboard.return_value = mock_clipboard_instance
            controller = Mock()
            controller.window = mock_window
            copy_method = WorkbenchController._copy_label_text.__get__(controller)
            copy_method(label, selected_only=False)
            mock_clipboard_instance.setText.assert_not_called()

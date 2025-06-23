import pytest
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QPixmap, QImage
from PySide6.QtCore import Qt
from pytestqt.qtbot import QtBot

from ui.hero_image_widget import HeroImageWidget


@pytest.fixture(scope="session")
def app():
    """Create a single QApplication instance for the whole test session."""
    q_app = QApplication.instance()
    if not q_app:
        q_app = QApplication([])
    return q_app


@pytest.fixture
def widget(qtbot: QtBot) -> HeroImageWidget:
    """Create and show a HeroImageWidget instance."""
    test_widget = HeroImageWidget()
    qtbot.addWidget(test_widget)
    return test_widget


class TestHeroImageWidget:
    def test_initial_state(self, widget: HeroImageWidget):
        """Test the widget's initial state after creation."""
        assert widget.hero_text.toPlainText() == "Select a part to view details"
        assert widget.hero_text.isVisible()
        assert not widget.hero_item.isVisible()

    def test_show_text(self, widget: HeroImageWidget):
        """Test the show_text method displays the correct message."""
        widget.show_text("Test Message")
        assert widget.hero_text.toPlainText() == "Test Message"
        assert widget.hero_text.isVisible()
        assert not widget.hero_item.isVisible()

    def test_show_loading(self, widget: HeroImageWidget):
        """Test the show_loading convenience method."""
        widget.show_loading()
        assert widget.hero_text.toPlainText() == "Loading..."
        assert widget.hero_text.isVisible()

    def test_show_no_image(self, widget: HeroImageWidget):
        """Test the show_no_image convenience method."""
        widget.show_no_image()
        assert widget.hero_text.toPlainText() == "No Image"
        assert widget.hero_text.isVisible()

    def test_show_pixmap(self, widget: HeroImageWidget):
        """Test that show_pixmap correctly displays an image."""
        pixmap = QPixmap(100, 100)
        pixmap.fill(Qt.red)

        widget.show_pixmap(pixmap)

        assert not widget.hero_text.isVisible()
        assert widget.hero_item.isVisible()
        assert widget.hero_item.pixmap().size() == pixmap.size()

    def test_show_pixmap_with_null_pixmap(self, widget: HeroImageWidget):
        """Test that providing a null pixmap shows the 'No Image' text."""
        widget.show_pixmap(QPixmap())

        assert widget.hero_text.toPlainText() == "No Image"
        assert widget.hero_text.isVisible()
        assert not widget.hero_item.isVisible()

    def test_clear_method(self, widget: HeroImageWidget):
        """Test that the clear method resets the widget to its initial state."""
        # First, set it to a different state
        pixmap = QPixmap(10, 10)
        widget.show_pixmap(pixmap)
        assert not widget.hero_text.isVisible()  # Pre-condition

        # Now, clear it
        widget.clear()

        assert widget.hero_text.toPlainText() == "Select a part to view details"
        assert widget.hero_text.isVisible()
        assert not widget.hero_item.isVisible()

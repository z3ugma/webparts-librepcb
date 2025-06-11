import pytest
import sys
import os
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

from PySide6.QtWidgets import QApplication
from PySide6.QtTest import QTest
from PySide6.QtCore import Qt

# Add the project root to the path so we can import our modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from ui.page_library import LibraryPage, LibraryPartLite
from models.library_part import LibraryPart


@pytest.fixture
def app():
    """Create QApplication instance for testing"""
    if not QApplication.instance():
        app = QApplication([])
    else:
        app = QApplication.instance()
    yield app


@pytest.fixture
def temp_library():
    """Create a temporary library with test data"""
    with tempfile.TemporaryDirectory() as temp_dir:
        library_path = Path(temp_dir) / "WebParts.lplib"
        webparts_dir = library_path / "webparts"
        pkg_dir = library_path / "pkg"
        
        # Create directory structure
        webparts_dir.mkdir(parents=True)
        pkg_dir.mkdir(parents=True)
        
        # Create test part 1
        part1_uuid = "test-uuid-1"
        part1_dir = webparts_dir / part1_uuid
        part1_dir.mkdir()
        
        part1_data = {
            "uuid": part1_uuid,
            "vendor": "TestVendor",
            "part_name": "TestPart1",
            "lcsc_id": "C12345",
            "manufacturer": "TestMfg",
            "mfr_part_number": "TP001",
            "description": "Test Part 1",
            "full_description": "This is test part 1",
            "datasheet_url": None,
            "stock_quantity": 100,
            "image": {},
            "symbol": {"uuid": "sym-uuid-1"},
            "footprint": {"uuid": "fp-uuid-1", "package_type": "QFN-32"},
            "component": {"uuid": "comp-uuid-1"},
            "device": {},
            "has_3d_model": False
        }
        
        with open(part1_dir / "part.wp", "w") as f:
            json.dump(part1_data, f, indent=2)
        
        # Create test part 2
        part2_uuid = "test-uuid-2"
        part2_dir = webparts_dir / part2_uuid
        part2_dir.mkdir()
        
        part2_data = {
            "uuid": part2_uuid,
            "vendor": "TestVendor",
            "part_name": "TestPart2",
            "lcsc_id": "C67890",
            "manufacturer": "TestMfg2",
            "mfr_part_number": "TP002",
            "description": "Test Part 2",
            "full_description": "This is test part 2",
            "datasheet_url": None,
            "stock_quantity": 50,
            "image": {},
            "symbol": {},
            "footprint": {"uuid": "fp-uuid-2", "package_type": "SOIC-8"},
            "component": {},
            "device": {"uuid": "dev-uuid-2"},
            "has_3d_model": True
        }
        
        with open(part2_dir / "part.wp", "w") as f:
            json.dump(part2_data, f, indent=2)
        
        yield library_path


def test_library_page_loads(app, temp_library):
    """Test that LibraryPage can be instantiated without errors"""
    with patch('ui.page_library.LibraryManager') as mock_manager:
        # Mock the library manager to use our temp library
        mock_instance = MagicMock()
        mock_instance.webparts_dir = temp_library / "webparts"
        mock_instance.get_all_parts.return_value = []
        mock_manager.return_value = mock_instance
        
        page = LibraryPage()
        assert page is not None
        assert page.tree is not None
        assert page.search_button is not None


def test_library_part_lite_creation():
    """Test LibraryPartLite data structure"""
    flags = {"footprint": True, "symbol": False, "component": True, "device": False}
    lite = LibraryPartLite("test-uuid", "TestPart", "C12345", flags, "/path/to/hero.png")
    
    assert lite.uuid == "test-uuid"
    assert lite.part_name == "TestPart" 
    assert lite.lcsc_id == "C12345"
    assert lite.status_flags["footprint"] is True
    assert lite.status_flags["symbol"] is False
    assert lite.hero_path == "/path/to/hero.png"


def test_library_page_tree_population(app, temp_library):
    """Test that the tree gets populated with library parts"""
    with patch('ui.page_library.LibraryManager') as mock_manager:
        # Create mock parts
        part1 = LibraryPart(
            uuid="test-uuid-1",
            vendor="TestVendor",
            part_name="TestPart1",
            lcsc_id="C12345",
            manufacturer="TestMfg",
            mfr_part_number="TP001",
            description="Test Part 1",
            full_description="This is test part 1",
            symbol={"uuid": "sym-uuid-1"},
            footprint={"uuid": "fp-uuid-1", "package_type": "QFN-32"},
            component={"uuid": "comp-uuid-1"},
            device={}
        )
        
        mock_instance = MagicMock()
        mock_instance.webparts_dir = temp_library / "webparts"
        mock_instance.get_all_parts.return_value = [part1]
        mock_manager.return_value = mock_instance
        
        page = LibraryPage()
        
        # Create test data
        flags = {"footprint": True, "symbol": True, "component": True, "device": False}
        lite = LibraryPartLite("test-uuid-1", "TestPart1", "C12345", flags, "")
        
        # Simulate parts loading
        page.on_parts_loaded([lite])
        
        # Check tree has been populated
        assert page.tree.topLevelItemCount() == 1
        item = page.tree.topLevelItem(0)
        assert item.text(0) == "TestPart1"
        assert item.text(1) == "✔"  # footprint
        assert item.text(2) == "✔"  # symbol  
        assert item.text(3) == "✔"  # component
        assert item.text(4) == "✘"  # device


if __name__ == "__main__":
    pytest.main([__file__])
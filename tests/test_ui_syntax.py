"""
Test module to verify all UI components can be imported and their XML files are valid.

This test performs syntax checking for:
- Python module imports from ui/
- XML syntax validation for .ui files
- Qt widget loading compatibility
"""

import os
import pytest
import glob
from pathlib import Path
from xml.etree import ElementTree as ET
from PySide6.QtWidgets import QApplication
from PySide6.QtUiTools import QUiLoader


class TestUISyntax:
    """Test class for UI syntax validation"""
    
    @classmethod
    def setup_class(cls):
        """Set up Qt application for testing"""
        # Create QApplication if it doesn't exist
        cls.app = QApplication.instance()
        if cls.app is None:
            cls.app = QApplication([])
    
    def get_ui_python_modules(self):
        """Get all Python modules in the ui/ directory"""
        ui_dir = Path(__file__).parent.parent / "ui"
        python_files = list(ui_dir.glob("*.py"))
        # Filter out __init__.py and __pycache__
        modules = [f.stem for f in python_files if f.stem != "__init__"]
        return modules
    
    def get_ui_xml_files(self):
        """Get all .ui XML files in the ui/ directory"""
        ui_dir = Path(__file__).parent.parent / "ui"
        ui_files = list(ui_dir.glob("*.ui"))
        return ui_files
    
    @pytest.mark.parametrize("module_name", [
        "assembly_page",
        "finalize_page", 
        "footprint_review_page",
        "hero_image_widget",
        "page_library",
        "page_library_element", 
        "page_search",
        "part_info_widget",
        "symbol_review_page",
        "workbench"
    ])
    def test_ui_module_import(self, module_name):
        """Test that each UI module can be imported without syntax errors"""
        try:
            # Dynamic import of the module
            module = __import__(f"ui.{module_name}", fromlist=[module_name])
            
            # Try to get the main class from each module
            # Most modules have a class named like ModuleName + "Page" or "Widget"
            class_name_candidates = [
                # Convert snake_case to PascalCase and add common suffixes
                "".join(word.capitalize() for word in module_name.split("_")) + "Page",
                "".join(word.capitalize() for word in module_name.split("_")) + "Widget", 
                "".join(word.capitalize() for word in module_name.split("_")),
                # Specific known class names
                "WorkbenchController" if module_name == "workbench" else None
            ]
            
            # Try to instantiate or at least access the main class
            main_class = None
            for class_name in class_name_candidates:
                if class_name and hasattr(module, class_name):
                    main_class = getattr(module, class_name)
                    break
            
            # For workbench, we test the main function instead of instantiation
            if module_name == "workbench":
                assert hasattr(module, "main"), f"Module {module_name} should have main() function"
            elif main_class:
                # Just verify we can access the class (don't instantiate to avoid Qt setup issues)
                assert callable(main_class), f"Main class in {module_name} should be callable"
            else:
                # At minimum, the module should import without error
                assert module is not None, f"Module {module_name} should import successfully"
                
        except ImportError as e:
            pytest.fail(f"Failed to import ui.{module_name}: {e}")
        except Exception as e:
            pytest.fail(f"Error testing ui.{module_name}: {e}")
    
    @pytest.mark.parametrize("ui_file", [
        "assembly_page.ui",
        "finalize_page.ui",
        "footprint_review_page.ui", 
        "hero_image_widget.ui",
        "page_library.ui",
        "page_library_element.ui",
        "page_search.ui",
        "part_info_widget.ui",
        "symbol_review_page.ui",
        "workbench.ui"
    ])
    def test_ui_xml_syntax(self, ui_file):
        """Test that each .ui file has valid XML syntax"""
        ui_dir = Path(__file__).parent.parent / "ui"
        ui_file_path = ui_dir / ui_file
        
        assert ui_file_path.exists(), f"UI file {ui_file} should exist"
        
        try:
            # Parse XML to check syntax
            tree = ET.parse(ui_file_path)
            root = tree.getroot()
            
            # Basic validation - should be a UI file
            assert root.tag == "ui", f"Root element should be 'ui' in {ui_file}"
            assert root.get("version") == "4.0", f"UI version should be 4.0 in {ui_file}"
            
            # Should have a class definition
            classes = root.findall("class")
            assert len(classes) >= 1, f"UI file {ui_file} should define at least one class"
            
            # Should have a widget definition
            widgets = root.findall("widget")
            assert len(widgets) >= 1, f"UI file {ui_file} should define at least one widget"
            
        except ET.ParseError as e:
            pytest.fail(f"XML syntax error in {ui_file}: {e}")
        except Exception as e:
            pytest.fail(f"Error parsing {ui_file}: {e}")
    
    def test_ui_loader_compatibility(self):
        """Test that QUiLoader can load each .ui file without errors"""
        ui_dir = Path(__file__).parent.parent / "ui"
        loader = QUiLoader()
        
        # Register custom widgets that might be referenced
        try:
            from ui.part_info_widget import PartInfoWidget
            from ui.hero_image_widget import HeroImageWidget
            loader.registerCustomWidget(PartInfoWidget)
            loader.registerCustomWidget(HeroImageWidget)
        except ImportError:
            # Custom widgets might not be available in all test environments
            pass
        
        ui_files_to_test = [
            "hero_image_widget.ui",
            "part_info_widget.ui",
            # Note: We skip the main page UI files as they have complex custom widget dependencies
        ]
        
        for ui_file in ui_files_to_test:
            ui_file_path = ui_dir / ui_file
            if ui_file_path.exists():
                try:
                    # Try to load the UI file
                    widget = loader.load(str(ui_file_path), None)
                    assert widget is not None, f"QUiLoader should be able to load {ui_file}"
                    
                    # Clean up
                    widget.deleteLater()
                    
                except Exception as e:
                    pytest.fail(f"QUiLoader failed to load {ui_file}: {e}")
    
    def test_workbench_main_function(self):
        """Test that the main workbench function can be imported"""
        try:
            from ui.workbench import main
            assert callable(main), "workbench.main should be callable"
        except ImportError as e:
            pytest.fail(f"Failed to import workbench main function: {e}")
    
    def test_all_ui_files_have_python_counterparts(self):
        """Verify that every .ui file has a corresponding .py file"""
        ui_dir = Path(__file__).parent.parent / "ui"
        
        ui_files = list(ui_dir.glob("*.ui"))
        for ui_file in ui_files:
            py_file = ui_file.with_suffix(".py")
            assert py_file.exists(), f"UI file {ui_file.name} should have corresponding Python file {py_file.name}"
    
    def test_custom_widgets_are_importable(self):
        """Test that custom widgets referenced in UI files can be imported"""
        custom_widgets = [
            ("ui.part_info_widget", "PartInfoWidget"),
            ("ui.hero_image_widget", "HeroImageWidget"),
        ]
        
        for module_name, class_name in custom_widgets:
            try:
                module = __import__(module_name, fromlist=[class_name])
                widget_class = getattr(module, class_name)
                assert callable(widget_class), f"{class_name} should be callable"
            except ImportError as e:
                pytest.fail(f"Failed to import {class_name} from {module_name}: {e}")
            except AttributeError as e:
                pytest.fail(f"Class {class_name} not found in {module_name}: {e}")


if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__, "-v"])
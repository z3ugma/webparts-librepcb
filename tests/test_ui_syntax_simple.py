"""
Simple syntax check test - mimics the manual command line validation
"""

import pytest
import subprocess
import sys
from pathlib import Path


def test_ui_modules_syntax_check():
    """Test that all UI modules can be imported - mimics manual command line check"""
    
    ui_modules = [
        "ui.assembly_page",
        "ui.finalize_page", 
        "ui.footprint_review_page",
        "ui.hero_image_widget",
        "ui.page_library",
        "ui.page_library_element",
        "ui.page_search",
        "ui.part_info_widget",
        "ui.symbol_review_page",
        "ui.workbench"
    ]
    
    for module in ui_modules:
        # Test import using subprocess to avoid Qt app conflicts
        cmd = [
            sys.executable, "-c", 
            f"import {module}; print('{module} syntax OK')"
        ]
        
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=10,
                cwd=Path(__file__).parent.parent  # Run from project root
            )
            
            assert result.returncode == 0, f"Import failed for {module}: {result.stderr}"
            assert "syntax OK" in result.stdout, f"Expected success message not found for {module}"
            
        except subprocess.TimeoutExpired:
            pytest.fail(f"Import test timed out for {module}")
        except Exception as e:
            pytest.fail(f"Unexpected error testing {module}: {e}")


def test_workbench_main_import():
    """Test the specific workbench main import that was used manually"""
    cmd = [
        sys.executable, "-c", 
        "from ui.workbench import main; print('Workbench syntax OK')"
    ]
    
    try:
        result = subprocess.run(
            cmd, 
            capture_output=True, 
            text=True, 
            timeout=10,
            cwd=Path(__file__).parent.parent
        )
        
        assert result.returncode == 0, f"Workbench main import failed: {result.stderr}"
        assert "Workbench syntax OK" in result.stdout, "Expected success message not found"
        
    except subprocess.TimeoutExpired:
        pytest.fail("Workbench main import test timed out")
    except Exception as e:
        pytest.fail(f"Unexpected error testing workbench main: {e}")


if __name__ == "__main__":
    # Allow running this test file directly
    pytest.main([__file__, "-v"])
import os
import sys
import pytest
from unittest.mock import patch, Mock
import requests

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, project_root)

from adapters.search_engine import SearchEngine, CACHE_DIR


class DummyEngine(SearchEngine):
    """A concrete implementation of SearchEngine for testing."""
    def search(self, search_term): pass
    def get_fully_hydrated_search_result(self, search_result): pass


@pytest.fixture
def cache_test_engine(tmp_path):
    """
    Creates a DummyEngine instance and redirects its CACHE_DIR
    to a temporary directory provided by pytest's tmp_path fixture.
    """
    # Point the module-level CACHE_DIR to the temp path for the duration of the test
    with patch('adapters.search_engine.CACHE_DIR', tmp_path):
        engine = DummyEngine()
        yield engine


@patch('adapters.search_engine.requests.get')
def test_download_first_time(mock_get, cache_test_engine):
    """
    Test that an image is downloaded from the network and saved to cache
    when it's not already cached.
    """
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.content = b'fake-image-data'
    mock_get.return_value = mock_response
    
    image_url = "http://example.com/image.png"
    
    data = cache_test_engine.download_image_from_url(image_url)
    
    mock_get.assert_called_once_with(image_url, headers={"User-Agent": "WebParts/0.1"})
    assert data == b'fake-image-data'
    
    expected_cache_file = cache_test_engine._get_cache_path(image_url, "png")
    assert expected_cache_file.exists()
    assert expected_cache_file.read_bytes() == b'fake-image-data'


@patch('adapters.search_engine.requests.get')
def test_download_from_cache(mock_get, cache_test_engine):
    """
    Test that an image is loaded from the cache on the second request
    and does not trigger a network call.
    """
    image_url = "http://example.com/image.png"
    expected_cache_file = cache_test_engine._get_cache_path(image_url, "png")
    expected_cache_file.write_bytes(b'cached-data')
    
    data = cache_test_engine.download_image_from_url(image_url)
    
    mock_get.assert_not_called()
    assert data == b'cached-data'


@patch('adapters.search_engine.requests.get')
def test_download_network_failure(mock_get, cache_test_engine):
    """
    Test that the download method handles network failures gracefully.
    """
    mock_get.side_effect = requests.exceptions.RequestException("Network error")
    image_url = "http://example.com/image.png"
    
    data = cache_test_engine.download_image_from_url(image_url)
    
    assert data is None
    expected_cache_file = cache_test_engine._get_cache_path(image_url, "png")
    assert not expected_cache_file.exists()

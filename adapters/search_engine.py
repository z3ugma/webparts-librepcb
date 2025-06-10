from abc import ABC, abstractmethod
import hashlib
import logging
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse
import requests

from models.search_result import SearchResult

logger = logging.getLogger(__name__)
CACHE_DIR = Path("image_cache")
CACHE_DIR.mkdir(exist_ok=True)  # Ensure cache directory exists on module load


class SearchEngine(ABC):
    """
    Abstract base class for a component search engine, including default
    implementations for common tasks like cached downloads.
    """

    @abstractmethod
    def search(self, search_term: str) -> List[SearchResult]:
        """Perform a search for a given term."""
        pass

    @abstractmethod
    def get_fully_hydrated_search_result(
        self, search_result: SearchResult
    ) -> Optional[SearchResult]:
        """Fetch all detailed data for a given search result."""
        pass

    def _get_cache_path(self, url: str, file_type: str) -> Path:
        url_hash = hashlib.md5(url.encode()).hexdigest()
        return CACHE_DIR / f"{url_hash}.{file_type}"

    def _load_from_cache(self, cache_path: Path) -> Optional[bytes]:
        if cache_path.exists():
            try:
                return cache_path.read_bytes()
            except Exception as e:
                logger.warning(f"Failed to read cache file {cache_path}: {e}")
        return None

    def _save_to_cache(self, cache_path: Path, data: bytes) -> None:
        try:
            cache_path.write_bytes(data)
            logger.info(f"💾 Saved to cache: {cache_path}")
        except Exception as e:
            logger.warning(f"Failed to save cache file {cache_path}: {e}")

    def _download_with_cache(self, url: str, file_type: str) -> Optional[bytes]:
        cache_path = self._get_cache_path(url, file_type)
        cached_data = self._load_from_cache(cache_path)
        if cached_data:
            return cached_data
        try:
            headers = {"User-Agent": "WebParts/0.1"}
            response = requests.get(url, headers=headers)
            if response.status_code == requests.codes.ok:
                data = response.content
                self._save_to_cache(cache_path, data)
                return data
        except Exception as e:
            logger.error(f"Error downloading {url}: {e}")
        return None

    def download_image_from_url(self, image_url: str) -> Optional[bytes]:
        if not image_url:
            return None
        # Use pathlib for robust path manipulation
        path = Path(urlparse(image_url).path)
        file_ext = path.suffix
        file_type = file_ext[1:].lower() if file_ext else "jpg"
        return self._download_with_cache(image_url, file_type)

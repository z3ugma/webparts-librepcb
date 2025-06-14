import hashlib
import os
from abc import ABC, abstractmethod
from enum import Enum
from pathlib import Path
from typing import List, Optional, Tuple

import requests

from models.search_result import SearchResult
from constants import CACHE_DIR, USER_AGENT

class Vendor(Enum):
    LCSC = "LCSC"

class SearchEngine(ABC):
    def __init__(self) -> None:
        CACHE_DIR.mkdir(exist_ok=True)

    @abstractmethod
    def search(self, vendor: Vendor, search_term: str) -> List[SearchResult]:
        """Perform a search for a given term."""
        pass

    @abstractmethod
    def get_fully_hydrated_search_result(
        self, search_result: SearchResult
    ) -> SearchResult:
        """Fetch all detailed data for a given search result."""
        pass

    def download_image_from_url(
        self, vendor: Vendor, image_url: str
    ) -> Optional[Tuple[bytes, str]]:
        if not image_url:
            return None
        cache_path = self._get_cache_path_for_image(image_url)
        cached_data = self._load_from_cache(cache_path)
        if cached_data:
            return cached_data, str(cache_path.resolve())
        headers = {
            "User-Agent": USER_AGENT,
        }
        try:
            r = requests.get(url=image_url, headers=headers)
            if r.status_code == 200:
                self._save_to_cache(cache_path, r.content)
                return r.content, str(cache_path.resolve())
        except requests.exceptions.RequestException:
            # Network error or other request failure
            pass
        return None

    def _get_cache_path_for_image(self, image_url: str) -> Path:
        _, ext = os.path.splitext(image_url)
        if not ext:
            ext = ".jpg"  # Default extension
        filename = hashlib.md5(image_url.encode()).hexdigest() + ext
        return CACHE_DIR / filename

    def _get_cache_path(self, name: str, extension: str) -> Path:
        return CACHE_DIR / f"{name}.{extension}"

    def _load_from_cache(self, path: Path) -> Optional[bytes]:
        if path.exists():
            return path.read_bytes()
        return None

    def _save_to_cache(self, path: Path, data: bytes):
        path.write_bytes(data)

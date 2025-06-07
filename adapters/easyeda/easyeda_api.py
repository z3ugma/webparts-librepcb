# Global imports
import hashlib
import logging
import os
from pathlib import Path
from typing import List, Optional
from urllib.parse import urlparse

import requests

from models.search_result import SearchResult

logger = logging.getLogger(__name__)

API_ENDPOINT = "https://easyeda.com/api/products/{lcsc_id}/components?version=6.4.19.5"
SVG_ENDPOINT = "https://easyeda.com/api/products/{lcsc_id}/svgs"
SEARCH_ENDPOINT = "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList/v2"
IMAGE_ENDPOINT = "https://jlcpcb.com/api/file/downloadByFileSystemAccessId/{image_id}"

CACHE_DIR = Path("image_cache")
CACHE_DIR.mkdir(exist_ok=True)


class EasyEDAApi:
    def __init__(self) -> None:
        self.headers = {
            "Accept-Encoding": "gzip, deflate",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-Agent": "WebParts v0.1",
        }

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
            logger.info(f"📁 Loaded from cache: {url}")
            return cached_data
        try:
            response = requests.get(url, headers={"User-Agent": self.headers["User-Agent"]})
            if response.status_code == requests.codes.ok:
                data = response.content
                self._save_to_cache(cache_path, data)
                logger.info(f"⬇️ Downloaded and cached: {url}")
                return data
            else:
                logger.warning(f"Failed to download {url}: HTTP {response.status_code}")
        except Exception as e:
            logger.error(f"Error downloading {url}: {e}")
        return None

    def get_component_data(self, lcsc_id: str) -> dict:
        """Fetches the raw component JSON data from the API."""
        r = requests.get(url=API_ENDPOINT.format(lcsc_id=lcsc_id), headers=self.headers)
        if r.status_code != 200:
            logger.error(f"Failed to get info for {lcsc_id}: HTTP {r.status_code}")
            return {}
        api_response = r.json()
        if not api_response.get("success"):
            logger.error(f"API request unsuccessful for {lcsc_id}: {api_response.get('msg')}")
            return {}
        logger.info(f"{r.status_code} {API_ENDPOINT.format(lcsc_id=lcsc_id)}")
        return api_response

    def get_svg_data(self, lcsc_id: str) -> dict:
        """Fetches the raw SVG data from the API."""
        r = requests.get(url=SVG_ENDPOINT.format(lcsc_id=lcsc_id), headers=self.headers)
        if r.status_code != 200:
            logger.error(f"Failed to get SVGs for {lcsc_id}: HTTP {r.status_code}")
            return {}
        api_response = r.json()
        if not api_response.get("success"):
            logger.error(f"API request for SVGs unsuccessful for {lcsc_id}: {api_response.get('msg')}")
            return {}
        logger.info(f"{r.status_code} {SVG_ENDPOINT.format(lcsc_id=lcsc_id)}")
        return api_response

    def download_image_from_url(self, image_url: str) -> Optional[bytes]:
        if not image_url: return None
        path = urlparse(image_url).path
        _filename, file_ext = os.path.splitext(path)
        file_type = file_ext[1:].lower() if file_ext else "jpg"
        return self._download_with_cache(image_url, file_type)

    def search_easyeda_api(self, search: str) -> List[SearchResult]:
        payload = {"currentPage": 1, "pageSize": 25, "searchType": 2, "keyword": search}
        headers = self.headers.copy()
        headers["Content-Type"] = "application/json"
        r = requests.post(url=SEARCH_ENDPOINT, json=payload, headers=headers)
        if r.status_code != requests.codes.ok:
            logger.error(f"Search failed: status code {r.status_code}")
            return []
        logger.info(f"{r.status_code} {SEARCH_ENDPOINT}")
        raw_results = r.json().get("data", {}).get("componentPageInfo", {}).get("list", [])
        
        # CORRECTED: Reverted to direct instantiation of SearchResult
        search_results = []
        for raw_result in raw_results:
            try:
                image_id = raw_result.get("productBigImageAccessId")
                image_url = IMAGE_ENDPOINT.format(image_id=image_id) if image_id else None
                search_result = SearchResult(
                    vendor="LCSC",
                    part_name=raw_result.get("componentModelEn", ""),
                    lcsc_id=raw_result.get("componentCode", ""),
                    description=raw_result.get("describe", ""),
                    manufacturer=raw_result.get("componentBrandEn", ""),
                    mfr_part_number=raw_result.get("componentModelEn", ""),
                    full_description=raw_result.get("describe", ""),
                    datasheet_url=raw_result.get("dataManualUrl"),
                    image_url=image_url,
                    package_type=raw_result.get("componentSpecificationEn"),
                    stock_quantity=raw_result.get("stockCount", 0),
                )
                search_results.append(search_result)
            except Exception as e:
                logger.warning(
                    f"Failed to parse search result: {e}, raw data: {raw_result}"
                )
        return search_results

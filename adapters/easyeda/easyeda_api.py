# Global imports
import json
import logging
from pathlib import Path
from typing import List, Optional

import requests

from models.search_result import SearchResult
from svg_utils import render_svg_to_png_bytes
from adapters.search_engine import SearchEngine

logger = logging.getLogger(__name__)

API_ENDPOINT = "https://easyeda.com/api/products/{lcsc_id}/components?version=6.4.19.5"
SVG_ENDPOINT = "https://easyeda.com/api/products/{lcsc_id}/svgs"
SEARCH_ENDPOINT = "https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList/v2"
IMAGE_ENDPOINT = "https://jlcpcb.com/api/file/downloadByFileSystemAccessId/{image_id}"


class EasyEDAApi(SearchEngine):
    def __init__(self) -> None:
        self.headers = {
            "Accept-Encoding": "gzip, deflate",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-Agent": "WebParts v0.1",
        }

    def get_and_cache_svg_data(self, lcsc_id: str) -> Optional[dict]:
        cache_path = self._get_cache_path(f"svg_{lcsc_id}", "json")
        cached_data = self._load_from_cache(cache_path)
        if cached_data:
            return json.loads(cached_data)
        r = requests.get(url=SVG_ENDPOINT.format(lcsc_id=lcsc_id), headers=self.headers)
        if r.status_code == 200 and r.json().get("success"):
            self._save_to_cache(cache_path, r.content)
            return r.json()
        return None
        
    def _generate_footprint_png_from_data(self, lcsc_id: str, svg_data: dict) -> Optional[str]:
        png_cache_path = self._get_cache_path(f"footprint_{lcsc_id}", "png")
        if png_cache_path.exists():
            return str(png_cache_path.resolve())
        try:
            svg_string = svg_data["result"][1]["svg"]
        except (IndexError, KeyError, TypeError):
            logger.warning(f"No footprint SVG found in svg_data for {lcsc_id}.")
            return None
        png_data = render_svg_to_png_bytes(svg_string.encode("utf-8"), 500, 500)
        if png_data:
            self._save_to_cache(png_cache_path, png_data)
            return str(png_cache_path.resolve())
        return None

    def _generate_symbol_png_from_data(self, lcsc_id: str, svg_data: dict) -> Optional[str]:
        png_cache_path = self._get_cache_path(f"symbol_{lcsc_id}", "png")
        if png_cache_path.exists():
            return str(png_cache_path.resolve())
        try:
            svg_string = svg_data["result"][0]["svg"]
        except (IndexError, KeyError, TypeError):
            logger.warning(f"No symbol SVG found in svg_data for {lcsc_id}.")
            return None
        png_data = render_svg_to_png_bytes(svg_string.encode("utf-8"), 500, 500)
        if png_data:
            self._save_to_cache(png_cache_path, png_data)
            return str(png_cache_path.resolve())
        return None

    def search(self, search_term: str) -> List[SearchResult]:
        payload = {"currentPage": 1, "pageSize": 25, "searchType": 2, "keyword": search_term}
        headers = self.headers.copy()
        headers["Content-Type"] = "application/json"
        r = requests.post(url=SEARCH_ENDPOINT, json=payload, headers=headers)
        if r.status_code != requests.codes.ok:
            return []
        raw_results = r.json().get("data", {}).get("componentPageInfo", {}).get("list", [])
        search_results = []
        for raw_result in raw_results:
            try:
                image_id = raw_result.get("productBigImageAccessId")
                image_url = IMAGE_ENDPOINT.format(image_id=image_id) if image_id else None
                search_results.append(SearchResult(
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
                ))
            except Exception as e:
                logger.warning(f"Failed to parse search result: {e}")
        return search_results

    def get_fully_hydrated_search_result(
        self, search_result: SearchResult
    ) -> SearchResult:
        svg_data = self.get_and_cache_svg_data(search_result.lcsc_id)
        
        if svg_data:
            search_result.symbol_png_path = self._generate_symbol_png_from_data(search_result.lcsc_id, svg_data)
            search_result.footprint_png_path = self._generate_footprint_png_from_data(search_result.lcsc_id, svg_data)
        else:
            logger.warning(f"Could not fetch SVG data for {search_result.lcsc_id}. Paths will be null.")
        
        return search_result

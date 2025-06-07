import logging
from typing import List, Optional

from PySide6.QtCore import QSize

from adapters.easyeda.easyeda_api import EasyEDAApi
from adapters.easyeda.easyeda_footprint import EasyEDAParser
from models.footprint import Footprint
from models.search_result import SearchResult
from svg_utils import add_pad_numbers_to_svg, render_svg_to_png_bytes

logger = logging.getLogger(__name__)

APIS = [EasyEDAApi()]


class Search:
    def __init__(self, apis=None):
        self.apis = apis if apis is not None else APIS

    def search(self, search_term: str) -> List[SearchResult]:
        logger.info(f"API: Searching for '{search_term}'...")
        all_results = []
        for api in self.apis:
            try:
                results = api.search_easyeda_api(search_term)
                all_results.extend(results)
            except Exception as e:
                logger.error(f"Failed to search with {api.__class__.__name__}: {e}")
        logger.info(f"API: Found {len(all_results)} results")
        return all_results

    def get_footprint(self, lcsc_id: str) -> Optional[Footprint]:
        if not self.apis:
            return None
        api = self.apis[0]
        component_data = api.get_component_data(lcsc_id)
        if not component_data or "result" not in component_data:
            return None
        parser = EasyEDAParser()
        return parser.parse_easyeda_json(component_data["result"])

    def get_footprint_png_with_pads(self, lcsc_id: str) -> Optional[bytes]:
        """
        Gets the footprint, adds pad numbers, renders it to a PNG, and caches the result.
        """
        if not self.apis:
            return None
        api = self.apis[0]

        # Use a consistent cache key for the final PNG with pad numbers
        png_cache_path = api._get_cache_path(f"footprint_{lcsc_id}_with_pads", "png")
        cached_png = api._load_from_cache(png_cache_path)
        if cached_png:
            logger.info(f"Loaded footprint PNG from cache for {lcsc_id}")
            return cached_png

        # --- If not in cache, generate it ---
        logger.info(f"Generating footprint PNG for {lcsc_id}...")
        footprint_model = self.get_footprint(lcsc_id)
        raw_svg_data = api.get_svg_data(lcsc_id)

        if not footprint_model or not raw_svg_data:
            logger.error(f"Missing data to generate footprint PNG for {lcsc_id}.")
            return None

        # Extract the SVG string from the raw data
        svg_string = raw_svg_data.get("result", [{}])[1].get("svg")
        if not svg_string:
            logger.error("Could not find SVG string in API response.")
            return None
            
        svg_with_pads = add_pad_numbers_to_svg(svg_string.encode('utf-8'), footprint_model.pads)
        
        # Render the final SVG to PNG bytes
        png_data = render_svg_to_png_bytes(svg_with_pads, QSize(500, 500))

        if png_data:
            logger.info(f"Successfully generated footprint PNG for {lcsc_id}, saving to cache.")
            api._save_to_cache(png_cache_path, png_data)
            return png_data
        
        logger.error(f"Failed to render footprint PNG for {lcsc_id}.")
        return None

    def download_image_from_url(self, image_url: str) -> Optional[bytes]:
        if not self.apis:
            return None
        api = self.apis[0]
        return api.download_image_from_url(image_url)

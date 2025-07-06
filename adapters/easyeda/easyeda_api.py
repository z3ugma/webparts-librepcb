import json
import logging
from typing import List, Optional
from uuid import UUID

import requests

import constants as const
from adapters.librepcb.librepcb_uuid import create_derived_uuidv4
from adapters.search_engine import SearchEngine, Vendor
from models.common_info import FootprintInfo, ImageInfo
from models.search_result import SearchResult
from svg_utils import render_svg_file_to_png_file

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
            "User-Agent": const.USER_AGENT,
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

    def _generate_footprint_png_from_data(
        self, lcsc_id: str, svg_data: dict
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Generates footprint SVG and a high-quality PNG, adding pad numbers to the SVG first.
        Returns (png_path, svg_path) tuple.
        """
        import shutil

        from svg_add_pad_labels import add_pad_numbers_to_svg_file

        png_cache_path = self._get_cache_path(f"footprint_{lcsc_id}", "png")
        svg_cache_path = self._get_cache_path(f"footprint_{lcsc_id}", "svg")

        if png_cache_path.exists() and svg_cache_path.exists():
            return str(png_cache_path.resolve()), str(svg_cache_path.resolve())

        try:
            raw_svg_string = svg_data["result"][1]["svg"]
        except (IndexError, KeyError, TypeError):
            logger.warning(f"No footprint SVG found in svg_data for {lcsc_id}.")
            return None, None

        # Save the raw SVG to a temporary file for processing
        temp_svg_path = self._get_cache_path(f"footprint_{lcsc_id}_temp", "svg")
        temp_svg_path.write_text(raw_svg_string, encoding="utf-8")

        # Add pad numbers to the SVG. This creates a new file with a `.text.svg` suffix.
        add_pad_numbers_to_svg_file(str(temp_svg_path))
        labeled_svg_path = temp_svg_path.with_suffix(".svg.text.svg")

        # If pad numbering succeeded, use the labeled SVG; otherwise, use the original.
        if labeled_svg_path.exists():
            shutil.move(str(labeled_svg_path), svg_cache_path)
            logger.info(f"Used labeled SVG for {lcsc_id}.")
        else:
            shutil.move(str(temp_svg_path), svg_cache_path)
            logger.warning(f"Pad numbering failed for {lcsc_id}, using original SVG.")

        # Clean up the original temp file if it's still there
        if temp_svg_path.exists():
            temp_svg_path.unlink()

        # Render the final SVG (with or without labels) to a high-quality PNG
        if svg_cache_path.exists():
            render_svg_file_to_png_file(str(svg_cache_path), str(png_cache_path))
            if png_cache_path.exists():
                return str(png_cache_path.resolve()), str(svg_cache_path.resolve())

        return None, str(svg_cache_path.resolve())

    def _generate_symbol_svg_and_png(
        self, lcsc_id: str, svg_data: dict
    ) -> tuple[Optional[str], Optional[str]]:
        """
        Generates symbol SVG and PNG.
        Returns (svg_path, png_path) tuple.
        """
        svg_cache_path = self._get_cache_path(f"symbol_{lcsc_id}", "svg")
        png_cache_path = self._get_cache_path(f"symbol_{lcsc_id}", "png")

        if svg_cache_path.exists() and png_cache_path.exists():
            return str(svg_cache_path.resolve()), str(png_cache_path.resolve())

        try:
            svg_string = svg_data["result"][0]["svg"]
            self._save_to_cache(svg_cache_path, svg_string.encode("utf-8"))
        except (IndexError, KeyError, TypeError):
            logger.warning(f"No symbol SVG found in svg_data for {lcsc_id}.")
            return None, None

        # Render the newly saved SVG file to a PNG file
        render_svg_file_to_png_file(str(svg_cache_path), str(png_cache_path))

        if png_cache_path.exists():
            return str(svg_cache_path.resolve()), str(png_cache_path.resolve())

        return str(svg_cache_path.resolve()), None

    def search(self, search_term: str) -> List[SearchResult]:
        payload = {
            "currentPage": 1,
            "pageSize": 25,
            "searchType": 2,
            "keyword": search_term,
        }
        headers = self.headers.copy()
        headers["Content-Type"] = "application/json"
        r = requests.post(url=SEARCH_ENDPOINT, json=payload, headers=headers)
        if r.status_code != requests.codes.ok:
            return []
        raw_results = (
            r.json().get("data", {}).get("componentPageInfo", {}).get("list", [])
        )
        search_results = []
        for raw_result in raw_results:
            try:
                image_id = raw_result.get("productBigImageAccessId")
                image_url = (
                    IMAGE_ENDPOINT.format(image_id=image_id) if image_id else None
                )
                search_results.append(
                    SearchResult(
                        vendor=Vendor.LCSC,
                        part_name=raw_result.get("componentModelEn", ""),
                        lcsc_id=raw_result.get("componentCode", ""),
                        description=raw_result.get("describe", ""),
                        manufacturer=raw_result.get("componentBrandEn", ""),
                        mfr_part_number=raw_result.get("componentModelEn", ""),
                        full_description=raw_result.get("describe", ""),
                        datasheet_url=raw_result.get("dataManualUrl"),
                        stock_quantity=raw_result.get("stockCount", 0),
                        image=ImageInfo(url=image_url),
                        footprint=FootprintInfo(
                            package_type=raw_result.get("componentSpecificationEn")
                        ),
                    )
                )
            except Exception as e:
                logger.warning(f"Failed to parse search result: {e}")
        return search_results

    def get_component_cad_data(self, lcsc_id: str) -> Optional[dict]:
        """Fetches the main CAD data blob for a component."""
        cache_path = self._get_cache_path(f"cad_{lcsc_id}", "json")
        cached_data = self._load_from_cache(cache_path)
        if cached_data:
            return json.loads(cached_data)

        r = requests.get(url=API_ENDPOINT.format(lcsc_id=lcsc_id), headers=self.headers)
        if r.status_code == 200 and r.json().get("success"):
            cad_data = r.json().get("result")
            self._save_to_cache(cache_path, json.dumps(cad_data).encode("utf-8"))
            return cad_data
        return None

    def get_fully_hydrated_search_result(
        self, search_result: SearchResult
    ) -> SearchResult:
        """
        Hydrates a search result with all necessary data, including UUIDs and asset paths.
        """
        cad_data = self.get_component_cad_data(search_result.lcsc_id)
        if not cad_data:
            logger.error(f"Could not fetch CAD data for {search_result.lcsc_id}.")
            return search_result

        search_result.raw_cad_data = cad_data

        svg_data = self.get_and_cache_svg_data(search_result.lcsc_id)
        if svg_data:
            symbol_svg_path, symbol_png_path = self._generate_symbol_svg_and_png(
                search_result.lcsc_id, svg_data
            )
            search_result.symbol_svg_cache_path = symbol_svg_path
            search_result.symbol_png_cache_path = symbol_png_path

            footprint_png_path, footprint_svg_path = (
                self._generate_footprint_png_from_data(search_result.lcsc_id, svg_data)
            )
            search_result.footprint_png_cache_path = footprint_png_path
            search_result.footprint_svg_cache_path = footprint_svg_path

        # Hydrate the hero image
        if search_result.image and search_result.image.url:
            try:
                # The method is on the base class
                _, cache_path = self.download_image_from_url(
                    search_result.vendor, search_result.image.url
                )
                search_result.hero_image_cache_path = cache_path
            except Exception as e:
                logger.error(
                    f"Failed to download hero image for {search_result.lcsc_id}: {e}"
                )

        try:
            raw_symbol_uuid = cad_data.get("dataStr", {}).get("head", {}).get("uuid")
            raw_package_uuid = (
                cad_data.get("packageDetail", {})
                .get("dataStr", {})
                .get("head", {})
                .get("uuid")
            )

            if raw_symbol_uuid:
                symbol_uuid_obj = UUID(raw_symbol_uuid)
                search_result.symbol.uuid = str(symbol_uuid_obj)
                search_result.component.uuid = str(
                    create_derived_uuidv4(symbol_uuid_obj, "component")
                )
                device_uuid_obj = create_derived_uuidv4(symbol_uuid_obj, "device")
                search_result.device.uuid = str(device_uuid_obj)
                search_result.uuid = str(device_uuid_obj)

            if raw_package_uuid:
                package_uuid_obj = UUID(raw_package_uuid)
                search_result.footprint.uuid = str(package_uuid_obj)

        except Exception as e:
            logger.error(
                f"Error extracting UUIDs for {search_result.lcsc_id}: {e}",
                exc_info=True,
            )

        try:
            if cad_data.get("packageDetail", {}).get("dataStr", {}).get("shape"):
                shapes = cad_data["packageDetail"]["dataStr"]["shape"]
                if any(s.startswith("SVGNODE") for s in shapes):
                    search_result.has_3d_model = True
        except Exception:
            pass

        return search_result

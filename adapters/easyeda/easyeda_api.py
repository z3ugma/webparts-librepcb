# Global imports
import logging

import requests

logger = logging.getLogger(__name__)

API_ENDPOINT = "https://easyeda.com/api/products/{lcsc_id}/components?version=6.4.19.5"
SVG_ENDPOINT = "https://easyeda.com/api/products/{lcsc_id}/svgs"
ENDPOINT_3D_MODEL_STEP = "https://modules.easyeda.com/qAxj6KHrDKw4blvCG8QJPs7Y/{uuid}"
# ENDPOINT_3D_MODEL_STEP found in https://modules.lceda.cn/smt-gl-engine/0.8.22.6032922c/smt-gl-engine.js : points to the bucket containing the step files.

# ------------------------------------------------------------


class EasyEDAApi:
    def __init__(self) -> None:
        self.headers = {
            "Accept-Encoding": "gzip, deflate",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-Agent": "WebParts v0.1",
        }

    def get_info_from_easyeda_api(self, lcsc_id: str) -> dict:
        r = requests.get(url=API_ENDPOINT.format(lcsc_id=lcsc_id), headers=self.headers)
        api_response = r.json()

        if not api_response or (
            "code" in api_response and api_response["success"] is False
        ):
            logger.error(f"{api_response}")
            return {}
        logger.info(f"{r.status_code} {API_ENDPOINT}")
        return r.json()

    def get_svgs(self, lcsc_id: str) -> dict:
        r = requests.get(url=SVG_ENDPOINT.format(lcsc_id=lcsc_id), headers=self.headers)
        api_response = r.json()

        if not api_response or (
            "code" in api_response and api_response["success"] is False
        ):
            logger.error(f"{api_response}")
            return {}
        logger.info(f"{r.status_code} {SVG_ENDPOINT}")
        return r.json()

    def get_cad_data_of_component(self, lcsc_id: str) -> dict:
        cp_cad_info = self.get_info_from_easyeda_api(lcsc_id=lcsc_id)
        if cp_cad_info == {}:
            return {}
        return cp_cad_info["result"]

    def get_step_3d_model(self, uuid: str) -> bytes:
        r = requests.get(
            url=ENDPOINT_3D_MODEL_STEP.format(uuid=uuid),
            headers={"User-Agent": self.headers["User-Agent"]},
        )
        if r.status_code != requests.codes.ok:
            logger.info(f"No step 3D model data found for uuid:{uuid} on easyeda")
            return None
        logger.info(f"{r.status_code} {ENDPOINT_3D_MODEL_STEP}")
        return r.content

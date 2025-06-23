import logging
from functools import wraps
from typing import Callable, Dict, List, Optional

from adapters.easyeda.easyeda_api import EasyEDAApi
from adapters.search_engine import SearchEngine, Vendor
from models.search_result import SearchResult

logger = logging.getLogger(__name__)

REGISTERED_ENGINES: Dict[Vendor, SearchEngine] = {Vendor.LCSC: EasyEDAApi()}


def with_engine(on_fail_return=None):
    """
    A decorator that finds the correct search engine based on the vendor,
    injects it into the decorated method, and handles engine-not-found errors.
    """

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(self, vendor_or_result, *args, **kwargs):
            if isinstance(vendor_or_result, SearchResult):
                vendor = vendor_or_result.vendor
            else:
                vendor = vendor_or_result

            # --- DEBUGGING LOGS ---
            logger.info(
                f"[DEBUG] Decorator received vendor: {vendor} (type: {type(vendor)})"
            )
            logger.info(f"[DEBUG] Available engine keys: {list(self.engines.keys())}")
            # --- END DEBUGGING ---

            engine = self.engines.get(vendor)

            if not engine:
                logger.error(f"No search engine registered for vendor: '{vendor}'")
                return on_fail_return() if callable(on_fail_return) else on_fail_return

            return func(self, engine, vendor_or_result, *args, **kwargs)

        return wrapper

    return decorator


class Search:
    """
    A lean orchestrator that delegates tasks to the appropriate,
    vendor-specific search engine using decorators to handle engine selection.
    """

    def __init__(self, engines: Dict[Vendor, SearchEngine] = None):
        self.engines = engines if engines is not None else REGISTERED_ENGINES

    @with_engine(on_fail_return=list)
    def search(
        self, engine: SearchEngine, vendor: Vendor, search_term: str
    ) -> List[SearchResult]:
        logger.info(
            f"Delegating search for '{search_term}' to {vendor.value} engine..."
        )
        return engine.search(search_term)

    @with_engine(on_fail_return=None)
    def get_fully_hydrated_search_result(
        self, engine: SearchEngine, search_result: SearchResult
    ) -> Optional[SearchResult]:
        logger.info(
            f"Delegating hydration for '{search_result.lcsc_id}' to {search_result.vendor.value} engine..."
        )
        return engine.get_fully_hydrated_search_result(search_result)

    @with_engine(on_fail_return=None)
    def download_image_from_url(
        self, engine: SearchEngine, vendor: Vendor, image_url: str
    ) -> Optional[tuple[bytes, str]]:
        return engine.download_image_from_url(vendor, image_url)

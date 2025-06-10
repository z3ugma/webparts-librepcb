import logging
from functools import wraps
from typing import Callable, Dict, List, Optional

from adapters.easyeda.easyeda_api import EasyEDAApi
from adapters.search_engine import SearchEngine
from models.search_result import SearchResult

logger = logging.getLogger(__name__)

REGISTERED_ENGINES: Dict[str, SearchEngine] = {"LCSC": EasyEDAApi()}


def with_engine(on_fail_return=None):
    """
    A decorator that finds the correct search engine based on the vendor,
    injects it into the decorated method, and handles engine-not-found errors.
    """
    # The decorator takes an argument, so it needs two levels of functions.
    def decorator(func: Callable):
        @wraps(func)
        def wrapper(self, vendor_or_result, *args, **kwargs):
            """
            The actual wrapper that replaces the original method.
            It finds the vendor from the first argument.
            """
            if isinstance(vendor_or_result, SearchResult):
                vendor = vendor_or_result.vendor
            else:
                vendor = vendor_or_result  # Assumes the first arg is the vendor string

            engine = self.engines.get(vendor)

            if not engine:
                logger.error(f"No search engine registered for vendor: '{vendor}'")
                # Return the specified default value (e.g., an empty list or None)
                return on_fail_return() if callable(on_fail_return) else on_fail_return
            
            # Call the original function, injecting the found engine as the first argument
            return func(self, engine, vendor_or_result, *args, **kwargs)
        return wrapper
    return decorator


class Search:
    """
    A lean orchestrator that delegates tasks to the appropriate,
    vendor-specific search engine using decorators to handle engine selection.
    """

    def __init__(self, engines: Dict[str, SearchEngine] = None):
        self.engines = engines if engines is not None else REGISTERED_ENGINES

    @with_engine(on_fail_return=list)
    def search(self, engine: SearchEngine, vendor: str, search_term: str) -> List[SearchResult]:
        logger.info(f"Delegating search for '{search_term}' to {vendor} engine...")
        # The vendor argument is passed through by the decorator but not needed here.
        return engine.search(search_term)

    @with_engine(on_fail_return=None)
    def get_fully_hydrated_search_result(
        self, engine: SearchEngine, search_result: SearchResult
    ) -> Optional[SearchResult]:
        logger.info(f"Delegating hydration for '{search_result.lcsc_id}' to {search_result.vendor} engine...")
        return engine.get_fully_hydrated_search_result(search_result)

    @with_engine(on_fail_return=None)
    def download_image_from_url(self, engine: SearchEngine, vendor: str, image_url: str) -> Optional[bytes]:
        # The vendor argument is passed through by the decorator but not needed here.
        return engine.download_image_from_url(image_url)

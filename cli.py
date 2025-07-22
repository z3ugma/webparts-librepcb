import argparse
import logging
import sys

from adapters.search_engine import Vendor
from library_manager import LibraryManager
from models.search_result import SearchResult
from search import Search

# --- Basic Logging Setup ---
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stdout,
)
logger = logging.getLogger("CLI")


def main():
    """Main function for the CLI tool."""
    parser = argparse.ArgumentParser(
        description="A CLI tool to fetch and process a specific LCSC component."
    )
    parser.add_argument(
        "lcsc_id",
        type=str,
        help="The exact LCSC Part Number (e.g., C2040) to process.",
    )
    args = parser.parse_args()

    lcsc_id = args.lcsc_id
    logger.info(f"Starting process for LCSC ID: {lcsc_id}")

    try:
        # Step 1: Search for the part
        logger.info(f"Searching for '{lcsc_id}'...")
        search_engine = Search()
        search_results = search_engine.search(Vendor.LCSC, lcsc_id)

        # Step 2: Find the exact match
        target_result: SearchResult | None = None
        for result in search_results:
            if result.lcsc_id == lcsc_id:
                logger.info(f"Found exact match: {result.mfr_part_number}")
                target_result = result
                break

        if not target_result:
            logger.error(f"Could not find an exact match for LCSC ID '{lcsc_id}'.")
            sys.exit(1)

        # Step 3: Fully hydrate the search result with all necessary data
        logger.info("Fetching detailed CAD data...")
        target_result.vendor = Vendor.LCSC
        hydrated_result = search_engine.get_fully_hydrated_search_result(target_result)
        if not hydrated_result or not hydrated_result.raw_cad_data:
            logger.error("Failed to fetch detailed CAD data for the part.")
            sys.exit(1)

        # Step 4: Add the part to the library
        logger.info("Initializing LibraryManager and adding part...")
        library_manager = LibraryManager()

        # Check if part already exists
        if library_manager.part_exists(hydrated_result.uuid):
            logger.warning(
                f"Part {lcsc_id} (UUID: {hydrated_result.uuid}) already exists in the library. Overwriting."
            )

        # This is a long-running, synchronous operation
        final_part = library_manager.add_part_from_search_result(hydrated_result)

        if final_part:
            logger.info("✅ Process completed successfully!")
            sys.exit(0)
        else:
            logger.error("❌ Process failed. Check logs for details.")
            sys.exit(1)

    except KeyboardInterrupt:
        logger.info("\nProcess interrupted by user. Exiting.")
        sys.exit(0)
    except Exception as e:
        logger.critical(f"An unhandled exception occurred: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()

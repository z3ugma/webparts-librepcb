# workers/symbol_checker.py
import logging
import re
import subprocess
import sys
from pathlib import Path
from typing import List, Tuple

logger = logging.getLogger(__name__)


def check_symbol(sym_dir_path: str) -> List[Tuple[str, str]]:
    """
    Runs `librepcb-cli open-symbol --check` and parses the output for issues.
    """
    # Local import to avoid ModuleNotFoundError when run directly
    from constants import LIBREPCB_CLI_PATH

    if not Path(sym_dir_path).is_dir():
        logger.error(f"Symbol directory not found: {sym_dir_path}")
        return []

    command = [
        LIBREPCB_CLI_PATH,
        "open-symbol",
        sym_dir_path,
        "--check",
    ]

    logger.info(f"Running command: {' '.join(command)}")

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            check=False,
        )

        output = result.stdout + result.stderr
        logger.debug(f"CLI Output:\n{output}")

        if result.returncode != 0 and "Finished with errors!" not in output:
            logger.error(f"LibrePCB-CLI failed with an unexpected error:\n{output}")
            return []

        pattern = re.compile(r"-\s*\[(WARNING|HINT|ERROR)\]\s*(.*)")
        matches = pattern.findall(output)

        parsed_messages = [(msg.strip(), severity) for severity, msg in matches]

        if parsed_messages:
            logger.info(
                f"Found {len(parsed_messages)} issues in symbol {Path(sym_dir_path).name}."
            )
        else:
            logger.info(f"No issues found in symbol {Path(sym_dir_path).name}.")

        return parsed_messages

    except FileNotFoundError:
        logger.error(f"The 'librepcb-cli' not found at '{LIBREPCB_CLI_PATH}'")
        return []
    except Exception as e:
        logger.error(f"An unexpected error occurred while checking symbol: {e}")
        return []


if __name__ == "__main__":
    import os

    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)

    from constants import LIBRARY_DIR

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )

    # --- Test Runner ---
    symbols_dir = LIBRARY_DIR / "sym"
    if not symbols_dir.exists() or not any(symbols_dir.iterdir()):
        print(f"Error: No symbol directories found in '{symbols_dir}'")
        sys.exit(1)

    print(f"--- Checking all symbols in {symbols_dir} ---")
    total_issues = 0
    symbols_checked = 0

    # Use glob to find all symbol directories (which are named with UUIDs)
    for sym_path in symbols_dir.glob("*"):
        if sym_path.is_dir():
            symbols_checked += 1
            print(f"\nChecking: {sym_path.name}")
            issues_found = check_symbol(str(sym_path))

            if issues_found:
                for msg, severity in issues_found:
                    print(f"  [{severity}] {msg}")
                    total_issues += 1
            else:
                print("  ✅ No issues found.")

    print("\n--- Summary ---")
    print(f"Checked {symbols_checked} symbols.")
    print(f"Found {total_issues} total issues.")
    print("---------------")

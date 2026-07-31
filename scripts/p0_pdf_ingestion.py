#!/usr/bin/env python3
"""
DEPRECATED: Old estimated page-based ingestion pipeline is completely disabled.
All real-page matching and provenance checks must go through scripts/p0_real_page_pipeline.py.
"""

import sys


def main():
    print(
        "FATAL ERROR: Old estimated page-based ingestion pipeline has been completely deprecated and disabled."
    )
    print(
        "To match real PDF page-level provenance, run: uv run python scripts/p0_real_page_pipeline.py"
    )
    raise RuntimeError(
        "DEPRECATED: Old estimated page-based ingestion pipeline is disabled."
    )


if __name__ == "__main__":
    main()
    sys.exit(1)

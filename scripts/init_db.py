from __future__ import annotations

import argparse
from pathlib import Path

from iot_home.db import DEFAULT_DB_PATH, connect, init_db


def main() -> None:
    parser = argparse.ArgumentParser(description="Initialize the local IoT SQLite database.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB_PATH, help="SQLite database path.")
    args = parser.parse_args()

    with connect(args.db) as conn:
        init_db(conn)
    print(f"Initialized {args.db}")


if __name__ == "__main__":
    main()

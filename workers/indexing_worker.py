"""Launcher tương đương python -m app.cli.indexing worker --index UUID."""

import sys

from app.cli.indexing import main

if __name__ == "__main__":
    sys.argv.insert(1, "worker")
    raise SystemExit(main())

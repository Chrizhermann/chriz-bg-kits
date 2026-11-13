"""Unified pytest entrypoint for chriz-bg-kits."""

from __future__ import annotations

import pathlib
import sys

import pytest


def main() -> int:
    tests_dir = pathlib.Path(__file__).resolve().parent
    repo_root = tests_dir.parent
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))
    return pytest.main(["-v", str(tests_dir), *sys.argv[1:]])


if __name__ == "__main__":
    raise SystemExit(main())

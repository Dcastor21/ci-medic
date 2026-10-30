"""Entry point for the Action and local runs; wires the pipeline together."""

from __future__ import annotations

import argparse
from collections.abc import Sequence

from cimedic import __version__


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cimedic",
        description="Diagnose failed CI runs: flaky vs real failure.",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    parser.parse_args(argv)
    parser.print_help()
    return 0

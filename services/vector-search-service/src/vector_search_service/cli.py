"""CLI scaffolding for phase 1."""

from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vss")
    sub = parser.add_subparsers(dest="command")

    sub.add_parser("build")
    sub.add_parser("serve")
    sub.add_parser("add")
    sub.add_parser("status")
    sub.add_parser("snapshot")
    return parser


def main() -> None:
    parser = build_parser()
    parser.parse_args()

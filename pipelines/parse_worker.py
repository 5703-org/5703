"""Private, bounded serialization entry point for isolated source parsing."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path

from .parse import parse


EXIT_SOURCE_UNAVAILABLE = 11
EXIT_INPUT_LIMIT = 12
EXIT_OUTPUT_LIMIT = 13
EXIT_PARSE_FAILED = 14


class OutputLimitExceeded(Exception):
    """The serialized parser result exceeded its configured byte ceiling."""


class BoundedUTF8Writer:
    def __init__(self, stream, maximum: int):
        self.stream = stream
        self.maximum = maximum
        self.written = 0

    def write(self, value: str) -> None:
        # json.dump can pass one long source passage to write(). Avoid making
        # another unbounded encoded copy of that already-parsed passage.
        for start in range(0, len(value), 16 * 1024):
            block = value[start : start + 16 * 1024].encode("utf-8")
            if self.written + len(block) > self.maximum:
                raise OutputLimitExceeded
            self.stream.write(block)
            self.written += len(block)


def _input_status(path: Path, expected_hash: str, maximum: int) -> int:
    try:
        if not path.is_file():
            return EXIT_SOURCE_UNAVAILABLE
        if path.stat().st_size > maximum:
            return EXIT_INPUT_LIMIT
        digest = hashlib.sha256()
        with path.open("rb") as source:
            for block in iter(lambda: source.read(64 * 1024), b""):
                digest.update(block)
        return 0 if digest.hexdigest() == expected_hash else EXIT_SOURCE_UNAVAILABLE
    except OSError:
        return EXIT_SOURCE_UNAVAILABLE


def execute(
    source: Path,
    media_type: str,
    parser_revision: str,
    expected_hash: str,
    output: Path,
    input_max_bytes: int,
    output_max_bytes: int,
) -> int:
    status = _input_status(source, expected_hash, input_max_bytes)
    if status:
        return status
    try:
        units = parse(source, media_type, parser_revision=parser_revision)
        with output.open("xb") as stream:
            writer = BoundedUTF8Writer(stream, output_max_bytes)
            json.dump(
                {"version": "isolated_parse_v1", "child_pid": os.getpid(), "units": units},
                writer,
                ensure_ascii=False,
                allow_nan=False,
                separators=(",", ":"),
            )
        return 0
    except OutputLimitExceeded:
        output.unlink(missing_ok=True)
        return EXIT_OUTPUT_LIMIT
    except Exception:
        output.unlink(missing_ok=True)
        return EXIT_PARSE_FAILED


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--media-type", choices=("application/pdf", "text/plain"), required=True)
    parser.add_argument("--parser-revision", required=True)
    parser.add_argument("--expected-sha256", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--input-max-bytes", type=int, required=True)
    parser.add_argument("--output-max-bytes", type=int, required=True)
    args = parser.parse_args()
    if args.input_max_bytes < 1 or args.output_max_bytes < 1:
        return EXIT_PARSE_FAILED
    return execute(
        args.source,
        args.media_type,
        args.parser_revision,
        args.expected_sha256,
        args.output,
        args.input_max_bytes,
        args.output_max_bytes,
    )


if __name__ == "__main__":
    raise SystemExit(main())

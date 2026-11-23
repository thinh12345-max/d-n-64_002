#!/usr/bin/env python3
"""Annotation Schema Validation Utility.

Validates annotation data against one of the four authoritative schemas:

    detection_ground_truth.schema.json
    tracking_ground_truth.schema.json
    counting_ground_truth.schema.json
    sampling_manifest.schema.json

The validator is a dataset/schema utility only. It does not generate
annotations, evaluate predictions, or modify any input data, schema, or
production file.

Usage:

    python tools/validate_annotation.py \
        --schema detection \
        --input path/to/detection.jsonl

Exit status:
    0  validation succeeded
    1  validation failed or an expected error occurred (missing file,
       missing schema, malformed input, unsupported schema/format)
"""

import argparse
import json
import sys
from pathlib import Path

try:
    import jsonschema
    from jsonschema import Draft7Validator
except ImportError as exc:  # pragma: no cover - dependency guard
    raise SystemExit(
        "BLOCKED: the 'jsonschema' package is required but is not installed. "
        "Install it into the project virtual environment (e.g. "
        "pip install jsonschema) before running this validator."
    ) from exc


# Schema registry. Keys are the short CLI names; values are the authoritative
# schema file names under annotation/schema/ together with the serialization
# format the authoritative data is expected to use.
SCHEMA_REGISTRY = {
    "detection": {
        "file": "detection_ground_truth.schema.json",
        "format": "jsonl",
    },
    "tracking": {
        "file": "tracking_ground_truth.schema.json",
        "format": "json_array",
    },
    "counting": {
        "file": "counting_ground_truth.schema.json",
        "format": "json_object",
    },
    "sampling": {
        "file": "sampling_manifest.schema.json",
        "format": "json_object",
    },
}

# Directory containing the authoritative schemas, relative to the project
# root (the parent of the tools/ directory that contains this file).
SCHEMA_DIR = Path(__file__).resolve().parent.parent / "annotation" / "schema"


def schema_path(schema_name: str) -> Path:
    """Return the authoritative schema file path for the given short name."""
    return SCHEMA_DIR / SCHEMA_REGISTRY[schema_name]["file"]


def load_schema(schema_name: str) -> dict:
    """Load and return the authoritative JSON Schema for the given name."""
    path = schema_path(schema_name)
    if not path.is_file():
        raise FileNotFoundError(
            f"authoritative schema not found: {path}"
        )
    with path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def load_data(input_path: Path, fmt: str):
    """Load the target annotation data according to its authoritative format.

    Detection ground truth is JSONL: one JSON object per line. Tracking
    ground truth is a single JSON array. Counting ground truth and the
    sampling manifest are single JSON objects.
    """
    if not input_path.is_file():
        raise FileNotFoundError(f"input file not found: {input_path}")

    if fmt == "jsonl":
        records = []
        with input_path.open("r", encoding="utf-8") as fh:
            for lineno, line in enumerate(fh, start=1):
                stripped = line.strip()
                if not stripped:
                    continue
                try:
                    records.append(json.loads(stripped))
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"malformed JSONL at {input_path}:{lineno}: {exc.msg}"
                    ) from exc
        return records

    if fmt == "json_array":
        with input_path.open("r", encoding="utf-8") as fh:
            try:
                data = json.load(fh)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"malformed JSON in {input_path}: {exc.msg}"
                ) from exc
        if not isinstance(data, list):
            raise ValueError(
                f"tracking ground truth must be a JSON array, got "
                f"{type(data).__name__}"
            )
        return data

    if fmt == "json_object":
        with input_path.open("r", encoding="utf-8") as fh:
            try:
                data = json.load(fh)
            except json.JSONDecodeError as exc:
                raise ValueError(
                    f"malformed JSON in {input_path}: {exc.msg}"
                ) from exc
        if not isinstance(data, dict):
            raise ValueError(
                f"{fmt.replace('_', ' ')} must be a JSON object, got "
                f"{type(data).__name__}"
            )
        return data

    raise ValueError(f"unsupported input format: {fmt}")


def validate(schema: dict, data, fmt: str) -> list:
    """Validate data against the schema, returning a list of error messages.

    For JSONL input the authoritative schema describes a single record, so
    each record is validated independently and errors are reported with the
    offending record's index.
    """
    validator = Draft7Validator(schema)
    errors = []
    if fmt == "jsonl":
        for index, record in enumerate(data):
            for err in validator.iter_errors(record):
                errors.append(f"record {index}: {err.message}")
    else:
        for err in validator.iter_errors(data):
            errors.append(err.message)
    return sorted(errors)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate annotation data against an authoritative annotation "
            "schema (detection, tracking, counting, or sampling manifest)."
        )
    )
    parser.add_argument(
        "--schema",
        required=True,
        choices=sorted(SCHEMA_REGISTRY),
        help="authoritative schema to validate against",
    )
    parser.add_argument(
        "--input",
        required=True,
        help="path to the annotation data file (JSON or JSONL)",
    )
    args = parser.parse_args(argv)

    schema_name = args.schema
    input_path = Path(args.input)
    fmt = SCHEMA_REGISTRY[schema_name]["format"]

    print(f"schema: {schema_name}")
    print(f"input:  {input_path}")

    try:
        schema = load_schema(schema_name)
        data = load_data(input_path, fmt)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    errors = validate(schema, data, fmt)

    if errors:
        print("validation: FAILED")
        for err in errors:
            print(f"  - {err}")
        return 1

    print("validation: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
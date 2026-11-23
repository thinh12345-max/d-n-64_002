#!/usr/bin/env python3
"""Sampling Manifest Validation Pipeline (Layer 1 + Layer 2).

This utility is a thin orchestration layer over the two existing
validators. It performs NO validation logic of its own:

    Layer 1: tools/validate_annotation.py --schema sampling --input <manifest>
    Layer 2: tools/validate_protocol_consistency.py --input <manifest>

Layer 2 is executed ONLY if Layer 1 succeeds. Neither layer may be bypassed.

Usage:

    python tools/validate_manifest.py \
        --input path/to/sampling_manifest.json

Exit status:
    0  both layers passed
    1  Layer 1 failure, Layer 2 failure, or expected input failure
    2  invalid CLI arguments
"""

import argparse
import subprocess
import sys
from pathlib import Path

# Directory containing this script; the sibling validators live beside it.
TOOLS_DIR = Path(__file__).resolve().parent

LAYER1 = TOOLS_DIR / "validate_annotation.py"
LAYER2 = TOOLS_DIR / "validate_protocol_consistency.py"


def run_layer(script: Path, argv: list) -> int:
    """Run a validator script with the given arguments, streaming its output.

    Returns the validator's exit code. The child process inherits stdout and
    stderr so its output appears verbatim and in order.
    """
    completed = subprocess.run(
        [sys.executable, str(script), *argv],
    )
    return completed.returncode


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a Sampling Manifest through the full two-layer "
            "pipeline: Layer 1 JSON Schema validation, then Layer 2 protocol "
            "consistency validation. No validation logic is implemented here."
        )
    )
    parser.add_argument(
        "--input",
        required=True,
        help="path to the sampling manifest JSON file",
    )
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    print(f"input: {input_path}")

    if not input_path.is_file():
        print(f"ERROR: input file not found: {input_path}", file=sys.stderr)
        return 1

    # --- Layer 1: JSON Schema validation (mandatory first) ---
    print("--- Layer 1: JSON Schema validation ---")
    layer1_args = ["--schema", "sampling", "--input", str(input_path)]
    rc1 = run_layer(LAYER1, layer1_args)

    if rc1 != 0:
        if rc1 == 2:
            print(
                "ERROR: Layer 1 exited with invalid arguments (unexpected); "
                "pipeline aborting",
                file=sys.stderr,
            )
        else:
            print(
                "Layer 1 FAILED; Layer 2 NOT executed (Section 8.5.3).",
                file=sys.stderr,
            )
        return 1

    # --- Layer 2: protocol consistency validation (only on Layer 1 pass) ---
    print("--- Layer 2: protocol consistency validation ---")
    rc2 = run_layer(LAYER2, ["--input", str(input_path)])

    if rc2 != 0:
        if rc2 == 2:
            print(
                "ERROR: Layer 2 exited with invalid arguments (unexpected); "
                "pipeline aborting",
                file=sys.stderr,
            )
        return 1

    print("pipeline: PASSED (Layer 1 and Layer 2)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
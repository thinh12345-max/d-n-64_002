"""Command-line entry point for the canonical dataset validator.

Usage::

    python -m tools.dataset_validator [DATASET_ROOT]
    python -m tools.dataset_validator --json [DATASET_ROOT]

Exit codes
----------
0  PASS
1  WARN
2  FAIL
3  NOT_VERIFIED / validator execution problem
"""

import argparse
import json
import sys

from tools.dataset_validator.validator import (
    DatasetValidator,
    EXIT_FAIL,
    EXIT_NOT_VERIFIED,
    EXIT_PASS,
    EXIT_WARN,
    render_report,
    validate_dataset,
)


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog="dataset_validator",
        description="Read-only canonical dataset validator for My-First-Project-4.",
    )
    parser.add_argument(
        "dataset_root",
        nargs="?",
        default=None,
        help="Path to the dataset root (defaults to My-First-Project-4).",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the structured result as JSON instead of the human report.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress the human-readable report; only print the exit code.",
    )
    args = parser.parse_args(argv)

    try:
        report = validate_dataset(args.dataset_root)
    except Exception as exc:  # VALIDATOR EXECUTION ERROR
        print("VALIDATOR EXECUTION ERROR: %s: %s" % (type(exc).__name__, exc))
        return EXIT_NOT_VERIFIED

    if args.json:
        payload = {
            "dataset_root": report.dataset_root,
            "overall_status": report.overall_status,
            "error_count": len(report.errors()),
            "warning_count": len(report.warnings()),
            "info_count": len(report.infos()),
            "exit_code": report.exit_code(),
            "image_count": report.image_count,
            "label_count": report.label_count,
            "per_split_image_counts": report.per_split_image_counts,
            "per_split_label_counts": report.per_split_label_counts,
            "person_stats": report.person_stats,
            "empty_label_stats": report.empty_label_stats,
            "roboflow_metadata": report.roboflow_metadata,
            "isolation_status": report.isolation_status,
            "checks": [c.as_dict() for c in report.checks],
        }
        print(json.dumps(payload, indent=2, default=str))
    elif not args.quiet:
        print(render_report(report))

    return report.exit_code()


if __name__ == "__main__":
    sys.exit(main())

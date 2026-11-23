"""Canonical read-only dataset validator for My-First-Project-4.

This package validates the YOLO-format detection dataset at
``My-First-Project-4`` exhaustively for all cheap structural and label
checks. It is a DIAGNOSTIC system only: it never modifies, moves, deletes,
renames, repairs, or clamps any dataset file.

See ``tools/dataset_validator/validator.py`` for the contract implementation
and ``tools/dataset_validator/__main__.py`` for the CLI entry point.
"""

from tools.dataset_validator.validator import (
    DatasetValidator,
    validate_dataset,
    EXIT_PASS,
    EXIT_WARN,
    EXIT_FAIL,
    EXIT_NOT_VERIFIED,
)

__all__ = [
    "DatasetValidator",
    "validate_dataset",
    "EXIT_PASS",
    "EXIT_WARN",
    "EXIT_FAIL",
    "EXIT_NOT_VERIFIED",
]
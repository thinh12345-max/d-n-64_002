#!/usr/bin/env python3
"""Sampling Manifest Protocol Consistency Validator (Layer 2).

This utility performs protocol-level consistency validation on a Sampling
Manifest AFTER JSON Schema validation. It is a separate layer from
``tools/validate_annotation.py`` and does not duplicate any JSON Schema
constraint (required fields, enums, regex patterns, numeric bounds,
``additionalProperties``, or structural constraints).

It validates only protocol-consistency requirements that are explicitly
stated in the authorized protocol text (Sections 2.2, 7.3, 7.4, 7.6, 7.7,
7.11.3, 7.11.4, 8.5.2 of docs/PHASE_1_3B_ANNOTATION_PROTOCOL.md). It does
not invent thresholds, tolerances, intervals, mappings, or rules that the
protocol does not state.

The validator is read-only: it never modifies the input manifest, never
repairs records, and never assigns or generates identifiers.

Usage:

    python tools/validate_protocol_consistency.py \
        --input path/to/sampling_manifest.json

Exit status:
    0  all protocol-consistency checks passed
    1  protocol-consistency failure or expected input/file error
    2  invalid CLI arguments
"""

import argparse
import json
import sys
from pathlib import Path


# Event-based sampling_reason values (Section 7.4, 7.11.4).
EVENT_BASED_REASONS = frozenset({
    "roi_crossing",
    "entry_event",
    "exit_event",
    "post_occlusion_appearance",
    "pre_occlusion_disappearance",
    "severe_occlusion",
    "ambiguous_identity",
    "class_ambiguity",
    "high_density",
})

# Explicit sampling_reason -> event_type mappings stated in the protocol
# (Section 7.11.3). The protocol states these three mappings directly and
# explicitly notes that not every sampling_reason maps to a distinct
# event_type; no other mapping is asserted and is therefore not enforced.
REASON_TO_EVENT_TYPE = {
    "roi_crossing": "roi_crossing",
    "entry_event": "entry",
    "exit_event": "exit",
}

# Deterministic split(frame_id) rule (Section 7.6, 7.11.4).
SPLIT_RANGES = (
    (0, 249, "train"),
    (250, 374, "val"),
    (375, 499, "test"),
)
# Frames 500-620 are unassigned and must not appear in the manifest
# (Section 7.6.1, 7.11.4).
UNASSIGNED_RANGE = (500, 620)


def expected_split(frame_id: int):
    """Return the protocol-assigned partition for a frame_id, or None if the
    frame_id is outside the assigned domain (unassigned, Section 7.6.1)."""
    if UNASSIGNED_RANGE[0] <= frame_id <= UNASSIGNED_RANGE[1]:
        return None
    for low, high, split in SPLIT_RANGES:
        if low <= frame_id <= high:
            return split
    return None


def check_protocol_consistency(manifest: dict) -> list:
    """Run every explicitly stated protocol-consistency check.

    Returns a list of human-readable error strings, each identifying the
    record index and, where available, the sample_id and frame_id.
    """
    errors = []

    # Prerequisite: the manifest must be an object with a samples array.
    # (Structure itself is the schema's responsibility; we only guard so
    # the per-sample checks below can run without crashing.)
    if not isinstance(manifest, dict):
        return ["manifest root is not a JSON object"]
    samples = manifest.get("samples")
    if not isinstance(samples, list):
        return ["manifest has no 'samples' array"]

    total_frames = manifest.get("total_frames")
    fps = manifest.get("fps")
    base_interval = manifest.get("base_interval")

    seen_frame_ids = {}
    seen_sample_ids = {}

    for index, sample in enumerate(samples):
        if not isinstance(sample, dict):
            errors.append(f"record {index}: sample is not a JSON object")
            continue

        sample_id = sample.get("sample_id")
        frame_id = sample.get("frame_id")
        timestamp = sample.get("timestamp")
        split = sample.get("split")
        sampling_reason = sample.get("sampling_reason")
        event_type = sample.get("event_type")

        # --- sample_id uniqueness (Section 7.4, 7.11.4) ---
        if sample_id is not None:
            if sample_id in seen_sample_ids:
                errors.append(
                    f"record {index}: duplicate sample_id {sample_id!r} "
                    f"(first at record {seen_sample_ids[sample_id]})"
                )
            else:
                seen_sample_ids[sample_id] = index

        # --- frame_id uniqueness (Section 7.4, 7.7, 7.11.1, 7.11.3, 7.11.4) ---
        if frame_id is not None:
            if frame_id in seen_frame_ids:
                errors.append(
                    f"record {index}: duplicate frame_id {frame_id} "
                    f"(first at record {seen_frame_ids[frame_id]})"
                )
            else:
                seen_frame_ids[frame_id] = index

        # --- frame_id within the source domain (Section 8.5.2) ---
        # "the sampled set recorded in samples is a subset of the frames
        # 0 to total_frames - 1."
        if isinstance(frame_id, int) and isinstance(total_frames, int):
            if frame_id >= total_frames:
                errors.append(
                    f"record {index}: frame_id {frame_id} is outside the "
                    f"source domain 0 to {total_frames - 1} (total_frames={total_frames})"
                )

        # --- timestamp derived from frame_id (Section 2.2, 7.2, 7.11.2,
        #     7.11.3, 8.5.2): timestamp = frame_id / fps ---
        if (isinstance(frame_id, int) and isinstance(fps, (int, float))
                and isinstance(timestamp, (int, float))):
            expected = frame_id / fps
            if timestamp != expected:
                errors.append(
                    f"record {index}: timestamp {timestamp!r} does not equal "
                    f"frame_id / fps ({frame_id} / {fps} = {expected!r})"
                )

        # --- split(frame_id) partition rule (Section 7.6, 7.11.4) ---
        if isinstance(frame_id, int):
            expected = expected_split(frame_id)
            if expected is None:
                errors.append(
                    f"record {index}: frame_id {frame_id} is in the "
                    f"unassigned range {UNASSIGNED_RANGE[0]}-{UNASSIGNED_RANGE[1]} "
                    f"and must not appear in the manifest (Section 7.6.1)"
                )
            elif split != expected:
                errors.append(
                    f"record {index}: split {split!r} does not match the "
                    f"split(frame_id) rule for frame_id {frame_id} (expected {expected!r})"
                )

        # --- baseline sampling consistency (Section 7.3, 7.11.4) ---
        # Directional: a base_temporal sample must be baseline-eligible.
        if sampling_reason == "base_temporal" and isinstance(base_interval, int):
            if isinstance(frame_id, int) and frame_id % base_interval != 0:
                errors.append(
                    f"record {index}: sampling_reason 'base_temporal' but "
                    f"frame_id {frame_id} is not a multiple of base_interval "
                    f"{base_interval} (Section 7.3)"
                )

        # --- event-boosted sampling consistency (Section 7.4, 7.10.2,
        #     7.11.3, 7.11.4) ---
        if sampling_reason in EVENT_BASED_REASONS:
            if event_type is None:
                errors.append(
                    f"record {index}: event-based sampling_reason "
                    f"{sampling_reason!r} requires an event_type "
                    f"(Section 7.11.2)"
                )
            else:
                mapped = REASON_TO_EVENT_TYPE.get(sampling_reason)
                if mapped is not None and event_type != mapped:
                    # Protocol-specific mapping (Section 7.11.3). The
                    # event_type *enum* itself is a schema constraint and is
                    # enforced by tools/validate_annotation.py (Layer 1); it
                    # is not rechecked here.
                    errors.append(
                        f"record {index}: sampling_reason "
                        f"{sampling_reason!r} requires event_type "
                        f"{mapped!r}, found {event_type!r} "
                        f"(Section 7.11.3)"
                    )
        elif sampling_reason == "base_temporal":
            # event_type is meaningful only when sampling_reason is
            # event-based; it is set to "none" otherwise (Section 8.5.2).
            if event_type is not None and event_type != "none":
                errors.append(
                    f"record {index}: sampling_reason 'base_temporal' must "
                    f"not carry an event_type other than 'none', found "
                    f"{event_type!r} (Section 8.5.2)"
                )

    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a Sampling Manifest for protocol-level consistency "
            "with the Section 7 sampling protocol (Layer 2). JSON Schema "
            "validation is performed separately by "
            "tools/validate_annotation.py."
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

    try:
        with input_path.open("r", encoding="utf-8") as fh:
            manifest = json.load(fh)
    except json.JSONDecodeError as exc:
        print(f"ERROR: malformed JSON in {input_path}: {exc.msg}",
              file=sys.stderr)
        return 1

    errors = check_protocol_consistency(manifest)

    if errors:
        print("protocol-consistency: FAILED")
        for err in errors:
            print(f"  - {err}")
        return 1

    print("protocol-consistency: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
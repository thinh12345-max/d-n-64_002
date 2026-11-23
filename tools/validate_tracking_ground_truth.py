#!/usr/bin/env python3
"""Tracking Ground Truth Protocol-Consistency Validator (Layer 2).

This utility performs protocol-level consistency validation on a Tracking
Ground Truth record AFTER JSON Schema validation. It is a separate layer
from ``tools/validate_annotation.py`` and does not duplicate any JSON
Schema constraint (required fields, enums, regex patterns, numeric bounds,
``additionalProperties``, or structural constraints).

It validates only protocol-consistency requirements that are explicitly
stated in Section 8.3.3 of docs/PHASE_1_3B_ANNOTATION_PROTOCOL.md:

  - ``global_id`` uniqueness across the Tracking GT file
  - ``timestamp`` derived from ``frame_id`` at the video's 15 FPS
  - ``start_frame`` / ``end_frame`` consistent with the track's observations
  - ``start_timestamp`` / ``end_timestamp`` derived from those bounds
  - ``center`` derived from ``bbox``
  - ``bbox`` orientation (``x1 < x2``, ``y1 < y2``)
  - minimum ``bbox`` size (10 x 10 pixels)
  - ``truncated`` derived from box geometry alone
  - ``occlusion`` / ``visibility`` consistency (``occlusion = 3`` implies
    ``visibility <= 0.1``; every observation has ``visibility > 0``)
  - ``roi_crossings`` ``frame_id`` correspondence with track observations,
    and ``roi_point`` consistency with the crossing observation's ``bbox``

No tolerance, threshold, or comparison method is invented: every check
uses the exact representation and semantics the protocol defines. The
validator is read-only; it never modifies the input, never repairs records,
and never assigns or generates identifiers.

Usage:

    python tools/validate_tracking_ground_truth.py \
        --input path/to/tracking_gt.json

Exit status:
    0  all protocol-consistency checks passed
    1  protocol-consistency failure or expected input/file error
    2  invalid CLI arguments
"""

import argparse
import json
import sys
from pathlib import Path

# Video frame rate, stated explicitly by the protocol (Section 2.2):
#     timestamp = frame_id / 15.0 seconds
# This is a protocol constant, not a tolerance.
FPS = 15.0

# Frame-domain and geometry constants stated by the protocol:
#   Section 2.1/3.1  -> 1020x500 coordinate space, integer coordinates
#   Section 3.3      -> frame boundary is y2 = 499 (height 500)
#   Section 2.6/3.6  -> minimum box size 10x10 pixels
FRAME_HEIGHT = 500          # last row index is FRAME_HEIGHT - 1
MIN_BOX_SIZE = 10
SEVERE_OCCLUSION_VIS_MAX = 0.1   # Section 4.1 / 8.3.3: occlusion=3 -> visibility <= 0.1


def load_input(input_path: Path):
    """Read the Tracking GT file and return the parsed JSON value.

    Raises FileNotFoundError if the path does not exist and ValueError if
    the file is not valid JSON. The caller maps these to exit code 1.
    """
    if not input_path.is_file():
        raise FileNotFoundError(f"input file not found: {input_path}")
    with input_path.open("r", encoding="utf-8") as fh:
        return json.load(fh)


def _fmt_num(value) -> str:
    """Render a number for error messages without inventing formatting."""
    if isinstance(value, float):
        return repr(value)
    return str(value)


def validate_global_ids(tracks: list) -> list:
    """Check that each track-level ``global_id`` appears exactly once.

    Section 8.3.3: within a Tracking GT file, each ``global_id`` must appear
    exactly once as a track key. Two tracks sharing a ``global_id`` describe
    the same physical object under two separate records and are not permitted.
    """
    errors = []
    seen = {}
    for track_index, track in enumerate(tracks):
        if not isinstance(track, dict):
            continue
        global_id = track.get("global_id")
        if global_id is None:
            continue
        if global_id in seen:
            errors.append(
                f"track[{track_index}] global_id={global_id}: duplicate "
                f"global_id, first used by track[{seen[global_id]}]"
            )
        else:
            seen[global_id] = track_index
    return errors


def _observation_errors(track_index, global_id, frame_index, obs) -> list:
    """Protocol-level per-observation checks (Section 8.3.3)."""
    errors = []
    frame_id = obs.get("frame_id")
    bbox = obs.get("bbox")
    center = obs.get("center")
    visibility = obs.get("visibility")
    occlusion = obs.get("occlusion")
    truncated = obs.get("truncated")

    # --- timestamp derived from frame_id (Section 8.3.3, 2.2) ---
    if isinstance(frame_id, int) and isinstance(obs.get("timestamp"), (int, float)):
        expected = frame_id / FPS
        if obs["timestamp"] != expected:
            errors.append(
                f"track[{track_index}] global_id={global_id}: "
                f"frame_id={frame_id}: timestamp {_fmt_num(obs['timestamp'])} "
                f"does not equal frame_id / {FPS} ({_fmt_num(expected)})"
            )

    # --- bbox orientation: x1 < x2 and y1 < y2 (Section 8.3.3, 3.1) ---
    if isinstance(bbox, list) and len(bbox) == 4 and all(isinstance(v, int) for v in bbox):
        x1, y1, x2, y2 = bbox
        if not (x1 < x2):
            errors.append(
                f"track[{track_index}] global_id={global_id}: "
                f"frame_id={frame_id}: bbox x1={x1} is not less than x2={x2}"
            )
        if not (y1 < y2):
            errors.append(
                f"track[{track_index}] global_id={global_id}: "
                f"frame_id={frame_id}: bbox y1={y1} is not less than y2={y2}"
            )

        # --- minimum bbox size 10x10 (Section 8.3.3, 2.6/3.6) ---
        width = x2 - x1
        height = y2 - y1
        if width < MIN_BOX_SIZE:
            errors.append(
                f"track[{track_index}] global_id={global_id}: "
                f"frame_id={frame_id}: bbox width {width} is below the "
                f"minimum {MIN_BOX_SIZE}"
            )
        if height < MIN_BOX_SIZE:
            errors.append(
                f"track[{track_index}] global_id={global_id}: "
                f"frame_id={frame_id}: bbox height {height} is below the "
                f"minimum {MIN_BOX_SIZE}"
            )

        # --- center derived from bbox (Section 8.3.3) ---
        if isinstance(center, list) and len(center) == 2 and all(
                isinstance(v, (int, float)) for v in center):
            expected_center = [(x1 + x2) / 2.0, (y1 + y2) / 2.0]
            if list(center) != expected_center:
                errors.append(
                    f"track[{track_index}] global_id={global_id}: "
                    f"frame_id={frame_id}: center {_fmt_num(center)} is "
                    f"inconsistent with bbox {bbox} "
                    f"(expected {_fmt_num(expected_center)})"
                )

        # --- truncated derived from box geometry alone (Section 8.3.3, 3.3) ---
        if isinstance(truncated, bool):
            touches_boundary = (
                x1 == 0 or x2 == 1019 or y1 == 0 or y2 == FRAME_HEIGHT - 1
            )
            if truncated != touches_boundary:
                errors.append(
                    f"track[{track_index}] global_id={global_id}: "
                    f"frame_id={frame_id}: truncated={truncated} but the bbox "
                    f"{'touches' if touches_boundary else 'does not touch'} "
                    f"the frame boundary"
                )

    # --- occlusion / visibility consistency (Section 8.3.3, 4.1) ---
    # Every observation that exists must have visibility > 0; a value of 0
    # means the object is fully hidden and contributes no observation.
    if isinstance(visibility, (int, float)) and not isinstance(visibility, bool):
        if visibility <= 0:
            errors.append(
                f"track[{track_index}] global_id={global_id}: "
                f"frame_id={frame_id}: visibility {_fmt_num(visibility)} is not "
                f"greater than 0, but an observation exists"
            )
        # occlusion = 3 (severe) must co-occur with visibility <= 0.1.
        if isinstance(occlusion, int) and not isinstance(occlusion, bool):
            if occlusion == 3 and visibility > SEVERE_OCCLUSION_VIS_MAX:
                errors.append(
                    f"track[{track_index}] global_id={global_id}: "
                    f"frame_id={frame_id}: occlusion=3 requires "
                    f"visibility <= {SEVERE_OCCLUSION_VIS_MAX}, found "
                    f"{_fmt_num(visibility)}"
                )

    return errors


def validate_roi_crossings(track_index, global_id, frames_by_id, track_errors):
    """Check roi_crossings frame_id correspondence and roi_point consistency.

    Section 8.3.3: each roi_crossings entry records a crossing at a frame_id
    that must exist among the track's observations, and the roi_point is the
    bottom-center point at that frame, derived from the observation's bbox.
    """
    errors = []
    crossings = frames_by_id.get("roi_crossings")
    if not crossings:
        return errors
    if not isinstance(crossings, list):
        return errors
    observations = frames_by_id.get("frames") or []
    obs_by_frame = {}
    for obs in observations:
        if isinstance(obs, dict) and isinstance(obs.get("frame_id"), int):
            obs_by_frame[obs["frame_id"]] = obs

    for crossing_index, crossing in enumerate(crossings):
        if not isinstance(crossing, dict):
            continue
        crossing_frame = crossing.get("frame_id")
        if not isinstance(crossing_frame, int):
            continue
        obs = obs_by_frame.get(crossing_frame)
        if obs is None:
            errors.append(
                f"track[{track_index}] global_id={global_id}: "
                f"roi_crossings[{crossing_index}]: frame_id={crossing_frame} "
                f"does not correspond to a track observation"
            )
            continue
        bbox = obs.get("bbox")
        roi_point = crossing.get("roi_point")
        if (isinstance(bbox, list) and len(bbox) == 4
                and all(isinstance(v, int) for v in bbox)
                and isinstance(roi_point, list) and len(roi_point) == 2
                and all(isinstance(v, (int, float)) for v in roi_point)):
            x1, y1, x2, y2 = bbox
            expected_point = [(x1 + x2) / 2.0, float(y2)]
            if list(roi_point) != expected_point:
                errors.append(
                    f"track[{track_index}] global_id={global_id}: "
                    f"roi_crossings[{crossing_index}] frame_id={crossing_frame}: "
                    f"roi_point {_fmt_num(roi_point)} is inconsistent with the "
                    f"observation bbox {bbox} (expected {_fmt_num(expected_point)})"
                )
    return errors


def validate_track_consistency(tracks: list) -> list:
    """Run every explicitly authorized per-track protocol-level check."""
    errors = []
    for track_index, track in enumerate(tracks):
        if not isinstance(track, dict):
            errors.append(f"track[{track_index}]: track is not a JSON object")
            continue

        global_id = track.get("global_id")
        frames = track.get("frames")

        # --- start_frame / end_frame consistent with observations ---
        # (Section 8.3.3): start_frame must be the minimum frame_id in the
        # track's frames array; end_frame must be the maximum.
        if isinstance(frames, list) and frames:
            observed_ids = [
                obs["frame_id"] for obs in frames
                if isinstance(obs, dict) and isinstance(obs.get("frame_id"), int)
            ]
            if observed_ids:
                min_frame = min(observed_ids)
                max_frame = max(observed_ids)
                start_frame = track.get("start_frame")
                end_frame = track.get("end_frame")
                if isinstance(start_frame, int) and start_frame != min_frame:
                    errors.append(
                        f"track[{track_index}] global_id={global_id}: "
                        f"start_frame={start_frame} does not equal the minimum "
                        f"observation frame_id {min_frame}"
                    )
                if isinstance(end_frame, int) and end_frame != max_frame:
                    errors.append(
                        f"track[{track_index}] global_id={global_id}: "
                        f"end_frame={end_frame} does not equal the maximum "
                        f"observation frame_id {max_frame}"
                    )

                # --- start_timestamp / end_timestamp derived at 15 FPS ---
                if isinstance(start_frame, int) and isinstance(
                        track.get("start_timestamp"), (int, float)):
                    expected = start_frame / FPS
                    if track["start_timestamp"] != expected:
                        errors.append(
                            f"track[{track_index}] global_id={global_id}: "
                            f"start_timestamp {_fmt_num(track['start_timestamp'])} "
                            f"does not equal start_frame / {FPS} "
                            f"({_fmt_num(expected)})"
                        )
                if isinstance(end_frame, int) and isinstance(
                        track.get("end_timestamp"), (int, float)):
                    expected = end_frame / FPS
                    if track["end_timestamp"] != expected:
                        errors.append(
                            f"track[{track_index}] global_id={global_id}: "
                            f"end_timestamp {_fmt_num(track['end_timestamp'])} "
                            f"does not equal end_frame / {FPS} "
                            f"({_fmt_num(expected)})"
                        )

        # --- per-observation checks ---
        if isinstance(frames, list):
            for frame_index, obs in enumerate(frames):
                if not isinstance(obs, dict):
                    errors.append(
                        f"track[{track_index}] global_id={global_id}: "
                        f"frames[{frame_index}]: observation is not a JSON object"
                    )
                    continue
                errors.extend(
                    _observation_errors(track_index, global_id, frame_index, obs)
                )

        # --- roi_crossings checks ---
        errors.extend(
            validate_roi_crossings(track_index, global_id, track, errors)
        )

    return errors


def validate_protocol_consistency(data) -> list:
    """Run every explicitly authorized protocol-level check on the data."""
    errors = []
    if not isinstance(data, list):
        return ["tracking ground truth root is not a JSON array of tracks"]
    errors.extend(validate_global_ids(data))
    errors.extend(validate_track_consistency(data))
    return errors


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Validate a Tracking Ground Truth record for protocol-level "
            "consistency with Section 8.3.3 (Layer 2). JSON Schema validation "
            "is performed separately by tools/validate_annotation.py."
        )
    )
    parser.add_argument(
        "--input",
        required=True,
        help="path to the tracking ground truth JSON file",
    )
    args = parser.parse_args(argv)

    input_path = Path(args.input)
    print(f"input: {input_path}")

    try:
        data = load_input(input_path)
    except FileNotFoundError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1
    except json.JSONDecodeError as exc:
        print(f"ERROR: malformed JSON in {input_path}: {exc.msg}",
              file=sys.stderr)
        return 1

    errors = validate_protocol_consistency(data)

    if errors:
        print("protocol-consistency: FAILED")
        for err in errors:
            print(f"  - {err}")
        return 1

    print("protocol-consistency: PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
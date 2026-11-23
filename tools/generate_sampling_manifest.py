#!/usr/bin/env python3
"""Deterministic Sampling Manifest Generator (baseline temporal sampling only).

This utility generates a Sampling Manifest by applying ONLY the baseline
keyframe sampling rule defined in Section 7.3 of the protocol:

    A source frame with frame_id = f is a baseline-sampled frame iff
    f mod base_interval == 0.

It is NOT an annotation tool, a Ground Truth generator, or an evaluation
tool. It does NOT fabricate event-based samples, Ground Truth identities,
counting events, or semantic labels.

The generator produces ONLY baseline samples (sampling_reason =
"base_temporal"). Event-boosted sampling is NOT implemented here: no
authoritative event source exists, and inventing events would violate
the protocol.

Every value that has no authoritative automatic source (traffic_density,
difficulty) MUST be supplied explicitly by the caller. The generator refuses
to guess.

Usage:

    python tools/generate_sampling_manifest.py \
        --video-id 3.mp4 \
        --total-frames 621 \
        --fps 15.0 \
        --base-interval 5 \
        --traffic-density low \
        --difficulty easy \
        --output path/to/sampling_manifest.json

Exit status:
    0  manifest generated and written
    1  invalid input, missing semantic metadata, or output-protection refusal
    2  invalid CLI arguments
"""

import argparse
import json
import sys
from pathlib import Path

# --- Protocol constants (Sections 7.6, 7.6.1, 7.11.4) ---
# split(frame_id): 0-249 -> train, 250-374 -> val, 375-499 -> test.
# Frames 500-620 are unassigned and must not appear in the manifest.
SPLIT_RANGES = (
    (0, 249, "train"),
    (250, 374, "val"),
    (375, 499, "test"),
)
UNASSIGNED_RANGE = (500, 620)

# Semantic strata that have no authoritative automatic source (Section 8.5.2).
# They MUST be supplied explicitly by the caller.
TRAFFIC_DENSITY_VALUES = frozenset({"low", "medium", "high"})
DIFFICULTY_VALUES = frozenset({"easy", "moderate", "hard"})


def expected_split(frame_id: int):
    """Return the protocol-assigned partition for a frame_id, or None if the
    frame_id is outside the assigned domain (unassigned, Section 7.6.1)."""
    if UNASSIGNED_RANGE[0] <= frame_id <= UNASSIGNED_RANGE[1]:
        return None
    for low, high, split in SPLIT_RANGES:
        if low <= frame_id <= high:
            return split
    return None


def baseline_frame_ids(total_frames: int, base_interval: int):
    """Yield the deterministic baseline-sampled frame_ids.

    Section 7.3: a source frame f is baseline-sampled iff
    f mod base_interval == 0, over the frame domain 0..total_frames-1.
    Frames in the unassigned range (500-620) are excluded (Section 7.6.1).
    """
    for frame_id in range(total_frames):
        if frame_id % base_interval != 0:
            continue
        if expected_split(frame_id) is None:
            continue
        yield frame_id


def build_manifest(
    video_id: str,
    total_frames: int,
    fps: float,
    base_interval: int,
    traffic_density: str,
    difficulty: str,
) -> dict:
    """Build the manifest dict from explicit, validated inputs.

    Deterministic: sample_id is assigned in ascending frame_id order, and
    timestamp is derived as frame_id / fps with no rounding policy applied.
    """
    samples = []
    for index, frame_id in enumerate(baseline_frame_ids(total_frames, base_interval)):
        samples.append({
            "sample_id": f"S_{index + 1:04d}",
            "frame_id": frame_id,
            "timestamp": frame_id / fps,
            "split": expected_split(frame_id),
            "sampling_reason": "base_temporal",
            "traffic_density": traffic_density,
            "difficulty": difficulty,
            # event_type is meaningful only when sampling_reason is
            # event-based; it is "none" otherwise (Section 8.5.2).
            "event_type": "none",
        })

    manifest = {
        "video_id": video_id,
        "total_frames": total_frames,
        "fps": fps,
        "base_interval": base_interval,
        "samples": samples,
    }
    return manifest


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Generate a Sampling Manifest from the deterministic baseline "
            "keyframe sampling rule (Section 7.3). Produces only "
            "base_temporal samples; no event-based samples are fabricated."
        )
    )
    parser.add_argument("--video-id", required=True,
                        help="source video identifier (e.g. 3.mp4)")
    parser.add_argument("--total-frames", required=True, type=int,
                        help="total number of source frames")
    parser.add_argument("--fps", required=True, type=float,
                        help="video frame rate")
    parser.add_argument("--base-interval", required=True, type=int,
                        help="baseline sampling interval in frames")
    parser.add_argument("--traffic-density", required=True,
                        help="traffic density stratum for every sample "
                             "(low|medium|high)")
    parser.add_argument("--difficulty", required=True,
                        help="frame difficulty stratum for every sample "
                             "(easy|moderate|hard)")
    parser.add_argument("--output", required=True,
                        help="path to write the generated manifest JSON")
    args = parser.parse_args(argv)

    # --- Validate inputs ---
    errors = []

    if args.total_frames <= 0:
        errors.append(f"--total-frames must be positive, got {args.total_frames}")
    if args.fps <= 0:
        errors.append(f"--fps must be positive, got {args.fps}")
    if args.base_interval <= 0:
        errors.append(
            f"--base-interval must be positive, got {args.base_interval}"
        )
    if args.traffic_density not in TRAFFIC_DENSITY_VALUES:
        errors.append(
            f"--traffic-density must be one of "
            f"{sorted(TRAFFIC_DENSITY_VALUES)}, got {args.traffic_density!r}"
        )
    if args.difficulty not in DIFFICULTY_VALUES:
        errors.append(
            f"--difficulty must be one of "
            f"{sorted(DIFFICULTY_VALUES)}, got {args.difficulty!r}"
        )

    if errors:
        for err in errors:
            print(f"ERROR: {err}", file=sys.stderr)
        return 1

    output_path = Path(args.output)

    # --- Output protection: never overwrite an existing file ---
    if output_path.is_file():
        print(
            f"ERROR: output file already exists and would be overwritten: "
            f"{output_path}",
            file=sys.stderr,
        )
        return 1

    manifest = build_manifest(
        video_id=args.video_id,
        total_frames=args.total_frames,
        fps=args.fps,
        base_interval=args.base_interval,
        traffic_density=args.traffic_density,
        difficulty=args.difficulty,
    )

    try:
        with output_path.open("w", encoding="utf-8") as fh:
            json.dump(manifest, fh, indent=2)
            fh.write("\n")
    except OSError as exc:
        print(f"ERROR: failed to write output {output_path}: {exc}",
              file=sys.stderr)
        return 1

    print(f"generated: {output_path}")
    print(f"  samples: {len(manifest['samples'])} "
          f"(sampling_reason=base_temporal only)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
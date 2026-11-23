"""TrackEval adapter for tracking evaluation.

Converts project tracking ground truth and ByteTrack predictions to TrackEval MOT format.

This adapter is evaluation-only and does not modify the original GT or prediction data.

Reference: D-06.10 Tracking Evaluation Protocol, D-06.18 Adapter Design, D-06.20 Evaluator Selection
"""

import csv
import json
from pathlib import Path
from typing import Dict, List, Tuple, Any, Optional

# Project class to TrackEval class ID mapping
CLASS_MAPPING = {
    "car": 1,
    "motorcycle": 2,
    "bus": 3,
    "truck": 4,
    "person": 5,
}

# Reverse mapping for reference
CLASS_MAPPING_REVERSE = {v: k for k, v in CLASS_MAPPING.items()}

# Valid classes
VALID_CLASSES = set(CLASS_MAPPING.keys())

# Image dimensions from protocol (evaluation boundary)
IMAGE_WIDTH = 1020
IMAGE_HEIGHT = 500

# Runtime tracking resolution
RUNTIME_WIDTH = 1280
RUNTIME_HEIGHT = 720

# Coordinate normalization factors
NORM_SCALE_X = IMAGE_WIDTH / RUNTIME_WIDTH  # 1020 / 1280
NORM_SCALE_Y = IMAGE_HEIGHT / RUNTIME_HEIGHT  # 500 / 720


class TrackEvalAdapterError(Exception):
    """Exception for adapter errors."""
    pass


def validate_gt_entry(entry: Dict[str, Any], frame_id: int) -> None:
    """Validate a single GT frame entry.

    Args:
        entry: GT frame entry dict
        frame_id: Frame ID for error messages

    Raises:
        TrackEvalAdapterError: If validation fails
    """
    required_fields = ["frame_id", "bbox", "visibility", "occlusion", "truncated", "center"]
    for field in required_fields:
        if field not in entry:
            raise TrackEvalAdapterError(
                f"GT frame {frame_id}: missing required field '{field}'"
            )

    # Validate bbox
    bbox = entry["bbox"]
    if not isinstance(bbox, list) or len(bbox) != 4:
        raise TrackEvalAdapterError(
            f"GT frame {frame_id}: bbox must be [x1, y1, x2, y2], got {bbox}"
        )

    x1, y1, x2, y2 = bbox
    if not (isinstance(x1, (int, float)) and isinstance(y1, (int, float))
            and isinstance(x2, (int, float)) and isinstance(y2, (int, float))):
        raise TrackEvalAdapterError(
            f"GT frame {frame_id}: bbox coordinates must be numeric"
        )

    if x2 <= x1 or y2 <= y1:
        raise TrackEvalAdapterError(
            f"GT frame {frame_id}: invalid bbox (x2 > x1 and y2 > y1 required)"
        )

    # Validate visibility
    visibility = entry["visibility"]
    if not isinstance(visibility, (int, float)) or not (0.0 <= visibility <= 1.0):
        raise TrackEvalAdapterError(
            f"GT frame {frame_id}: visibility must be 0.0-1.0, got {visibility}"
        )

    # Validate occlusion
    occlusion = entry["occlusion"]
    if occlusion not in [0, 1, 2, 3]:
        raise TrackEvalAdapterError(
            f"GT frame {frame_id}: occlusion must be 0-3, got {occlusion}"
        )


def validate_prediction_entry(entry: Dict[str, Any], frame_id: int) -> None:
    """Validate a single prediction entry.

    Args:
        entry: Prediction entry dict
        frame_id: Frame ID for error messages

    Raises:
        TrackEvalAdapterError: If validation fails
    """
    required_fields = ["frame_id", "track_id", "bbox", "class", "confidence"]
    for field in required_fields:
        if field not in entry:
            raise TrackEvalAdapterError(
                f"Prediction frame {frame_id}: missing required field '{field}'"
            )

    # Validate bbox
    bbox = entry["bbox"]
    if not isinstance(bbox, list) or len(bbox) != 4:
        raise TrackEvalAdapterError(
            f"Prediction frame {frame_id}: bbox must be [x1, y1, x2, y2]"
        )

    # Validate class
    cls = entry["class"]
    if cls not in VALID_CLASSES:
        raise TrackEvalAdapterError(
            f"Prediction frame {frame_id}: invalid class '{cls}', must be one of {VALID_CLASSES}"
        )

    # Validate confidence
    conf = entry["confidence"]
    if not isinstance(conf, (int, float)) or not (0.0 <= conf <= 1.0):
        raise TrackEvalAdapterError(
            f"Prediction frame {frame_id}: confidence must be 0.0-1.0, got {conf}"
        )


def convert_gt_to_trackeval(
    gt_tracks: List[Dict[str, Any]],
    include_occlusion_metadata: bool = True
) -> Tuple[List[List[Any]], Dict[str, Any]]:
    """Convert project GT tracks to TrackEval MOT format.

    Args:
        gt_tracks: List of GT track dicts from tracking_ground_truth.json
        include_occlusion_metadata: If True, include original occlusion in metadata

    Returns:
        Tuple of (MOT format rows, metadata dict with original occlusion)
    """
    mot_rows = []
    occlusion_metadata = {}  # frame_id -> {gt_id: occlusion}

    for track in gt_tracks:
        global_id = track.get("global_id")
        if not global_id:
            raise TrackEvalAdapterError("GT track missing 'global_id'")

        track_class = track.get("class")
        if track_class not in VALID_CLASSES:
            raise TrackEvalAdapterError(f"Invalid GT class: {track_class}")

        class_id = CLASS_MAPPING[track_class]

        for frame_entry in track.get("frames", []):
            frame_id = frame_entry.get("frame_id")
            if frame_id is None:
                raise TrackEvalAdapterError("GT frame entry missing 'frame_id'")

            # Validate entry
            validate_gt_entry(frame_entry, frame_id)

            # Extract bbox [x1, y1, x2, y2]
            x1, y1, x2, y2 = frame_entry["bbox"]
            w = x2 - x1
            h = y2 - y1

            # Frame is already 0-based per project protocol (GT: 0-620)
            # No +1 shift needed

            # MOT format: frame, id, x, y, w, h, conf, cls, -1, -1, -1, -1
            # For GT, conf=1, cls=class_id
            # TrackEval uses -1 for unused fields (visibility handled via zero_marked)
            mot_row = [
                frame_id,         # 0-based frame (per protocol)
                global_id,        # GT identity
                x1, y1, w, h,    # bbox
                1,                # confidence (GT = 1)
                class_id,         # class
                -1, -1, -1, -1   # unused fields
            ]
            mot_rows.append(mot_row)

            # Store occlusion metadata for secondary analysis
            if include_occlusion_metadata:
                occlusion = frame_entry.get("occlusion", 0)
                if frame_id not in occlusion_metadata:
                    occlusion_metadata[frame_id] = {}
                occlusion_metadata[frame_id][global_id] = occlusion

    # Sort by frame, then by id for deterministic output
    mot_rows.sort(key=lambda r: (r[0], str(r[1])))

    metadata = {
        "occlusion": occlusion_metadata,
        "class_mapping": CLASS_MAPPING,
        "image_width": IMAGE_WIDTH,
        "image_height": IMAGE_HEIGHT,
    }

    return mot_rows, metadata


def convert_predictions_to_trackeval(
    predictions: List[Dict[str, Any]]
) -> List[List[Any]]:
    """Convert ByteTrack predictions to TrackEval MOT format.

    Per D-06.36/D-06.38: prediction bboxes are normalized from runtime
    resolution (1280×720) to evaluation resolution (1020×500) at the
    evaluation boundary, before xyxy → xywh conversion.

    Args:
        predictions: List of prediction dicts from ByteTrack output

    Returns:
        MOT format rows
    """
    mot_rows = []

    for pred in predictions:
        frame_id = pred.get("frame_id")
        if frame_id is None:
            raise TrackEvalAdapterError("Prediction missing 'frame_id'")

        track_id = pred.get("track_id")
        if track_id is None:
            raise TrackEvalAdapterError("Prediction missing 'track_id'")

        # Validate entry
        validate_prediction_entry(pred, frame_id)

        # Extract bbox [x1, y1, x2, y2] - already in evaluation coordinates (1020×500)
        x1, y1, x2, y2 = pred["bbox"]

        # Convert xyxy → xywh (preserving floating-point precision)
        w = x2 - x1
        h = y2 - y1

        # Frame is already 0-based per project protocol (predictions: 0-620)
        # No +1 shift needed

        cls = pred["class"]
        class_id = CLASS_MAPPING[cls]
        confidence = pred["confidence"]

        # MOT format: frame, id, x, y, w, h, conf, cls, -1, -1, -1, -1
        mot_row = [
            frame_id,         # 0-based frame (per protocol)
            int(track_id),   # runtime track_id
            x1, y1, w, h,   # bbox in evaluation coordinates
            confidence,       # detection confidence
            class_id,         # class
            -1, -1, -1, -1   # unused fields
        ]
        mot_rows.append(mot_row)

    # Sort by frame, then by track_id for deterministic output
    mot_rows.sort(key=lambda r: (r[0], r[1]))

    return mot_rows


def write_mot_file(filepath: Path, rows: List[List[Any]]) -> None:
    """Write MOT format file.

    Args:
        filepath: Output file path
        rows: MOT format rows
    """
    with open(filepath, 'w', newline='') as f:
        writer = csv.writer(f)
        for row in rows:
            writer.writerow(row)


def load_gt_tracks(gt_path: Path) -> List[Dict[str, Any]]:
    """Load GT tracks from JSON file.

    Args:
        gt_path: Path to tracking_ground_truth.json

    Returns:
        List of GT track dicts

    Raises:
        TrackEvalAdapterError: If loading fails
    """
    try:
        with open(gt_path, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        raise TrackEvalAdapterError(f"GT file not found: {gt_path}")
    except json.JSONDecodeError as e:
        raise TrackEvalAdapterError(f"Invalid JSON in GT file: {e}")

    if not isinstance(data, list):
        raise TrackEvalAdapterError("GT file must contain a JSON array of tracks")

    return data


def load_predictions(pred_path: Path) -> List[Dict[str, Any]]:
    """Load predictions from JSON file.

    Args:
        pred_path: Path to predictions.json

    Returns:
        List of prediction dicts

    Raises:
        TrackEvalAdapterError: If loading fails
    """
    try:
        with open(pred_path, 'r') as f:
            data = json.load(f)
    except FileNotFoundError:
        raise TrackEvalAdapterError(f"Prediction file not found: {pred_path}")
    except json.JSONDecodeError as e:
        raise TrackEvalAdapterError(f"Invalid JSON in prediction file: {e}")

    if not isinstance(data, list):
        raise TrackEvalAdapterError("Prediction file must contain a JSON array")

    return data


def get_visibility_gaps(gt_tracks: List[Dict[str, Any]]) -> Dict[str, List[Tuple[int, int]]]:
    """Identify visibility=0 gaps in GT tracks.

    Per protocol: visibility=0 means physical object exists but is fully invisible.
    The gap frames are NOT in the frames[] array.

    Args:
        gt_tracks: List of GT track dicts

    Returns:
        Dict mapping global_id -> list of (start_frame, end_frame) gaps
    """
    gaps = {}

    for track in gt_tracks:
        global_id = track.get("global_id")
        if not global_id:
            continue

        start_frame = track.get("start_frame")
        end_frame = track.get("end_frame")
        if start_frame is None or end_frame is None:
            continue

        # Get visible frames from frames[]
        visible_frames = set()
        for frame_entry in track.get("frames", []):
            frame_id = frame_entry.get("frame_id")
            if frame_id is not None:
                visible_frames.add(frame_id)

        # Find gaps: frames in [start_frame, end_frame] but not in visible_frames
        track_gaps = []
        current_gap_start = None

        for f in range(start_frame, end_frame + 1):
            if f not in visible_frames:
                if current_gap_start is None:
                    current_gap_start = f
            else:
                if current_gap_start is not None:
                    track_gaps.append((current_gap_start, f - 1))
                    current_gap_start = None

        if current_gap_start is not None:
            track_gaps.append((current_gap_start, end_frame))

        if track_gaps:
            gaps[global_id] = track_gaps

    return gaps


def convert_gt_with_visibility_gaps(
    gt_tracks: List[Dict[str, Any]],
    include_metadata: bool = True
) -> Tuple[List[List[Any]], Dict[str, Any]]:
    """Convert GT to TrackEval format, handling visibility=0 gaps.

    Per D-06.18 adapter design:
    - Omit invisible GT frames (visibility=0 gaps) from TrackEval input
    - Prediction during gap -> FP (handled by TrackEval)
    - No prediction during gap -> no FN (handled by TrackEval)

    This function explicitly documents the gaps for reference but does NOT
    create fake GT entries.

    Args:
        gt_tracks: List of GT track dicts
        include_metadata: Include original metadata

    Returns:
        Tuple of (MOT format rows, metadata including gap info)
    """
    # Get visibility gaps
    gaps = get_visibility_gaps(gt_tracks)

    # Convert visible GT entries (visibility > 0 frames only)
    mot_rows, metadata = convert_gt_to_trackeval(gt_tracks, include_occlusion_metadata=include_metadata)

    # Add gap information to metadata
    metadata["visibility_gaps"] = gaps

    return mot_rows, metadata


def create_seqinfo(filepath: Path, num_frames: int, fps: int = 15) -> None:
    """Create seqinfo.ini for TrackEval sequence.

    Args:
        filepath: Path to seqinfo.ini
        num_frames: Number of frames in sequence
        fps: Frames per second
    """
    seqinfo = f"""[Sequence]
name=seq
imDir=img
frameRate={fps}
seqLength={num_frames}
imWidth={IMAGE_WIDTH}
imHeight={IMAGE_HEIGHT}
"""
    with open(filepath, 'w') as f:
        f.write(seqinfo)


def adapter_summary(
    gt_tracks: List[Dict[str, Any]],
    predictions: List[Dict[str, Any]],
    mot_gt_rows: List[List[Any]],
    mot_pred_rows: List[List[Any]],
    metadata: Dict[str, Any]
) -> Dict[str, Any]:
    """Generate summary of adapter conversion.

    Args:
        gt_tracks: Original GT tracks
        predictions: Original predictions
        mot_gt_rows: Converted GT rows
        mot_pred_rows: Converted prediction rows
        metadata: Adapter metadata

    Returns:
        Summary dict
    """
    # Count visible GT entries
    visible_gt_count = sum(len(t.get("frames", [])) for t in gt_tracks)

    # Count predictions
    pred_count = len(predictions)

    # Count unique frames
    gt_frames = set(r[0] for r in mot_gt_rows)
    pred_frames = set(r[0] for r in mot_pred_rows)

    # Count unique identities
    gt_ids = set(r[1] for r in mot_gt_rows)
    pred_ids = set(r[1] for r in mot_pred_rows)

    # Count gaps
    gaps = metadata.get("visibility_gaps", {})
    total_gap_frames = sum(
        sum(end - start + 1 for start, end in track_gaps)
        for track_gaps in gaps.values()
    )

    return {
        "visible_gt_entries": visible_gt_count,
        "gt_entries_in_trackeval": len(mot_gt_rows),
        "predictions": pred_count,
        "predictions_in_trackeval": len(mot_pred_rows),
        "gt_frames": len(gt_frames),
        "pred_frames": len(pred_frames),
        "unique_gt_ids": len(gt_ids),
        "unique_pred_ids": len(pred_ids),
        "visibility_gaps": len(gaps),
        "total_gap_frames": total_gap_frames,
        "frame_index_offset": "0-based (per project protocol)",
        "class_mapping": CLASS_MAPPING,
    }

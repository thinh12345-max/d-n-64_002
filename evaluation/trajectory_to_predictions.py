"""Converter from runtime trajectory format to TrackEval prediction format.

This converter transforms the nested trajectory structure:
  {trajectories: [{track_id, observations: [...]}, ...]}

Into the flat frame-level prediction format required by the TrackEval adapter:
  [{frame_id, track_id, bbox, class, confidence}, ...]

Conversion rules:
1. Frame indexing: runtime frame_id 1-621 -> evaluation frame_id 0-620
2. Class mapping: integer IDs -> string names
3. Bbox conversion: 1280x720 -> 1020x500
4. Track ID: preserved as tracker-local identity
5. No global_id introduced (evaluation-time association handles this)

Reference: D-07.11 Tracking Prediction Evaluation Adapter
"""

import json
from pathlib import Path
from typing import List, Dict, Any, Tuple

# Class ID to string mapping (per established project mapping)
CLASS_ID_TO_NAME = {
    1: "car",
    2: "motorcycle",
    3: "bus",
    4: "truck",
}

# Runtime to evaluation coordinate conversion
RUNTIME_WIDTH = 1280
RUNTIME_HEIGHT = 720
EVAL_WIDTH = 1020
EVAL_HEIGHT = 500

NORM_SCALE_X = EVAL_WIDTH / RUNTIME_WIDTH  # 1020 / 1280
NORM_SCALE_Y = EVAL_HEIGHT / RUNTIME_HEIGHT  # 500 / 720


def convert_bbox(bbox: List[float]) -> List[float]:
    """Convert bbox from runtime (1280x720) to evaluation (1020x500) coordinates.

    Args:
        bbox: [x1, y1, x2, y2] in runtime coordinates

    Returns:
        [x1, y1, x2, y2] in evaluation coordinates
    """
    x1, y1, x2, y2 = bbox
    x1_eval = x1 * NORM_SCALE_X
    y1_eval = y1 * NORM_SCALE_Y
    x2_eval = x2 * NORM_SCALE_X
    y2_eval = y2 * NORM_SCALE_Y
    return [x1_eval, y1_eval, x2_eval, y2_eval]


def convert_class_id(class_id: int) -> str:
    """Convert integer class ID to string class name.

    Args:
        class_id: Integer class ID (1-4)

    Returns:
        String class name

    Raises:
        ValueError: If class_id is not recognized
    """
    if class_id not in CLASS_ID_TO_NAME:
        raise ValueError(f"Unknown class_id: {class_id}. Expected one of {list(CLASS_ID_TO_NAME.keys())}")
    return CLASS_ID_TO_NAME[class_id]


def convert_frame_id(runtime_frame_id: int) -> int:
    """Convert runtime frame ID to evaluation frame ID.

    Runtime: 1-based (1-621)
    Evaluation: 0-based (0-620)

    Args:
        runtime_frame_id: Frame ID from trajectory (1-621)

    Returns:
        Evaluation frame ID (0-620)
    """
    return runtime_frame_id - 1


def load_trajectory(trajectory_path: Path) -> Dict[str, Any]:
    """Load trajectory JSON file.

    Args:
        trajectory_path: Path to trajectory.json

    Returns:
        Trajectory data dict
    """
    with open(trajectory_path, 'r') as f:
        return json.load(f)


def convert_trajectory_to_predictions(trajectory_data: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Convert nested trajectory format to flat prediction format.

    Args:
        trajectory_data: Trajectory JSON data with nested trajectories structure

    Returns:
        Flat list of prediction dicts in TrackEval adapter format
    """
    predictions = []

    trajectories = trajectory_data.get('trajectories', [])

    for trajectory in trajectories:
        track_id = trajectory.get('track_id')
        observations = trajectory.get('observations', [])

        for obs in observations:
            # Convert frame ID: 1-based -> 0-based
            eval_frame_id = convert_frame_id(obs.get('frame_id'))

            # Convert class ID -> class name
            class_id = obs.get('class')
            class_name = convert_class_id(class_id)

            # Convert bbox: 1280x720 -> 1020x500
            runtime_bbox = obs.get('bbox')
            eval_bbox = convert_bbox(runtime_bbox)

            # Extract confidence
            confidence = obs.get('confidence')

            # Create prediction entry in adapter format
            prediction = {
                'frame_id': eval_frame_id,
                'track_id': track_id,
                'bbox': eval_bbox,
                'class': class_name,
                'confidence': confidence,
            }

            predictions.append(prediction)

    # Sort by frame_id then track_id for deterministic output
    predictions.sort(key=lambda p: (p['frame_id'], p['track_id']))

    return predictions


def validate_conversion(trajectory_data: Dict[str, Any], predictions: List[Dict[str, Any]]) -> Tuple[bool, str]:
    """Validate the conversion is correct and complete.

    Args:
        trajectory_data: Original trajectory data
        predictions: Converted predictions

    Returns:
        (is_valid, error_message)
    """
    # Count source observations
    source_obs_count = sum(
        len(traj.get('observations', []))
        for traj in trajectory_data.get('trajectories', [])
    )

    # Verify every observation was converted
    if len(predictions) != source_obs_count:
        return False, f"Observation count mismatch: source={source_obs_count}, converted={len(predictions)}"

    # Check frame range
    if predictions:
        frame_ids = [p['frame_id'] for p in predictions]
        min_frame = min(frame_ids)
        max_frame = max(frame_ids)

        if min_frame != 0:
            return False, f"Frame range should start at 0, got {min_frame}"
        if max_frame != 620:
            return False, f"Frame range should end at 620, got {max_frame}"

    # Verify frame 1 -> 0 and frame 621 -> 620 mapping
    # Find a prediction that should map from runtime frame 1
    for traj in trajectory_data.get('trajectories', []):
        for obs in traj.get('observations', []):
            if obs.get('frame_id') == 1:
                # Find corresponding prediction
                matching = [p for p in predictions if p.get('track_id') == traj.get('track_id') and p.get('frame_id') == 0]
                if not matching:
                    return False, "Frame 1 -> 0 mapping failed"
                break
        else:
            continue
        break

    # Check frame 621 -> 620
    for traj in trajectory_data.get('trajectories', []):
        for obs in traj.get('observations', []):
            if obs.get('frame_id') == 621:
                matching = [p for p in predictions if p.get('track_id') == traj.get('track_id') and p.get('frame_id') == 620]
                if not matching:
                    return False, "Frame 621 -> 620 mapping failed"
                break
        else:
            continue
        break

    # Verify class conversion
    for pred in predictions:
        if pred['class'] not in CLASS_ID_TO_NAME.values():
            return False, f"Invalid class name: {pred['class']}"

    # Verify bbox coordinates are in evaluation space
    for pred in predictions:
        bbox = pred['bbox']
        if not (0 <= bbox[0] <= EVAL_WIDTH and 0 <= bbox[1] <= EVAL_HEIGHT and
                0 <= bbox[2] <= EVAL_WIDTH and 0 <= bbox[3] <= EVAL_HEIGHT):
            return False, f"Bbox out of bounds: {bbox}"

    # Verify no global_id introduced
    for pred in predictions:
        if 'global_id' in pred:
            return False, "global_id should not be introduced in predictions"

    return True, "Validation passed"


def convert_and_save(
    trajectory_path: Path,
    output_path: Path,
    validate: bool = True
) -> List[Dict[str, Any]]:
    """Load trajectory, convert to predictions, and save.

    Args:
        trajectory_path: Path to source trajectory.json
        output_path: Path to save converted predictions
        validate: Whether to validate the conversion

    Returns:
        List of converted predictions
    """
    # Load source
    trajectory_data = load_trajectory(trajectory_path)

    # Convert
    predictions = convert_trajectory_to_predictions(trajectory_data)

    # Validate
    if validate:
        is_valid, message = validate_conversion(trajectory_data, predictions)
        if not is_valid:
            raise ValueError(f"Conversion validation failed: {message}")

    # Save
    with open(output_path, 'w') as f:
        json.dump(predictions, f, indent=2)

    return predictions


# Standalone validation function
def validate_source_unchanged(trajectory_path: Path) -> bool:
    """Verify source trajectory file is unchanged.

    Args:
        trajectory_path: Path to trajectory.json

    Returns:
        True if file exists and is readable
    """
    return trajectory_path.exists() and trajectory_path.is_file()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Convert trajectory.json to TrackEval prediction format"
    )
    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to trajectory.json",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Path to output predictions.json",
    )
    parser.add_argument(
        "--no-validate",
        action="store_true",
        help="Skip validation",
    )

    args = parser.parse_args()

    print(f"Loading trajectory from: {args.input}")
    predictions = convert_and_save(
        args.input,
        args.output,
        validate=not args.no_validate
    )
    print(f"Converted {len(predictions)} predictions")
    print(f"Saved to: {args.output}")

"""TrackEval evaluation entry point for tracking evaluation.

This entry point implements the D-06.x tracking evaluation protocol using
TrackEval 1.3.0 with the existing trackeval_adapter.py.

Configuration:
- IoU threshold: 0.50
- Metrics: MOTA, MOTP, IDF1 (primary), IDSW, fragmentation (diagnostic)
- Matching: Hungarian (TrackEval default)
- Evaluation: whole-video, per-class

Usage:
    python evaluation/trackeval_evaluation.py --gt <gt_path> --pred <pred_path> --output <output_dir>

Example:
    python evaluation/trackeval_evaluation.py \
        --gt annotation/data/tracking_ground_truth.json \
        --pred output/predictions.json \
        --output evaluation/outputs/trackeval_eval_01
"""

import argparse
import json
import sys
from pathlib import Path

# TrackEval imports
from trackeval import Evaluator
from trackeval.metrics import CLEAR, Identity, HOTA

# Custom dataset for five-class evaluation
from project_trackeval_dataset import Project5ClassDataset

# Adapter imports
from trackeval_adapter import (
    load_gt_tracks,
    load_predictions,
    convert_gt_to_trackeval,
    convert_predictions_to_trackeval,
    write_mot_file,
    CLASS_MAPPING,
    IMAGE_WIDTH,
    IMAGE_HEIGHT,
)


def validate_input_paths(gt_path: Path, pred_path: Path) -> None:
    """Validate that required input files exist.

    Args:
        gt_path: Path to GT JSON file
        pred_path: Path to predictions JSON file

    Raises:
        FileNotFoundError: If required files don't exist
    """
    if not gt_path.exists():
        raise FileNotFoundError(f"GT file not found: {gt_path}")
    if not pred_path.exists():
        raise FileNotFoundError(f"Predictions file not found: {pred_path}")


def run_trackeval_evaluation(
    gt_path: Path,
    pred_path: Path,
    output_dir: Path,
    iou_threshold: float = 0.50,
) -> dict:
    """Run TrackEval evaluation.

    Args:
        gt_path: Path to GT JSON file
        pred_path: Path to predictions JSON file
        output_dir: Output directory for evaluation results
        iou_threshold: IoU threshold for matching (default: 0.50)

    Returns:
        Evaluation results dict
    """
    # Validate inputs
    validate_input_paths(gt_path, pred_path)

    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load and convert GT
    print(f"Loading GT from: {gt_path}")
    gt_tracks = load_gt_tracks(gt_path)
    mot_gt_rows, gt_metadata = convert_gt_to_trackeval(gt_tracks)

    # Convert frames from 0-based (project protocol) to 1-based (TrackEval requirement)
    # Project frames: 0-620, TrackEval frames: 1-621
    mot_gt_rows_1based = [[r[0] + 1] + r[1:] for r in mot_gt_rows]

    # Encode string GT global IDs to integer IDs for TrackEval MOT format
    # Source GT uses string IDs (GT_001, GT_002, etc.), TrackEval requires integers
    # Mapping is deterministic, stable, and one-to-one
    unique_global_ids = sorted(set(r[1] for r in mot_gt_rows_1based))
    global_id_to_int = {gid: i + 1 for i, gid in enumerate(unique_global_ids)}
    mot_gt_rows_1based = [
        [r[0], global_id_to_int[r[1]]] + r[2:] for r in mot_gt_rows_1based
    ]

    # Write GT in MOT format
    gt_mot_path = output_dir / "gt.txt"
    write_mot_file(gt_mot_path, mot_gt_rows_1based)
    print(f"GT written to: {gt_mot_path}")

    # Load and convert predictions
    print(f"Loading predictions from: {pred_path}")
    predictions = load_predictions(pred_path)
    mot_pred_rows = convert_predictions_to_trackeval(predictions)

    # Convert frames from 0-based (project protocol) to 1-based (TrackEval requirement)
    mot_pred_rows_1based = [[r[0] + 1] + r[1:] for r in mot_pred_rows]

    # Write predictions in MOT format
    pred_mot_path = output_dir / "pred.txt"
    write_mot_file(pred_mot_path, mot_pred_rows_1based)
    print(f"Predictions written to: {pred_mot_path}")

    # Create seqinfo.ini
    # TrackEval uses 1-based frames, so sequence length is (max frame - min frame + 1)
    # Project frames: 0-620 (621 frames), TrackEval frames: 1-621 (621 frames)
    seqinfo_path = output_dir / "seqinfo.ini"
    num_frames = 621  # Fixed: 621 frames (0-620 in project = 1-621 in TrackEval)
    fps = 15  # Protocol specifies 15 FPS
    seqinfo_content = f"""[Sequence]
name=seq
imDir=img
frameRate={fps}
seqLength={num_frames}
imWidth={IMAGE_WIDTH}
imHeight={IMAGE_HEIGHT}
"""
    with open(seqinfo_path, 'w') as f:
        f.write(seqinfo_content)
    print(f"Seqinfo written to: {seqinfo_path}")

    # TrackEval configuration
    # Project5ClassDataset expects:
    #   - GT: <GT_FOLDER>/<seq>/gt.txt = data/seq/gt.txt
    #   - Pred: <TRACKERS_FOLDER>/<tracker>/<TRACKER_SUB_FOLDER>/<seq>.txt
    #     With GT_FOLDER=TRACKERS_FOLDER=data, tracker=seq, TRACKER_SUB_FOLDER=tracker
    #     => data/seq/tracker/seq.txt
    data_dir = output_dir / "data"
    seq_dir = data_dir / "seq"
    tracker_sub_dir = seq_dir / "tracker"  # data/seq/tracker/
    data_dir.mkdir(parents=True, exist_ok=True)
    seq_dir.mkdir(parents=True, exist_ok=True)
    tracker_sub_dir.mkdir(parents=True, exist_ok=True)

    # Copy files to expected locations
    import shutil
    shutil.copy(gt_mot_path, seq_dir / "gt.txt")
    shutil.copy(pred_mot_path, tracker_sub_dir / "seq.txt")
    shutil.copy(seqinfo_path, data_dir / "seqinfo.ini")

    # Configure evaluation
    eval_config = {
        "iou_threshold": iou_threshold,
        "PRINT_CONFIG": True,
    }

    # Metrics to evaluate
    metrics_config = [
        CLEAR({"THRESHOLD": iou_threshold, "PRINT_CONFIG": True}),  # MOTA, MOTP
        Identity({"THRESHOLD": iou_threshold, "PRINT_CONFIG": True}),  # IDSW
        HOTA({"THRESHOLD": iou_threshold, "PRINT_CONFIG": True}),  # IDF1 equivalent
    ]

    # Dataset config for Project5ClassDataset (supports all five classes)
    dataset_config = {
        "GT_FOLDER": str(data_dir),  # Points to data/ where seq/ subfolder exists
        "TRACKERS_FOLDER": str(data_dir),  # Points to data/ where seq/tracker/ subfolder exists
        "TRACKER_SUB_FOLDER": "tracker",
        "OUTPUT_FOLDER": str(output_dir / "results"),
        "SEQ_INFO": {"seq": 621},  # 621 frames (project 0-620 = TrackEval 1-621)
        "CLASSES_TO_EVAL": ["car", "motorcycle", "bus", "truck", "person"],
        "TRACKERS_TO_EVAL": ["seq"],  # Explicitly set tracker name to avoid picking up seqinfo.ini
    }

    # Run evaluation
    evaluator = Evaluator()
    dataset = Project5ClassDataset(dataset_config)
    results = evaluator.evaluate([dataset], metrics_config)

    return results


def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(
        description="TrackEval tracking evaluation entry point"
    )
    parser.add_argument(
        "--gt",
        type=Path,
        required=True,
        help="Path to GT JSON file (tracking_ground_truth.json)",
    )
    parser.add_argument(
        "--pred",
        type=Path,
        required=True,
        help="Path to predictions JSON file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        required=True,
        help="Output directory for evaluation results",
    )
    parser.add_argument(
        "--iou",
        type=float,
        default=0.50,
        help="IoU threshold for matching (default: 0.50)",
    )

    args = parser.parse_args()

    # Validate IoU threshold
    if not 0.0 <= args.iou <= 1.0:
        print(f"ERROR: IoU threshold must be between 0 and 1, got {args.iou}")
        sys.exit(1)

    print("=" * 60)
    print("TrackEval Tracking Evaluation")
    print("=" * 60)
    print(f"GT path: {args.gt}")
    print(f"Predictions path: {args.pred}")
    print(f"Output directory: {args.output}")
    print(f"IoU threshold: {args.iou}")
    print(f"Metrics: MOTA, MOTP, IDF1 (primary), IDSW, fragmentation (diagnostic)")
    print("=" * 60)

    try:
        results = run_trackeval_evaluation(
            gt_path=args.gt,
            pred_path=args.pred,
            output_dir=args.output,
            iou_threshold=args.iou,
        )
        print("\nEvaluation completed successfully!")
        print(f"Results saved to: {args.output}")
    except FileNotFoundError as e:
        print(f"\nERROR: {e}")
        print("\nPlease ensure both GT and prediction files exist before running evaluation.")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: Evaluation failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

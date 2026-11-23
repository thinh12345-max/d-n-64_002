"""Traffic AI — Vehicle Counting Pipeline.

Identity Contract (D-05.18-C)
=============================
track_id  = ByteTrack runtime identity.  Assigned per video run.  Non-deterministic
            across runs.  Used as the runtime trajectory key in trajectory.json.
global_id = Runtime identity assigned by Global Identity association pipeline.
            Per-observation (PER_OBSERVATION) - each frame may carry a global_id.

track_id != global_id.  The runtime trajectory artifact is keyed by track_id only.
global_id is an additional identity layer attached to each observation.
"""

from dataclasses import dataclass
from pathlib import Path
import json
import math
import os
import random
import logging
import sys

import cv2
import numpy as np
import torch
from ultralytics import YOLO

from config import get_config
from decision3_geometry import classify_decision3

# Global Identity imports for runtime association
from global_identity import (
    RuntimeGlobalIdentityRegistry,
    RuntimeTrackingObservation,
    RuntimeTrackSegment,
    CandidateGenerator,
    AssociationBaseline,
    associate_track_segments,
    observation_from_bytetrack,
    build_track_segments_from_observations,
    build_global_identity_artifact,
    serialize_global_identity_artifact,
)


def setup_logging(config) -> logging.Logger:
    """Setup logging based on configuration."""
    log_level = getattr(logging, config.logging.level)
    log_format = config.logging.format

    logger = logging.getLogger("traffic_ai")
    logger.setLevel(log_level)

    # Clear existing handlers
    logger.handlers.clear()

    # Console handler
    handler = logging.StreamHandler(sys.stdout)
    handler.setLevel(log_level)
    formatter = logging.Formatter(log_format)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger


def setup_seeds(config) -> None:
    """Set deterministic seeds for reproducibility."""
    seeds = config.seeds
    random.seed(seeds.random)
    np.random.seed(seeds.numpy)
    torch.manual_seed(seeds.torch)
    torch.cuda.manual_seed_all(seeds.torch_cuda)
    torch.backends.cudnn.deterministic = seeds.cudnn_deterministic
    torch.backends.cudnn.benchmark = seeds.cudnn_benchmark


def ensure_file_exists(path: Path, logger: logging.Logger) -> None:
    """Check if file exists, raise error with clear message if not."""
    if not path.exists():
        logger.error("File not found: %s", path)
        raise FileNotFoundError(f"File not found: {path}")


def opencv_gui_available() -> bool:
    """Return True when a desktop GUI environment is available.

    This keeps the existing headless fallback but restores optional windowed
    visualization on normal desktop machines. The computational pipeline is
    unchanged; only the display capability check is gated.
    """
    if sys.platform.startswith("win") or sys.platform.startswith("darwin"):
        return True
    if sys.platform.startswith("linux"):
        return "DISPLAY" in os.environ or "WAYLAND_DISPLAY" in os.environ
    return False


@dataclass
class EntityState:
    entity_id: int
    last_point: tuple[int, int]
    last_box: tuple[int, int, int, int]
    last_frame: int
    label: str
    confidence: float
    counted: bool = False


def decision3_observation_point(box: tuple) -> tuple:
    """Compute the Decision 3 observation point from a detection bbox.

    Decision 3 uses the bbox GEOMETRIC CENTER as its observation point:

        cx = (x1 + x2) / 2
        cy = (y1 + y2) / 2

    The bbox entering this helper is already represented as integer GT
    pixel coordinates (1020x500) per the ratified coordinate contract; this
    integer representation is the existing input convention and is NOT
    introduced by this helper. classify_decision3() expects native 1280x720
    coordinates, so the geometric center is recovered into native space via
    the inverse A2 dimension-ratio mapping:

        x_native = cx * 1280 / 1020
        y_native = cy * 720 / 500

    This helper computes the geometric center using float arithmetic and
    applies no additional rounding or clamping of its own. The no-rounding
    / no-clamping rule applies to the Decision 3 geometry transformation
    and polygon evaluation path, not to the integer representation of the
    input bbox.

    This helper does NOT alter the Counting ROI observation point. Decision
    3 uses the bbox GEOMETRIC CENTER (cx, cy) as its observation point while
    the Counting ROI independently uses the bbox BOTTOM-CENTER (cx, y2). The
    two observation points are never shared.
    """
    x1, y1, x2, y2 = box
    cx = (x1 + x2) / 2
    cy = (y1 + y2) / 2
    native_center = (
        cx * 1280 / 1020,
        cy * 720 / 500,
    )
    return native_center


def inside_roi(point: tuple, roi_points: list, logger: logging.Logger) -> bool:
    """Check if point is inside ROI polygon."""
    try:
        return cv2.pointPolygonTest(np.array(roi_points, np.int32), point, False) >= 0
    except Exception as e:
        logger.error("ROI check failed: %s", e)
        return False


def box_iou(box_a: tuple, box_b: tuple) -> float:
    """Calculate intersection over union between two boxes."""
    ax1, ay1, ax2, ay2 = box_a
    bx1, by1, bx2, by2 = box_b

    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)

    inter_w = max(0, inter_x2 - inter_x1)
    inter_h = max(0, inter_y2 - inter_y1)
    inter_area = inter_w * inter_h

    area_a = (ax2 - ax1) * (ay2 - ay1)
    area_b = (bx2 - bx1) * (by2 - by1)
    union_area = area_a + area_b - inter_area

    return inter_area / union_area if union_area > 0 else 0.0


def cleanup_tracker_links(tracker_to_entity: dict, entities: dict, frame_index: int, max_stale: int) -> None:
    """Remove stale trackers."""
    stale_trackers = []
    for tracker_key, entity_id in tracker_to_entity.items():
        state = entities.get(entity_id)
        if state is None or frame_index - state.last_frame > max_stale:
            stale_trackers.append(tracker_key)

    for key in stale_trackers:
        tracker_to_entity.pop(key, None)


def is_reasonable_match(state: EntityState, point: tuple, box: tuple, frame_index: int, max_distance: int = 50, max_gap: int = 30) -> bool:
    """Check if match is reasonable based on position and frame gap."""
    frame_gap = frame_index - state.last_frame
    if frame_gap <= 0 or frame_gap > max_gap:
        return False

    distance = math.dist(point, state.last_point)
    if distance > max_distance:
        return False

    return True


def assign_entity(track_id: int, point: tuple, box: tuple, label: str, frame_index: int,
                  tracker_to_entity: dict, entities: dict, next_entity_id: int, matched_entity_ids: set) -> tuple:
    """Assign entity to existing or create new entity."""
    tracker_key = track_id
    existing_entity_id = tracker_to_entity.get(tracker_key)

    if existing_entity_id is not None:
        state = entities.get(existing_entity_id)
        if state is not None and existing_entity_id not in matched_entity_ids:
            if is_reasonable_match(state, point, box, frame_index):
                matched_entity_ids.add(existing_entity_id)
                return existing_entity_id, next_entity_id
        tracker_to_entity.pop(tracker_key, None)

    # Find best matching existing entity (same label)
    best_entity_id = None
    best_score = None

    for entity_id, state in entities.items():
        if entity_id in matched_entity_ids:
            continue
        if state.label != label:
            continue
        if not is_reasonable_match(state, point, box, frame_index):
            continue

        frame_gap = frame_index - state.last_frame
        distance = math.dist(point, state.last_point)
        overlap = box_iou(box, state.last_box)
        score = distance + frame_gap * 2 - overlap * 100

        if best_score is None or score < best_score:
            best_score = score
            best_entity_id = entity_id

    if best_entity_id is None:
        next_entity_id += 1
        best_entity_id = next_entity_id
        entities[best_entity_id] = EntityState(
            entity_id=best_entity_id,
            last_point=point,
            last_box=box,
            last_frame=frame_index,
            label=label,
            confidence=0.0,
        )

    tracker_to_entity[tracker_key] = best_entity_id
    matched_entity_ids.add(best_entity_id)
    return best_entity_id, next_entity_id


def build_counts(entities: dict, countable_labels: list) -> dict:
    """Count vehicles that have been counted."""
    counts = {label: 0 for label in countable_labels}
    for state in entities.values():
        if state.counted:
            counts[state.label] += 1
    return counts


def build_trajectory_artifact(
    track_observations: dict[int, list[dict]],
    track_id_to_global_id: dict[int, str] | None = None,
) -> dict:
    """Materialize a RuntimeTrajectory artifact from accumulated raw observations.

    Grouped by runtime identity key track_id. Frame order, temporal gaps, and
    center points are all preserved from the raw observations.

    Args:
        track_observations: Dictionary mapping track_id to list of observation dicts
        track_id_to_global_id: Optional mapping from track_id to runtime global_id.
            If provided, each observation will include its associated global_id.
            This mapping comes from the runtime Global Identity association result.
    """
    if track_id_to_global_id is None:
        track_id_to_global_id = {}

    trajectories = []
    for track_id, observations in sorted(track_observations.items()):
        if not observations:
            continue
        trajectories.append({
            "track_id": track_id,
            "start_frame": observations[0]["frame_id"],
            "end_frame": observations[-1]["frame_id"],
            "start_timestamp": observations[0]["timestamp"],
            "end_timestamp": observations[-1]["timestamp"],
            "observations": [
                {
                    "frame_id": obs["frame_id"],
                    "timestamp": obs["timestamp"],
                    "bbox": obs["bbox"],
                    "class": obs["class"],
                    "confidence": obs["confidence"],
                    "cx": obs["cx"],
                    "cy": obs["cy"],
                    "global_id": track_id_to_global_id.get(track_id),
                }
                for obs in observations
            ],
        })
    return {"trajectories": trajectories}


def serialize_trajectory_artifact(artifact: dict, output_dir: Path) -> Path:
    """Write the RuntimeTrajectory artifact to a deterministic JSON file."""
    path = output_dir / "trajectory.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(artifact, f, indent=4)
    return path


def tracking_observation_adapter(result, frame_index: int, fps: float = 15.0) -> list[dict]:
    """Adapt Ultralytics tracking output to the D-05.2 detection-to-tracking contract.

    This adapter exposes the tracker-local identity and raw observation fields while
    keeping ``track_id`` distinct from any later global identity. It does not create
    trajectories or modify ROI logic.
    """
    observations = []
    if result is None:
        return observations

    boxes_obj = result.boxes
    if boxes_obj is None or boxes_obj.id is None:
        return observations

    boxes = boxes_obj.xyxy.cpu().numpy() if hasattr(boxes_obj.xyxy, 'cpu') else np.array(boxes_obj.xyxy)
    ids = boxes_obj.id.cpu().numpy() if hasattr(boxes_obj.id, 'cpu') else np.array(boxes_obj.id)
    classes = boxes_obj.cls.cpu().numpy() if hasattr(boxes_obj.cls, 'cpu') else np.array(boxes_obj.cls)
    confs = boxes_obj.conf.cpu().numpy() if hasattr(boxes_obj.conf, 'cpu') else np.array(boxes_obj.conf)

    for box, raw_track_id, cls, conf in zip(boxes, ids, classes, confs):
        x1, y1, x2, y2 = map(int, box)
        observations.append({
            "frame_id": int(frame_index),
            "timestamp": float(frame_index) / float(fps),
            "track_id": int(raw_track_id),
            "class": int(cls),
            "bbox": [x1, y1, x2, y2],
            "confidence": float(conf),
        })

    return observations


def persist_tracking_observations(track_observations: dict[int, list[dict]], observations: list[dict]) -> dict[int, list[dict]]:
    """Persist tracker-local observations in frame order per track_id.

    This is intentionally minimal: it preserves the existing tracker-local identity,
    keeps the temporal sequence by frame_id, and does not create any global identity,
    trajectory state, or ROI semantics.
    """
    for observation in observations:
        x1, y1, x2, y2 = observation["bbox"]
        observation["cx"] = (x1 + x2) / 2.0
        observation["cy"] = (y1 + y2) / 2.0
        track_id = int(observation["track_id"])
        track_observations.setdefault(track_id, []).append(observation)
    return track_observations


def draw_detection(frame, box: tuple, text: str, color: tuple, center_point: tuple, inside_current: bool) -> None:
    """Draw bounding box and ID label for each tracked vehicle."""
    x1, y1, x2, y2 = box
    thickness = 2 if inside_current else 1
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, thickness)
    cv2.circle(frame, center_point, 4, color, -1)
    cv2.putText(
        frame,
        text,
        (x1, max(20, y1 - 10)),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.45,
        color,
        2,
    )


def main():
    """Main execution function."""
    # Load configuration
    config = get_config()

    # Setup logging
    logger = setup_logging(config)

    logger.info("=" * 60)
    logger.info("Traffic AI - Vehicle Counting Pipeline")
    logger.info("=" * 60)
    logger.info("Configuration: %s", config.project.name)
    logger.info("Model: %s", config.model.path)
    logger.info("Device: %s", config.model.device)
    logger.info("Tracker: %s", config.tracker.type)
    logger.info("Confidence: %.2f", config.model.confidence)
    logger.info("IoU: %.2f", config.model.iou)
    logger.info("Image size: %d", config.model.imgsz)
    logger.info("Video source: %s", config.video.source)
    logger.info("ROI enabled: %s", config.roi.enabled)
    logger.info("Output directory: %s", config.output.directory)

    # Setup deterministic seeds
    setup_seeds(config)

    # Validate paths
    model_path = Path(config.model.path)
    video_path = Path(config.video.source)
    output_dir = Path(config.output.directory)

    ensure_file_exists(model_path, logger)
    ensure_file_exists(video_path, logger)
    output_dir.mkdir(parents=True, exist_ok=True)

    # Load model and get class mapping
    logger.info("Loading custom model: %s", model_path)
    model = YOLO(str(model_path))
    model_class_names = model.names
    logger.info("Model classes: %s", model_class_names)

    # Create reverse mapping (class_id -> class_name) using countable labels from config
    countable_labels = config.counting.countable_labels
    id_to_name = {}
    for class_id, class_name in model_class_names.items():
        name_lower = str(class_name).lower()
        if name_lower in countable_labels:
            id_to_name[int(class_id)] = name_lower

    logger.info("Countable classes mapping: %s", id_to_name)

    if not id_to_name:
        logger.error("No countable classes found in model. Check countable_labels in config.")
        raise ValueError("No countable classes found in model")

    # Colors for visualization from config
    class_colors = {}
    for label, color in config.visualization.class_colors.items():
        class_colors[label] = tuple(color)

    outside_roi_color = tuple(config.visualization.outside_roi_color)

    # Tracking state
    tracker_to_entity = {}  # (track_id) -> entity_id
    entities = {}  # entity_id -> EntityState
    track_observations = {}  # track_id -> ordered observations
    next_entity_id = 0
    frame_index = 0

    # Global Identity state (runtime state, per video run only)
    gi_registry = RuntimeGlobalIdentityRegistry()
    gi_observations = []  # List[RuntimeTrackingObservation] for Global Identity pipeline
    gi_candidate_generator = CandidateGenerator()
    gi_association_baseline = AssociationBaseline()

    # Open video
    cap = cv2.VideoCapture(str(video_path))
    if not cap.isOpened():
        logger.error("Cannot open video: %s", video_path)
        raise RuntimeError(f"Cannot open video: {video_path}")

    source_fps = cap.get(cv2.CAP_PROP_FPS)
    if not (isinstance(source_fps, float) and source_fps > 0 and math.isfinite(source_fps)):
        raise ValueError(
            f"Invalid source FPS retrieved from video: {source_fps!r}. "
            "Cannot compute trajectory timestamps."
        )
    logger.info("Source video FPS: %.3f", source_fps)

    # Get source dimensions for coordinate mapping
    source_width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    source_height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    display_width, display_height = config.video.frame_size

    # Calculate scaling factors for coordinate mapping (source -> display space)
    scale_x = display_width / source_width
    scale_y = display_height / source_height
    logger.info("Coordinate mapping: source %dx%d -> display %dx%d (scale: %.4f, %.4f)",
                source_width, source_height, display_width, display_height, scale_x, scale_y)

    # ROI points
    roi_points = config.roi.points if config.roi.enabled else []

    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                break

            frame_index += 1

            # Skip frames if configured
            if config.video.frame_skip > 0 and frame_index % (config.video.frame_skip + 1) != 1:
                continue

            cleanup_tracker_links(tracker_to_entity, entities, frame_index, config.tracker.config.get("stale_frames", 30))

            # Resize frame
            annotated_frame = cv2.resize(frame, tuple(config.video.frame_size))
            matched_entity_ids = set()

            # Runtime tracker: ByteTrack (algorithm/configuration change from BoT-SORT).
            # track_id = tracker-local runtime identity for this video run only.
            # Global ID association is NOT implemented; track_id != global_id.
            result = model.track(
                frame,
                persist=True,
                classes=list(id_to_name.keys()),
                conf=config.model.confidence,
                iou=config.model.iou,
                imgsz=config.model.imgsz,
                tracker="bytetrack.yaml",
                verbose=False,
            )[0]

            tracking_observations = tracking_observation_adapter(result, frame_index, fps=source_fps)
            persist_tracking_observations(track_observations, tracking_observations)

            # Convert ByteTrack observations to RuntimeTrackingObservation for Global Identity pipeline
            for obs in tracking_observations:
                gi_obs = observation_from_bytetrack(obs, class_mapping=id_to_name)
                gi_observations.append(gi_obs)

            for observation in tracking_observations:
                class_id = int(observation["class"])

                # Get label from our mapping
                label = id_to_name.get(class_id)
                if label is None:
                    continue  # Skip classes not in our countable types

                # Parse bounding box
                x1, y1, x2, y2 = observation["bbox"]
                width = x2 - x1
                height = y2 - y1

                # Minimum size filter
                if width < config.counting.min_box_size or height < config.counting.min_box_size:
                    continue

                # Center point calculation
                center_x = (x1 + x2) / 2
                center_y = (y1 + y2) / 2
                center_point = (int(center_x), int(center_y))
                box_tuple = (x1, y1, x2, y2)
                track_id = int(observation["track_id"])
                conf = float(observation["confidence"])

                # ROI check uses bottom-center
                roi_point = (center_x, y2)
                inside_current = inside_roi(roi_point, roi_points, logger) if config.roi.enabled else True

                # Decision 3 region classification (separate layer; does not affect
                # ROI or counting). The bbox values here have already been
                # converted to integer GT pixel coordinates per the ratified
                # coordinate contract. Decision 3 uses the GEOMETRIC CENTER of
                # that integer bbox as its observation point (cx, cy), derived
                # independently from the Counting ROI BOTTOM-CENTER (roi_point)
                # used above. The helper recovers the native 1280x720 observation
                # point from the GT-space geometric center via the inverse A2
                # mapping. No additional rounding or clamping is applied by the
                # helper; the no-rounding/no-clamping rule applies to the
                # Decision 3 geometry transformation and polygon evaluation path.
                decision3_region = classify_decision3(
                    decision3_observation_point(box_tuple)
                )

                # Assign entity ID
                entity_id, next_entity_id = assign_entity(
                    track_id,
                    center_point,
                    box_tuple,
                    label,
                    frame_index,
                    tracker_to_entity,
                    entities,
                    next_entity_id,
                    matched_entity_ids,
                )

                # Update state
                state = entities[entity_id]
                state.last_point = center_point
                state.last_box = box_tuple
                state.last_frame = frame_index
                state.confidence = conf

                # Mark as counted only when object is inside ROI with sufficient confidence
                if inside_current and state.confidence >= config.counting.min_confidence and not state.counted:
                    state.counted = True
                    logger.debug("Entity %d (%s) counted at frame %d", entity_id, label, frame_index)

                # REPAIR 1: Map bbox from source space to display space
                display_x1 = int(x1 * scale_x)
                display_y1 = int(y1 * scale_y)
                display_x2 = int(x2 * scale_x)
                display_y2 = int(y2 * scale_y)
                display_box = (display_x1, display_y1, display_x2, display_y2)

                # Map center point to display space
                display_center_x = int(center_x * scale_x)
                display_center_y = int(center_y * scale_y)
                display_center_point = (display_center_x, display_center_y)

                # REPAIR 2: Drawing is independent of counting - draw for every valid detection
                color = class_colors.get(label, outside_roi_color) if inside_current else outside_roi_color
                draw_detection(
                    annotated_frame,
                    display_box,
                    f"T{track_id} E{entity_id}",
                    color,
                    display_center_point,
                    inside_current,
                )

            # Build final counts
            vehicle_count = build_counts(entities, countable_labels)

            # Visualization
            if config.roi.enabled:
                roi_color = tuple(config.visualization.roi_color)
                cv2.polylines(annotated_frame, [np.array(roi_points, np.int32)], True, roi_color, config.visualization.roi_thickness)

            y_offset = 30
            for label, count in vehicle_count.items():
                cv2.putText(
                    annotated_frame,
                    f"{label.upper()}: {count}",
                    (20, y_offset),
                    cv2.FONT_HERSHEY_SIMPLEX,
                    0.6,
                    (255, 255, 0),
                    2,
                )
                y_offset += 25

            if config.visualization.show_window and opencv_gui_available():
                try:
                    cv2.imshow(config.visualization.window_name, annotated_frame)
                    if cv2.waitKey(1) == 27:  # ESC key
                        logger.info("ESC pressed, stopping...")
                        break
                except cv2.error:
                    logger.warning("OpenCV GUI backend unavailable; continuing without visualization.")
                    config.visualization.show_window = False

    finally:
        cap.release()
        if opencv_gui_available():
            try:
                cv2.destroyAllWindows()
            except cv2.error:
                pass

    # Save results
    vehicle_count = build_counts(entities, countable_labels)
    output_path = output_dir / config.output.json_filename

    with output_path.open("w", encoding="utf-8") as f:
        json.dump(vehicle_count, f, indent=4)

    logger.info("=" * 60)
    logger.info("FINAL VEHICLE COUNTS")
    logger.info("=" * 60)
    for label, count in vehicle_count.items():
        logger.info("%s: %d", label.upper(), count)
    logger.info("Results saved to: %s", output_path)

    # ===== Global Identity Runtime Association =====
    # Build track_id -> global_id mapping from runtime associations
    track_id_to_global_id: dict[int, str] = {}
    if gi_observations:
        gi_segments = build_track_segments_from_observations(gi_observations)
        logger.info("Global Identity: built %d track segments from %d observations",
                    len(gi_segments), len(gi_observations))

        # Run association pipeline
        decisions = associate_track_segments(
            gi_segments,
            gi_registry,
            candidate_generator=gi_candidate_generator,
            association_baseline=gi_association_baseline,
        )

        # Log association results
        match_count = sum(1 for d in decisions if d.decision == "MATCH")
        no_match_count = sum(1 for d in decisions if d.decision == "NO_MATCH")
        logger.info("Global Identity: %d MATCH, %d NO_MATCH decisions", match_count, no_match_count)
        logger.info("Global Identity: %d runtime identities created", gi_registry.count_identities())

        # Log detailed associations for debugging
        for gid in gi_registry.list_identities():
            record = gi_registry.get_by_global_id(gid)
            track_ids = record.get_track_ids()
            logger.debug("Global Identity: %s -> track_ids=%s", gid, track_ids)
            # Build track_id -> global_id mapping for trajectory
            for tid in track_ids:
                track_id_to_global_id[tid] = gid

        # Build and serialize Global Identity audit artifact
        gi_artifact = build_global_identity_artifact(gi_registry, decisions)
        gi_artifact_path = serialize_global_identity_artifact(gi_artifact, output_dir)
        logger.info("Global Identity audit artifact saved to: %s", gi_artifact_path)

    # Materialize and serialize RuntimeTrajectory artifact with global_id
    trajectory_artifact = build_trajectory_artifact(track_observations, track_id_to_global_id)
    trajectory_path = serialize_trajectory_artifact(trajectory_artifact, output_dir)
    logger.info("Runtime trajectory artifact saved to: %s", trajectory_path)


if __name__ == "__main__":
    main()
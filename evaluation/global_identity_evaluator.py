"""Global Identity Evaluation — Temporal Consistency Metrics.

Implements the second atomic layer of the Global Identity evaluation pipeline:
  1. Frame-level Hungarian matching from GI-08.8 (IoU >= 0.50, D1+D2).
  2. ID Preserved Score - temporal consistency of runtime global_id assignments.
  3. Global Identity Fragmentation - one GT identity represented by multiple runtime IDs.
  4. Global Identity Merge - one runtime global ID associated with multiple GT identities.
  5. Provisional identity handling (reported separately, not penalized).
  6. Per-class reporting for car, motorcycle, bus, truck (D5).

Reference: docs/GI_08_DECISION_RECORD.md

Decisions applied:
  - D1: IoU >= 0.50
  - D2: Hungarian one-to-one matching
  - D5: aggregate + per-class reporting
  - D6: minimum 1 observation
  - D7: timestamp-based temporal alignment
  - D8: GT-validated continuity (NOT implemented - belongs to next stage)
"""

import json
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Optional

import numpy as np
from scipy.optimize import linear_sum_assignment


# =============================================================================
# Data Classes
# =============================================================================

@dataclass(frozen=True)
class RuntimeObservation:
    """A runtime observation from trajectory.json."""
    track_id: int
    frame_id: int
    timestamp: float
    global_id: str
    bbox: tuple[int, int, int, int]  # [x1, y1, x2, y2]
    class_id: int
    confidence: float
    cx: float
    cy: float


@dataclass(frozen=True)
class GTObservation:
    """A ground-truth observation from tracking_ground_truth.json."""
    global_id: str
    frame_id: int
    timestamp: float
    bbox: tuple[int, int, int, int]  # [x1, y1, x2, y2]
    center: tuple[float, float]
    class_name: str
    visibility: float
    occlusion: int


@dataclass(frozen=True)
class MatchedPair:
    """A matched runtime-to-GT pair in a single frame."""
    runtime_obs: RuntimeObservation
    gt_obs: GTObservation
    iou: float


# =============================================================================
# IoU Calculation (D1: IoU >= 0.50 threshold)
# =============================================================================

def box_iou_xyxy(a, b):
    """Intersection-over-Union for two [x1, y1, x2, y2] boxes.

    Args:
        a: First box as (x1, y1, x2, y2).
        b: Second box as (x1, y1, x2, y2).

    Returns:
        IoU value in range [0, 1]. Returns 0 for non-overlapping/invalid boxes.
    """
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b

    # Compute intersection
    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)

    iw = ix2 - ix1
    ih = iy2 - iy1

    # No intersection
    if iw <= 0.0 or ih <= 0.0:
        return 0.0

    inter = iw * ih

    # Compute areas
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)

    union = area_a + area_b - inter
    if union <= 0.0:
        return 0.0

    return inter / union


def compute_iou_matrix(runtime_obs_list, gt_obs_list):
    """Compute IoU matrix between runtime and GT observations.

    Args:
        runtime_obs_list: List of RuntimeObservation.
        gt_obs_list: List of GTObservation.

    Returns:
        numpy array of shape (len(runtime), len(gt)) with IoU values.
    """
    n_runtime = len(runtime_obs_list)
    n_gt = len(gt_obs_list)

    if n_runtime == 0 or n_gt == 0:
        return np.zeros((n_runtime, n_gt))

    iou_matrix = np.zeros((n_runtime, n_gt), dtype=np.float64)

    for i, r in enumerate(runtime_obs_list):
        for j, g in enumerate(gt_obs_list):
            iou_matrix[i, j] = box_iou_xyxy(r.bbox, g.bbox)

    return iou_matrix


# =============================================================================
# Hungarian Matching (D2: Hungarian one-to-one)
# =============================================================================

def hungarian_matching(iou_matrix, iou_threshold=0.50):
    """Perform Hungarian one-to-one assignment.

    Args:
        iou_matrix: numpy array of shape (n_runtime, n_gt) with IoU values.
        iou_threshold: Minimum IoU to retain a match (default 0.50 per D1).

    Returns:
        List of tuples: (runtime_index, gt_index, iou_value) for matched pairs.
        Only includes matches with IoU >= iou_threshold.
    """
    n_runtime, n_gt = iou_matrix.shape

    if n_runtime == 0 or n_gt == 0:
        return []

    # Hungarian algorithm finds the optimal one-to-one assignment
    # We use negative IoU because scipy.optimize.linear_sum_assignment minimizes
    # Cost matrix must be square, so we pad if necessary
    max_dim = max(n_runtime, n_gt)

    # Create cost matrix: 1 - IoU so that higher IoU = lower cost
    # Pad with zeros (max IoU = 0, cost = 1) for extra rows/cols
    cost_matrix = np.ones((max_dim, max_dim), dtype=np.float64)
    cost_matrix[:n_runtime, :n_gt] = 1.0 - iou_matrix

    # Hungarian assignment
    row_ind, col_ind = linear_sum_assignment(cost_matrix)

    # Extract valid matches
    matches = []
    for r_idx, g_idx in zip(row_ind[:n_runtime], col_ind[:n_gt]):
        if r_idx < n_runtime and g_idx < n_gt:
            iou_value = iou_matrix[r_idx, g_idx]
            if iou_value >= iou_threshold:
                matches.append((r_idx, g_idx, iou_value))

    return matches


# =============================================================================
# Data Loading
# =============================================================================

def load_runtime_observations(trajectory_path="outputs/trajectory.json"):
    """Load runtime observations from trajectory.json.

    Args:
        trajectory_path: Path to trajectory.json.

    Returns:
        Dictionary mapping (frame_id, timestamp) -> list of RuntimeObservation.
    """
    with open(trajectory_path, "r") as f:
        data = json.load(f)

    observations_by_frame = {}

    for trajectory in data.get("trajectories", []):
        track_id = trajectory["track_id"]
        start_frame = trajectory["start_frame"]
        start_timestamp = trajectory["start_timestamp"]

        for obs in trajectory.get("observations", []):
            frame_id = obs["frame_id"]
            timestamp = obs["timestamp"]
            bbox = tuple(obs["bbox"])
            class_id = obs["class"]
            confidence = obs["confidence"]
            cx = obs["cx"]
            cy = obs["cy"]
            global_id = obs.get("global_id", "")

            runtime_obs = RuntimeObservation(
                track_id=track_id,
                frame_id=frame_id,
                timestamp=timestamp,
                global_id=global_id,
                bbox=bbox,
                class_id=class_id,
                confidence=confidence,
                cx=cx,
                cy=cy,
            )

            key = (frame_id, timestamp)
            if key not in observations_by_frame:
                observations_by_frame[key] = []
            observations_by_frame[key].append(runtime_obs)

    return observations_by_frame


def load_gt_observations(gt_path="annotation/data/tracking_ground_truth.json"):
    """Load GT observations from tracking_ground_truth.json.

    Args:
        gt_path: Path to tracking_ground_truth.json.

    Returns:
        Dictionary mapping frame_id -> list of GTObservation.
    """
    with open(gt_path, "r") as f:
        gt_data = json.load(f)

    observations_by_frame = {}

    for gt_object in gt_data:
        global_id = gt_object["global_id"]
        class_name = gt_object["class"]

        for frame_data in gt_object.get("frames", []):
            frame_id = frame_data["frame_id"]
            timestamp = frame_data["timestamp"]
            bbox = tuple(frame_data["bbox"])
            center = tuple(frame_data["center"])
            visibility = frame_data.get("visibility", 1.0)
            occlusion = frame_data.get("occlusion", 0)

            gt_obs = GTObservation(
                global_id=global_id,
                frame_id=frame_id,
                timestamp=timestamp,
                bbox=bbox,
                center=center,
                class_name=class_name,
                visibility=visibility,
                occlusion=occlusion,
            )

            if frame_id not in observations_by_frame:
                observations_by_frame[frame_id] = []
            observations_by_frame[frame_id].append(gt_obs)

    return observations_by_frame


# =============================================================================
# Temporal Alignment (D7: timestamp-based)
# =============================================================================

def align_runtime_to_gt_by_timestamp(runtime_by_frame, gt_by_frame):
    """Align runtime observations to GT by timestamp.

    D7 Rule: timestamp-based temporal alignment.
    - Runtime frame N corresponds temporally to GT frame N-1
    - Runtime starts at frame 1
    - GT starts at frame 0

    The correspondence is established by frame position:
    - Runtime frame 1 → GT frame 0
    - Runtime frame 2 → GT frame 1
    - etc.

    Args:
        runtime_by_frame: Dict mapping (frame_id, timestamp) -> list of RuntimeObservation.
        gt_by_frame: Dict mapping frame_id -> list of GTObservation.

    Returns:
        Dictionary mapping (runtime_frame_id, gt_frame_id) -> (runtime_obs, gt_obs) lists.
    """
    aligned = {}

    # D7: Runtime frame N corresponds to GT frame N-1
    # This is a positional mapping based on frame index
    for (runtime_frame_id, runtime_timestamp), runtime_obs_list in runtime_by_frame.items():
        # Calculate the corresponding GT frame (D7: N → N-1)
        gt_frame_id = runtime_frame_id - 1

        # Get GT observations for this frame
        if gt_frame_id in gt_by_frame:
            gt_obs_list = gt_by_frame[gt_frame_id]
            key = (runtime_frame_id, gt_frame_id)
            aligned[key] = (runtime_obs_list, gt_obs_list)

    return aligned


# =============================================================================
# Frame-Level Matching
# =============================================================================

def match_frame(runtime_obs_list, gt_obs_list, iou_threshold=0.50):
    """Match runtime observations to GT observations in a single frame.

    Uses Hungarian one-to-one assignment (D2) with IoU threshold (D1: 0.50).

    Args:
        runtime_obs_list: List of RuntimeObservation.
        gt_obs_list: List of GTObservation.
        iou_threshold: Minimum IoU for valid match (default 0.50).

    Returns:
        List of MatchedPair for successfully matched observations.
    """
    if not runtime_obs_list or not gt_obs_list:
        return []

    # Compute IoU matrix
    iou_matrix = compute_iou_matrix(runtime_obs_list, gt_obs_list)

    # Hungarian matching
    matches = hungarian_matching(iou_matrix, iou_threshold)

    # Build matched pairs
    matched_pairs = []
    for r_idx, g_idx, iou_value in matches:
        matched_pairs.append(MatchedPair(
            runtime_obs=runtime_obs_list[r_idx],
            gt_obs=gt_obs_list[g_idx],
            iou=iou_value,
        ))

    return matched_pairs


def evaluate_all_frames(
    trajectory_path="outputs/trajectory.json",
    gt_path="annotation/data/tracking_ground_truth.json",
    iou_threshold=0.50
):
    """Evaluate all frames: load, align, and match.

    Args:
        trajectory_path: Path to trajectory.json.
        gt_path: Path to tracking_ground_truth.json.
        iou_threshold: IoU threshold (default 0.50 per D1).

    Returns:
        Dictionary with:
          - aligned_frames: Dict of (runtime_frame_id, gt_frame_id) -> matched pairs
          - statistics: Dict of evaluation statistics
    """
    # Load data
    runtime_by_frame = load_runtime_observations(trajectory_path)
    gt_by_frame = load_gt_observations(gt_path)

    # Align by timestamp
    aligned = align_runtime_to_gt_by_timestamp(runtime_by_frame, gt_by_frame)

    # Match each aligned frame
    frame_results = {}
    total_runtime_obs = 0
    total_gt_obs = 0
    total_matches = 0

    for (runtime_frame_id, gt_frame_id), (runtime_obs_list, gt_obs_list) in aligned.items():
        matched_pairs = match_frame(runtime_obs_list, gt_obs_list, iou_threshold)

        frame_results[(runtime_frame_id, gt_frame_id)] = {
            "runtime_count": len(runtime_obs_list),
            "gt_count": len(gt_obs_list),
            "matched_count": len(matched_pairs),
            "matches": matched_pairs,
        }

        total_runtime_obs += len(runtime_obs_list)
        total_gt_obs += len(gt_obs_list)
        total_matches += len(matched_pairs)

    statistics = {
        "total_runtime_observations": total_runtime_obs,
        "total_gt_observations": total_gt_obs,
        "total_matched_pairs": total_matches,
        "iou_threshold": iou_threshold,
        "matching_method": "hungarian_one_to_one",
    }

    return {
        "aligned_frames": frame_results,
        "statistics": statistics,
    }


# =============================================================================
# Utility Functions
# =============================================================================

def get_frame_matches(results, runtime_frame_id):
    """Get matches for a specific runtime frame.

    Args:
        results: Return value from evaluate_all_frames.
        runtime_frame_id: The runtime frame_id to query.

    Returns:
        List of MatchedPair or empty list if frame not found.
    """
    for (r_frame, g_frame), data in results["aligned_frames"].items():
        if r_frame == runtime_frame_id:
            return data["matches"]
    return []


def get_all_global_ids_in_frame(results, runtime_frame_id):
    """Get all unique global_ids present in a runtime frame.

    Args:
        results: Return value from evaluate_all_frames.
        runtime_frame_id: The runtime frame_id to query.

    Returns:
        Set of global_id strings.
    """
    global_ids = set()
    matches = get_frame_matches(results, runtime_frame_id)
    for pair in matches:
        global_ids.add(pair.runtime_obs.global_id)
    return global_ids


# =============================================================================
# Temporal Consistency Metrics (GI-08.9)
# =============================================================================

def load_global_identity_registry(gi_path="outputs/global_identity.json"):
    """Load runtime global identity registry from global_identity.json.

    Args:
        gi_path: Path to global_identity.json.

    Returns:
        Dictionary mapping global_id -> {"provisional": bool, "track_ids": [int]}.
    """
    with open(gi_path, "r") as f:
        data = json.load(f)

    registry = {}
    for identity in data.get("global_identities", []):
        gid = identity["global_id"]
        track_ids = [seg["track_id"] for seg in identity.get("track_segments", [])]
        registry[gid] = {
            "provisional": identity.get("provisional", False),
            "track_ids": track_ids,
        }

    return registry


def build_matched_observations(results):
    """Build a list of all matched observations with their identities.

    Args:
        results: Return value from evaluate_all_frames.

    Returns:
        List of dicts with: runtime_global_id, gt_global_id, track_id, class_name, is_provisional.
    """
    matched_obs = []

    for (runtime_frame_id, gt_frame_id), data in results["aligned_frames"].items():
        for pair in data["matches"]:
            runtime_obs = pair.runtime_obs
            gt_obs = pair.gt_obs

            matched_obs.append({
                "runtime_global_id": runtime_obs.global_id,
                "gt_global_id": gt_obs.global_id,
                "track_id": runtime_obs.track_id,
                "class_name": gt_obs.class_name,
                "runtime_frame_id": runtime_frame_id,
                "gt_frame_id": gt_frame_id,
            })

    return matched_obs


def evaluate_id_preserved_score(matched_observations, global_registry):
    """Evaluate ID Preserved Score - consistency of runtime global_id with matched GT.

    For each runtime global_id, determine the dominant GT identity and count
    observations consistent with that identity.

    Args:
        matched_observations: List from build_matched_observations.
        global_registry: Dict from load_global_identity_registry.

    Returns:
        Dict with id_preserved_score and detailed counts.
    """
    if not matched_observations:
        return {
            "id_preserved_score": None,
            "total_matched_observations": 0,
            "total_consistent_observations": 0,
            "details": {},
        }

    # Group by runtime global_id
    by_runtime_id = defaultdict(list)
    for obs in matched_observations:
        by_runtime_id[obs["runtime_global_id"]].append(obs)

    # For each runtime global_id, find dominant GT identity
    consistent_count = 0
    details = {}

    for runtime_gid, obs_list in by_runtime_id.items():
        # Count GT identities for this runtime global_id
        gt_counts = defaultdict(int)
        for obs in obs_list:
            gt_counts[obs["gt_global_id"]] += 1

        # Find dominant GT identity
        if gt_counts:
            dominant_gt = max(gt_counts.keys(), key=lambda g: gt_counts[g])
            dominant_count = gt_counts[dominant_gt]
            is_consistent = dominant_count == len(obs_list)

            # Count observations consistent with dominant identity
            consistent_count += dominant_count

            details[runtime_gid] = {
                "dominant_gt_id": dominant_gt,
                "total_observations": len(obs_list),
                "consistent_observations": dominant_count,
                "is_consistent": is_consistent,
                "gt_distribution": dict(gt_counts),
            }

    total_matched = len(matched_observations)
    score = consistent_count / total_matched if total_matched > 0 else None

    return {
        "id_preserved_score": score,
        "total_matched_observations": total_matched,
        "total_consistent_observations": consistent_count,
        "details": details,
    }


def evaluate_global_identity_fragmentation(matched_observations):
    """Evaluate Global Identity Fragmentation - one GT represented by multiple runtime IDs.

    For each GT identity, collect all distinct runtime global_ids that match it.

    Args:
        matched_observations: List from build_matched_observations.

    Returns:
        Dict with fragmentation_count, fragmented_gt_identities, and details.
    """
    if not matched_observations:
        return {
            "fragmentation_count": 0,
            "fragmented_gt_identities": [],
            "total_gt_identities": 0,
            "details": {},
        }

    # Group by GT identity
    by_gt_id = defaultdict(set)
    for obs in matched_observations:
        by_gt_id[obs["gt_global_id"]].add(obs["runtime_global_id"])

    # Find fragmented GT identities (more than one runtime global_id)
    fragmented = []
    details = {}

    for gt_gid, runtime_gids in by_gt_id.items():
        num_runtime_ids = len(runtime_gids)
        details[gt_gid] = {
            "runtime_global_ids": sorted(runtime_gids),
            "count": num_runtime_ids,
        }
        if num_runtime_ids > 1:
            fragmented.append(gt_gid)

    return {
        "fragmentation_count": len(fragmented),
        "fragmented_gt_identities": sorted(fragmented),
        "total_gt_identities": len(by_gt_id),
        "details": details,
    }


def evaluate_global_identity_merge(matched_observations):
    """Evaluate Global Identity Merge - one runtime ID matched to multiple GT identities.

    For each runtime global_id, collect all distinct GT identities matched to it.

    Args:
        matched_observations: List from build_matched_observations.

    Returns:
        Dict with merge_count, merged_runtime_identities, and details.
    """
    if not matched_observations:
        return {
            "merge_count": 0,
            "merged_runtime_identities": [],
            "total_runtime_identities": 0,
            "details": {},
        }

    # Group by runtime global_id
    by_runtime_id = defaultdict(set)
    for obs in matched_observations:
        by_runtime_id[obs["runtime_global_id"]].add(obs["gt_global_id"])

    # Find merged runtime identities (more than one GT identity)
    merged = []
    details = {}

    for runtime_gid, gt_ids in by_runtime_id.items():
        num_gt_ids = len(gt_ids)
        details[runtime_gid] = {
            "gt_identities": sorted(gt_ids),
            "count": num_gt_ids,
        }
        if num_gt_ids > 1:
            merged.append(runtime_gid)

    return {
        "merge_count": len(merged),
        "merged_runtime_identities": sorted(merged),
        "total_runtime_identities": len(by_runtime_id),
        "details": details,
    }


def evaluate_provisional_identities(matched_observations, global_registry):
    """Evaluate provisional identity handling.

    Report confirmed vs provisional global IDs separately.
    Do NOT penalize provisional identities - report separately.

    Args:
        matched_observations: List from build_matched_observations.
        global_registry: Dict from load_global_identity_registry.

    Returns:
        Dict with provisional and confirmed counts.
    """
    provisional_gids = set()
    confirmed_gids = set()

    for gid, info in global_registry.items():
        if info["provisional"]:
            provisional_gids.add(gid)
        else:
            confirmed_gids.add(gid)

    # Count matched observations belonging to each type
    provisional_matched = 0
    confirmed_matched = 0
    unmatched_gids = set()

    for obs in matched_observations:
        runtime_gid = obs["runtime_global_id"]
        if runtime_gid in provisional_gids:
            provisional_matched += 1
        elif runtime_gid in confirmed_gids:
            confirmed_matched += 1
        else:
            unmatched_gids.add(runtime_gid)

    return {
        "confirmed_global_ids": sorted(confirmed_gids),
        "provisional_global_ids": sorted(provisional_gids),
        "confirmed_matched_observations": confirmed_matched,
        "provisional_matched_observations": provisional_matched,
        "unmatched_runtime_ids": sorted(unmatched_gids),
    }


def evaluate_per_class(matched_observations):
    """Evaluate metrics per class (D5: car, motorcycle, bus, truck).

    Args:
        matched_observations: List from build_matched_observations.

    Returns:
        Dict with per-class metrics.
    """
    # Define target classes
    target_classes = {"car", "motorcycle", "bus", "truck"}

    # Group by class
    by_class = defaultdict(list)
    for obs in matched_observations:
        class_name = obs.get("class_name", "").lower()
        by_class[class_name].append(obs)

    per_class = {}

    for class_name in target_classes:
        obs_list = by_class.get(class_name, [])

        if not obs_list:
            per_class[class_name] = {
                "total_matched_observations": 0,
                "id_preserved_score": None,
                "note": "No matched observations for this class",
            }
            continue

        # ID preserved score for this class
        by_runtime_id = defaultdict(list)
        for obs in obs_list:
            by_runtime_id[obs["runtime_global_id"]].append(obs)

        consistent = 0
        for runtime_gid, obs_items in by_runtime_id.items():
            gt_counts = defaultdict(int)
            for obs in obs_items:
                gt_counts[obs["gt_global_id"]] += 1
            dominant = max(gt_counts.values()) if gt_counts else 0
            consistent += dominant

        score = consistent / len(obs_list) if obs_list else None

        per_class[class_name] = {
            "total_matched_observations": len(obs_list),
            "id_preserved_score": score,
        }

    return per_class


def evaluate_temporal_consistency(
    trajectory_path="outputs/trajectory.json",
    gt_path="annotation/data/tracking_ground_truth.json",
    gi_path="outputs/global_identity.json",
    iou_threshold=0.50,
):
    """Evaluate temporal consistency metrics.

    This is the main entry point for GI-08.9 evaluation.

    Args:
        trajectory_path: Path to trajectory.json.
        gt_path: Path to tracking_ground_truth.json.
        gi_path: Path to global_identity.json.
        iou_threshold: IoU threshold (default 0.50 per D1).

    Returns:
        Dict with all temporal consistency metrics.
    """
    # Load frame-level matching results (GI-08.8)
    results = evaluate_all_frames(
        trajectory_path=trajectory_path,
        gt_path=gt_path,
        iou_threshold=iou_threshold,
    )

    # Build matched observations list
    matched_observations = build_matched_observations(results)

    # Count total runtime observations
    total_runtime_obs = results["statistics"]["total_runtime_observations"]
    total_matched = len(matched_observations)
    total_unmatched = total_runtime_obs - total_matched

    # Load global identity registry
    global_registry = load_global_identity_registry(gi_path)

    # Compute metrics
    id_preserved = evaluate_id_preserved_score(matched_observations, global_registry)
    fragmentation = evaluate_global_identity_fragmentation(matched_observations)
    merge = evaluate_global_identity_merge(matched_observations)
    provisional = evaluate_provisional_identities(matched_observations, global_registry)
    per_class = evaluate_per_class(matched_observations)

    # Build aggregate summary
    aggregate = {
        "total_runtime_observations": total_runtime_obs,
        "total_matched_observations": total_matched,
        "total_unmatched_runtime_observations": total_unmatched,
        "id_preserved_score": id_preserved["id_preserved_score"],
        "fragmentation_count": fragmentation["fragmentation_count"],
        "merge_count": merge["merge_count"],
        "iou_threshold": iou_threshold,
        "matching_method": "hungarian_one_to_one",
    }

    return {
        "aggregate_summary": aggregate,
        "id_preserved_details": id_preserved,
        "fragmentation_summary": fragmentation,
        "merge_summary": merge,
        "provisional_summary": provisional,
        "per_class_summary": per_class,
        "frame_matching_statistics": results["statistics"],
    }


# =============================================================================
# GI-08.10: GT-Validated Identity ID Switch Detection
# =============================================================================

def build_gt_temporal_sequence(results, gt_by_frame):
    """Build temporal sequence of matched observations for each GT identity.

    Args:
        results: Return value from evaluate_all_frames.
        gt_by_frame: Dict from load_gt_observations.

    Returns:
        Dict mapping gt_global_id -> list of observations in timestamp order.
        Each observation contains: timestamp, runtime_frame_id, gt_frame_id,
        runtime_global_id, track_id, class_name, iou.
    """
    gt_sequence = defaultdict(list)

    for (runtime_frame_id, gt_frame_id), data in results["aligned_frames"].items():
        for pair in data["matches"]:
            runtime_obs = pair.runtime_obs
            gt_obs = pair.gt_obs

            # Get timestamp from GT (more reliable)
            gt_obs_for_frame = gt_by_frame.get(gt_frame_id, [])
            timestamp = None
            for g in gt_obs_for_frame:
                if g.global_id == gt_obs.global_id:
                    timestamp = g.timestamp
                    break

            if timestamp is None:
                timestamp = runtime_obs.timestamp

            gt_sequence[gt_obs.global_id].append({
                "timestamp": timestamp,
                "runtime_frame_id": runtime_frame_id,
                "gt_frame_id": gt_frame_id,
                "runtime_global_id": runtime_obs.global_id,
                "track_id": runtime_obs.track_id,
                "class_name": gt_obs.class_name,
                "iou": pair.iou,
                "gt_visibility": gt_obs.visibility,
                "gt_occlusion": gt_obs.occlusion,
            })

    # Sort each GT sequence by timestamp
    for gt_id in gt_sequence:
        gt_sequence[gt_id].sort(key=lambda x: x["timestamp"])

    return dict(gt_sequence)


def check_gt_continuity(gt_id, start_time, end_time, gt_by_frame):
    """Check if GT identity remains continuously valid across an interval.

    D8 Rule: GT-validated continuity.
    A switch is confirmed only if GT evidence shows the identity remained
    continuously valid/visible through the interval.

    Args:
        gt_id: The GT identity to check.
        start_time: Start timestamp of the interval.
        end_time: End timestamp of the interval.
        gt_by_frame: Dict from load_gt_observations (raw GT data).
            Can contain either GTObservation objects or dicts.

    Returns:
        Dict with:
            - is_continuous: bool
            - has_gt_coverage: bool (GT has observations in interval)
            - visibility_gaps: list of intervals with missing GT
            - evidence: details about GT coverage
    """
    # Collect all GT observations for this identity from raw GT data
    gt_observations = []
    for frame_id, obs_list in gt_by_frame.items():
        for obs in obs_list:
            # Handle both GTObservation objects and dicts
            if hasattr(obs, 'global_id'):
                obs_global_id = obs.global_id
                obs_timestamp = obs.timestamp
                obs_visibility = obs.visibility
                obs_occlusion = obs.occlusion
            else:
                obs_global_id = obs.get("global_id")
                obs_timestamp = obs.get("timestamp")
                obs_visibility = obs.get("visibility", 1.0)
                obs_occlusion = obs.get("occlusion", 0)

            if obs_global_id == gt_id:
                gt_observations.append({
                    "timestamp": obs_timestamp,
                    "frame_id": frame_id,
                    "visibility": obs_visibility,
                    "occlusion": obs_occlusion,
                })

    if not gt_observations:
        return {
            "is_continuous": False,
            "has_gt_coverage": False,
            "visibility_gaps": [(start_time, end_time)],
            "evidence": "No GT observations found for this identity",
        }

    # Check if there are GT observations before and after the interval
    # Use <= and >= so boundary observations are included
    before_obs = [o for o in gt_observations if o["timestamp"] <= start_time]
    after_obs = [o for o in gt_observations if o["timestamp"] >= end_time]

    if not before_obs or not after_obs:
        # No GT observations on both sides of the interval
        return {
            "is_continuous": False,
            "has_gt_coverage": False,
            "visibility_gaps": [(start_time, end_time)],
            "evidence": "GT identity not observed on both sides of interval",
        }

    # Check GT coverage throughout the interval
    # A GT identity is continuous if it appears in GT frames reasonably close
    # to both the start and end of the runtime gap

    # Find GT observations closest to start and end of interval
    closest_before = max(before_obs, key=lambda o: o["timestamp"])
    closest_after = min(after_obs, key=lambda o: o["timestamp"])

    # Check if there's any GT observation that bridges the gap
    # If GT shows the object existed continuously, we consider it continuous

    # For D8: we need GT evidence that the identity was valid through the interval
    # Look for GT observations strictly between start_time and end_time (not at boundaries)
    interval_gt_obs = [o for o in gt_observations if start_time < o["timestamp"] < end_time]

    has_full_coverage = len(interval_gt_obs) > 0

    # Also check if the closest observations are "close enough" to suggest continuity
    # The gap between last before and first after should be bridged by GT
    time_gap = end_time - start_time
    last_before_time = closest_before["timestamp"]
    first_after_time = closest_after["timestamp"]

    # GT coverage: is there GT evidence of continuity?
    # We need GT observations IN the interval to confirm continuity
    # A large gap between GT observations indicates the identity may have disappeared

    # If there's a significant time gap in GT observations, continuity is broken
    gt_gap = first_after_time - last_before_time

    # Strict continuity check: require actual GT coverage in the interval
    is_continuous = has_full_coverage

    # Additional info for classification
    has_boundary_coverage = len(before_obs) > 0 and len(after_obs) > 0

    return {
        "is_continuous": is_continuous,
        "has_gt_coverage": has_full_coverage,  # GT in interval
        "has_boundary_coverage": has_boundary_coverage,  # GT at both boundaries
        "visibility_gaps": [] if is_continuous else [(start_time, end_time)],
        "evidence": {
            "interval_gt_obs_count": len(interval_gt_obs),
            "last_before_time": last_before_time,
            "first_after_time": first_after_time,
            "gt_gap": gt_gap,
            "time_gap": time_gap,
        },
    }


def detect_candidate_id_switches(gt_sequence):
    """Detect candidate global_id changes for each GT identity.

    A candidate switch is when the runtime global_id changes for the same GT.

    Args:
        gt_sequence: Dict from build_gt_temporal_sequence.

    Returns:
        List of candidate switches with details.
    """
    candidates = []

    for gt_id, observations in gt_sequence.items():
        if len(observations) < 2:
            continue

        # Look for global_id changes
        for i in range(len(observations) - 1):
            curr = observations[i]
            next_obs = observations[i + 1]

            if curr["runtime_global_id"] != next_obs["runtime_global_id"]:
                candidate = {
                    "gt_identity": gt_id,
                    "previous_global_id": curr["runtime_global_id"],
                    "new_global_id": next_obs["runtime_global_id"],
                    "previous_timestamp": curr["timestamp"],
                    "new_timestamp": next_obs["timestamp"],
                    "previous_runtime_frame": curr["runtime_frame_id"],
                    "new_runtime_frame": next_obs["runtime_frame_id"],
                    "previous_track_id": curr["track_id"],
                    "new_track_id": next_obs["track_id"],
                    "previous_iou": curr["iou"],
                    "new_iou": next_obs["iou"],
                    "class_name": curr.get("class_name"),
                }
                candidates.append(candidate)

    return candidates


def validate_gt_continuity_for_candidates(
    candidates,
    gt_sequence,
    gt_by_frame,
):
    """Validate each candidate switch with GT continuity check (D8).

    Args:
        candidates: List from detect_candidate_id_switches.
        gt_sequence: Dict from build_gt_temporal_sequence.
        gt_by_frame: Dict from load_gt_observations.

    Returns:
        List of validated switches with classification.
    """
    validated = []

    for candidate in candidates:
        gt_id = candidate["gt_identity"]
        start_time = candidate["previous_timestamp"]
        end_time = candidate["new_timestamp"]

        # Check GT continuity
        continuity = check_gt_continuity(
            gt_id, start_time, end_time, gt_by_frame
        )

        result = candidate.copy()
        result["gt_continuity"] = continuity

        # Classify the candidate
        # D8 Rule: Distinguish between confirmed switches and unresolved cases
        if continuity["has_gt_coverage"] and continuity["is_continuous"]:
            # GT has observations in the interval and confirms continuity
            result["classification"] = "CONFIRMED_GI_ID_SWITCH"
            result["classification_reason"] = "GT evidence confirms continuous identity across interval"
        elif continuity.get("has_boundary_coverage", False):
            # GT has observations at boundaries but not in the interval
            # This is insufficient to confirm continuity
            result["classification"] = "INSUFFICIENT_GT_EVIDENCE"
            result["classification_reason"] = "GT identity not continuous across interval - only boundary coverage"
        else:
            # No GT coverage at boundaries - runtime disappeared but GT cannot validate
            result["classification"] = "UPSTREAM_GAP_OR_UNRESOLVED"
            result["classification_reason"] = "GT evidence insufficient to validate continuity - no boundary coverage"

        validated.append(result)

    return validated


def evaluate_global_identity_id_switches(
    trajectory_path="outputs/trajectory.json",
    gt_path="annotation/data/tracking_ground_truth.json",
    gi_path="outputs/global_identity.json",
    iou_threshold=0.50,
):
    """Evaluate Global Identity ID switches using GT-validated continuity (D8).

    This is the main entry point for GI-08.10 evaluation.

    Args:
        trajectory_path: Path to trajectory.json.
        gt_path: Path to tracking_ground_truth.json.
        gi_path: Path to global_identity.json.
        iou_threshold: IoU threshold (default 0.50 per D1).

    Returns:
        Dict with all ID switch analysis results.
    """
    # Load frame-level matching results (GI-08.8)
    results = evaluate_all_frames(
        trajectory_path=trajectory_path,
        gt_path=gt_path,
        iou_threshold=iou_threshold,
    )

    # Load GT observations for continuity checking
    gt_by_frame = load_gt_observations(gt_path)

    # Build temporal sequence for each GT identity
    gt_sequence = build_gt_temporal_sequence(results, gt_by_frame)

    # Detect candidate global_id changes
    candidates = detect_candidate_id_switches(gt_sequence)

    # Validate with GT continuity (D8)
    validated_switches = validate_gt_continuity_for_candidates(
        candidates, gt_sequence, gt_by_frame
    )

    # Load global registry for provisional checking
    global_registry = load_global_identity_registry(gi_path)

    # Classify results
    confirmed_switches = [s for s in validated_switches if s["classification"] == "CONFIRMED_GI_ID_SWITCH"]
    upstream_gap = [s for s in validated_switches if s["classification"] == "UPSTREAM_GAP_OR_UNRESOLVED"]
    insufficient_gt = [s for s in validated_switches if s["classification"] == "INSUFFICIENT_GT_EVIDENCE"]

    # Collect statistics
    affected_gt_ids = set(s["gt_identity"] for s in validated_switches)
    affected_global_ids = set()
    for s in validated_switches:
        affected_global_ids.add(s["previous_global_id"])
        affected_global_ids.add(s["new_global_id"])

    # Check provisional involvement
    provisional_involvement = 0
    provisional_details = []
    for switch in validated_switches:
        prev_prov = global_registry.get(switch["previous_global_id"], {}).get("provisional", False)
        new_prov = global_registry.get(switch["new_global_id"], {}).get("provisional", False)
        if prev_prov or new_prov:
            provisional_involvement += 1
            provisional_details.append({
                "gt_identity": switch["gt_identity"],
                "previous_global_id": switch["previous_global_id"],
                "new_global_id": switch["new_global_id"],
                "previous_provisional": prev_prov,
                "new_provisional": new_prov,
            })

    # Per-class analysis
    per_class = {}
    target_classes = {"car", "motorcycle", "bus", "truck"}

    for class_name in target_classes:
        class_switches = [s for s in validated_switches if s.get("class_name") == class_name]
        class_confirmed = [s for s in class_switches if s["classification"] == "CONFIRMED_GI_ID_SWITCH"]

        per_class[class_name] = {
            "candidate_transitions": len(class_switches),
            "confirmed_switches": len(class_confirmed),
            "upstream_gap_or_unresolved": len([s for s in class_switches if s["classification"] == "UPSTREAM_GAP_OR_UNRESOLVED"]),
            "insufficient_gt_evidence": len([s for s in class_switches if s["classification"] == "INSUFFICIENT_GT_EVIDENCE"]),
        }

    # Build aggregate summary
    aggregate = {
        "total_gt_identities_analyzed": len(gt_sequence),
        "candidate_transitions": len(candidates),
        "confirmed_gi_id_switches": len(confirmed_switches),
        "upstream_gap_or_unresolved": len(upstream_gap),
        "insufficient_gt_evidence": len(insufficient_gt),
        "affected_gt_identities": len(affected_gt_ids),
        "affected_global_ids": len(affected_global_ids),
        "provisional_involvement": provisional_involvement,
        "iou_threshold": iou_threshold,
        "matching_method": "hungarian_one_to_one",
        "d8_method": "gt_validated_continuity",
    }

    return {
        "aggregate_summary": aggregate,
        "candidate_transitions": candidates,
        "validated_switches": validated_switches,
        "confirmed_gi_id_switches": confirmed_switches,
        "upstream_gap_or_unresolved": upstream_gap,
        "insufficient_gt_evidence": insufficient_gt,
        "affected_gt_identities": sorted(affected_gt_ids),
        "affected_global_ids": sorted(affected_global_ids),
        "provisional_involvement": provisional_involvement,
        "provisional_details": provisional_details,
        "per_class_summary": per_class,
        "evidence_records": validated_switches,
    }

"""Minimal Global Identity layer for the project.

This module intentionally keeps tracker-local identity and project-global identity
separate. It does not infer identity associations and does not rewrite tracking
observation data.
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, Optional


@dataclass(frozen=True)
class RuntimeTrackingObservation:
    """Deterministic representation of a runtime tracking observation.

    This is the observation interface between Multi-Object Tracking and Global Identity.
    It preserves the ByteTrack output semantics without modification.

    Fields:
        track_id: ByteTrack-assigned runtime identity (tracker-local, per video run)
        frame_id: Frame index (0-based)
        timestamp: Frame timestamp in seconds
        bbox: Bounding box [x1, y1, x2, y2] in 1020x500 space
        class_name: Object class (car, motorcycle, bus, truck, etc.)
        confidence: Detection confidence
        cx: Center x coordinate = (x1 + x2) / 2
        cy: Center y coordinate = (y1 + y2) / 2
    """

    track_id: int
    frame_id: int
    timestamp: float
    bbox: tuple[int, int, int, int]
    class_name: str
    confidence: float
    cx: float
    cy: float

    def __post_init__(self) -> None:
        if not isinstance(self.track_id, int) or self.track_id < 0:
            raise ValueError(f"track_id must be a non-negative integer, got {self.track_id}")
        if not isinstance(self.frame_id, int) or self.frame_id < 0:
            raise ValueError(f"frame_id must be a non-negative integer, got {self.frame_id}")
        if not isinstance(self.timestamp, (int, float)) or self.timestamp < 0:
            raise ValueError(f"timestamp must be non-negative, got {self.timestamp}")
        if not isinstance(self.bbox, (tuple, list)) or len(self.bbox) != 4:
            raise ValueError(f"bbox must be a 4-element tuple/list, got {self.bbox}")
        if not isinstance(self.class_name, str):
            raise ValueError(f"class_name must be a string, got {self.class_name}")
        if not isinstance(self.confidence, (int, float)) or not (0.0 <= self.confidence <= 1.0):
            raise ValueError(f"confidence must be between 0.0 and 1.0, got {self.confidence}")
        if not isinstance(self.cx, (int, float)):
            raise ValueError(f"cx must be a number, got {self.cx}")
        if not isinstance(self.cy, (int, float)):
            raise ValueError(f"cy must be a number, got {self.cy}")

    @classmethod
    def from_dict(cls, data: dict) -> "RuntimeTrackingObservation":
        """Construct observation from a dictionary (e.g., from main.py tracking observations)."""
        return cls(
            track_id=int(data["track_id"]),
            frame_id=int(data["frame_id"]),
            timestamp=float(data["timestamp"]),
            bbox=tuple(data["bbox"]),
            class_name=str(data["class"]),
            confidence=float(data["confidence"]),
            cx=float(data["cx"]),
            cy=float(data["cy"]),
        )

    def to_dict(self) -> dict:
        """Convert observation to dictionary for compatibility with existing trajectory code."""
        return {
            "track_id": self.track_id,
            "frame_id": self.frame_id,
            "timestamp": self.timestamp,
            "bbox": list(self.bbox),
            "class": self.class_name,
            "confidence": self.confidence,
            "cx": self.cx,
            "cy": self.cy,
        }


def _compute_center(bbox: tuple) -> tuple[float, float]:
    """Compute center coordinates from bounding box."""
    x1, y1, x2, y2 = bbox
    return ((x1 + x2) / 2.0, (y1 + y2) / 2.0)


def observation_from_bytetrack(
    bytetrack_data: dict,
    class_mapping: Optional[dict[int, str]] = None,
) -> RuntimeTrackingObservation:
    """Convert ByteTrack output to RuntimeTrackingObservation.

    This is the runtime integration seam that bridges ByteTrack output to Global Identity.

    ByteTrack output format:
        {
            "track_id": int,
            "frame_id": int,
            "timestamp": float,
            "bbox": [x1, y1, x2, y2],
            "class": int,  # class ID (not class name)
            "confidence": float,
            "cx": float,  # optional, computed from bbox if not present
            "cy": float,  # optional, computed from bbox if not present
        }

    Args:
        bytetrack_data: ByteTrack observation dictionary
        class_mapping: Optional mapping from class ID (int) to class name (str).
            If not provided, class is converted to string directly.

    Returns:
        RuntimeTrackingObservation with preserved track_id, frame_id, bbox, class, confidence
    """
    track_id = int(bytetrack_data["track_id"])
    frame_id = int(bytetrack_data["frame_id"])
    timestamp = float(bytetrack_data["timestamp"])
    bbox = tuple(bytetrack_data["bbox"])
    class_id = bytetrack_data["class"]
    confidence = float(bytetrack_data["confidence"])

    # Handle class: use mapping if provided, otherwise convert to string
    if class_mapping is not None:
        class_name = class_mapping.get(int(class_id), str(class_id))
    else:
        class_name = str(class_id)

    # Handle center coordinates: use provided or compute from bbox
    if "cx" in bytetrack_data and "cy" in bytetrack_data:
        cx = float(bytetrack_data["cx"])
        cy = float(bytetrack_data["cy"])
    else:
        cx, cy = _compute_center(bbox)

    return RuntimeTrackingObservation(
        track_id=track_id,
        frame_id=frame_id,
        timestamp=timestamp,
        bbox=bbox,
        class_name=class_name,
        confidence=confidence,
        cx=cx,
        cy=cy,
    )


def build_track_segments_from_observations(
    observations: list[RuntimeTrackingObservation],
) -> list[RuntimeTrackSegment]:
    """Build RuntimeTrackSegments from a list of RuntimeTrackingObservations.

    Observations are grouped by track_id to form contiguous track segments.

    Args:
        observations: List of RuntimeTrackingObservation in any order

    Returns:
        List of RuntimeTrackSegment, one per unique track_id
    """
    from collections import defaultdict

    # Group observations by track_id
    by_track_id: dict[int, list[RuntimeTrackingObservation]] = defaultdict(list)
    for obs in observations:
        by_track_id[obs.track_id].append(obs)

    # Create segments with sorted observations
    segments = []
    for track_id, obs_list in by_track_id.items():
        segment = RuntimeTrackSegment(track_id=track_id)
        # Sort by frame_id for deterministic order
        for obs in sorted(obs_list, key=lambda o: o.frame_id):
            segment.add_observation(obs)
        segments.append(segment)

    # Sort segments by track_id for deterministic output
    return sorted(segments, key=lambda s: s.track_id)


@dataclass
class RuntimeTrackSegment:
    """A contiguous sequence of observations from a single ByteTrack track_id.

    This represents all observations belonging to the same tracker-local track_id.
    Global Identity associates multiple track segments into persistent runtime identities.
    """

    track_id: int
    observations: list[RuntimeTrackingObservation] = field(default_factory=list)

    @property
    def start_frame(self) -> int:
        """First frame in this segment."""
        if not self.observations:
            raise ValueError("Cannot get start_frame of empty track segment")
        return min(obs.frame_id for obs in self.observations)

    @property
    def end_frame(self) -> int:
        """Last frame in this segment."""
        if not self.observations:
            raise ValueError("Cannot get end_frame of empty track segment")
        return max(obs.frame_id for obs in self.observations)

    @property
    def start_timestamp(self) -> float:
        """Timestamp of first frame in this segment."""
        if not self.observations:
            raise ValueError("Cannot get start_timestamp of empty track segment")
        return min(obs.timestamp for obs in self.observations)

    @property
    def end_timestamp(self) -> float:
        """Timestamp of last frame in this segment."""
        if not self.observations:
            raise ValueError("Cannot get end_timestamp of empty track segment")
        return max(obs.timestamp for obs in self.observations)

    @property
    def class_name(self) -> str:
        """Class of all observations in this segment (must be consistent)."""
        if not self.observations:
            raise ValueError("Cannot get class_name of empty track segment")
        classes = set(obs.class_name for obs in self.observations)
        if len(classes) != 1:
            raise ValueError(f"Inconsistent class names in track segment: {classes}")
        return next(iter(classes))

    @property
    def center_at_start(self) -> tuple[float, float]:
        """Center coordinates at the start of the segment."""
        if not self.observations:
            raise ValueError("Cannot get center_at_start of empty track segment")
        sorted_obs = sorted(self.observations, key=lambda o: o.frame_id)
        return (sorted_obs[0].cx, sorted_obs[0].cy)

    @property
    def center_at_end(self) -> tuple[float, float]:
        """Center coordinates at the end of the segment."""
        if not self.observations:
            raise ValueError("Cannot get center_at_end of empty track segment")
        sorted_obs = sorted(self.observations, key=lambda o: o.frame_id)
        return (sorted_obs[-1].cx, sorted_obs[-1].cy)

    def add_observation(self, observation: RuntimeTrackingObservation) -> None:
        """Add an observation to this track segment."""
        if not isinstance(observation, RuntimeTrackingObservation):
            raise TypeError(f"Expected RuntimeTrackingObservation, got {type(observation).__name__}")
        if observation.track_id != self.track_id:
            raise ValueError(
                f"Observation track_id {observation.track_id} does not match segment track_id {self.track_id}"
            )
        self.observations.append(observation)

    def temporal_gap_to(self, other: "RuntimeTrackSegment") -> int:
        """Calculate frame gap between end of this segment and start of another."""
        return other.start_frame - self.end_frame

    def spatial_distance_to(self, other: "RuntimeTrackSegment") -> float:
        """Calculate center-point distance from end of this segment to start of another."""
        end_x, end_y = self.center_at_end
        start_x, start_y = other.center_at_start
        return math.sqrt((start_x - end_x) ** 2 + (start_y - end_y) ** 2)

    def motion_direction(self) -> Optional[tuple[float, float]]:
        """Calculate motion direction vector (dx, dy) from start to end of segment.

        Returns:
            Tuple (dx, dy) representing normalized direction vector, or None if insufficient data.
        """
        if len(self.observations) < 2:
            return None
        sorted_obs = sorted(self.observations, key=lambda o: o.frame_id)
        dx = sorted_obs[-1].cx - sorted_obs[0].cx
        dy = sorted_obs[-1].cy - sorted_obs[0].cy
        # Normalize
        magnitude = (dx ** 2 + dy ** 2) ** 0.5
        if magnitude == 0:
            return (0.0, 0.0)
        return (dx / magnitude, dy / magnitude)

    def motion_speed(self) -> Optional[float]:
        """Calculate average speed (pixels per frame) of the segment.

        Returns:
            Speed in pixels/frame, or None if insufficient data.
        """
        if len(self.observations) < 2:
            return None
        sorted_obs = sorted(self.observations, key=lambda o: o.frame_id)
        dx = sorted_obs[-1].cx - sorted_obs[0].cx
        dy = sorted_obs[-1].cy - sorted_obs[0].cy
        distance = (dx ** 2 + dy ** 2) ** 0.5
        frame_span = sorted_obs[-1].frame_id - sorted_obs[0].frame_id
        if frame_span == 0:
            return 0.0
        return distance / frame_span

GLOBAL_ID_PATTERN = re.compile(r"^GT_\d{3}$")
RUNTIME_GLOBAL_ID_PATTERN = re.compile(r"^G\d{3}$")


def validate_global_id(global_id: str) -> bool:
    """Validate the project's deterministic global ID format (GT_XXX)."""
    return isinstance(global_id, str) and GLOBAL_ID_PATTERN.fullmatch(global_id) is not None


def validate_runtime_global_id(global_id: str) -> bool:
    """Validate runtime global ID format (GXXX)."""
    return isinstance(global_id, str) and RUNTIME_GLOBAL_ID_PATTERN.fullmatch(global_id) is not None


def is_gt_global_id(global_id: str) -> bool:
    """Check if the global_id is a GT identity (GT_XXX format)."""
    return validate_global_id(global_id)


@dataclass
class GlobalIdentityAssociation:
    """Explicit representation of a global identity and its associated track IDs.

    status == "RESOLVED" means there is explicit evidence of the association.
    status == "UNRESOLVED" means a track exists without a trusted global identity.
    """

    global_id: Optional[str] = None
    track_ids: list[int] = field(default_factory=list)
    status: str = "UNRESOLVED"

    def validate(self) -> None:
        if self.status not in {"RESOLVED", "UNRESOLVED"}:
            raise ValueError(f"Unsupported identity state: {self.status}")

        if self.status == "RESOLVED":
            if not self.global_id:
                raise ValueError("Resolved identity requires a global_id")
            if not validate_global_id(self.global_id):
                raise ValueError(f"Invalid global_id format: {self.global_id}")
            if not self.track_ids:
                raise ValueError("Resolved identity requires at least one track_id")
            for track_id in self.track_ids:
                if not isinstance(track_id, int):
                    raise TypeError(f"track_id must be int, got {type(track_id).__name__}")
                if track_id < 0:
                    raise ValueError(f"track_id must be non-negative: {track_id}")
        else:
            if self.global_id is not None:
                raise ValueError("UNRESOLVED identity cannot contain a global_id")
            if self.track_ids:
                for track_id in self.track_ids:
                    if not isinstance(track_id, int):
                        raise TypeError(f"track_id must be int, got {type(track_id).__name__}")
                    if track_id < 0:
                        raise ValueError(f"track_id must be non-negative: {track_id}")

    @classmethod
    def from_resolved(cls, global_id: str, track_ids: Iterable[int]) -> "GlobalIdentityAssociation":
        if not validate_global_id(global_id):
            raise ValueError(f"Invalid global_id format: {global_id}")
        record = cls(global_id=global_id, track_ids=list(track_ids), status="RESOLVED")
        record.validate()
        return record

    @classmethod
    def from_unresolved(cls, track_id: int) -> "GlobalIdentityAssociation":
        record = cls(global_id=None, track_ids=[int(track_id)], status="UNRESOLVED")
        record.validate()
        return record


class GlobalIdentityRegistry:
    """Minimal registry for explicit global identity associations.

    This is intentionally a foundation layer. It does not infer associations from
    trajectory, bbox proximity, or time continuity.
    """

    def __init__(self):
        self._by_global_id: dict[str, GlobalIdentityAssociation] = {}
        self._by_track_id: dict[int, GlobalIdentityAssociation] = {}

    def register_resolved(self, global_id: str, track_ids: Iterable[int]) -> GlobalIdentityAssociation:
        if not validate_global_id(global_id):
            raise ValueError(f"Invalid global_id format: {global_id}")

        if isinstance(track_ids, int):
            raise TypeError("track_ids must be an iterable of ints, not a single int")

        mapping = GlobalIdentityAssociation.from_resolved(global_id, track_ids)
        self._by_global_id[global_id] = mapping

        for track_id in mapping.track_ids:
            self._by_track_id[track_id] = mapping

        return mapping

    def register_unresolved(self, track_id: int) -> GlobalIdentityAssociation:
        mapping = GlobalIdentityAssociation.from_unresolved(track_id)
        self._by_track_id[int(track_id)] = mapping
        return mapping

    def get_by_track_id(self, track_id: int) -> Optional[GlobalIdentityAssociation]:
        return self._by_track_id.get(int(track_id))

    def get_by_global_id(self, global_id: str) -> Optional[GlobalIdentityAssociation]:
        return self._by_global_id.get(global_id)

    def set_track_ids_for_global_id(self, global_id: str, track_ids: Iterable[int]) -> GlobalIdentityAssociation:
        if not validate_global_id(global_id):
            raise ValueError(f"Invalid global_id format: {global_id}")

        track_list = [int(track_id) for track_id in track_ids]
        if not track_list:
            raise ValueError("A resolved global identity requires at least one track_id")

        record = GlobalIdentityAssociation(global_id=global_id, track_ids=track_list, status="RESOLVED")
        record.validate()
        self._by_global_id[global_id] = record

        for track_id in track_list:
            self._by_track_id[track_id] = record

        return record


@dataclass
class RuntimeGlobalIdentityRecord:
    """A runtime global identity record with associated track segments.

    This represents a persistent runtime identity that has been explicitly associated
    with one or more track segments by an external caller.

    The `provisional` flag indicates whether this identity was assigned due to
    insufficient evidence (UNRESOLVED association). A provisional identity represents
    a "best guess" new identity when evidence is insufficient to determine whether
    the segment belongs to an existing identity or is truly a new physical object.
    """

    global_id: str
    track_segments: list[RuntimeTrackSegment] = field(default_factory=list)
    created_order: int = 0
    provisional: bool = False

    def __post_init__(self) -> None:
        if not validate_runtime_global_id(self.global_id):
            raise ValueError(f"Invalid runtime global_id format: {self.global_id}")
        if not isinstance(self.created_order, int):
            raise TypeError(f"created_order must be int, got {type(self.created_order).__name__}")
        if not isinstance(self.provisional, bool):
            raise TypeError(f"provisional must be bool, got {type(self.provisional).__name__}")

    def add_track_segment(self, segment: RuntimeTrackSegment) -> None:
        """Add a track segment to this identity record."""
        if not isinstance(segment, RuntimeTrackSegment):
            raise TypeError(f"Expected RuntimeTrackSegment, got {type(segment).__name__}")
        if segment in self.track_segments:
            raise ValueError(f"Track segment with track_id {segment.track_id} already associated")
        self.track_segments.append(segment)

    def get_track_ids(self) -> list[int]:
        """Get all track IDs associated with this identity."""
        return [seg.track_id for seg in self.track_segments]

    @property
    def start_frame(self) -> int:
        """First frame across all associated segments."""
        if not self.track_segments:
            raise ValueError("No track segments")
        return min(seg.start_frame for seg in self.track_segments)

    @property
    def end_frame(self) -> int:
        """Last frame across all associated segments."""
        if not self.track_segments:
            raise ValueError("No track segments")
        return max(seg.end_frame for seg in self.track_segments)


class RuntimeGlobalIdentityRegistry:
    """Registry for runtime global identity management.

    This is a STATE MANAGEMENT layer only. It does NOT determine whether
    track segments belong to the same object. Associations must be explicitly
    supplied by a caller.

    The registry uses a separate runtime namespace (G001, G002, ...) distinct
    from GT global_id (GT_XXX) to prevent GT leakage.
    """

    def __init__(self):
        self._by_global_id: dict[str, RuntimeGlobalIdentityRecord] = {}
        self._by_track_id: dict[int, RuntimeGlobalIdentityRecord] = {}
        self._next_id: int = 1

    def _generate_next_global_id(self) -> str:
        """Generate the next deterministic runtime global_id (G001, G002, ...)."""
        gid = f"G{self._next_id:03d}"
        self._next_id += 1
        return gid

    def create_identity(self, provisional: bool = False) -> str:
        """Create a new runtime global identity and return its ID.

        The identity is created empty (no track segments associated).
        Use associate_track_segment() to associate track segments.

        Args:
            provisional: If True, marks this identity as provisional. A provisional
                identity represents a "best guess" when evidence is insufficient
                to determine whether the segment belongs to an existing identity
                or is truly a new physical object.
        """
        global_id = self._generate_next_global_id()
        record = RuntimeGlobalIdentityRecord(
            global_id=global_id,
            created_order=len(self._by_global_id) + 1,
            provisional=provisional,
        )
        self._by_global_id[global_id] = record
        return global_id

    def register_identity(self, global_id: str) -> RuntimeGlobalIdentityRecord:
        """Register an explicitly provided runtime global_id.

        Use this when the global_id is provided externally (not generated).
        Raises ValueError if the ID is already registered or is a GT ID.
        """
        if is_gt_global_id(global_id):
            raise ValueError(f"GT global_id '{global_id}' cannot be registered in runtime registry")
        if not validate_runtime_global_id(global_id):
            raise ValueError(f"Invalid runtime global_id format: {global_id}")
        if global_id in self._by_global_id:
            raise ValueError(f"Global_id '{global_id}' is already registered")

        record = RuntimeGlobalIdentityRecord(
            global_id=global_id,
            created_order=len(self._by_global_id) + 1,
        )
        self._by_global_id[global_id] = record
        return record

    def associate_track_segment(
        self, global_id: str, segment: RuntimeTrackSegment
    ) -> RuntimeGlobalIdentityRecord:
        """Associate a track segment with an existing runtime global identity.

        The association must be explicitly supplied by the caller. This method
        does NOT determine whether the segment belongs to the identity.
        """
        if is_gt_global_id(global_id):
            raise ValueError(f"Cannot associate with GT global_id '{global_id}'")

        record = self._by_global_id.get(global_id)
        if record is None:
            raise KeyError(f"Global_id '{global_id}' not found in registry")

        existing = self._by_track_id.get(segment.track_id)
        if existing is not None:
            if existing.global_id != global_id:
                raise ValueError(
                    f"Track_id {segment.track_id} is already associated with "
                    f"global_id '{existing.global_id}'"
                )
            return record

        record.add_track_segment(segment)
        self._by_track_id[segment.track_id] = record
        return record

    def get_by_global_id(self, global_id: str) -> Optional[RuntimeGlobalIdentityRecord]:
        """Retrieve a runtime global identity record by global_id."""
        return self._by_global_id.get(global_id)

    def get_by_track_id(self, track_id: int) -> Optional[RuntimeGlobalIdentityRecord]:
        """Retrieve the runtime global identity associated with a track_id."""
        return self._by_track_id.get(track_id)

    def list_identities(self) -> list[str]:
        """List all registered runtime global_ids in deterministic order (by creation order)."""
        records = sorted(self._by_global_id.values(), key=lambda r: r.created_order)
        return [r.global_id for r in records]

    def get_all_records(self) -> list[RuntimeGlobalIdentityRecord]:
        """Get all identity records in deterministic order (by creation order)."""
        return sorted(self._by_global_id.values(), key=lambda r: r.created_order)

    def identity_exists(self, global_id: str) -> bool:
        """Check if a runtime global identity exists."""
        return global_id in self._by_global_id

    def get_track_ids_for_identity(self, global_id: str) -> list[int]:
        """Get all track_ids associated with a global identity."""
        record = self._by_global_id.get(global_id)
        if record is None:
            raise KeyError(f"Global_id '{global_id}' not found in registry")
        return record.get_track_ids()

    def count_identities(self) -> int:
        """Return the count of registered identities."""
        return len(self._by_global_id)

    def clear(self) -> None:
        """Clear all registry state."""
        self._by_global_id.clear()
        self._by_track_id.clear()
        self._next_id = 1


@dataclass(frozen=True)
class TrackSegmentCandidate:
    """Represents a candidate pair of track segments for potential identity association.

    This is NOT an identity decision. It represents plausible candidates that
    a future Association Matcher may consider.

    Fields:
        previous_track_id: Track ID of the earlier segment
        current_track_id: Track ID of the later segment
        temporal_gap: Frame gap between segments (other.start_frame - self.end_frame)
        spatial_distance: Center-point distance between segments
        class_match: Whether class names match (supporting metadata only)
        class_name: Class name from the earlier segment (for reference)
    """

    previous_track_id: int
    current_track_id: int
    temporal_gap: int
    spatial_distance: float
    class_match: bool
    class_name: str

    def __post_init__(self) -> None:
        if not isinstance(self.previous_track_id, int) or self.previous_track_id < 0:
            raise ValueError(f"previous_track_id must be non-negative int, got {self.previous_track_id}")
        if not isinstance(self.current_track_id, int) or self.current_track_id < 0:
            raise ValueError(f"current_track_id must be non-negative int, got {self.current_track_id}")
        if self.previous_track_id == self.current_track_id:
            raise ValueError("Self-candidate not allowed")
        if not isinstance(self.temporal_gap, int):
            raise ValueError(f"temporal_gap must be int, got {type(self.temporal_gap).__name__}")
        if not isinstance(self.spatial_distance, (int, float)) or self.spatial_distance < 0:
            raise ValueError(f"spatial_distance must be non-negative, got {self.spatial_distance}")
        if not isinstance(self.class_match, bool):
            raise ValueError(f"class_match must be bool, got {type(self.class_match).__name__}")
        if not isinstance(self.class_name, str):
            raise ValueError(f"class_name must be str, got {type(self.class_name).__name__}")

    def to_dict(self) -> dict:
        """Convert to dictionary for serialization."""
        return {
            "previous_track_id": self.previous_track_id,
            "current_track_id": self.current_track_id,
            "temporal_gap": self.temporal_gap,
            "spatial_distance": self.spatial_distance,
            "class_match": self.class_match,
            "class_name": self.class_name,
        }


@dataclass(frozen=True)
class AssociationEvidence:
    """Evidence components for an association decision.

    This captures the raw evidence used to make an association decision.
    Used for auditability and transparency.
    """

    temporal_gap: int
    spatial_distance: float
    motion_direction_match: bool
    motion_direction_angle: float
    class_match: bool
    class_name: str
    temporal_within_threshold: bool
    spatial_within_threshold: bool

    def to_dict(self) -> dict:
        """Convert to dictionary for audit trail."""
        return {
            "temporal_gap": self.temporal_gap,
            "spatial_distance": self.spatial_distance,
            "motion_direction_match": self.motion_direction_match,
            "motion_direction_angle": self.motion_direction_angle,
            "class_match": self.class_match,
            "class_name": self.class_name,
            "temporal_within_threshold": self.temporal_within_threshold,
            "spatial_within_threshold": self.spatial_within_threshold,
        }


@dataclass(frozen=True)
class AssociationDecision:
    """Represents an association decision for a candidate pair.

    decision: MATCH (associate), NO_MATCH (do not associate), UNRESOLVED (insufficient evidence)
    evidence: The evidence components used to make the decision
    reason: Human-readable explanation of the decision
    """

    previous_track_id: int
    current_track_id: int
    decision: str
    evidence: AssociationEvidence
    reason: str

    def __post_init__(self) -> None:
        if self.decision not in {"MATCH", "NO_MATCH", "UNRESOLVED"}:
            raise ValueError(f"Invalid decision: {self.decision}")
        if not isinstance(self.evidence, AssociationEvidence):
            raise TypeError(f"evidence must be AssociationEvidence, got {type(self.evidence).__name__}")
        if not isinstance(self.reason, str):
            raise ValueError(f"reason must be str, got {type(self.reason).__name__}")

    def to_dict(self) -> dict:
        """Convert to dictionary for audit trail."""
        return {
            "previous_track_id": self.previous_track_id,
            "current_track_id": self.current_track_id,
            "decision": self.decision,
            "evidence": self.evidence.to_dict(),
            "reason": self.reason,
        }


class CandidateGenerator:
    """Generates candidate pairs of track segments for potential identity association.

    This is a deterministic candidate generation layer. It identifies pairs of
    track segments that are plausible candidates for a future Association Matcher.

    IMPORTANT: This does NOT decide identity. It only produces candidates
    that may be evaluated by a future association layer.
    """

    def __init__(self, max_temporal_gap: Optional[int] = None):
        """Initialize the candidate generator.

        Args:
            max_temporal_gap: Maximum frame gap to consider as candidate.
                If None, all temporal gaps are considered (configurable boundary).
                This is a research parameter, not a scientifically optimal threshold.
        """
        self._max_temporal_gap = max_temporal_gap

    def generate_candidates(
        self, segments: list[RuntimeTrackSegment]
    ) -> list[TrackSegmentCandidate]:
        """Generate candidate pairs from a list of track segments.

        This is deterministic: the same ordered input produces the same output.

        Args:
            segments: List of track segments to generate candidates from

        Returns:
            List of candidate pairs (deterministic order, no duplicates, no self-candidates)
        """
        if not segments:
            return []

        # Sort segments by start_frame for deterministic ordering
        sorted_segments = sorted(segments, key=lambda s: (s.start_frame, s.track_id))

        candidates: list[TrackSegmentCandidate] = []
        seen_pairs: set[tuple[int, int]] = set()

        for i, segment_current in enumerate(sorted_segments):
            for segment_next in sorted_segments[i + 1:]:
                # Skip if segment_next starts before segment_current ends
                if segment_next.start_frame <= segment_current.end_frame:
                    continue

                temporal_gap = segment_current.temporal_gap_to(segment_next)

                # Apply temporal boundary if configured
                if self._max_temporal_gap is not None and temporal_gap > self._max_temporal_gap:
                    continue

                spatial_distance = segment_current.spatial_distance_to(segment_next)

                # Class metadata (supporting evidence only, not identity decision)
                try:
                    class_match = segment_current.class_name == segment_next.class_name
                    class_name = segment_current.class_name
                except ValueError:
                    class_match = False
                    class_name = ""

                # Create canonical pair (smaller track_id first for determinism)
                track_id_current = segment_current.track_id
                track_id_next = segment_next.track_id

                if track_id_current < track_id_next:
                    prev_id, curr_id = track_id_current, track_id_next
                else:
                    prev_id, curr_id = track_id_next, track_id_current

                pair_key = (prev_id, curr_id)
                if pair_key in seen_pairs:
                    continue
                seen_pairs.add(pair_key)

                candidate = TrackSegmentCandidate(
                    previous_track_id=prev_id,
                    current_track_id=curr_id,
                    temporal_gap=temporal_gap,
                    spatial_distance=spatial_distance,
                    class_match=class_match,
                    class_name=class_name,
                )
                candidates.append(candidate)

        # Sort final candidates for deterministic output
        return sorted(
            candidates,
            key=lambda c: (c.previous_track_id, c.current_track_id)
        )


class AssociationBaseline:
    """Deterministic baseline association engine.

    Evaluates candidates and produces association decisions (MATCH/NO_MATCH/UNRESOLVED).

    This is a BASELINE implementation. It does NOT claim optimal thresholds.
    Thresholds are explicit configurable parameters.
    """

    def __init__(
        self,
        max_temporal_gap: int = 30,
        max_spatial_distance: float = 200.0,
        require_class_match: bool = False,
        unresolved_temporal_threshold: Optional[int] = None,
        unresolved_spatial_threshold: Optional[float] = None,
    ):
        """Initialize the association baseline.

        Args:
            max_temporal_gap: Maximum temporal gap for MATCH consideration.
                BASELINE PARAMETER - not scientifically optimized.
            max_spatial_distance: Maximum spatial distance for MATCH consideration.
                BASELINE PARAMETER - not scientifically optimized.
            require_class_match: Whether class must match for MATCH.
                False by default because project has observed class inconsistencies.
            unresolved_temporal_threshold: If provided, temporal gaps between this and
                max_temporal_gap result in UNRESOLVED rather than NO_MATCH.
                BASELINE PARAMETER - not scientifically optimized.
            unresolved_spatial_threshold: If provided, spatial distances between this and
                max_spatial_distance result in UNRESOLVED rather than NO_MATCH.
                BASELINE PARAMETER - not scientifically optimized.
        """
        self._max_temporal_gap = max_temporal_gap
        self._max_spatial_distance = max_spatial_distance
        self._require_class_match = require_class_match
        self._unresolved_temporal_threshold = unresolved_temporal_threshold
        self._unresolved_spatial_threshold = unresolved_spatial_threshold

    @property
    def max_temporal_gap(self) -> int:
        return self._max_temporal_gap

    @property
    def max_spatial_distance(self) -> float:
        return self._max_spatial_distance

    @property
    def require_class_match(self) -> bool:
        return self._require_class_match

    @property
    def unresolved_temporal_threshold(self) -> Optional[int]:
        return self._unresolved_temporal_threshold

    @property
    def unresolved_spatial_threshold(self) -> Optional[float]:
        return self._unresolved_spatial_threshold

    def evaluate_candidate(
        self,
        candidate: TrackSegmentCandidate,
        previous_segment: RuntimeTrackSegment,
        current_segment: RuntimeTrackSegment,
    ) -> AssociationDecision:
        """Evaluate a single candidate and produce an association decision.

        Args:
            candidate: The candidate pair to evaluate
            previous_segment: The earlier track segment
            current_segment: The later track segment

        Returns:
            AssociationDecision with MATCH/NO_MATCH/UNRESOLVED
        """
        temporal_gap = candidate.temporal_gap
        spatial_distance = candidate.spatial_distance
        class_match = candidate.class_match
        class_name = candidate.class_name

        # Calculate motion direction continuity
        prev_direction = previous_segment.motion_direction()
        curr_direction = current_segment.motion_direction()

        motion_direction_match = False
        motion_direction_angle = 180.0  # Default to opposite

        if prev_direction is not None and curr_direction is not None:
            # Calculate angle between motion directions
            dot = prev_direction[0] * curr_direction[0] + prev_direction[1] * curr_direction[1]
            # Clamp to [-1, 1] for arccos
            dot = max(-1.0, min(1.0, dot))
            motion_direction_angle = math.degrees(math.acos(dot))
            # Consider directions similar if angle < 90 degrees
            motion_direction_match = motion_direction_angle < 90.0

        temporal_within_threshold = temporal_gap <= self._max_temporal_gap
        spatial_within_threshold = spatial_distance <= self._max_spatial_distance

        # Check for unresolved zone if configured
        unresolved_temporal_within = False
        unresolved_spatial_within = False

        if self._unresolved_temporal_threshold is not None:
            unresolved_temporal_within = temporal_gap <= self._unresolved_temporal_threshold

        if self._unresolved_spatial_threshold is not None:
            unresolved_spatial_within = spatial_distance <= self._unresolved_spatial_threshold

        evidence = AssociationEvidence(
            temporal_gap=temporal_gap,
            spatial_distance=spatial_distance,
            motion_direction_match=motion_direction_match,
            motion_direction_angle=motion_direction_angle,
            class_match=class_match,
            class_name=class_name,
            temporal_within_threshold=temporal_within_threshold,
            spatial_within_threshold=spatial_within_threshold,
        )

        # Decision logic - check for NO_MATCH first (clearly exceeds thresholds)
        if self._unresolved_temporal_threshold is not None:
            # Has unresolved zone - check if clearly exceeds it
            if temporal_gap > self._unresolved_temporal_threshold:
                return AssociationDecision(
                    previous_track_id=candidate.previous_track_id,
                    current_track_id=candidate.current_track_id,
                    decision="NO_MATCH",
                    evidence=evidence,
                    reason=f"Temporal gap {temporal_gap} exceeds unresolved threshold {self._unresolved_temporal_threshold}",
                )
            # Within unresolved zone but outside MATCH zone - UNRESOLVED
            elif not temporal_within_threshold:
                return AssociationDecision(
                    previous_track_id=candidate.previous_track_id,
                    current_track_id=candidate.current_track_id,
                    decision="UNRESOLVED",
                    evidence=evidence,
                    reason=f"Temporal gap {temporal_gap} exceeds MATCH threshold {self._max_temporal_gap} but within unresolved threshold {self._unresolved_temporal_threshold}",
                )
        elif not temporal_within_threshold:
            return AssociationDecision(
                previous_track_id=candidate.previous_track_id,
                current_track_id=candidate.current_track_id,
                decision="NO_MATCH",
                evidence=evidence,
                reason=f"Temporal gap {temporal_gap} exceeds threshold {self._max_temporal_gap}",
            )

        if self._unresolved_spatial_threshold is not None:
            # Has unresolved zone - check if clearly exceeds it
            if spatial_distance > self._unresolved_spatial_threshold:
                return AssociationDecision(
                    previous_track_id=candidate.previous_track_id,
                    current_track_id=candidate.current_track_id,
                    decision="NO_MATCH",
                    evidence=evidence,
                    reason=f"Spatial distance {spatial_distance:.1f} exceeds unresolved threshold {self._unresolved_spatial_threshold}",
                )
            # Within unresolved zone but outside MATCH zone - UNRESOLVED
            elif not spatial_within_threshold:
                return AssociationDecision(
                    previous_track_id=candidate.previous_track_id,
                    current_track_id=candidate.current_track_id,
                    decision="UNRESOLVED",
                    evidence=evidence,
                    reason=f"Spatial distance {spatial_distance:.1f} exceeds MATCH threshold {self._max_spatial_distance} but within unresolved threshold {self._unresolved_spatial_threshold}",
                )
        elif not spatial_within_threshold:
            return AssociationDecision(
                previous_track_id=candidate.previous_track_id,
                current_track_id=candidate.current_track_id,
                decision="NO_MATCH",
                evidence=evidence,
                reason=f"Spatial distance {spatial_distance:.1f} exceeds threshold {self._max_spatial_distance}",
            )

        if self._require_class_match and not class_match:
            return AssociationDecision(
                previous_track_id=candidate.previous_track_id,
                current_track_id=candidate.current_track_id,
                decision="NO_MATCH",
                evidence=evidence,
                reason="Class mismatch and class match is required",
            )

        # All thresholds satisfied - this is a MATCH
        return AssociationDecision(
            previous_track_id=candidate.previous_track_id,
            current_track_id=candidate.current_track_id,
            decision="MATCH",
            evidence=evidence,
            reason="All baseline thresholds satisfied",
        )

    def evaluate_candidates(
        self,
        candidates: list[TrackSegmentCandidate],
        segments: list[RuntimeTrackSegment],
    ) -> list[AssociationDecision]:
        """Evaluate multiple candidates and produce association decisions.

        Args:
            candidates: List of candidates to evaluate
            segments: List of track segments (for accessing segment data)

        Returns:
            List of AssociationDecision in deterministic order
        """
        if not candidates:
            return []

        # Build segment lookup
        segment_by_id = {seg.track_id: seg for seg in segments}

        decisions: list[AssociationDecision] = []
        for candidate in candidates:
            prev_seg = segment_by_id.get(candidate.previous_track_id)
            curr_seg = segment_by_id.get(candidate.current_track_id)

            if prev_seg is None or curr_seg is None:
                continue

            decision = self.evaluate_candidate(candidate, prev_seg, curr_seg)
            decisions.append(decision)

        # Sort for deterministic output
        return sorted(
            decisions,
            key=lambda d: (d.previous_track_id, d.current_track_id)
        )


def build_global_identity_artifact(
    registry: RuntimeGlobalIdentityRegistry,
    decisions: list[AssociationDecision],
) -> dict:
    """Build a deterministic Global Identity audit artifact.

    This artifact provides runtime observability of Global Identity associations
    without modifying the association algorithm.

    Args:
        registry: RuntimeGlobalIdentityRegistry with registered identities
        decisions: List of AssociationDecision for audit trail

    Returns:
        Dictionary artifact with runtime global identities and associations
    """
    artifact = {
        "global_identities": [],
        "decisions": [],
    }

    # Build global identity records in deterministic order (by creation order)
    for record in registry.get_all_records():
        identity_entry = {
            "global_id": record.global_id,
            "provisional": record.provisional,
            "track_segments": [],
        }

        # Add track segments for this identity
        for segment in record.track_segments:
            segment_entry = {
                "track_id": segment.track_id,
                "start_frame": segment.start_frame,
                "end_frame": segment.end_frame,
            }
            identity_entry["track_segments"].append(segment_entry)

        # Sort track segments by track_id for deterministic output
        identity_entry["track_segments"] = sorted(
            identity_entry["track_segments"],
            key=lambda s: s["track_id"]
        )

        artifact["global_identities"].append(identity_entry)

    # Add decisions for audit trail
    for decision in decisions:
        decision_entry = {
            "previous_track_id": decision.previous_track_id,
            "current_track_id": decision.current_track_id,
            "decision": decision.decision,
            "reason": decision.reason,
            "evidence": {
                "temporal_gap": decision.evidence.temporal_gap,
                "spatial_distance": decision.evidence.spatial_distance,
                "class_match": decision.evidence.class_match,
            },
        }
        artifact["decisions"].append(decision_entry)

    # Sort decisions by track_id pair for deterministic output
    artifact["decisions"] = sorted(
        artifact["decisions"],
        key=lambda d: (d["previous_track_id"], d["current_track_id"])
    )

    return artifact


def serialize_global_identity_artifact(artifact: dict, output_dir: Path) -> Path:
    """Write the Global Identity audit artifact to a deterministic JSON file.

    Args:
        artifact: The audit artifact dictionary
        output_dir: Directory to write the artifact

    Returns:
        Path to the written artifact
    """
    path = output_dir / "global_identity.json"
    with path.open("w", encoding="utf-8") as f:
        json.dump(artifact, f, indent=4)
    return path


def associate_track_segments(
    segments: list[RuntimeTrackSegment],
    registry: RuntimeGlobalIdentityRegistry,
    candidate_generator: Optional[CandidateGenerator] = None,
    association_baseline: Optional[AssociationBaseline] = None,
) -> list[AssociationDecision]:
    """Associate track segments into global identities.

    This is the main entry point for the association pipeline.

    Args:
        segments: List of track segments to associate
        registry: Registry to store global identity associations
        candidate_generator: Optional candidate generator (creates default if None)
        association_baseline: Optional association baseline (creates default if None)

    Returns:
        List of AssociationDecision for audit trail
    """
    if candidate_generator is None:
        candidate_generator = CandidateGenerator()

    if association_baseline is None:
        association_baseline = AssociationBaseline()

    # Generate candidates
    candidates = candidate_generator.generate_candidates(segments)

    # Evaluate candidates
    decisions = association_baseline.evaluate_candidates(candidates, segments)

    # Apply MATCH decisions to registry
    for decision in decisions:
        if decision.decision == "MATCH":
            prev_id = decision.previous_track_id
            curr_id = decision.current_track_id

            # Get existing global_id for previous track if any
            prev_global = registry.get_by_track_id(prev_id)
            curr_global = registry.get_by_track_id(curr_id)

            if prev_global is None and curr_global is None:
                # Both new - create new identity
                new_id = registry.create_identity()
                prev_seg = next(s for s in segments if s.track_id == prev_id)
                curr_seg = next(s for s in segments if s.track_id == curr_id)
                registry.associate_track_segment(new_id, prev_seg)
                registry.associate_track_segment(new_id, curr_seg)
            elif prev_global is not None and curr_global is None:
                # Previous already has identity, add current
                registry.associate_track_segment(prev_global.global_id,
                    next(s for s in segments if s.track_id == curr_id))
            elif prev_global is None and curr_global is not None:
                # Current already has identity, add previous
                registry.associate_track_segment(curr_global.global_id,
                    next(s for s in segments if s.track_id == prev_id))
            # If both have identity, they're already associated (should not happen with current logic)

    # Handle unmatched segments - assign new identities
    # Track which track_ids are in MATCH vs NO_MATCH decisions
    matched_track_ids: set[int] = set()
    no_match_track_ids: set[int] = set()

    for decision in decisions:
        if decision.decision == "MATCH":
            matched_track_ids.add(decision.previous_track_id)
            matched_track_ids.add(decision.current_track_id)
        elif decision.decision == "NO_MATCH":
            no_match_track_ids.add(decision.previous_track_id)
            no_match_track_ids.add(decision.current_track_id)

    for segment in segments:
        if segment.track_id not in matched_track_ids:
            if registry.get_by_track_id(segment.track_id) is None:
                # Determine identity type based on evidence:
                # - MATCH: confirmed identity (handled above)
                # - NO_MATCH: confirmed new identity - we have evidence they're NOT the same
                # - UNRESOLVED: provisional - insufficient evidence either way
                # - No candidate: provisional - insufficient evidence to form candidate
                if segment.track_id in no_match_track_ids:
                    # NO_MATCH means evidence was sufficient to reject - confirmed new identity
                    new_id = registry.create_identity(provisional=False)
                else:
                    # UNRESOLVED or no candidate - evidence insufficient
                    new_id = registry.create_identity(provisional=True)
                registry.associate_track_segment(new_id, segment)

    return decisions


__all__ = [
    "GLOBAL_ID_PATTERN",
    "RUNTIME_GLOBAL_ID_PATTERN",
    "validate_global_id",
    "validate_runtime_global_id",
    "is_gt_global_id",
    "GlobalIdentityAssociation",
    "GlobalIdentityRegistry",
    "RuntimeTrackingObservation",
    "RuntimeTrackSegment",
    "RuntimeGlobalIdentityRecord",
    "RuntimeGlobalIdentityRegistry",
    "TrackSegmentCandidate",
    "CandidateGenerator",
    "AssociationEvidence",
    "AssociationDecision",
    "AssociationBaseline",
    "associate_track_segments",
    "observation_from_bytetrack",
    "build_track_segments_from_observations",
    "build_global_identity_artifact",
    "serialize_global_identity_artifact",
]

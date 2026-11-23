# Global Identity Specification

## 1. Purpose

Global Identity provides persistent identity association across tracker-local track segments in the research architecture. It bridges the gap between the frame-by-frame tracking output from Multi-Object Tracking and the trajectory-level analysis performed by downstream stages. The purpose is to recognize when multiple tracker-local track segments correspond to the same real-world object, even when the tracker assigns them different `track_id` values due to occlusions, re-identification failures, or tracking discontinuities.

## 2. Architectural Position

Global Identity occupies a specific position in the research pipeline:

```
Video → Temporal Sampling → Object Detection → Multi-Object Tracking → Global Identity → Trajectory
```

The ByteTrack `track_id` remains the tracker-local runtime identity. It is assigned per video run and is non-deterministic across runs. Global Identity operates on the tracking layer output but does not replace or modify the tracker's internal identity assignment.

## 3. Identity Semantics

The system distinguishes three distinct identity concepts:

| Identity Type | Source | Scope | Usage |
|---|---|---|---|
| `track_id` | ByteTrack | Tracker-local, per video run | Runtime trajectory key |
| runtime `global_id` | Global Identity layer | Persistent across track segments | Runtime identity association |
| GT `global_id` | Ground truth annotation | Video-wide, immutable | Evaluation only |

**Explicit constraints:**
- `track_id` is assigned by ByteTrack and MUST NOT be renamed or replaced by `global_id`.
- runtime `global_id` represents a persistent runtime identity assigned by the Global Identity layer.
- GT `global_id` belongs exclusively to ground truth/evaluation and MUST NOT be injected into runtime Global Identity decisions.
- `track_id != global_id` — the runtime trajectory artifact is keyed by `track_id` only.

## 4. Runtime Input Contract

Global Identity receives the following information from the Tracking layer:

| Field | Type | Description |
|---|---|---|
| `track_id` | int | ByteTrack-assigned runtime identity |
| `frame_id` | int | Frame index (0-based) |
| `timestamp` | float | Frame timestamp (seconds) |
| `bbox` | list[int] | Bounding box [x1, y1, x2, y2] in 1020×500 space |
| `class` | str | Object class (car, motorcycle, bus, truck) |
| `confidence` | float | Detection confidence |
| `center` | tuple | Center coordinates (cx, cy) = [(x1+x2)/2, (y1+y2)/2] |

No additional fields are currently available or justified by the architecture.

## 5. Association Principle

Global Identity is formulated as an association problem: determining whether two or more tracker-local track segments correspond to the same real-world object.

**Candidate evidence categories:**

1. **Temporal continuity** — gap between track segments relative to expected object behavior
2. **Spatial continuity** — distance between end of one track segment and start of another
3. **Motion/trajectory continuity** — velocity consistency, trajectory direction alignment
4. **Appearance information** — visual similarity (if later introduced; currently NOT available)
5. **Class consistency** — object class must match (supporting evidence only, not sufficient alone)

We do not define final weights or thresholds in this specification. Association algorithm design is deferred to future implementation.

## 6. Unresolved Association

The system MUST allow an association decision to remain unresolved when evidence is insufficient.

A new track segment that cannot be confidently associated with an existing global identity MUST be assigned a new runtime `global_id` or marked as unresolved. The system MUST NOT force every new track to match an existing global identity. False identity mergers are more costly than unresolved identity gaps.

## 7. Registry Contract

The `GlobalIdentityRegistry` maintains the relationship between runtime `global_id` and associated `track_id` segments:

- Stores mapping from runtime `global_id` to associated track segment identifiers
- Stores reverse mapping from `track_id` to its assigned `global_id`
- Preserves association status: "RESOLVED" (explicit evidence) vs "UNRESOLVED" (no confident association)
- Maintains audit trail: which track segments are linked to which global identity

The registry does not perform association logic; it only records the results of association decisions.

## 8. Runtime Boundary

```
Video → Sampling → Detection → Tracking → Global Identity → Trajectory
```

Global Identity operates on runtime tracking information only. Ground truth data is NOT part of the runtime path. The runtime pipeline processes video frames through detection and tracking, producing tracker-local track segments. Global Identity then associates these segments into persistent identities. The Trajectory stage receives both the original `track_id`-keyed observations and, optionally, the global identity associations.

## 9. Evaluation Boundary

A separate evaluation boundary exists where runtime global identities can be compared with GT global identities:

- Evaluation compares the runtime `global_id` assignments against ground truth `global_id` annotations
- Evaluation metrics assess association accuracy (ID switches, ID fragments, identity merges)
- Evaluation MUST NOT alter runtime identity decisions
- GT `global_id` is used ONLY for evaluation, never as input to runtime association

## 10. Scientific Constraints

The following constraints govern Global Identity implementation:

1. **No GT leakage** — ground truth identity information MUST NOT be used in runtime Global Identity decisions
2. **No replacement of ByteTrack** — Global Identity does not modify tracking behavior
3. **No modification of detection** — Global Identity does not alter detection output
4. **No modification of trajectory semantics** — Trajectory artifact structure remains unchanged
5. **No forced identity matching** — Unresolved associations are permitted
6. **Deterministic behavior** — Association decisions should be deterministic for reproducibility
7. **Auditable decisions** — Every association decision must be traceable to specific evidence
8. **No unsupported identity claim** — Runtime global_id must be supported by evidence, not assumption

## 11. Implementation Status

| Component | Status |
|---|---|
| Global Identity foundation | FOUNDATION_ONLY |
| Runtime Association | NOT_IMPLEMENTED |
| Runtime Integration | NOT_IMPLEMENTED |

The foundation layer includes:
- `GLOBAL_ID_PATTERN` validation (GT_XXX format)
- `validate_global_id()` function
- `GlobalIdentityAssociation` dataclass
- `GlobalIdentityRegistry` class
- `RuntimeTrackingObservation` dataclass (observation interface)
- `RuntimeTrackSegment` dataclass (track segment representation)

Runtime association between track segments is NOT implemented.

### Observation Interface (Implemented)

The observation interface is defined as:

```python
@dataclass(frozen=True)
class RuntimeTrackingObservation:
    track_id: int           # ByteTrack runtime identity
    frame_id: int          # Frame index (0-based)
    timestamp: float       # Frame timestamp in seconds
    bbox: tuple[int, int, int, int]  # [x1, y1, x2, y2]
    class_name: str        # Object class
    confidence: float      # Detection confidence [0.0, 1.0]
    cx: float              # Center x = (x1 + x2) / 2
    cy: float              # Center y = (y1 + y2) / 2
```

Track segments are represented as:

```python
@dataclass
class RuntimeTrackSegment:
    track_id: int
    observations: list[RuntimeTrackingObservation]
```

The interface provides:
- `from_dict()` constructor for compatibility with existing tracking code
- `to_dict()` for trajectory compatibility
- `temporal_gap_to()` for inter-segment temporal analysis
- `spatial_distance_to()` for inter-segment spatial analysis
- Deterministic construction (no randomness)

## 12. Future Implementation Boundary

Future implementation may add the following components, in order of priority:

1. **Observation interface** — Define how Global Identity receives track segment data from the Tracking layer
2. **Candidate generation** — Generate candidate pairs/groups of track segments for potential association
3. **Association baseline** — Implement baseline association algorithm using temporal, spatial, and motion continuity
4. **Registry integration** — Integrate association results with GlobalIdentityRegistry
5. **Controlled validation** — Validate association quality against held-out data
6. **Appearance/Re-ID** — Add appearance features only if justified by baseline performance gaps
7. **Runtime integration** — Connect Global Identity into the main pipeline
8. **Evaluation** — Implement evaluation metrics comparing runtime vs GT global_ids

No implementation of the above is performed in this specification task.

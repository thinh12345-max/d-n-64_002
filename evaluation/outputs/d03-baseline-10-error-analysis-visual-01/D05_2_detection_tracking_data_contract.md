# D-05.2 Detection → Tracking Data Contract

## 1. Scope

This document defines only the interface contract between the existing OBJECT DETECTING stage and the future MULTI-OBJECT TRACKING stage.

This contract is intentionally limited to the detector-to-tracker handoff. It does not implement a tracker, does not define trajectory generation, does not define global identity, and does not alter the D-03 or D-04 baseline findings.

## 2. Detection Observation Identity

Detector observations are per-frame detections.

A detector observation is not a global identity. It is not a tracker track identity. It is not ground-truth identity.

Each detection refers to a single frame observation and must be interpreted as a frame-local measurement. The detector output is a list of observed objects for one frame, not a persistent identity across frames.

## 3. Required Detection Fields

The detector-to-tracker interface must provide the minimum information required for tracking to consume ordered detections per frame.

Required fields:

- frame_id: the frame index to which the detection belongs
- timestamp: the time associated with the frame, consistent with the existing temporal protocol
- class: the object class label already used by the project
- bounding box: the spatial extent of the detection in the current frame
- detection confidence: only if the existing detector interface already emits it; otherwise this field is absent and must not be assumed

The tracker contract must not require fields that are not already established by the existing project artifacts.

## 4. Coordinate Convention

The established project convention is the bounding box representation [x1, y1, x2, y2] in pixels within the project frame coordinate space.

This contract preserves that convention exactly. No new coordinate convention is introduced. The tracker input must consume the same box representation already established by the project, without converting to a different format within this task.

## 5. Class Semantics

The detector-to-tracker interface must preserve the existing project class semantics.

The class field must use the class labels already established by the project without renaming, consolidating, or adding classes.

No new class taxonomy is introduced by this contract.

## 6. Temporal Semantics

Detections belong to a specific frame_id.

The temporal sampling protocol remains authoritative. This task does not create a new sampling rule, does not re-interpret sampling, and does not change the project’s existing frame/timestamp semantics.

Tracking must consume detections in frame order and must consider the detection to be bound to its source frame.

## 7. Tracker Identity Boundary

The following identity distinctions are explicitly preserved:

- detector observation ≠ tracker track identity
- tracker track identity ≠ ground-truth global identity

A tracker may assign a track_id internally for per-object continuity across frames, but track_id must not be treated as a global_id.

This contract does not define or infer global identity semantics. It does not introduce GT_XXX identity semantics into the production tracker contract.

## 8. Global Identity Boundary

Global identity belongs to the later identity stage.

Global identity must not be inferred merely from detector output. Detector observations are frame-local and insufficient to establish persistent identity across time.

This task does not create a global ID assignment rule. The tracker output and the future global identity stage remain separate responsibilities.

## 9. Trajectory Boundary

Trajectory is a later derived representation of tracked identity observations.

The trajectory stage is downstream of tracking and identity logic. It is not part of this detector-to-tracker contract.

This task does not implement trajectory generation, trajectory assembly, or trajectory-level reasoning.

## 10. Missing / Invalid Detections

The contract defines only the following frame-level behavior:

- No detections in a frame: the detection list for that frame is empty; the tracker must receive an empty observation set for that frame without inventing synthetic detections.
- Multiple detections in a frame: each detection remains an independent observation for that frame; no global identity is implied across them.
- Invalid bounding boxes: an invalid bbox is outside the contract and must not be silently repaired or reinterpreted by this task. The detector-to-tracker interface must preserve the project-established box format and validity semantics; invalid boxes are not converted into new semantics in this task.

This document does not define recovery algorithms, correction heuristics, or filtering logic beyond the contract boundary.

## 11. Output Boundary

The expected future tracker input is:

- ordered per-frame detection observations
- frame-scoped association to frame_id and timestamp
- class labels consistent with the project semantics
- bounding boxes in the project-established [x1, y1, x2, y2] form
- detector confidence only when already present in the detector interface

The expected future tracker output is:

- tracked object observations over time
- track-level association within the tracker’s internal state
- no claim of global identity
- no claim of trajectory generation
- no claim of ground-truth identity semantics

This is a contract-only handoff for the next stage. It does not implement tracker logic, does not define tracker evaluation, and does not define downstream identity or trajectory behavior beyond the stated boundaries.

# D-05.3 Tracking Implementation Boundary

## 1. Purpose

This document defines the implementation boundary for the future Multi-Object Tracking stage.

It is a planning and contract artifact only. It does not implement a tracker, does not run inference, does not train a model, and does not process video or image data.

## 2. Tracker Input

The tracker receives the detection observations produced by the Object Detection stage.

The accepted input is a sequence of frame-scoped detections, each associated with a frame_id and, where supported by the existing detector interface, timestamp and confidence.

The tracker input must preserve the detection contract established in D-05.2:

- detections are per-frame observations
- detections are not global identities
- bounding boxes remain in the project-established [x1, y1, x2, y2] form
- class semantics remain unchanged from the project
- detection confidence is included only if already supported by the existing detector interface

The tracker input boundary does not include global identity assignment, trajectory generation, ROI event interpretation, or graph construction.

## 3. Tracker Output

The tracker is allowed to produce tracking observations that associate detections across frames within the tracker’s internal state.

The tracker output is limited to tracker-local observations such as:

- a tracked object instance observed over consecutive frames
- a track_id assigned within the tracker
- frame-to-frame association state for detections under the tracker’s scope

The tracker output must not claim persistent real-world identity, must not claim global identity, and must not produce the final trajectory representation.

## 4. Track_id Semantics

track_id is strictly tracker-local identity.

track_id is NOT global_id.

track_id is not a ground-truth identity.

track_id is not a persistent real-world identity claim.

The tracker may assign track_id values for continuity within the tracker’s own observation sequence, but the meaning of those IDs is limited to the tracking stage and must not be interpreted as later-stage global identity.

## 5. Frame-to-Frame Association

Tracking associates detections across frames.

This contract defines only the boundary of that association: detections from consecutive frames may be related in the tracker’s temporal state. The task does not specify a tracking algorithm or implementation method.

No algorithmic detail is introduced here beyond the statement that the tracker operates over frame-to-frame association of detections.

## 6. Missing Detections

The tracker must operate within the boundary of frame-level missing detections.

This task defines only the contract boundary:

- if a frame contains no detections, the tracker receives no detection observations for that frame
- if a frame contains multiple detections, they are treated as multiple independent observations for that frame
- the tracker does not define a recovery algorithm for missing observations in this task

The tracking stage does not invent detections, does not synthesize missing evidence, and does not define correction rules beyond the contract boundary.

## 7. Track Creation

Track creation is a boundary-only concept for the tracking stage.

The tracker may create a track when a detection enters the tracker’s observation sequence, but this document does not specify the creation rule, threshold, algorithm, or scoring behavior.

Track creation remains an implementation detail to be resolved by the future tracker, not by this planning task.

## 8. Track Termination

Track termination is a boundary-only concept for the tracking stage.

The tracker may terminate a track when the observation sequence ends or the object is no longer associated with active detections, but this document does not define an algorithm, policy, or threshold.

Track termination remains outside the scope of this planning contract and is not implemented here.

## 9. Identity Limit

The tracker must not claim persistent real-world identity.

Global identity belongs to the later Global Identity stage.

The tracker is not responsible for later identity assignment, identity reconciliation, or global identity persistence. Those are downstream responsibilities.

## 10. Trajectory Limit

The tracker must not implement the final trajectory representation.

Trajectory is produced later by the Trajectory stage from tracked identity observations.

This task does not generate trajectories, does not define trajectory semantics beyond the boundary, and does not implement trajectory assembly.

## 11. ROI Limit

The tracker must not perform ROI event interpretation.

ROI Events / Traffic State is a later stage.

This task does not assign events, infer traffic state, or reason over ROI crossing behavior.

## 12. Graph Limit

The tracker must not construct the spatio-temporal graph.

Graph construction belongs to the later graph stage. This task does not build graph nodes, edges, or connectivity relationships for analysis.

## 13. Evaluation Limit

This task does not introduce tracking metrics.

The tracker does not calculate or define MOTA, MOTP, IDF1, HOTA, or any other metric in this task.

No evaluation protocol is defined or modified here.

## 14. Boundary Summary

The tracking stage is responsible only for frame-to-frame association of detections under a tracker-local identity mechanism.

The tracking stage does not claim global identity, does not build trajectories, does not interpret ROI events, does not construct the spatio-temporal graph, and does not define evaluation metrics.

This is a contract-only boundary for the next stage and must remain free of implementation logic.
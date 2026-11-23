# D-05.5 Tracker Implementation Specification

## 1. Implementation Scope

This document defines the minimal implementation specification for the Multi-Object Tracking stage.

The scope of this stage is limited to processing ordered frame-level detection observations into tracker-local track observations. It does not implement the final global identity stage, does not construct trajectories, does not interpret ROI events, and does not build the spatio-temporal graph.

## 2. Input Contract

The tracker receives detector observations that satisfy the existing Detection → Tracking contract established in D-05.2.

At a minimum, the tracker input includes the detection observation fields already defined by the project contract:

- frame_id
- timestamp
- class
- bounding box in the established [x1, y1, x2, y2] pixel convention
- detector confidence only if the existing detector interface already provides it

The tracker consumes detection observations in frame order. It does not define a new sampling policy, and it does not modify the authoritative temporal protocol.

## 3. Output Contract

The minimum tracker output is a set of tracker-local observations associated with frames.

Each track observation must distinguish:

- frame_id
- timestamp
- track_id
- associated detection information

The minimum output contract is limited to the observation of a detection associated with a tracker-local track over time. The tracker output does not include global_id.

## 4. Track Identity Boundary

The implementation specification explicitly preserves the identity boundary:

track_id ≠ global_id

track_id is local tracker identity.

global_id belongs to a later stage.

The tracker does not assign persistent real-world identity. The tracker is not a global identity system.

## 5. Temporal Boundary

The tracker operates on ordered frame observations.

The established temporal sampling protocol remains authoritative. No new sampling policy is introduced by this stage.

The tracker must treat detections as belonging to the specific frame_id from which they were observed.

## 6. Track Lifecycle Boundary

This specification defines only the implementation responsibilities for the tracker lifecycle without prescribing unverified algorithm parameters.

- Track creation: the tracker may create a new local track when a new detection enters the active observation sequence.
- Track continuation: the tracker may continue an existing local track across consecutive observations when detections are associated over time.
- Temporary missed detection: the tracker may maintain the local track through a short period where detections are absent, within the scope of the local tracking stage.
- Track termination: the tracker may terminate a local track when its observation sequence ends or when no valid association remains.

This specification does not prescribe a specific matching algorithm, threshold, or recovery policy beyond the contract boundary.

## 7. Trajectory Boundary

The tracker may expose ordered track observations required by the later Trajectory stage.

However, the tracker must not implement the final Trajectory stage.

The final trajectory representation is produced later from tracked identity observations, not within the tracker implementation specification.

## 8. ROI Boundary

The tracker must not interpret ROI crossings or produce ROI event semantics.

ROI Events / Traffic State remains a later stage and is outside the scope of this tracker specification.

## 9. Global Identity Boundary

The tracker must not assign persistent real-world identity.

Global identity belongs to the later Global Identity stage and must not be conflated with tracker-local identity.

## 10. Graph Boundary

The tracker must not construct the spatio-temporal graph.

Graph construction is a later stage and remains outside the implementation scope of this specification.

## 11. Evaluation Boundary

This task does not define or calculate tracking metrics.

No tracking metric, evaluation protocol, or benchmark is introduced here.

## 12. Implementation Inputs and Outputs

Conceptual flow:

Detection observations
→ Tracker
→ Track observations

This is a minimal specification for the stage boundary and does not include code-level implementation details.
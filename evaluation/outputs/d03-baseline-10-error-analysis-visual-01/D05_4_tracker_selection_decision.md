# D-05.4 Tracker Selection Decision

## 1. Purpose

This document defines the decision boundary for selecting a Multi-Object Tracking method for the project.

This is a decision-only document. It does not select a final tracker implementation, does not benchmark tracker methods, does not run inference, and does not implement tracking logic.

## 2. Known from Existing Project

The following facts are already established by the existing project artifacts and contracts:

- The current stage is Object Detection and the next stage is Multi-Object Tracking.
- Detector observations are per-frame detections and are not global identities.
- The tracker input must satisfy the existing detection-to-tracking contract.
- The tracker must preserve the identity boundary:
  - detector observation ≠ track_id ≠ global_id
- track_id is tracker-local identity and is not global_id.
- global_id belongs to the later Global Identity stage.
- trajectory is a later stage and is not implemented by this task.
- ROI event interpretation and spatio-temporal graph construction are later stages and are not part of tracker selection.

## 3. To Be Evaluated

The following criteria must be evaluated when selecting a tracking method:

1. Compatibility with the existing detector output.
2. Frame-to-frame association capability.
3. Stable tracker-local track_id semantics.
4. Ability to handle temporary missed detections.
5. Ability to handle object entrances and exits.
6. Suitability for traffic scenes.
7. Computational practicality for the project's real-time objective.
8. Compatibility with later trajectory construction.
9. Compatibility with later ROI event detection.
10. Separation between tracker identity and future global identity.

These are selection criteria only. They do not represent final implementation approval or final method choice.

## 4. Candidate Methods

Common MOT candidates may be considered, including ByteTrack, BoT-SORT, OC-SORT, and DeepSORT.

This document does not claim empirical superiority for any candidate.
This document does not fabricate benchmark results.
This document does not claim that any method is more accurate or faster unless that fact is already established by an existing project artifact.

Candidate names are included only as method families relevant to the selection decision. They are not final implementation decisions.

## 5. Decision Boundary

The selection decision must be clearly separated into the following categories:

### KNOWN FROM EXISTING PROJECT

- detector observations are per-frame and not global identities
- track_id is tracker-local
- global_id belongs to a later Global Identity stage
- trajectory is downstream of tracking
- ROI event interpretation is downstream of tracking
- graph construction is downstream of tracking

### TO BE EVALUATED

- compatibility with the current detector output
- track association behavior across frames
- missed-detection tolerance
- entrance/exit handling
- suitability for traffic scenes
- computational practicality
- compatibility with future trajectory construction
- compatibility with future ROI event detection
- tracker identity separation from global identity

### NOT YET DECIDED

- the final tracker method
- implementation details
- algorithmic configuration
- evaluation protocol
- final score thresholds
- final identity semantics beyond tracker-local track_id
- any trajectory representation beyond temporal observations required by the later stage

## 6. Important Identity Rule

The following identity distinctions are preserved:

- detector observation ≠ track_id ≠ global_id

track_id is tracker-local.

global_id belongs to the later Global Identity stage.

This rule is not a proposal for a new identity model and does not convert the tracker into a global identity system.

## 7. Important Trajectory Rule

This document does not define the final trajectory implementation.

Only the requirement is stated: the tracker output must provide the temporal observations required by the later Trajectory stage.

The Trajectory stage is responsible for constructing the final trajectory representation from tracked identity observations.

## 8. Important ROI and Graph Rules

This document does not implement ROI event detection.
This document does not construct the spatio-temporal graph.

ROI Events / Traffic State and the spatio-temporal graph remain later stages beyond the tracker selection decision.

## 9. Decision-Only Boundary

The outcome of this document is a selection framework, not an implementation decision.

The project must still resolve the final tracker choice under the criteria above, without claiming that the selection is already complete unless an existing project artifact explicitly does so.
# D-05.1 Tracking Transition Context

## 1. Master Trajectory Position

The current stage is OBJECT DETECTING. This stage is complete.
The next stage is MULTI-OBJECT TRACKING.

The master project trajectory is:

VIDEO
→ TEMPORAL SAMPLING
→ OBJECT DETECTING
→ MULTI-OBJECT TRACKING
→ GLOBAL IDENTITY
→ TRAJECTORY
→ ROI EVENTS / TRAFFIC STATE
→ SPATIO-TEMPORAL GRAPH
→ TRAFFIC FLOW ANALYSIS
→ REAL-TIME EVALUATION

## 2. Established Detection Baseline

The detection baseline has been completed.
The error-analysis documentation has been completed.

This document does not reproduce D-03 or D-04.

## 3. Evidence Constraints Inherited by Tracking

The following boundaries are inherited by the tracking stage and must not be violated:

- Evidence boundary: the visual sample is deterministic and is not statistically representative. Visual observations must not be generalized to the entire dataset.
- Visual-sample boundary: the visual sample contains 12 inspected cases. No category may be upgraded.
- Category status boundary:
  - BORDERLINE_IOU_MATCH is the only visual category currently classified as SUPPORTED.
  - SMALL_OBJECT, FALSE_POSITIVE_BACKGROUND, LOCALIZATION_ERROR, and FALSE_NEGATIVE remain PARTIALLY_SUPPORTED.
  - DUPLICATE_DETECTION, LOW_CONFIDENCE, and CROWDING remain NOT_DIRECTLY_SUPPORTED.
- Person-class boundary: the evaluated validation/test subsets contain no person ground truth. Person precision, recall, AP, false-positive, or false-negative performance must not be inferred. The absence of person ground truth must not be interpreted as poor person-class performance.
- Causal boundary: causal mechanisms for individual errors are not established by current evidence.
- Confidence boundary: confidence semantics are inherited from the detection stage and are not redefined here.
- Generalization boundary: dataset-wide prevalence of visual error categories is not established.

## 4. Required Detection-to-Tracking Interface

Tracking consumes ordered detections associated with frames.

The interface must provide, at minimum:

- frame_id
- timestamp
- bounding box
- object class
- detection confidence, if available
- frame ordering

It is not claimed that all of these fields are already implemented in the current artifacts.

## 5. Identity Boundary

The following identity boundary is explicitly preserved:

GROUND-TRUTH GLOBAL ID ≠ PRODUCTION TRACKER ID

The identity mechanism is not designed or implemented in this task.

## 6. Temporal Boundary

The existing temporal sampling protocol remains authoritative.

No sampling rule is changed by this task.

## 7. Open Decisions Before Tracking

The following decisions are open and must be resolved before tracking implementation:

- tracker selection
- tracker input contract
- handling of detection confidence
- tracker identity semantics
- tracking evaluation protocol
- relationship between tracker output and future global identity

None of these decisions are resolved by this document.

## 8. Prohibited Assumptions

Current evidence does not establish:

- dataset-wide prevalence of visual error categories
- person-class performance
- causal mechanisms for individual errors
- statistical significance of valid/test differences
- model architecture or training details not established by the artifacts

## 9. Next Stage

NEXT STAGE: MULTI-OBJECT TRACKING

Tracking implementation begins only after the tracking transition contract is explicitly locked.
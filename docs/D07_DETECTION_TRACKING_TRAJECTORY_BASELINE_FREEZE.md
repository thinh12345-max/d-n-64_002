# D-07.54 — Detection → Tracking → Trajectory Baseline Freeze Record

**Date:** 2026-09-17
**Status:** FORMAL FREEZE

---

## Research Boundary

The current research scope ends at:

`Detection → Tracking → Trajectory`

The following remain OUT OF SCOPE:

* ROI Events
* Traffic State
* Spatio-Temporal Graph
* Traffic Flow Analysis
* downstream control/decision logic

---

## Verified Baseline

### Detection

* **Model:** `runs/detect/train-16/weights/best.pt`
* **Architecture:** YOLOv8m
* **Confidence:** `0.30`
* **IoU:** `0.50`
* **imgsz:** `640`

The controlled confidence experiment D-07.44 did NOT justify changing the baseline.

### Tracking

* **Tracker:** ByteTrack
* **persist:** `True`
* Production tracking configuration unchanged
* No confirmed identity-switching implementation defect
* Current evaluator recorded `IDSW=0` under its evaluation conventions

> **Note:** `IDSW=0` is NOT proof of perfect tracking. It reflects the evaluation metric under the current evaluator conventions only.

### Trajectory

* Trajectory generated from runtime tracking observations
* `track_id` is tracker-local runtime identity
* Frame order preserved
* Timestamps preserved
* bbox and center observations preserved
* **No** interpolation
* **No** smoothing
* **No** velocity
* **No** acceleration
* **No** prediction
* **No** direction estimation
* **No** ROI event generation

---

## Dataset / Detection Findings

### Instance Counts

| Class | Train | Train % | Valid | Valid % |
|-------|-------|---------|-------|---------|
| bus | 431 | 0.9% | 42 | 1.3% |
| car | 21,706 | 45.5% | 1,193 | 35.8% |
| motorcycle | 23,187 | 48.6% | 1,939 | 58.1% |
| person | 546 | 1.1% | 0 | 0.0% |
| truck | 1,811 | 3.8% | 163 | 4.9% |
| **Total** | **47,681** | 100% | **3,337** | 100% |

### Explicit Findings

1. **Person zero validation:** Person having zero validation instances (546 train, 0 valid) is a **verified dataset characteristic**.

2. **Bus bounding box size:** Bus bounding boxes are very small as an **observed characteristic** (95% < 20px). This is NOT a confirmed causal explanation for zero bus detections.

3. **Validation reliability:** The validation image count (43 images, 3,337 instances) is NOT classified as automatically invalid or unreliable.

---

## Frame / Coordinate Conventions

### Frame Numbering

| Source | Convention |
|--------|------------|
| Decoded source stream | frames `0–620` |
| Source FPS | `15` |
| Runtime trajectory | frames `1–621` |
| Evaluation conversion | protocol frame `0` → TrackEval frame `1` |

> **Note:** The frame-index difference is an explicit convention handled at the evaluation boundary. Do NOT change the convention.

### Coordinate Spaces

| Space | Dimensions |
|-------|------------|
| Source coordinates | `1280 × 720` |
| Evaluation coordinates | `1020 × 500` |

---

## Identity Semantics

**`track_id` ≠ `global_id`**

| Concept | Definition |
|---------|------------|
| `track_id` | Runtime ByteTrack identity (assigned per video run, non-deterministic) |
| `global_id` | GT identity concept for future identity association |

* Operational cross-track Global Identity Association is NOT implemented
* This is intentional and remains outside the current baseline scope

---

## Known Minor Issues

1. **Configuration confidence:** Current configuration was observed with confidence `0.20`, while the evaluated frozen baseline is `0.30`.

2. **Frame numbering:** Runtime trajectory uses 1-based frame numbering while GT/evaluation uses 0-based numbering.

> **Note:** These were identified as known consistency/documentation issues in D-07.53 and were not judged blocking.

---

## Audit Status Chain

| Audit | Status | Resolution |
|-------|--------|------------|
| D-07.43 | PASS | Controlled Detection experiment design |
| D-07.44 | PASS | Confidence experiment |
| D-07.45 | PASS | Model/training provenance |
| D-07.46 | PASS | Class remapping verification |
| D-07.47 | FAIL | Evaluation mapping audit (clarified by D-07.48/D-07.49) |
| D-07.48 | PASS | Class universe audit |
| D-07.49 | PASS | Detection vs Tracking evaluation boundary |
| D-07.50 | CORRECTED | Dataset/annotation audit (corrected percentages) |
| D-07.51 | FAIL | Audit consistency check (corrections identified) |
| D-07.52 | PASS | Corrected audit record |
| D-07.53 | PASS | Final Detection → Tracking → Trajectory consistency audit |

---

## Freeze Decision

**BASELINE_FREEZE: YES**

This means:

* No changes to the current baseline unless a separately authorized experiment is opened
* Future Detection improvements must be controlled experiments
* Future Tracking improvements must be controlled experiments
* Future Trajectory changes must be separately justified and evaluated

> **Freeze does NOT mean the baseline is perfect.**

---

## Strict No-Change Rules

Do NOT:

* modify source code
* modify model weights
* modify configuration
* retrain
* modify annotations
* modify dataset splits
* change ByteTrack
* change trajectory logic
* change evaluation protocol
* implement Global Identity Association
* implement ROI Events
* implement Traffic State
* implement Spatio-Temporal Graph
* implement Traffic Flow Analysis
* create annotated video output

---

## Next Boundary

ROI Events (out of scope for this baseline)

# PROJECT SCOPE STATUS RECONCILIATION

**Date:** 2026-09-19

---

## 1. Official Research Title

**"Ứng dụng YoLov8 để phân tích và theo dõi lưu lượng giao thông theo thời gian thực"**

---

## 2. Current Research Boundary

The current research scope ends at **Trajectory**.

The following remain **OUT OF SCOPE**:
- ROI Events
- Traffic State
- Spatio-Temporal Graph
- Traffic Flow Analysis
- Real-time Evaluation
- Traffic Control / Policy

---

## 3. Pipeline Architecture

```
Video → Temporal Sampling → Object Detection → Multi-Object Tracking → Global Identity → Trajectory
```

---

## 4. Status Table (Tiers 1–5)

| Tier | Stage | Status | Evidence Source |
|------|-------|--------|-----------------|
| Tier 1 | Data Foundation | VALIDATED_OPEN | TIER_1_DATA_FOUNDATION_VALIDATION.md |
| Tier 2 | Object Detection | EVALUATED | TIER_2_DETECTION_CLOSURE.md |
| Tier 3 | Multi-Object Tracking | EVALUATED | TIER_3_TRACKING_CLOSURE.md |
| Tier 4 | Global Identity | CLOSED | GI_08_EVALUATION_CLOSURE.md |
| Tier 5 | Trajectory | VALID | PIPELINE_EVIDENCE_CLOSURE.md |

---

## 5. Evidence Basis for Each Tier

### Tier 1 — Data Foundation

**Status:** VALIDATED_OPEN

**Evidence:**
- Video source: public/3.mp4 (621 frames, 15 FPS)
- Dataset: My-First-Project-4 (train/valid/test splits)
- Ground truth: annotation/data/tracking_ground_truth.json
- Annotation schema: Defined in PHASE_1_3A_GROUND_TRUTH_SPEC.md

**Key Metrics:**
| Split | Images | Boxes |
|-------|--------|-------|
| Train | 2,309 | 47,681 |
| Valid | 43 | 3,337 |
| Test | 21 | 1,607 |

### Tier 2 — Object Detection

**Status:** EVALUATED

**Evidence:**
- Baseline: YOLOv8m, checkpoint: runs/detect/train-16/weights/best.pt
- Configuration: confidence=0.30, IoU=0.50, image size=640
- Evaluation: D-03 Detection Model Evaluation Protocol

**Key Metrics:**
| Metric | Value |
|--------|-------|
| mAP@0.5 | ~0.68 |
| mAP@0.5:0.95 | ~0.32 |
| Precision | ~0.22 |
| Recall | ~0.86 |

### Tier 3 — Multi-Object Tracking

**Status:** EVALUATED

**Evidence:**
- Tracker: ByteTrack (persist=True, stale_frames=30)
- Protocol: D-06.10 Tracking Evaluation Protocol
- Runtime artifact: outputs/trajectory.json

**Key Metrics:**
| Metric | Value |
|--------|-------|
| Trajectories | 25 |
| Observations | 4,532 |
| IDSW (evaluator convention) | 0 |
| Temporal gaps | 11 |

### Tier 4 — Global Identity

**Status:** CLOSED

**Evidence:**
- Evaluation: GI-08 Evaluation Closure
- Methodology: D1–D8 criteria frozen

**Key Metrics:**
| Metric | Value |
|--------|-------|
| Runtime global IDs | 15 |
| Confirmed | 10 |
| Provisional | 5 |
| Matched observations | 2,039 |
| ID Preserved Score | 0.9259 |
| Fragmented GT identities | 0 |
| Merged runtime global IDs | 3 |
| Confirmed GI ID switches (D8) | 0 |

### Tier 5 — Trajectory

**Status:** VALID

**Evidence:**
- Artifact: outputs/trajectory.json (GI-integrated)
- Validation: PIPELINE_EVIDENCE_CLOSURE

**Key Metrics:**
| Metric | Value |
|--------|-------|
| Trajectories | 25 |
| Observations | 4,532 |
| Unique track_ids | 25 |
| Frame range | 1–621 |
| Global_id coverage | 100% |
| Temporal gaps | 11 |

---

## 6. Important Limitations for Each Tier

### Tier 1 — Data Foundation

1. **Dataset expansion allowed:** The dataset is NOT permanently frozen. Future controlled expansion is permitted under the established protocol.
2. **Person class:** Zero instances in validation/test splits (only in training).
3. **Class imbalance:** Car + motorcycle comprise >94% of all instances.
4. **Single video:** All evaluation on one video (3.mp4), no generalization evidence.

### Tier 2 — Object Detection

1. **Reproducibility limitation:** Exact training hardware, duration, and augmentation parameters not available.
2. **High false positive rate:** FP/TP ratio ~3.5:1, precision ~22%.
3. **Bus detection:** Zero runtime detections observed (small object challenge).
4. **Person class:** Cannot be evaluated (no validation/test ground truth).

### Tier 3 — Multi-Object Tracking

1. **IDSW interpretation:** IDSW = 0 under evaluator convention does NOT prove zero physical identity errors.
2. **No Re-ID:** ByteTrack uses motion-only association, no appearance-based matching.
3. **Track fragmentation:** 11 temporal gaps observed (may be detection-related).
4. **Non-deterministic:** track_id assignments vary across runs.

### Tier 4 — Global Identity

1. **ID Preserved Score scope:** 0.9259 is calculated over matched observations only (2,039/2,039), NOT overall Global Identity accuracy. 1,976 runtime observations were unmatched.
2. **Merge cases:** 3 merged runtime global IDs remain.
3. **Provisional identities:** 5 runtime global IDs are provisional.
4. **IDSW limitation:** 0 confirmed GI ID switches (D8 criterion) does not mean zero possible identity errors in unmatched observations or under different evaluation criteria.

### Tier 5 — Trajectory

1. **track_id as primary key:** track_id remains the trajectory primary key; global_id is stored per observation.
2. **Temporal gaps:** 11 gaps observed in trajectory data.
3. **No perfect reconstruction claim:** The trajectory represents runtime observations with documented gaps, not a claim of perfect reconstruction.

---

## 7. Tier 1 Dataset Expansion Statement

> **The dataset remains open for controlled future expansion.**

The current dataset state is validated and documented. Dataset expansion is a planned future activity under the established protocol. Any expansion must:
- Maintain the same class universe (5 classes: bus, car, motorcycle, person, truck)
- Follow the same annotation schema
- Preserve train/valid/test partition integrity
- Document new dataset version

This validation represents a point-in-time assessment, not a permanent freeze.

---

## 8. Downstream Tiers Statement

> **Tiers 6 and beyond are outside the current research scope.**

The following stages have NOT been implemented or evaluated:
- ROI Events
- Traffic State
- Spatio-Temporal Graph
- Traffic Flow Analysis
- Real-time Evaluation

---

## 9. Cross-Tier Consistency Check

| Consistency Check | Status |
|-------------------|--------|
| Pipeline architecture consistent across all tiers | PASS |
| track_id ≠ global_id distinction maintained | PASS |
| ID Preserved Score scope (matched observations only) preserved | PASS |
| IDSW = 0 interpretation preserved (not zero errors) | PASS |
| Tier 1 open status preserved (not permanently frozen) | PASS |
| Global Identity CLOSED status preserved | PASS |
| Trajectory VALID status preserved | PASS |
| Limitations preserved across all tiers | PASS |

**CROSS_TIER_CONSISTENCY: PASS**

---

## 10. Final Current-Scope Status

| Tier | Stage | Status |
|------|-------|--------|
| Tier 1 | Data Foundation | VALIDATED_OPEN |
| Tier 2 | Object Detection | EVALUATED |
| Tier 3 | Multi-Object Tracking | EVALUATED |
| Tier 4 | Global Identity | CLOSED |
| Tier 5 | Trajectory | VALID |

The research pipeline is complete through **Trajectory** (Tier 5). All tiers have documented evidence, established baselines, and preserved limitations.

---

RESULT: PASS
CURRENT_SCOPE_END: TRAJECTORY
TIER_1_STATUS: VALIDATED_OPEN
TIER_2_STATUS: EVALUATED
TIER_3_STATUS: EVALUATED
TIER_4_STATUS: CLOSED
TIER_5_STATUS: VALID
TIER_1_DATASET_EXPANSION_ALLOWED: YES
CROSS_TIER_CONSISTENCY: PASS
DOWNSTREAM_TIERS_ASSESSED: NO
DOCUMENT_CREATED: docs/PROJECT_SCOPE_STATUS_RECONCILIATION.md
SOURCE_CHANGES: NO
TEST_CHANGES: NO
GT_CHANGES: NO
RUNTIME_ARTIFACT_CHANGES: NO

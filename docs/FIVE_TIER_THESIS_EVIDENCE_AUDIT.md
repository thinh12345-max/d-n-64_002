# FIVE-TIER THESIS EVIDENCE SUFFICIENCY AUDIT

**Date:** 2026-09-19

---

## 1. Official Research Title

**"Ứng dụng YoLov8 để phân tích và theo dõi lưu lượng giao thông theo thời gian thực"**

---

## 2. Current Scope Boundary

The current research scope ends at **Trajectory** (Tier 5).

Pipeline:
```
Video → Temporal Sampling → Object Detection → Multi-Object Tracking → Global Identity → Trajectory
```

Out of scope: ROI Events, Traffic State, Spatio-Temporal Graph, Traffic Flow Analysis, Real-time Evaluation

---

## 3. Evidence-Readiness Table (Tiers 1–5)

| Tier | Stage | Thesis-Readiness Status | Evidence Source |
|------|-------|------------------------|-----------------|
| Tier 1 | Data Foundation | SUFFICIENT_WITH_LIMITATIONS | TIER_1_DATA_FOUNDATION_VALIDATION.md |
| Tier 2 | Object Detection | SUFFICIENT_WITH_LIMITATIONS | TIER_2_DETECTION_CLOSURE.md |
| Tier 3 | Multi-Object Tracking | SUFFICIENT_WITH_LIMITATIONS | TIER_3_TRACKING_CLOSURE.md |
| Tier 4 | Global Identity | SUFFICIENT_FOR_THESIS | GI_08_EVALUATION_CLOSURE.md |
| Tier 5 | Trajectory | SUFFICIENT_FOR_THESIS | PIPELINE_EVIDENCE_CLOSURE.md |

---

## 4. Evidence Available for Each Tier

### TIER 1 — DATA FOUNDATION

**Thesis-Readiness Status:** SUFFICIENT_WITH_LIMITATIONS

**Evidence Available:**
| Dimension | Status |
|-----------|--------|
| Data provenance | ✅ public/3.mp4 documented |
| Frame/source information | ✅ 621 frames, 15 FPS |
| Temporal sampling protocol | ✅ Full frame rate |
| Partition/split rules | ✅ Train/Valid/Test defined |
| Annotation schema | ✅ Defined in PHASE_1_3A_GROUND_TRUTH_SPEC.md |
| Class definitions | ✅ 5 classes (bus, car, motorcycle, person, truck) |
| Leakage control | ✅ Temporal block splitting |
| Dataset characteristics | ✅ Split statistics documented |
| Relationship to Detection | ✅ Dataset supports Tier 2 |

**Quantitative Evidence:**
| Split | Images | Boxes |
|-------|--------|-------|
| Train | 2,309 | 47,681 |
| Valid | 43 | 3,337 |
| Test | 21 | 1,607 |

**Critical Limitations to Report:**
1. Dataset remains **VALIDATED_OPEN** — not permanently frozen, may expand
2. Person class: 0 instances in Valid/Test (546 in Train only)
3. Class imbalance: Car + Motorcycle >94%
4. Single video source: no generalization evidence

**Missing Evidence Items:** None that prevent thesis writing. The openness is a documented characteristic, not a gap.

---

### TIER 2 — OBJECT DETECTION

**Thesis-Readiness Status:** SUFFICIENT_WITH_LIMITATIONS

**Evidence Available:**
| Dimension | Status |
|-----------|--------|
| Model/baseline configuration | ✅ YOLOv8m documented |
| Model provenance | ✅ Checkpoint: runs/detect/train-16/weights/best.pt |
| Dataset relationship | ✅ My-First-Project-4 |
| Class universe | ✅ 5 classes consistent |
| Evaluation evidence | ✅ D-03 protocol |
| Quantitative results | ✅ mAP, Precision, Recall |
| Per-class behavior | ✅ Documented |
| Known limitations | ✅ Documented |
| Reproducibility | ⚠️ Partial (hardware/duration not available) |

**Quantitative Evidence:**
| Metric | Value |
|--------|-------|
| mAP@0.5 | ~0.68 |
| mAP@0.5:0.95 | ~0.32 |
| Precision | ~0.22 |
| Recall | ~0.86 |

**Per-Class Evidence:**
| Class | Precision | Recall |
|-------|-----------|--------|
| bus | 0.159 | 0.857 |
| car | 0.190 | 0.895 |
| motorcycle | 0.259 | 0.847 |
| truck | 0.183 | 0.804 |
| person | N/A | N/A |

**Critical Limitations to Report:**
1. High false positive rate (FP/TP ~3.5:1)
2. Bus detection: Zero runtime detections (small object challenge)
3. Person class: Cannot be evaluated (no Valid/Test ground truth)
4. Reproducibility: Exact training hardware/duration not available
5. Baseline is NOT claimed as optimal

**Missing Evidence Items:** None that prevent thesis writing. The reproducibility gap is a documented limitation to acknowledge.

---

### TIER 3 — MULTI-OBJECT TRACKING

**Thesis-Readiness Status:** SUFFICIENT_WITH_LIMITATIONS

**Evidence Available:**
| Dimension | Status |
|-----------|--------|
| ByteTrack configuration | ✅ persist=True, stale_frames=30 |
| Runtime integration | ✅ Detection → Tracking pipeline |
| Tracking protocol | ✅ D-06.10 defined |
| Tracking evaluation | ✅ MOTA, MOTP, IDF1, IDSW |
| IDSW evidence | ✅ 0 (evaluator convention) |
| Fragmentation/gap evidence | ✅ 11 temporal gaps |
| Limitations | ✅ Documented |
| Reproducibility | ✅ Config available |

**Quantitative Evidence:**
| Metric | Value |
|--------|-------|
| Trajectories | 25 |
| Observations | 4,532 |
| IDSW | 0 (evaluator convention) |
| Temporal gaps | 11 |

**Critical Limitations to Report:**
1. **IDSW = 0 interpretation:** Must state explicitly this is under evaluator convention and does NOT prove zero physical identity errors
2. No Re-ID/appearance matching: Motion-only association
3. Track fragmentation: 11 gaps (may be detection-related)
4. Non-deterministic track_ids across runs
5. **CRITICAL:** Do NOT present Global Identity fragmentation metrics as ByteTrack fragmentation results

**Missing Evidence Items:** None that prevent thesis writing.

---

### TIER 4 — GLOBAL IDENTITY

**Thesis-Readiness Status:** SUFFICIENT_FOR_THESIS

**Evidence Available:**
| Dimension | Status |
|-----------|--------|
| Motivation for Global Identity | ✅ Documented in GI spec |
| Runtime implementation | ✅ Identity registry |
| Association baseline | ✅ Hungarian matching (IoU≥0.50) |
| Identity registry | ✅ 15 runtime global IDs |
| Provisional identity semantics | ✅ 5 provisional documented |
| Runtime artifact | ✅ outputs/trajectory.json |
| Evaluation protocol | ✅ D1-D8 criteria |
| Quantitative evaluation | ✅ Complete metrics |
| Fragmentation | ✅ 0 fragmented GT identities |
| Merge | ✅ 3 merged runtime global IDs |
| ID-switch analysis | ✅ 0 confirmed (D8) |
| Limitations | ✅ Documented |

**Quantitative Evidence:**
| Metric | Value |
|--------|-------|
| Runtime global IDs | 15 |
| Confirmed | 10 |
| Provisional | 5 |
| Matched observations | 2,039 |
| Unmatched runtime observations | 1,976 |
| ID Preserved Score | 0.9259 |
| Fragmented GT identities | 0 |
| Merged runtime global IDs | 3 |
| Confirmed GI ID switches (D8) | 0 |

**Critical Limitations to Report:**
1. **ID Preserved Score scope:** 0.9259 is over matched observations (2,039) only — NOT overall Global Identity accuracy
2. 1,976 runtime observations unmatched and excluded from denominator
3. 3 merge cases remain
4. 5 provisional identities
5. **CRITICAL:** 0 confirmed ID switches (D8) does NOT mean perfect identity preservation

**Missing Evidence Items:** None.

---

### TIER 5 — TRAJECTORY

**Thesis-Readiness Status:** SUFFICIENT_FOR_THESIS

**Evidence Available:**
| Dimension | Status |
|-----------|--------|
| Trajectory construction | ✅ Documented |
| track_id as primary key | ✅ Verified |
| Per-observation global_id | ✅ 100% coverage |
| Temporal ordering | ✅ Timestamp validated |
| Frame coverage | ✅ Frames 1-621 |
| Temporal gaps | ✅ 11 gaps documented |
| Required observation fields | ✅ Defined |
| Cross-artifact traceability | ✅ Verified |
| Limitations | ✅ Documented |

**Quantitative Evidence:**
| Metric | Value |
|--------|-------|
| Trajectories | 25 |
| Observations | 4,532 |
| Unique track_ids | 25 |
| Frame range | 1–621 |
| Global_id coverage | 100% |
| Temporal gaps | 11 |

**Critical Limitations to Report:**
1. track_id is primary key; global_id is per-observation field
2. 11 temporal gaps present
3. No claim of perfect trajectory reconstruction

**Missing Evidence Items:** None.

---

## 5. Cross-Tier Traceability Assessment

| Check | Status |
|-------|--------|
| Tier 1 → Tier 2: Data supports Detection | PASS |
| Tier 2 → Tier 3: Detection → Tracking interface | PASS |
| Tier 3 → Tier 4: track_id → global_id association | PASS |
| Tier 4 → Tier 5: global_id integrated into trajectory | PASS |
| Quantitative results traceable to stage | PASS |
| Limitations not converted to positive claims | PASS |
| No tier-jumping evidence misinterpretation | PASS |

**CROSS_TIER_TRACEABILITY: PASS**

---

## 6. Overall Thesis Evidence Status

| Tier | Status | Rationale |
|------|--------|------------|
| Tier 1 | SUFFICIENT_WITH_LIMITATIONS | Dataset is VALIDATED_OPEN (not frozen) — this is a documented characteristic, not a gap |
| Tier 2 | SUFFICIENT_WITH_LIMITATIONS | Reproducibility partial, baseline not optimal — limitations to document |
| Tier 3 | SUFFICIENT_WITH_LIMITATIONS | IDSW interpretation must be explicit, no GI metrics misinterpretation |
| Tier 4 | SUFFICIENT_FOR_THESIS | Complete evidence, limitations documented |
| Tier 5 | SUFFICIENT_FOR_THESIS | Complete evidence, limitations documented |

**Overall Status:** THESIS_EVIDENCE_SUFFICIENT_WITH_LIMITATIONS

---

## 7. Remaining Evidence Tasks

**None required.**

All tiers have sufficient evidence to write defensible thesis sections. The "limitations" noted above are documented characteristics that must be explicitly reported in the thesis, not tasks to complete.

---

## 8. Important Notes for Thesis Writing

1. **Tier 1 openness:** The VALIDATED_OPEN status is a feature, not a bug. Document the current state while acknowledging future expansion possibility.

2. **Tier 2 baseline:** Explicitly state this is a baseline, not an optimized solution. Acknowledge reproducibility limitations.

3. **Tier 3 IDSW:** MUST explicitly state "IDSW = 0 under the evaluator convention (D06.10), which does not prove zero physical identity errors."

4. **Tier 4 ID Preserved Score:** MUST state "0.9259 among matched runtime observations (2,039), NOT overall accuracy. 1,976 observations were unmatched."

5. **Tier 5 trajectory:** Do not claim perfect reconstruction. Document the 11 temporal gaps.

---

RESULT: PASS
OVERALL_THESIS_EVIDENCE_STATUS: THESIS_EVIDENCE_SUFFICIENT_WITH_LIMITATIONS
TIER_1_EVIDENCE: SUFFICIENT_WITH_LIMITATIONS
TIER_2_EVIDENCE: SUFFICIENT_WITH_LIMITATIONS
TIER_3_EVIDENCE: SUFFICIENT_WITH_LIMITATIONS
TIER_4_EVIDENCE: SUFFICIENT_FOR_THESIS
TIER_5_EVIDENCE: SUFFICIENT_FOR_THESIS
CRITICAL_EVIDENCE_MISSING: NO
CROSS_TIER_TRACEABILITY: PASS
TIER_1_REMAINS_OPEN: YES
DOWNSTREAM_TIERS_ASSESSED: NO
DOCUMENT_CREATED: docs/FIVE_TIER_THESIS_EVIDENCE_AUDIT.md
SOURCE_CHANGES: NO
TEST_CHANGES: NO
GT_CHANGES: NO
RUNTIME_ARTIFACT_CHANGES: NO

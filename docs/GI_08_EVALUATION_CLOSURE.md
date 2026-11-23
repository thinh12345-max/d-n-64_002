# GI-08 — GLOBAL IDENTITY EVALUATION CLOSURE

**Status:** CLOSED — EVIDENCE FROZEN

---

## AUTHORITATIVE DECISIONS (UNCHANGED)

| Decision | Value |
|----------|-------|
| D1 | IoU >= 0.50 |
| D2 | Hungarian one-to-one |
| D3 | Runtime visibility unavailable |
| D4 | Runtime occlusion unavailable |
| D5 | Aggregate + per-class |
| D6 | Minimum 1 observation |
| D7 | Timestamp-based temporal alignment |
| D8 | GT-validated continuity |

---

## MATCHING RESULTS

| Metric | Value |
|--------|-------|
| Total runtime observations | 4,015 |
| Total GT observations | 3,186 |
| Matched observations | 2,039 |
| Unmatched runtime observations | 1,976 |

**Accounting:** 2,039 + 1,976 = 4,015

---

## ID PRESERVED SCORE

| Metric | Value |
|--------|-------|
| Consistent matched observations | 1,888 |
| Matched observations | 2,039 |
| ID Preserved Score | 0.9259 (92.59%) |

**Important:** This score is calculated over matched runtime observations only. It is NOT overall Global Identity accuracy.

---

## FRAGMENTATION

| Metric | Value |
|--------|-------|
| GT identities analyzed | 22 |
| Fragmented GT identities | 0 |

---

## MERGE

| Metric | Value |
|--------|-------|
| Merged runtime global IDs | 3 |

**Merged IDs and corresponding GT identity groups:**

| Runtime Global ID | Matched GT Identities |
|-------------------|----------------------|
| G001 | GT_017, GT_021, GT_023 |
| G002 | GT_018, GT_019, GT_020 |
| G003 | GT_026, GT_027, GT_028, GT_029, GT_030, GT_031, GT_032 |

---

## PROVISIONAL IDENTITIES

| Metric | Value |
|--------|-------|
| Total runtime global IDs | 15 |
| Confirmed | 10 |
| Provisional | 5 |

**Confirmed:** G001, G002, G003, G007, G010, G011, G012, G013, G014, G015

**Provisional:** G004, G005, G006, G008, G009

**Note:** Provisional status is reported separately and is not automatically treated as an error.

---

## PER-CLASS RESULTS

| Class | Matched Observations | ID Preserved Score |
|-------|---------------------|-------------------|
| car | 1,491 | 0.9987 |
| motorcycle | 456 | 0.9189 |
| bus | 92 | 0.5652 |
| truck | 0 | N/A |

---

## ID SWITCH ANALYSIS (D8)

| Metric | Value |
|--------|-------|
| GT identities analyzed | 22 |
| Candidate transitions | 0 |
| Confirmed GI ID switches | 0 |
| Upstream gap/unresolved | 0 |
| Insufficient GT evidence | 0 |

**Interpretation:** No confirmed Global Identity ID switches were detected under the D8 GT-validated continuity criterion.

---

## CROSS-METRIC AUDIT

**GI_08.11_AUDIT_STATUS: PASS**

The independent audit confirmed consistency among:
- Frame-level matching
- ID Preserved Score
- Fragmentation
- Merge
- Provisional handling
- Per-class reporting
- GT-validated ID-switch analysis
- Deterministic repeated evaluation

---

## LIMITATIONS

1. The ID Preserved Score applies only to matched observations.
2. 1,976 runtime observations were unmatched and therefore are not represented in the ID Preserved Score denominator.
3. Zero detected ID switches does not establish perfect real-world identity accuracy.
4. Three merge cases remain present.
5. Runtime visibility and occlusion fields are unavailable.
6. Re-identification/appearance-based matching was not implemented.
7. Parameter optimization was not performed.
8. The evaluation does not establish generalization beyond the evaluated video/data.
9. GT identities were used for evaluation only and were never assigned to runtime global IDs.

---

## RESEARCH SCOPE

Global Identity is evaluated as the architectural stage:

`Multi-Object Tracking → Global Identity → Trajectory`

The evaluation does not introduce a new research-pipeline stage.

The current research scope remains:

`Video → Temporal Sampling → Object Detection → Multi-Object Tracking → Global Identity → Trajectory`

This scope does NOT include:
- ROI Events
- Traffic State
- Spatio-Temporal Graph
- Traffic Flow Analysis
- Real-time Evaluation
- Traffic Control/Policy

---

## EVIDENCE FREEZE

| Status | Value |
|--------|-------|
| GI_08_EVALUATION_STATUS | CLOSED |
| GI_08_EVIDENCE_FREEZE | YES |
| GI_08_IMPLEMENTATION_STATUS | COMPLETE |
| GI_08_METHODOLOGY_STATUS | CLOSED |
| GI_08_FURTHER_METRICS_REQUIRED | NO |

The evidence freeze means the current GI-08 results are frozen as the evaluated baseline. Future experiments must be treated as separate experiments and must not silently overwrite these results.

---

## VERIFICATION CHECKLIST

- [x] All GI-08.8–GI-08.11 results represented
- [x] Numerical values exactly preserved
- [x] D1–D8 unchanged
- [x] Limitation statements present
- [x] Research-scope boundary preserved
- [x] Evidence-freeze status explicit
- [x] No source code changed
- [x] No tests changed
- [x] No GT data changed
- [x] No runtime artifacts changed

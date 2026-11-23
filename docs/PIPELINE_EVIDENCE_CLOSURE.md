# PIPELINE EVIDENCE CLOSURE

**Status:** CLOSED — EVIDENCE FROZEN

---

## PIPELINE BOUNDARY

The authoritative current research pipeline is:

`Video → Temporal Sampling → Object Detection → Multi-Object Tracking → Global Identity → Trajectory`

The current research scope ends at:

`Trajectory`

The following remain OUT OF SCOPE:

- ROI Events
- Traffic State
- Spatio-Temporal Graph
- Traffic Flow Analysis
- Real-time Evaluation
- Traffic Control / Policy

---

## STAGE STATUS

### Temporal Sampling

**Status:** CLOSED

- Production pipeline uses full source frame rate
- Dataset sampling is construction/evaluation protocol only
- Established sampling protocol remains authoritative
- No low-change frame removal is part of the production pipeline

### Object Detection

**Status:** FROZEN

Baseline configuration:

| Parameter | Value |
|-----------|-------|
| Model | YOLOv8m |
| Weights | best.pt |
| Confidence | 0.30 |
| IoU | 0.50 |
| Image size | 640 |
| Classes | bus, car, motorcycle, person, truck |

**Limitations:** Prior evaluation showed substantial detection false positives/false negatives and class-specific limitations. Confidence 0.30 is not claimed to be globally optimal.

### Multi-Object Tracking

**Status:** EVALUATED

| Parameter | Value |
|-----------|-------|
| Tracker | ByteTrack |
| persist | True |
| track_id | Runtime identity |

**Note:** Previous evaluation reported IDSW = 0 under the evaluator convention. `IDSW = 0` does not by itself prove perfect physical identity preservation across track_id changes.

### Global Identity

**Status:** CLOSED

Closed GI-08 evidence:

| Metric | Value |
|--------|-------|
| Runtime global IDs | 15 |
| Confirmed | 10 |
| Provisional | 5 |
| Runtime observations | 4,015 |
| GT observations | 3,186 |
| Matched observations | 2,039 |
| Unmatched runtime observations | 1,976 |
| ID Preserved Score | 0.9259 |
| Fragmented GT identities | 0 |
| Merged runtime global IDs | 3 |
| Confirmed GI ID switches (D8) | 0 |

**Confirmed IDs:** G001, G002, G003, G007, G010, G011, G012, G013, G014, G015

**Provisional IDs:** G004, G005, G006, G008, G009

**GI-08 methodology:** CLOSED

**GI-08 evidence freeze:** YES

**Important:** The 0.9259 score is calculated only over matched observations and is NOT overall Global Identity accuracy.

### Trajectory

**Status:** VALID

GI-integrated artifact:

| Metric | Value |
|--------|-------|
| Trajectories | 25 |
| Observations | 4,532 |
| Unique track_ids | 25 |
| Global_id coverage | 4,532 / 4,532 |
| Frame range | 1–621 |
| Duplicate (track_id, frame_id) pairs | 0 |
| Temporal gaps | 11 |
| Timestamp ordering | PASS |
| GT identity leakage | NO |

**Key design:** `track_id` remains the primary trajectory key; `global_id` is stored PER_OBSERVATION.

GI-09.02 reconciliation:

- Current independently calculated gaps: 11
- Reported gaps: 11
- Reconciliation: MATCH
- Historical baseline artifact unavailable
- Historical baseline: 4,114 observations, 25 trajectories, 26 gaps
- Historical regression conclusion: NOT_DETERMINABLE

---

## CROSS-STAGE INTEGRITY

Established boundaries:

1. GT identities are evaluation-only.
2. Runtime global IDs are distinct from GT IDs.
3. `track_id` remains the Trajectory primary key.
4. `global_id` is an observation-level identity field.
5. Detection, Tracking, Global Identity, and Trajectory errors remain analytically separate.
6. No downstream graph or traffic-flow processing has been introduced.

---

## CURRENT EVIDENCE STATUS

| Status | Value |
|--------|-------|
| PIPELINE_EVIDENCE_STATUS | CLOSED |
| PIPELINE_EVIDENCE_FREEZE | YES |
| CURRENT_SCOPE_END | TRAJECTORY |
| DOWNSTREAM_IMPLEMENTATION_STATUS | NOT_STARTED |

This closure freezes the current evidence state, not the claim of perfect real-world performance. Future experiments must create separate evidence records and must not silently overwrite this closure.

---

## LIMITATIONS

- Detection quality remains imperfect.
- Detection and tracking metrics are dataset/evaluator dependent.
- Global Identity evaluation excludes unmatched runtime observations from the ID Preserved Score denominator.
- Three merge cases remain in the evaluated Global Identity result.
- Five runtime global IDs are provisional.
- Zero confirmed GI ID switches is specific to the D8 criterion and evaluated data.
- Historical pre-GI Trajectory artifact is unavailable for direct regression comparison.
- Real-world physical identity accuracy is not established.
- Re-ID/appearance matching is not implemented.
- Parameter optimization is not part of the current frozen evidence.
- Downstream traffic-state, graph, flow-analysis, and control stages are not implemented.

---

## VERIFICATION CHECKLIST

- [x] All required evidence sources read
- [x] Numerical values exactly preserved
- [x] Pipeline boundary exactly recorded
- [x] Stage status accurately represented
- [x] Cross-stage integrity boundaries preserved
- [x] Limitation statements present
- [x] Evidence-freeze status explicit
- [x] No source code changed
- [x] No tests changed
- [x] No GT data changed
- [x] No runtime artifacts changed

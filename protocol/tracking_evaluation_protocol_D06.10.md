# D-06.10 — TRACKING EVALUATION PROTOCOL SPECIFICATION

**Version:** 1.0
**Status:** LOCKED
**Based on:** D-06.09 and D-06.09C Human Scientific Decisions

---

## 1. PURPOSE AND SCOPE

This protocol defines the evaluation methodology for the multi-object tracking (MOT) system in the YOLOv8-based traffic tracking project. The protocol specifies how runtime ByteTrack output is compared against Tracking Ground Truth (GT) to compute standard MOT metrics.

**Scope:**
- Tracking evaluation only (detector evaluation is separate)
- Single-video evaluation (3.mp4, 621 frames at 15 FPS)
- Global identity tracking (GT global_id) vs. tracker-local identity (track_id)
- Whole-video aggregation primary; per-class secondary

**Out of Scope:**
- ROI event detection
- Traffic state analysis
- Spatio-temporal graph construction
- Traffic flow analysis
- Prediction
- Real-time evaluation

---

## 2. EVALUATION UNIT

| Unit | Definition |
|------|------------|
| **Video** | Complete 3.mp4 (621 frames, 0–620) |
| **Frame** | Individual source frame indexed 0 to 620 |
| **Object Instance** | Bounding box with class label in a single frame |
| **Track** | Temporal sequence of object instances with consistent identity |
| **Identity** | GT global_id = persistent physical-object identity across video; runtime track_id = tracker-local identity |

---

## 3. INPUTS

### 3.1 Tracking Ground Truth (JSON)

| Field | Type | Description |
|-------|------|-------------|
| global_id | string | Persistent identity "GT_XXX" (zero-padded) |
| class | string | Object class: car, motorcycle, bus, truck, person |
| start_frame | integer | First frame where object appears (annotated) |
| end_frame | integer | Last frame where object appears (annotated) |
| frames[] | array | Per-frame observations with visibility > 0 |

### 3.2 Per-Frame GT Entry (frames[] element)

| Field | Type | Description |
|-------|------|-------------|
| frame_id | integer | Frame index (0–620) |
| timestamp | number | frame_id / 15.0 (seconds) |
| bbox | array | [x1, y1, x2, y2] in 1020×500 space |
| center | array | [cx, cy] derived center point |
| visibility | number | Visible fraction (0.0–1.0), NOT present for visibility=0 |
| occlusion | integer | 0=none, 1=partial, 2=heavy, 3=severe |
| truncated | boolean | True if bbox touches frame boundary |

### 3.3 Runtime ByteTrack Output

| Field | Type | Description |
|-------|------|-------------|
| frame_id | integer | Frame index |
| track_id | integer | Tracker-local identity (not global_id) |
| bbox | array | [x1, y1, x2, y2] |
| class | string | Predicted class |
| confidence | number | Detection confidence |

---

## 4. FRAME CORRESPONDENCE

**Protocol:** Source frame 0 = runtime frame 0 = GT frame 0.

Every source frame (0–620) participates in evaluation. The evaluation operates on the complete frame sequence with no temporal subsampling for tracking evaluation purposes.

---

## 5. GROUND-TRUTH TRACK SEMANTICS

### 5.1 Track Identity

- **global_id**: Persistent physical-object identity spanning the entire video. The same physical object retains the same global_id when sufficient observable evidence supports continuity (appearance, vehicle class, spatial continuity, movement/direction, temporal continuity, reappearance after occlusion).

### 5.2 Temporal Extent

- **start_frame**: First frame where the object appears (annotated, visible)
- **end_frame**: Last frame where the object appears (annotated, visible)
- **Full existence interval**: start_frame ≤ frame_id ≤ end_frame defines the temporal extent in which the annotated physical object is considered to EXIST in the scene.

### 5.3 Visibility States

| State | Condition | Evaluation Treatment |
|-------|-----------|---------------------|
| **Visible annotated frame** | frame_id in frames[] | Standard matching against GT |
| **Visibility=0 gap** | start_frame ≤ frame_id ≤ end_frame AND frame_id NOT in frames[] | Object EXISTS but is FULLY INVISIBLE. Runtime detection = FP |
| **Before start_frame** | frame_id < start_frame | No GT claim; ignore |
| **After end_frame** | frame_id > end_frame | No GT claim; ignore |
| **Unknown presence** | Not covered by any GT track | Not equivalent to visibility=0 |

### 5.4 Visibility=0 Gap Semantics (Q5 LOCKED)

Per D-06.09C:

> A gap inside the temporal extent (start_frame ≤ frame_id ≤ end_frame) where the object is not represented in frames[] means: the physical object is still considered present; the object is fully invisible / not visually observable during that gap; the gap is therefore a visibility=0 interval, not an unknown/unannotated interval.

**Q5 Rule:** Runtime detections during a GT visibility=0 gap are treated as FALSE POSITIVES.

---

## 6. PREDICTION SEMANTICS

### 6.1 Tracker Output

- **track_id**: Tracker-local identity assigned by ByteTrack. This is NOT global_id.
- **bbox**: Predicted bounding box [x1, y1, x2, y2]
- **class**: Predicted object class
- **confidence**: Detection confidence score

### 6.2 ByteTrack Output as-Produced (Q4 LOCKED)

Use ByteTrack output as-produced. Do not re-run NMS during primary tracking evaluation.

---

## 7. FRAME-LEVEL MATCHING (Q1, Q2 LOCKED)

### 7.1 Matching Parameters

| Parameter | Value |
|-----------|-------|
| IoU threshold | **0.50** (Q1) |
| Algorithm | **Hungarian / Linear Sum Assignment** (Q2) |
| Matching type | One-to-one |

### 7.2 Matching Process

1. For each frame, compute pairwise IoU between all GT bboxes and all predicted bboxes
2. Build cost matrix (1 - IoU)
3. Apply Hungarian algorithm for optimal assignment
4. Assign matches where IoU ≥ 0.50
5. Unmatched GT = False Negative (FN)
6. Unmatched prediction = False Positive (FP)

### 7.3 Clarification

This matching algorithm is the **evaluator's algorithm** for computing MOTA/MOTP. It is independent of ByteTrack's internal association algorithm.

---

## 8. IDENTITY ASSOCIATION FOR EVALUATION

### 8.1 Identity Types

| Type | Scope | Description |
|------|-------|-------------|
| **GT global_id** | Video-wide | Persistent physical-object identity |
| **Runtime track_id** | Per-frame | Tracker-local identity from ByteTrack |

### 8.2 Evaluation-Time Association

During evaluation, runtime track_ids are matched against GT global_ids to compute identity-based metrics (IDF1, IDSW).

**Critical distinction:**
> THIS IS EVALUATION-TIME ASSOCIATION ONLY.
>
> It must NOT be called "runtime Global Identity Association."
>
> Runtime Global Identity Association (propagating global_id across frames in the tracker) remains unimplemented.

### 8.3 IDSW Definition (Q7 LOCKED)

Use the **Standard MOT IDSW convention**:
- IDSW occurs when a GT track changes its associated runtime track_id
- Do not redefine IDSW into a project-specific non-standard metric

---

## 9. VISIBILITY=0 HANDLING (Q5 LOCKED)

### 9.1 Formal Definition

For a GT identity with global_id G:
- Let T = {frame_id | start_frame ≤ frame_id ≤ end_frame}
- Let V = {frame_id in frames[] | visibility > 0}
- Let Gap = T \ V (frames in temporal extent but not in visible frames)

For any frame f ∈ Gap:
- The GT object is considered **physically present but fully invisible**
- Any runtime detection at frame f matching bbox criteria is counted as **False Positive**

### 9.2 Q5 Rule (LOCKED)

> Runtime detections during a GT visibility=0 gap are treated as FALSE POSITIVES.

### 9.3 What NOT to Count as Visibility=0

- Frames before start_frame
- Frames after end_frame
- Regions with no GT tracks
- Genuinely unknown presence

---

## 10. OCCLUSION HANDLING (Q6 LOCKED)

### 10.1 Primary Policy

**All occlusion levels are included in primary metrics.**

- occlusion = 0 (none)
- occlusion = 1 (partial, 1–50%)
- occlusion = 2 (heavy, >50–90%)
- occlusion = 3 (severe, >90%)

No occlusion level is excluded from MOTA/MOTP/IDF1 computation.

### 10.2 Secondary Analysis

Occlusion-stratified results may be reported as secondary analysis where sufficient GT exists.

---

## 11. TRACK BIRTH / TRACK DEATH

### 11.1 Predictions Before GT Start

Frame f where f < GT.start_frame:
- No GT exists → ignore (neither FP nor FN)

### 11.2 Predictions After GT End

Frame f where f > GT.end_frame:
- No GT exists → ignore (neither FP nor FN)

### 11.3 GT Objects Before First Matched Prediction

A GT track may have unmatched visible frames at its start → counted as FN.

### 11.4 GT Objects After Last Matched Prediction

A GT track may have unmatched visible frames at its end → counted as FN.

---

## 12. METRICS (Q10 LOCKED)

### 12.1 Primary Metrics

| Metric | Formula | Description |
|--------|---------|-------------|
| **MOTA** | 1 - (FN + FP + IDSW) / GT | Multi-object tracking accuracy |
| **MOTP** | Σ IoU_correct / N_correct | Localization accuracy |
| **IDF1** | Per established MOT evaluation convention | Identity preservation |

### 12.2 Secondary Diagnostics

| Metric | Description |
|--------|-------------|
| FN | False Negative (missed GT objects) |
| FP | False Positive (incorrect predictions) |
| IDSW | Identity Switches (Standard MOT definition) |
| **fragmentation** | One GT global_id matched to two+ runtime track_ids (Q8) |
| **merge** | Multiple GT global_ids matched to one runtime track_id (Q9) |

### 12.3 MOTA GT Unit Definition (LOCKED — D-06.11B)

**GT for the MOTA denominator means:** The total number of valid GT object instances evaluated at the frame level across the sequence.

- One frame containing N valid GT objects contributes N frame-level GT object instances to the denominator.
- This is NOT the number of unique global_id values.
- This is NOT a unique physical-object count.
- This is NOT a per-track count counted once per video.
- This is NOT the number of video frames.

This definition is consistent with:
- Frame-level matching (Section 7)
- FN = unmatched GT visible frames
- FP = unmatched predictions
- IDSW = Standard MOT identity switches
- Visibility=0 semantics: a visibility=0 gap does not add a visible GT instance to the denominator, but a runtime detection during that gap is still FP (Section 9)

### 12.4 MOTA Terms (Q8, Q9 LOCKED)

- **FN**: Unmatched GT visible frames
- **FP**: Unmatched predictions
- **IDSW**: Standard MOT identity switches

**Fragmentation and merge are NOT added as independent MOTA terms.** They are reported separately as diagnostics.

### 12.5 IDF1 Implementation Note

> Do NOT invent a custom IDF1 formula.
>
> IDF1 shall be computed according to an established MOT evaluation convention/reference implementation selected during the implementation stage.
>
> The evaluator (TrackEval, py-motmetrics, or another established MOT evaluation library) shall be selected at implementation time. This decision is deferred.

---

## 13. AGGREGATION (Q11 LOCKED)

### 13.1 Primary Aggregation

**Whole-video aggregate** is primary:
- Compute metrics across all frames (0–620)
- Single set of aggregate numbers per experiment

### 13.2 Secondary Aggregation

**Per-class results** are secondary:
- car, motorcycle, bus, truck, person (if annotated)
- Compute metrics for each class separately

### 13.3 Occlusion-Stratified

Occlusion-stratified results may be reported as secondary analysis where sufficient GT exists.

---

## 14. BASELINE AND COMPARATIVE EXPERIMENTS (Q3 LOCKED)

### 14.1 Baseline Definition

The **baseline** is the current production configuration:
- YOLOv8 detector (current model)
- ByteTrack tracker (current configuration)
- Current threshold settings
- No modifications

### 14.2 Comparative Experiments

A **comparative experiment** is an explicitly defined alternative configuration:
- Must document all changed variables
- Must not silently redefine the baseline
- Must identify which configuration is being evaluated

### 14.3 Experimental Boundary

| Boundary | Definition |
|----------|------------|
| Within baseline | Production-unchanged evaluation |
| Comparative | Explicitly documented alternative |

Do not claim causality when multiple variables are changed simultaneously.

---

## 15. REPRODUCIBILITY REQUIREMENTS

Each experiment must record:

| Field | Description |
|-------|-------------|
| Model/Version | YOLOv8 model identifier |
| Tracker | ByteTrack version/configuration |
| Configuration | All tracker parameters |
| **IoU threshold** | **0.50** (for evaluation) |
| **Matching algorithm** | **Hungarian** |
| Frame indexing | Source frame 0 = runtime 0 = GT 0 |
| Source FPS | 15 FPS |
| GT version | Tracking GT identifier |
| Evaluation protocol version | D-06.10 |
| Experiment identifier | Unique per experiment run |

---

## 16. SCIENTIFIC LIMITATIONS

### 16.1 Dataset Limitations

- Single-video Tracking GT (not a diverse MOT benchmark)
- No tracking GT train/validation/test split
- Results may not generalize to other videos

### 16.2 System Limitations

- No runtime Global Identity Association
- Evaluation-time identity association only
- Tracker-local track_id ≠ global_id

### 16.3 Deferred Features

The following remain outside Tracking Evaluation scope:
- ROI Events
- Traffic State
- Spatio-temporal Graph
- Traffic Flow Analysis
- Prediction
- Real-time Evaluation

---

## 17. OPEN IMPLEMENTATION ITEMS

These are implementation details that do NOT alter the locked scientific methodology:

| Item | Options | Decision |
|------|---------|----------|
| Hungarian library | scipy.optimize.linear_sum_assignment, ortools, custom | Open |
| IoU computation | Various bbox formats | Open |
| IDF1 evaluator | Established MOT evaluation library | Deferred |
| File I/O | JSON, CSV, pickle | Open |
| Reporting format | JSON, HTML, Markdown | Open |

**Note:** If an implementation detail could change the scientific meaning of a metric, it is a PROTOCOL DECISION, not merely an implementation detail.

---

## 18. PROTOCOL TRACEABILITY

| Decision | Protocol Section |
|----------|------------------|
| Q1 (IoU=0.50) | Section 7.1, Section 15 |
| Q2 (Hungarian) | Section 7.1, Section 15 |
| Q3 (Baseline + Comparative) | Section 14 |
| Q4 (ByteTrack as-produced) | Section 6.2 |
| Q5 (visibility=0 = FP) | Section 5.3, Section 9 |
| Q6 (all occlusion in primary) | Section 10 |
| Q7 (Standard MOT IDSW) | Section 8.3 |
| Q8 (fragmentation diagnostic) | Section 12.4 |
| Q9 (merge diagnostic) | Section 12.4 |
| Q10 (MOTA/MOTP/IDF1 + diagnostics) | Section 12 |
| Q11 (whole-video primary) | Section 13 |

---

## 19. FINAL CONSISTENCY CHECK

### 19.1 Internal Consistency

- Q1 (IoU=0.50) → Section 7.1 ✓
- Q2 (Hungarian) → Section 7.1 ✓
- Q3 (baseline structure) → Section 14 ✓
- Q4 (no NMS re-run) → Section 6.2 ✓
- Q5 (visibility=0 = FP) → Section 5.3, 9 ✓
- Q6 (all occlusion) → Section 10 ✓
- Q7 (Standard MOT IDSW) → Section 8.3 ✓
- Q8 (fragmentation not in MOTA) → Section 12.4 ✓
- Q9 (merge not in MOTA) → Section 12.4 ✓
- Q10 (metrics defined) → Section 12 ✓
- Q11 (aggregation) → Section 13 ✓

### 19.2 Conflicts

**NONE.** No contradictions between locked decisions and protocol sections.

---

## APPENDIX A: GLOSSARY

| Term | Definition |
|------|------------|
| GT | Ground Truth |
| MOT | Multi-Object Tracking |
| MOTA | Multi-Object Tracking Accuracy |
| MOTP | Multi-Object Tracking Precision |
| IDF1 | ID F1 Score |
| IDSW | Identity Switch |
| FN | False Negative |
| FP | False Positive |
| IoU | Intersection over Union |
| Hungarian | Hungarian / Linear Sum Assignment algorithm |
| global_id | Persistent physical-object identity in GT |
| track_id | Tracker-local identity from ByteTrack |

---

## APPENDIX B: Q5 FORMALIZATION

For implementation, Q5 visibility=0 handling:

```
For each GT track G with global_id:
  start = G.start_frame
  end = G.end_frame
  visible_frames = {f.frame_id for f in G.frames}

  For frame f in range(start, end + 1):
    if f NOT in visible_frames:
      # This is a visibility=0 gap
      # GT object exists but is fully invisible
      # Any runtime detection at frame f is FP
```

---

**END OF PROTOCOL SPECIFICATION**

---

## OUTPUT:

**D-06.10_STATUS:** PASS

**PROTOCOL_SECTIONS:**
1. Purpose and Scope
2. Evaluation Unit
3. Inputs
4. Frame Correspondence
5. Ground-Truth Track Semantics
6. Prediction Semantics
7. Frame-Level Matching
8. Identity Association for Evaluation
9. Visibility=0 Handling
10. Occlusion Handling
11. Track Birth / Track Death
12. Metrics
13. Aggregation
14. Baseline and Comparative Experiments
15. Reproducibility Requirements
16. Scientific Limitations
17. Open Implementation Items
18. Protocol Traceability
19. Final Consistency Check
+ Appendix A: Glossary
+ Appendix B: Q5 Formalization

**DECISION_TRACEABILITY:**
Q1 → Section 7.1, 15
Q2 → Section 7.1, 15
Q3 → Section 14
Q4 → Section 6.2
Q5 → Section 5.3, 9
Q6 → Section 10
Q7 → Section 8.3
Q8 → Section 12.3
Q9 → Section 12.3
Q10 → Section 12
Q11 → Section 13

**METHODOLOGICAL_CONFLICTS:** NONE

**OPEN_PROTOCOL_DECISIONS:** NONE

**IMPLEMENTATION_ONLY:**
- Hungarian algorithm library selection
- IoU computation implementation
- MOTA denominator definition
- IDF1 reference implementation (must be established convention)
- File I/O format
- Reporting format

**DEFERRED:**
- ROI_EVENTS
- TRAFFIC_STATE
- SPATIO_TEMPORAL_GRAPH
- TRAFFIC_FLOW_ANALYSIS
- PREDICTION
- REAL_TIME_EVALUATION

**MODIFIED_FILES:**
- protocol/tracking_evaluation_protocol_D06.10.md (CREATED)

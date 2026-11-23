# PHASE 1.3A — GROUND TRUTH & EVALUATION SPECIFICATION

## 1. Purpose

This document specifies the Ground Truth dataset design for evaluating the current YOLOv8m + ByteTrack + Entity Association + ROI Counting pipeline. The goal is to create a scientifically rigorous evaluation framework that:

- **Validates current baseline performance** without modifying the production pipeline
- **Preserves compatibility** with future trajectory analysis, traffic state estimation, and dynamic traffic graph research
- **Prevents data leakage** through proper temporal splitting strategies
- **Provides representative sampling** across traffic conditions

**Scope:** Design only. No implementation, annotation, or code changes in this phase.

---

## 2. Current Baseline Data

### 2.1 Pipeline Architecture Summary

| Stage | Implementation | Key Parameters |
|-------|---------------|----------------|
| Detection | YOLOv8m (custom trained, `train-16/weights/best.pt`) | imgsz=640, conf=0.3, IoU=0.5 |
| Tracking | ByteTrack (ultralytics built-in) | `bytetrack.yaml`, stale_frames=30 |
| Entity Association | Custom Hungarian-style matching | max_distance=50px, max_gap=30 frames |
| ROI Counting | Polygon-based point-in-polygon test | ROI: [(80,40), (1000,40), (1000,490), (80,490)] |
| Countable Classes | 5 classes | car, motorcycle, bus, truck, person |

### 2.2 Output Schema (Current Production)

The pipeline produces a single JSON file `vehicle_counts.json` with aggregate counts:

```json
{
  "car": 18,
  "motorcycle": 9,
  "bus": 0,
  "truck": 1,
  "person": 2
}
```

**Key Limitation:** Per-frame, per-object data is NOT persisted. Only final aggregate counts are saved.

### 2.3 Internal Data Structures (Not Exported)

| Structure | Fields | Description |
|-----------|--------|-------------|
| `EntityState` (dataclass) | `entity_id`, `last_point`, `last_box`, `last_frame`, `label`, `confidence`, `counted` | Persistent vehicle identity across frames |
| `tracker_to_entity` | `track_id` (ByteTrack) → `entity_id` | Maps ByteTrack IDs to stable entity IDs |
| Detection per frame | `box` (xyxy), `track_id`, `class_id`, `confidence` | Raw YOLO + ByteTrack output |

### 2.4 Video Source

- **File:** `public/3.mp4`
- **Resolution:** 1020 × 500 (resized from source)
- **FPS:** 15.0
- **Duration:** ~33 seconds (500 frames benchmarked)

### 2.5 Training Data (Existing Annotations)

- **Format:** YOLO format (class_id, x_center, y_center, width, height) — normalized
- **Classes:** 5 classes: `bus(0)`, `car(1)`, `motorcycle(2)`, `truck(3)`, `other(4)`
- **Location:** `My-First-Project-1/train/labels/` and `val/labels/`
- **Note:** These are detection annotations only — no tracking IDs, no temporal linkage

---

## 3. What Must Be Annotated

### 3.1 Mandatory for Phase 1.3A Evaluation

| Aspect | Ground Truth Required | Purpose |
|--------|----------------------|---------|
| **Detection** | Per-frame bounding boxes + class labels | Evaluate YOLOv8m precision/recall/mAP |
| **Tracking** | Persistent global object IDs across frames | Evaluate ByteTrack + Entity Association ID consistency |
| **Counting** | Ground truth count events at ROI boundary | Evaluate final aggregate vehicle counts |

### 3.2 Postponed to Future Phases

| Aspect | Phase | Reason |
|--------|-------|--------|
| **Trajectory reconstruction** (smooth center points, velocity, acceleration) | 1.5+ | Requires dense temporal sampling; current 15 FPS may be insufficient |
| **Traffic state** (density, flow, occupancy per zone) | 1.5+ | Requires zone definitions and aggregation logic not yet designed |
| **Dynamic traffic graph** (nodes=zones, edges=flows) | 1.6+ | Depends on traffic state definitions |
| **Lane detection / speed estimation** | 1.5+ | Not supported by current pipeline |
| **Prediction / forecasting** | 2.0+ | Research stage, not evaluation |

---

## 4. Detection Annotation Schema

### 4.1 Minimum Required Fields

```json
{
  "frame_id": 0,
  "timestamp": 0.0,
  "annotations": [
    {
      "object_id": null,
      "class": "car",
      "bbox": [x1, y1, x2, y2],
      "visibility": 1.0,
      "occlusion": 0,
      "truncated": false,
      "difficult": false
    }
  ]
}
```

### 4.2 Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `frame_id` | int | Yes | Sequential frame index (0-based) |
| `timestamp` | float | Yes | Seconds from video start (frame_id / 15.0) |
| `object_id` | int/null | No | Global track ID if tracking GT exists; null for detection-only frames |
| `class` | string | Yes | One of: `car`, `motorcycle`, `bus`, `truck`, `person` |
| `bbox` | array[4] | Yes | [x1, y1, x2, y2] in pixels (1020×500 coordinate space) |
| `visibility` | float | Yes | 0.0–1.0, fraction of object visible |
| `occlusion` | int | Yes | 0=none, 1=partial, 2=heavy, 3=severe |
| `truncated` | bool | Yes | True if bbox extends beyond frame boundary |
| `difficult` | bool | Yes | True if annotation is ambiguous (e.g., heavy rain, night) |

### 4.3 Design Decisions

- **Coordinate space:** 1020×500 (resized frame) — matches pipeline input
- **No confidence field:** Ground truth has no confidence
- **`object_id` optional:** Allows detection-only annotation on frames without tracking GT
- **Visibility/occlusion:** Essential for stratified evaluation (e.g., mAP@50 on occluded objects)

---

## 5. Tracking Annotation Schema

### 5.1 Minimum Required Fields

```json
{
  "tracks": [
    {
      "global_id": 1,
      "class": "car",
      "frames": [
        {
          "frame_id": 10,
          "timestamp": 0.667,
          "bbox": [100, 200, 150, 260],
          "visibility": 0.9,
          "occlusion": 0
        },
        {
          "frame_id": 11,
          "timestamp": 0.733,
          "bbox": [102, 202, 152, 262],
          "visibility": 0.9,
          "occlusion": 0
        }
      ],
      "start_frame": 10,
      "end_frame": 45,
      "start_timestamp": 0.667,
      "end_timestamp": 3.0
    }
  ]
}
```

### 5.2 Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `global_id` | int | Yes | Persistent unique ID across entire video |
| `class` | string | Yes | Vehicle class (constant per track) |
| `frames` | array | Yes | Per-frame observations |
| `frame_id` | int | Yes | Frame index |
| `timestamp` | float | Yes | Seconds from video start |
| `bbox` | array[4] | Yes | [x1, y1, x2, y2] |
| `visibility` | float | Yes | 0.0–1.0 |
| `occlusion` | int | Yes | 0–3 |
| `start_frame` | int | Yes | First frame track appears |
| `end_frame` | int | Yes | Last frame track appears |
| `start_timestamp` | float | Yes | Derived from start_frame |
| `end_timestamp` | float | Yes | Derived from end_frame |

### 5.3 Enabling Tracking Metrics

This schema enables computation of:

| Metric | What It Measures | Requirement |
|--------|------------------|-------------|
| **IDF1** | Identity F1 score (detection + association) | `global_id` + per-frame bbox |
| **HOTA** | Higher Order Tracking Accuracy | `global_id` + per-frame bbox + class |
| **MOTA** | Multiple Object Tracking Accuracy | `global_id` + per-frame bbox + FP/FN |
| **ID Switches** | Number of identity swaps | `global_id` continuity |
| **Track Fragmentation** | Number of track breaks | `start_frame` / `end_frame` gaps |

**Critical:** Global IDs must be consistent across the ENTIRE video, not reset per scene.

---

## 6. Counting Ground Truth Schema

### 6.1 What Constitutes a "Counted Vehicle"

A vehicle is counted **iff**:
1. Its **bottom-center point** (bbox center_x, bbox y2) crosses the ROI polygon boundary
2. The crossing is **in the designated direction** (entry into ROI)
3. The vehicle class is in `countable_labels` (car, motorcycle, bus, truck, person)
4. The vehicle has **sufficient confidence** (≥ 0.2 per config)

### 6.2 Count Event Schema

```json
{
  "count_events": [
    {
      "event_id": 1,
      "global_id": 42,
      "class": "car",
      "frame_id": 150,
      "timestamp": 10.0,
      "roi_point": [520, 300],
      "direction": "entry",
      "bbox_at_crossing": [490, 250, 550, 350]
    }
  ],
  "roi_polygon": [[80,40], [1000,40], [1000,490], [80,490]],
  "countable_classes": ["car", "motorcycle", "bus", "truck", "person"],
  "total_counts": {
    "car": 18,
    "motorcycle": 9,
    "bus": 0,
    "truck": 1,
    "person": 2
  }
}
```

### 6.3 Field Definitions

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `event_id` | int | Yes | Unique count event identifier |
| `global_id` | int | Yes | Links to tracking GT |
| `class` | string | Yes | Vehicle class |
| `frame_id` | int | Yes | Frame where crossing detected |
| `timestamp` | float | Yes | Seconds from video start |
| `roi_point` | array[2] | Yes | Bottom-center point at crossing [x, y] |
| `direction` | string | Yes | `entry` or `exit` (current pipeline counts entry only) |
| `bbox_at_crossing` | array[4] | Yes | Full bbox at crossing frame |

### 6.4 Design Decisions

- **Bottom-center point:** Matches pipeline's `roi_point = (center_x, y2)` exactly
- **ROI polygon:** Must match config.yaml precisely
- **Direction:** Current pipeline only counts entry; exit events recorded for future bidirectional counting
- **Link to `global_id`:** Enables verification that each counted vehicle has a valid track

---

## 7. Future Trajectory Compatibility

### 7.1 Required Data Representation

The tracking annotation schema (Section 5) already provides the minimal trajectory data:

```
track_id + frame_id + timestamp + center_x + center_y + bbox
```

Derived per frame:
- `center_x = (x1 + x2) / 2`
- `center_y = (y1 + y2) / 2`

### 7.2 Trajectory-Ready Format (No Implementation)

For future Phase 1.5 trajectory extraction, the following can be derived **without re-annotation**:

| Derived Field | Formula | Use Case |
|---------------|---------|----------|
| `velocity_px_per_frame` | `dist(center_t, center_t-1)` | Speed estimation |
| `acceleration` | `vel_t - vel_t-1` | Behavior classification |
| `heading` | `atan2(dy, dx)` | Lane adherence, turning |
| `path_length` | `sum(velocity)` | Distance traveled |

### 7.3 Sampling Consideration

At 15 FPS, center-point displacement between frames is ~3–10 pixels for typical traffic. This is **sufficient for trajectory reconstruction** but may require smoothing (Kalman, spline) for velocity/acceleration.

**No additional annotation fields needed** — the tracking schema is trajectory-compatible.

---

## 8. Future Traffic Graph Compatibility

### 8.1 Conceptual Graph Structure (Future Phase 1.6+)

```
Node (Zone): traffic zone / lane / intersection approach / counting region
Edge (Flow): movement relationship between zones (count of vehicles transitioning)
```

### 8.2 Information to Preserve

| Information | Current Schema Support | Purpose |
|-------------|------------------------|---------|
| **Zone membership per frame** | ROI polygon + bbox → point-in-polygon | Assign vehicle to zone per frame |
| **Zone transitions** | Track `global_id` + sequential zone membership | Build origin-destination matrix |
| **Dwell time per zone** | `timestamp` differences within zone | Occupancy, density |
| **Flow count per edge** | Count of `global_id` transitions A→B | Edge weights in traffic graph |
| **Temporal resolution** | 15 FPS timestamps | Time-varying graph snapshots |

### 8.3 Required Additions (Future, Not Now)

- **Zone definitions:** Multiple polygons (lanes, approaches, intersections)
- **Zone taxonomy:** Hierarchical (intersection → approach → lane)
- **Transition rules:** Which zone transitions are valid

**Current Action:** Ensure tracking GT has `global_id`, `timestamp`, `bbox` — sufficient to compute zone membership post-hoc when zones are defined.

---

## 9. Dataset Directory Structure

```
dataset/
├── raw/
│   ├── video/
│   │   └── 3.mp4                    # Source video (original resolution)
│   └── frames/
│       └── 3/                       # Extracted frames (1020×500)
│           ├── frame_000000.jpg
│           ├── frame_000001.jpg
│           └── ...
├── annotations/
│   ├── detection/
│   │   └── 3_detection.jsonl        # Per-frame detection GT (JSONL)
│   ├── tracking/
│   │   └── 3_tracking.json          # Full tracking GT (JSON)
│   └── counting/
│       └── 3_counting.json          # Count events + ROI + totals
├── metadata/
│   ├── video_info.json              # FPS, resolution, duration, codec
│   ├── roi_config.json              # ROI polygon, countable classes
│   ├── class_mapping.json           # class_id ↔ class_name
│   └── annotation_protocol.md       # Annotation guidelines
├── splits/
│   ├── train.json                   # Frame IDs for training
│   ├── val.json                     # Frame IDs for validation
│   └── test.json                    # Frame IDs for testing
└── evaluation/
    ├── metrics_config.yaml          # Metric definitions, thresholds
    └── baseline_results/            # Baseline predictions for comparison
```

### 9.1 Design Principles

| Principle | Implementation |
|-----------|----------------|
| **Single source of truth** | Raw video + extracted frames at pipeline resolution |
| **Modular annotations** | Separate files for detection/tracking/counting — can be used independently |
| **JSONL for detection** | Streaming-friendly, one line per frame |
| **JSON for tracking/counting** | Hierarchical structure (tracks, events) |
| **Metadata separation** | Config, protocols, class mapping versioned separately |
| **No redundancy** | Counting GT references tracking GT via `global_id` |

---

## 10. Annotation Formats

### 10.1 Format Comparison

| Format | Detection | Tracking | Counting | Trajectory |
|--------|-----------|----------|----------|------------|
| **JSONL** | ✅ Best (streaming) | ❌ Hierarchical | ❌ Hierarchical | ⚠️ Possible |
| **JSON** | ⚠️ Large file | ✅ Best (nested) | ✅ Best (events) | ✅ Good |
| **COCO** | ✅ Standard | ❌ No tracking | ❌ No counting | ❌ No |
| **YOLO** | ✅ Compact | ❌ No tracking | ❌ No counting | ❌ No |
| **MOT Challenge** | ❌ No detection | ✅ Standard | ❌ No counting | ✅ Trajectory |

### 10.2 Recommended Formats

| Task | Format | Rationale |
|------|--------|-----------|
| **Detection** | JSONL | One line per frame; streamable; matches per-frame pipeline |
| **Tracking** | JSON (MOT-inspired) | Nested track structure; global IDs; standard tools exist |
| **Counting** | JSON | Event list + metadata; human-readable |
| **Trajectory (future)** | JSON or Parquet | Derived from tracking; columnar for analytics |

### 10.3 Detection JSONL Example

```jsonl
{"frame_id": 0, "timestamp": 0.0, "annotations": [{"class": "car", "bbox": [100,200,150,260], "visibility": 1.0, "occlusion": 0, "truncated": false, "difficult": false}]}
{"frame_id": 1, "timestamp": 0.067, "annotations": [{"class": "car", "bbox": [102,202,152,262], "visibility": 1.0, "occlusion": 0, "truncated": false, "difficult": false}, {"class": "motorcycle", "bbox": [500,300,530,350], "visibility": 0.8, "occlusion": 1, "truncated": false, "difficult": false}]}
```

### 10.4 Tracking JSON Example (MOT-Compatible)

```json
{
  "video": "3.mp4",
  "fps": 15.0,
  "frame_size": [1020, 500],
  "tracks": [
    {
      "id": 1,
      "class": "car",
      "frames": [
        {"frame_id": 10, "bbox": [100,200,150,260], "visibility": 1.0, "occlusion": 0},
        {"frame_id": 11, "bbox": [102,202,152,262], "visibility": 1.0, "occlusion": 0}
      ]
    }
  ]
}
```

---

## 11. Dataset Split Strategy

### 11.1 Temporal Leakage Risk

**Random frame splitting is PROHIBITED** for video data. Adjacent frames are highly correlated (same vehicles, same background). Random split would put the same vehicle in train and test → inflated metrics.

### 11.2 Recommended Strategy: Temporal Block Splitting

```
Video: [======== 500 frames ========]
         │         │         │
      Train      Val       Test
    (0-249)   (250-374)  (375-499)
```

| Split | Frames | Duration | Use Case |
|-------|--------|----------|----------|
| **Train** | 0–249 | 16.7s | Model fine-tuning (if needed), threshold calibration |
| **Validation** | 250–374 | 8.3s | Hyperparameter tuning, early stopping |
| **Test** | 375–499 | 8.3s | Final unbiased evaluation |

### 11.3 Multi-Video Extension (Future)

When multiple videos exist:

| Strategy | Description | Leakage Risk |
|----------|-------------|--------------|
| **Video-level split** | Entire videos assigned to train/val/test | None (gold standard) |
| **Scene-level split** | Different intersections/cameras per split | Low |
| **Temporal block per video** | As above, within each video | None |

**Current Project:** Single video → temporal block split is the only valid option.

### 11.4 Split File Format

```json
// splits/test.json
{
  "video": "3.mp4",
  "split": "test",
  "frame_ids": [375, 376, ..., 499],
  "frame_range": [375, 499],
  "duration_seconds": 8.33
}
```

---

## 12. Annotation Sampling Strategy

### 12.1 Not Every Frame Needs Annotation

At 15 FPS, 500 frames = 33 seconds. Annotating every frame is redundant for vehicles moving slowly.

### 12.2 Recommended Sampling

| Strategy | Description | Annotation Load | Coverage |
|----------|-------------|-----------------|----------|
| **Keyframe + interpolation** | Annotate every 5th frame (3 FPS), interpolate | 100 frames | High (smooth motion) |
| **Stratified by density** | More frames during high-density periods | Variable | Representative |
| **Event-based** | Annotate frames with: entry/exit, occlusion, new objects | Variable | High for critical events |

### 12.3 Recommended Hybrid Approach

1. **Base rate:** Every 5th frame (30 frames per second of video) → 100 frames for 33s video
2. **Boost around events:** ±10 frames around each ROI crossing, occlusion start/end, track birth/death
3. **Stratify by condition:** Ensure minimum frames per:
   - Traffic density: low (<5 vehicles), medium (5–15), high (>15)
   - Vehicle composition: car-heavy, motorcycle-heavy, mixed
   - Illumination: bright, shadow, transition
   - Occlusion: none, partial, heavy

### 12.4 Sampling Protocol

```yaml
# metadata/annotation_protocol.md
sampling:
  base_interval: 5          # Annotate every 5th frame
  event_window: 10          # ±10 frames around events
  min_frames_per_stratum:
    density_low: 10
    density_medium: 15
    density_high: 20
    motorcycle_heavy: 10
    shadow: 10
    occlusion_heavy: 15
events_to_capture:
  - roi_crossing
  - track_birth
  - track_death
  - occlusion_start
  - occlusion_end
  - class_change (if any)
```

### 12.5 Interpolation for Unannotated Frames

For detection evaluation on unannotated frames:
- **Do NOT interpolate** — evaluate only on annotated frames
- For tracking: interpolated boxes can be used to compute IDF1/HOTA on all frames if annotator provides keyframes with interpolation guidance

---

## 13. Evaluation Metrics

### 13.1 Detection Metrics

| Metric | Formula | Why Appropriate |
|--------|---------|-----------------|
| **Precision** | TP / (TP + FP) | Measures false alarms — critical for counting |
| **Recall** | TP / (TP + FN) | Measures missed vehicles — directly affects count accuracy |
| **mAP@50** | Mean AP at IoU≥0.5 | Standard detection benchmark; balances precision/recall |
| **mAP@50:95** | Mean AP at IoU 0.5:0.95 | Stricter localization quality |

**Recommendation:** Report **mAP@50** as primary (matches ByteTrack association threshold), **mAP@50:95** as secondary.

### 13.2 Tracking Metrics

| Metric | Formula | Why Appropriate |
|--------|---------|-----------------|
| **IDF1** | 2×IDTP / (2×IDTP + IDFP + IDFN) | Combines detection + association; identity-aware |
| **HOTA** | √(DetA × AssA) | Decomposes into detection accuracy (DetA) + association accuracy (AssA) |
| **MOTA** | 1 − (FP + FN + IDSW) / GT | Classic MOT metric; penalizes ID switches |
| **ID Switches** | Count of identity changes | Directly measures tracking consistency |
| **Track Fragmentation** | Count of track breaks | Measures track continuity |

**Recommendation:** **IDF1** as primary (most balanced), **HOTA** for detailed analysis, **ID Switches** for operational monitoring.

**Do NOT use:** CLEAR MOT metrics alone (MOTA/MOTP) — they hide association quality.

### 13.3 Counting Metrics

| Metric | Formula | Why Appropriate |
|--------|---------|-----------------|
| **MAE** | Mean\|Predicted − Ground Truth\| | Absolute error in vehicle count; intuitive |
| **RMSE** | √Mean(Predicted − GT)² | Penalizes large errors more |
| **Relative Error** | \|Pred − GT\| / GT | Normalized by volume; comparable across classes |

**Do NOT use:** MAPE (Mean Absolute Percentage Error) — **undefined when GT=0** (e.g., bus=0 in current data).

**Per-class reporting mandatory:** Car, motorcycle, bus, truck, person separately.

### 13.4 Postponed Metrics

| Metric | Phase | Reason |
|--------|-------|--------|
| **Trajectory RMSE** | 1.5 | Requires dense trajectory GT |
| **Velocity MAE** | 1.5 | Requires calibrated speed |
| **Traffic state accuracy** | 1.5+ | Requires zone definitions |
| **Graph flow error** | 1.6+ | Requires traffic graph |

---

## 14. Data Leakage Prevention

### 14.1 Sources of Leakage

| Source | Risk | Mitigation |
|--------|------|------------|
| **Temporal correlation** | Same vehicle in train/test | Temporal block split (Sec 11) |
| **Background memorization** | Model learns static scene | Video-level split when multi-video |
| **Annotation bias** | Annotator sees model predictions | Blind annotation (no model output shown) |
| **Hyperparameter tuning on test** | Overfitting to test set | Strict train/val/test separation |
| **Frame-level split** | Adjacent frames in different splits | Prohibited |

### 14.2 Leakage Prevention Checklist

- [ ] Splits defined at **video level** or **temporal block level** — never frame level
- [ ] Test set **never used** for threshold tuning, model selection, or hyperparameter search
- [ ] Annotators work **without access** to model predictions
- [ ] Validation set used **only** for hyperparameter tuning
- [ ] Final metrics reported **only once** on test set
- [ ] Cross-validation: **temporal K-fold** (block-wise), not random

### 14.3 Experiment Unit Definition

| Unit | Definition | Use For |
|------|------------|---------|
| **Frame** | Single timestamp | Detection metrics (per-frame) |
| **Track** | Single global_id trajectory | Tracking metrics (IDF1, HOTA) |
| **Event** | Single ROI crossing | Counting metrics (MAE per class) |
| **Video** | Entire sequence | Aggregate counting, system-level FPS |

---

## 15. Phase 1.3B Prerequisites

Phase 1.3B = **Annotation Implementation**

| Prerequisite | Status | Notes |
|--------------|--------|-------|
| Finalized annotation schema | ✅ This spec | Review and approve |
| Annotation tool selected | ❌ Pending | CVAT, LabelStudio, or custom |
| Annotator guidelines written | ❌ Pending | Based on Section 4–6 |
| Sampling frames extracted | ❌ Pending | Per Section 12 |
| Inter-annotator agreement protocol | ❌ Pending | 2+ annotators, Cohen's κ |
| Quality control pipeline | ❌ Pending | Automated validation scripts |

---

## 16. Phase 1.3C Prerequisites

Phase 1.3C = **Evaluation Execution**

| Prerequisite | Status | Notes |
|--------------|--------|-------|
| Phase 1.3B complete | ❌ | Annotated dataset ready |
| Evaluation codebase | ❌ | Metrics computation (py-motmetrics, custom) |
| Baseline predictions exported | ❌ | Run current pipeline on test split, save per-frame outputs |
| Statistical significance testing | ❌ | Bootstrap confidence intervals |
| Report template | ❌ | Standardized results format |

---

## 17. Open Questions

| # | Question | Impact | Decision Needed |
|---|----------|--------|-----------------|
| 1 | **Annotation tool:** CVAT vs LabelStudio vs custom? | Cost, speed, format support | Choose before 1.3B |
| 2 | **Inter-annotator agreement:** How many annotators? | Quality assurance, cost | Define protocol |
| 3 | **Occlusion definition:** 4-level (0–3) sufficient? | Detection metric stratification | Confirm or refine |
| 4 | **Truncation handling:** Annotate full extent or visible only? | mAP calculation | Standardize |
| 5 | **Person class:** Include in counting GT? | Current pipeline counts it | Confirm scope |
| 6 | **Multi-video:** When will additional videos be available? | Split strategy, generalization | Plan timeline |
| 7 | **Confidence threshold sweep:** Evaluate at multiple conf levels? | Understanding precision/recall tradeoff | Add to 1.3C |
| 8 | **Class imbalance:** Bus/truck rare — oversample in annotation? | Metric reliability | Stratified sampling |

---

## Appendix A: Current Pipeline Configuration Reference

```yaml
# config/config.yaml (Phase 1.2 baseline)
model:
  path: "runs/detect/train-16/weights/best.pt"
  imgsz: 640
  confidence: 0.30
  iou: 0.5
tracker:
  type: "bytetrack"
  config:
    stale_frames: 30
roi:
  enabled: true
  points: [[80,40], [1000,40], [1000,490], [80,490]]
counting:
  countable_labels: ["car", "motorcycle", "bus", "truck", "person"]
  min_confidence: 0.2
  min_box_size: 10
video:
  source: "public/3.mp4"
  frame_size: [1020, 500]
```

---

## Appendix B: Class Mapping

| Model Class ID | Class Name | Countable |
|----------------|------------|-----------|
| 0 | bus | ✅ |
| 1 | car | ✅ |
| 2 | motorcycle | ✅ |
| 3 | truck | ✅ |
| 4 | other | ❌ (ignored) |

Note: `person` class not in custom model — comes from YOLOv8 pretrained classes if enabled.

---

**Document Version:** 1.0
**Phase:** 1.3A — Design Only
**Next Phase:** 1.3B — Annotation Implementation (pending review)
**Status:** READY FOR REVIEW
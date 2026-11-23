# PHASE 1.3B — ANNOTATION PROTOCOL & TOOL DESIGN

**Status:** DRAFT — Sections 1–7.10 complete; Section 7.11 onward pending
**Phase:** 1.3B — Annotation Implementation
**Depends on:** Phase 1.3A Ground Truth Specification (finalized)
**Next:** Section 8 (Data Schema)

---

## 1. Scope

This document defines the annotation protocol for creating Ground Truth (GT) data to evaluate the YOLOv8m + ByteTrack + Entity Association + ROI Counting pipeline. The protocol transforms the Phase 1.3A specification into explicit, reproducible annotation rules.

**Target Video:** `public/3.mp4` (1280×720 → 1020×500 resized, 15 FPS, 621 frames, ≈41.4s)
**Pipeline Resolution:** 1020×500 (all annotations in this coordinate space)
**ROI Polygon:** `[(80,40), (1000,40), (1000,490), (80,490)]`
**Countable Classes:** `car`, `motorcycle`, `bus`, `truck`, `person`
**Model Classes (custom YOLOv8m):** `bus`(0), `car`(1), `motorcycle`(2), `person`(3), `truck`(4)

---

## 2. Annotation Rules (General)

### 2.1 Coordinate System
- All bounding boxes: `[x1, y1, x2, y2]` in **pixels** (1020×500 coordinate space)
- Origin: top-left (0, 0)
- x increases rightward, y increases downward
- Integer coordinates only

### 2.2 Frame Referencing
- `frame_id`: 0-based sequential index (0 to 620)
- `timestamp = frame_id / 15.0` seconds

### 2.3 Class Labels (Exact Strings)
| Class | Model ID | Countable | Notes |
|-------|----------|-----------|-------|
| `car` | 1 | ✅ | Most frequent; sedans, SUVs, hatchbacks |
| `motorcycle` | 2 | ✅ | Two-wheelers; includes scooters |
| `bus` | 0 | ✅ | Large passenger vehicles; rare in this video |
| `truck` | 4 | ✅ | Cargo vehicles; box trucks, pickups with cargo bed |
| `person` | 3 | ✅ | Pedestrians; upright, walking/standing |

**Note:** The training data contains an `other` class (ID 4 in data.yaml) which maps to `truck` in the model. The model does NOT have an `other` class.

### 2.4 Ambiguous / Unclassifiable Objects
- **Rule:** If an object cannot be confidently assigned to one of the 5 classes, annotate as `difficult: true` with `class: "car"` (most conservative) and add a note in comments field.
- **Do NOT create new classes.** The evaluation schema only supports these 5 classes.

### 2.5 Objects Outside ROI
- Annotate **ALL** visible objects in the frame, not just those inside ROI
- Objects outside ROI are needed for tracking continuity and detection evaluation
- Counting GT only references tracks that cross ROI boundary

### 2.6 Very Small Objects (< 10×10 pixels)
- **Annotate if:** Clearly identifiable as one of the 5 classes
- **Do NOT annotate if:** Indistinguishable blob (set `difficult: true` if annotated)
- **Min box size:** 10×10 pixels (matches pipeline `min_box_size: 10`)

---

## 3. Bounding Box Policy

### 3.1 Core Principle: Tight Box Around Visible Extent

**Draw the tightest axis-aligned rectangle that encloses all VISIBLE pixels of the object.**

This means:
- Include all visible parts of the vehicle/person
- Do NOT include occluded/hidden portions
- Do NOT extrapolate full extent based on object class knowledge

### 3.2 Handling of Occluded Regions

| Scenario | Box Treatment |
|----------|---------------|
| **Partial occlusion by another vehicle** | Box encloses only visible portions. If occlusion splits object into disconnected visible parts, use ONE box covering the convex hull of all visible parts. |
| **Partial occlusion by static scene (pole, sign, tree)** | Box encloses visible portions only. Do not extend behind occluder. |
| **Heavy occlusion (>50% hidden)** | Still draw box around visible portion. Mark `occlusion: 2` (heavy) or `3` (severe). |
| **Full/temporary invisibility** | **No annotation** for that frame. Track continuity handled via `global_id` in tracking GT. |

### 3.3 Truncated Objects (At Image Boundary)

| Scenario | Box Treatment | `truncated` Field |
|----------|---------------|-------------------|
| Object touches frame edge (x1=0 or x2=1019 or y1=0 or y2=499) | Draw box to frame edge | `true` |
| Object partially outside frame (only corner visible) | Draw box around visible portion to frame edge | `true` |
| Object fully inside frame with margin ≥ 1 pixel | Normal tight box | `false` |

**Note:** The ROI polygon has 80px left margin and 20px right margin from frame edges. Most truncation occurs at top/bottom (y=0 or y=499).

### 3.4 Overlapping Vehicles

- **Each vehicle gets its own box** — never merge two vehicles into one box
- If Vehicle A occludes Vehicle B: Box A around A's visible extent, Box B around B's visible extent
- Boxes may overlap in annotation — this is correct and expected
- Class each box independently based on visible features

### 3.5 Parked / Stationary Vehicles

- **Annotate identically to moving vehicles** — same box rules, same class labels
- Track ID continuity maintained across frames (same `global_id` if persistent)
- Counting: Only counted if bottom-center crosses ROI boundary in entry direction
- In this video: Vehicles appear to be moving through; no long-term parked vehicles observed

### 3.6 Class-Specific Box Guidelines

| Class | Typical Size Range (1020×500) | Box Notes |
|-------|-------------------------------|-----------|
| `car` | 15×15 (far) to 180×70 (close) | Include roof, windows, wheels if visible |
| `motorcycle` | 12×21 (far) to 70×70 (close w/ rider) | Include handlebars, wheels, rider body |
| `bus` | Not observed in 3.mp4 | Full body length; include windows |
| `truck` | 170×170 (close) | Include cab + cargo bed; long aspect ratio |
| `person` | 15×34 to 40×80 | Full body height; upright posture |

### 3.7 Edge Cases & Decisions

| Edge Case | Decision |
|-----------|----------|
| Vehicle reflection on wet road | **Do not annotate** reflection as separate object |
| Shadow of vehicle | **Do not annotate** shadow |
| Vehicle partially behind ROI boundary line | Box to visible pixels; `truncated: true` if at frame edge, `false` if only at ROI line |
| Two motorcycles riding close together | Two separate boxes if distinguishable; one box with `difficult: true` if merged |
| Person riding motorcycle | **One box** labeled `motorcycle` (vehicle class takes precedence); rider not separate `person` |
| Person inside car/truck | **Do not annotate** separate `person` — only the vehicle |
| Trailer attached to truck | **One box** labeled `truck` enclosing truck + trailer |

### 3.8 Annotation Format (Per-Frame Detection JSONL)

```jsonl
{"frame_id": 100, "timestamp": 6.667, "annotations": [
  {"class": "car", "bbox": [420, 170, 483, 211], "visibility": 1.0, "occlusion": 0, "truncated": false, "difficult": false},
  {"class": "motorcycle", "bbox": [536, 190, 572, 217], "visibility": 0.9, "occlusion": 0, "truncated": false, "difficult": false}
]}
```

---

## 4. Occlusion Policy

### 4.1 Occlusion Levels (4-Level Scale)

Based on analysis of the video, objects exhibit **partial occlusion by other vehicles** as the primary occlusion type. Full occlusion (object completely hidden, visibility = 0) results in **no bbox annotation** for that frame. The 4 levels apply only to frames where the object has a visible bbox:

| Level | Label | Definition | Visibility Range | Examples in 3.mp4 |
|-------|-------|------------|------------------|-------------------|
| **0** | `none` | Object fully visible; no overlapping objects or scene elements blocking view | 1.0 (exactly) | Isolated car in lane, motorcycle alone |
| **1** | `partial` | 1–50% of object area obscured by another vehicle or scene element | (0.5, 1.0) | Car behind another car's rear; motorcycle beside truck |
| **2** | `heavy` | >50–90% of object area obscured; only small portion visible | (0.1, 0.5] | Car mostly hidden behind bus/truck; only roof visible |
| **3** | `severe` | >90% obscured; barely detectable (few pixels, ambiguous shape) | (0.0, 0.1] | Only corner of vehicle peeking from behind another |

**Visibility = 0 (full invisibility):** No bbox annotation in that frame. The `global_id` track persists without observation (see Section 5.3, Scenario 3).

### 4.2 Justification for 4 Levels

- **3 levels (none/partial/heavy) is insufficient:** The gap between "partial" (up to 50%) and "heavy" (50-90%) vs "severe" (>90%) is meaningful for evaluation. mAP on severely occluded objects (level 3) is a distinct stress test.
- **5+ levels adds annotator burden** without clear metric separation. MOT benchmarks (KITTI, MOT17) use 3-4 levels.
- **Visibility fraction (0.0–1.0) is recorded separately** for continuous analysis; occlusion level is categorical for stratified reporting.

### 4.3 Occlusion Source Classification

| Source | Annotation Handling |
|--------|---------------------|
| **Vehicle-vehicle** (dynamic) | Primary type in this video. Annotate both vehicles; each gets occlusion level based on how much of IT is hidden. |
| **Vehicle-static** (pole, sign, tree, building) | Mark occlusion level; note source in comments if tool supports it. |
| **ROI boundary / frame edge** | This is **truncation**, not occlusion. Set `truncated: true`, `occlusion: 0` (unless also occluded by another object). |
| **Self-occlusion** (e.g., person turning) | Included in occlusion level assessment. |

### 4.4 Measurement Protocol

**Annotator estimates visible fraction by eye** — no pixel counting required.

1. Mentally reconstruct full object extent from visible cues (wheels, roofline, known proportions)
2. Estimate percentage of that extent currently visible
3. Assign level per table above
4. Record `visibility` as continuous float (0.0–1.0) for finer granularity

**Calibration examples from 3.mp4:**
- Frame 0: Car at [301,146,333,184] — isolated, `occlusion: 0`, `visibility: 1.0`
- Frame 0: Car at [362,146,390,168] — partially behind car at [301,146,...], `occlusion: 1`, `visibility: ~0.7`
- Frame 550: Large car [389,208,577,282] overlaps multiple — check each overlapped vehicle's visible fraction

### 4.5 Temporal Consistency

- Occlusion level can change frame-to-frame as vehicles move
- **Do not force consistency** — annotate what is visible in each frame
- Tracking GT will link frames; evaluation handles occlusion transitions

### 4.6 Occlusion vs. Difficult Flag

| Condition | `occlusion` | `difficult` |
|-----------|-------------|-------------|
| Clear but heavy rain / night / glare | 0–3 (actual occlusion) | `true` |
| Severe occlusion (level 3) | 3 | `false` (unless also ambiguous) |
| Ambiguous class (car vs truck) | actual level | `true` |
| Motion blur | actual level | `true` |

---

## 5. Ground Truth global_id Policy (Tracking Identity)

This section defines the rigorous identity policy for Ground Truth tracks. **Critical principle:** Ground Truth `global_id` MUST be completely independent from ByteTrack `track_id`. These are separate identity spaces and must never be conflated.

### 5.1 Core Identity Principle

| Property | Ground Truth `global_id` | ByteTrack `track_id` |
|----------|--------------------------|----------------------|
| **Source** | Human-annotated, video-wide persistent identity | Algorithmic, per-session tracker output |
| **Scope** | Entire video (0–620 frames) | Resets if tracker re-initializes |
| **Stability** | Immutable once assigned | Can change due to ID switches, fragmentation |
| **Purpose** | Evaluation ground truth | System under test output |
| **Example** | `GT_001` | `17` |

**Rule:** Never map `global_id` ↔ `track_id` during annotation. The evaluation code performs matching; annotators assign `global_id` based solely on visual identity continuity.

### 5.2 Global ID Assignment Rules

#### 5.2.1 Naming Convention
- Format: `GT_XXX` (zero-padded 3-digit, e.g., `GT_001`, `GT_042`, `GT_127`)
- Sequential assignment in order of first appearance (by `start_frame`)
- Maximum expected: < 100 unique objects in 3.mp4

#### 5.2.2 Identity Continuity Conditions
A single `global_id` persists across frames **iff all** of the following hold:
1. **Visual continuity:** Same physical object observed (color, shape, type, distinguishing features)
2. **Spatiotemporal plausibility:** Motion trajectory is physically possible (no teleportation > 100px/frame)
3. **Class consistency:** Object class does not change (car → truck requires new ID)
4. **No identity merge:** Two distinct objects never share one `global_id`

#### 5.2.3 Identity Termination Conditions
A `global_id` terminates (object leaves scene permanently) when:
- Object exits frame and does not reappear within 30 frames (2 seconds)
- Annotator confirms object has left the scene (parked and never moves, drives away)
- Video ends

### 5.3 Explicit Rules for Identity Scenarios

| # | Scenario | global_id Rule | Rationale |
|---|----------|----------------|-----------|
| **1** | Object entering frame | Assign **new** `global_id` (next sequential) | First observation = birth event |
| **2** | Object leaving frame | Terminate track at last visible frame; `end_frame` = last frame with annotation | No extrapolation beyond visibility |
| **3** | **Temporary occlusion (visibility = 0, ≤ 30 frames)** | **Same** `global_id` continues; **no bbox annotation** during full invisibility; `frames` array has gap | Short occlusion = tracking continuity; GT track persists without observation |
| **4** | **Reappearance after temporary occlusion (≤ 30 frames gap, visibility > 0)** | **Same** `global_id` if visual match confirmed (appearance + trajectory) | Verified re-identification |
| **5** | **Short disappearance (1–30 frames, object left ROI/camera view but may return)** | **Same** `global_id` if re-enters within 30 frames AND visual match confirmed | Distinguishes temporary exit from permanent leave |
| **6** | **Long disappearance (> 30 frames / 2 sec gap)** | **New** `global_id` on reappearance | Cannot reliably associate; prevents false continuity |
| **7** | Objects crossing each other | **Distinct** `global_id`s maintained throughout; boxes may overlap | Crossing ≠ merging; each object retains identity |
| **8** | Similar-looking vehicles (same color/model) | Separate `global_id`s; distinguish by trajectory, entry time, spatial separation | Visual similarity ≠ same object |
| **9** | Vehicle-to-vehicle overlap (one passes behind another) | Each maintains own `global_id`; occlusion level records visibility | Overlap is temporary; identities independent |
| **10** | Objects partially outside frame | Continue same `global_id` if > 50% visible; terminate if fully exits | Truncation ≠ identity loss |
| **11** | Objects that cannot be confidently associated | Assign **new** `global_id`; mark `difficult: true` on reappearance | Conservative: prefer fragmentation over false merge |
| **12** | Identity continuity across sampled frames | `global_id` spans ALL frames (annotated + interpolated); sampling only reduces annotation density | Track exists continuously; annotation is sparse observation |
| **13** | New object creation | New `global_id` when: first appearance in frame, OR reappearance after > 30-frame gap, OR class change | Clear birth criteria |
| **14** | Object termination | Track ends at `end_frame` = last annotated frame; no annotation after full exit | Clear death criteria |

**Key distinction — three temporal regimes:**
| Regime | Frame Gap | Visibility During Gap | global_id | Example |
|--------|-----------|----------------------|-----------|---------|
| **Temporary occlusion** | 1–30 | 0 (fully hidden behind object) | **Same** | Car passes behind truck |
| **Short disappearance** | 1–30 | N/A (left camera/ROI view) | **Same** if visual match on return | Car exits left, re-enters right within 2 sec |
| **Long disappearance** | > 30 | N/A | **New** | Car parks and leaves; or drives away permanently |

### 5.4 Special Cases from 3.mp4 Analysis

| Case | Decision | Evidence Basis |
|------|----------|----------------|
| **Motorcycle + rider** | Single `global_id`, class=`motorcycle` | Rider not separate person; vehicle class takes precedence |
| **Trailer + truck** | Single `global_id`, class=`truck` | Rigid coupling; moves as unit |
| **Person inside vehicle** | Not annotated separately | Only vehicle box; person not visible as independent entity |
| **Reflections/shadows** | No `global_id` assigned | Not physical objects |
| **Parked vehicles** (if any) | `global_id` persists while stationary; counted only on ROI crossing | Same identity rules; counting is separate |

### 5.5 Minimum Ground Truth Track Representation

Per Phase 1.3A Section 5 and future graph compatibility requirements, each GT track must contain:

```json
{
  "global_id": "GT_001",
  "class": "car",
  "frames": [
    {
      "frame_id": 10,
      "timestamp": 0.667,
      "bbox": [100, 200, 150, 260],
      "visibility": 1.0,
      "occlusion": 0,
      "truncated": false,
      "center": [125, 230]
    }
  ],
  "start_frame": 10,
  "end_frame": 150,
  "start_timestamp": 0.667,
  "end_timestamp": 10.0,
  "roi_crossings": [
    {"frame_id": 45, "direction": "entry", "roi_point": [520, 300]}
  ]
}
```

**Required fields (minimum for trajectory → zone transition → traffic state → dynamic graph):**

| Field | Type | Purpose |
|-------|------|---------|
| `global_id` | string | Persistent identity (GT_XXX format) |
| `class` | string | Vehicle class (constant per track) |
| `frame_id` | int | Frame index |
| `timestamp` | float | Seconds from video start |
| `bbox` | [x1,y1,x2,y2] | Visible extent in pixels |
| `center` | [cx, cy] | Derived: ((x1+x2)/2, (y1+y2)/2) — for trajectory |
| `visibility` | float | 0.0–1.0 (continuous) |
| `occlusion` | int | 0–3 (categorical) |
| `truncated` | bool | At frame boundary |
| `start_frame` / `end_frame` | int | Track temporal extent |
| `roi_crossings` | array | Links to counting events (optional, for validation) |

**Only add fields when justified** — this minimal set supports all planned downstream analyses.

### 5.6 Identity Edge Cases (Explicitly Documented)

| Edge Case | Policy | Unresolved? |
|-----------|--------|-------------|
| Two vehicles of same class/color enter simultaneously from opposite sides | Assign separate `global_id`s based on entry frame order and trajectory | No — spatial separation resolves |
| Vehicle stops on ROI boundary for > 30 frames | Continues same `global_id`; occlusion = 0; not "disappeared" | No — stationary ≠ invisible |
| **Vehicle class appears to change** (e.g., truck → car due to occlusion/distance) | **Class is immutable per `global_id`.** If class genuinely changes → **terminate old track, start new `global_id`**. If uncertain (distance/occlusion) → **continue same `global_id`, mark `difficult: true` on affected frames, keep original class** | No — class immutability is enforced; uncertainty → difficult flag |
| Vehicle splits into two (trailer detaches) | Original `global_id` = truck; new `global_id` = trailer (if separately mobile) | Unlikely in 3.mp4 |
| Night/illumination change causing appearance shift | Same `global_id` if trajectory continuous; `difficult: true` during transition | No — trajectory is primary |

**Class immutability rule:** A `global_id` track has exactly one `class` value for its entire lifetime. Class changes = new object = new `global_id`. Ambiguity at distance/occlusion does NOT justify class change — use `difficult: true` instead.

---

## 6. Counting Event Policy

This section defines precisely what constitutes a Ground Truth counting event. The policy derives counting events **from Ground Truth tracks**, not from predictions. Each event references a `global_id`.

### 6.1 Counting Boundary / ROI

| Property | Value | Source |
|----------|-------|--------|
| **ROI Polygon** | `[(80,40), (1000,40), (1000,490), (80,490)]` | config.yaml |
| **Coordinate Space** | 1020×500 (pipeline resolution) | Video resize |
| **Boundary Type** | Closed polygon; crossing = bottom-center point transition from outside → inside | Pipeline implementation |
| **Countable Classes** | `car`, `motorcycle`, `bus`, `truck`, `person` | config.yaml |

### 6.2 Crossing Condition

A Ground Truth counting event occurs **iff all** conditions hold:

1. **Track exists:** Object has a valid `global_id` in tracking GT
2. **Class is countable:** `class ∈ {car, motorcycle, bus, truck, person}`
3. **Bottom-center crossing:** The point `(center_x, y2)` = `((x1+x2)/2, y2)` crosses the ROI polygon boundary
4. **Direction = entry:** Crossing from **outside → inside** the ROI polygon
5. **First crossing only:** Each `global_id` generates **at most one** entry event per video

**Mathematical definition:**
```
Let P_t = bottom-center point at frame t
Let P_{t-1} = bottom-center point at frame t-1
Let ROI = polygon

Crossing at frame t  ⇔  P_{t-1} ∉ ROI  AND  P_t ∈ ROI
Direction = "entry"  (inside is toward frame center)
```

### 6.3 Count Event Fields

```json
{
  "event_id": 1,
  "global_id": "GT_001",
  "class": "car",
  "frame_id": 150,
  "timestamp": 10.0,
  "roi_point": [520, 300],
  "direction": "entry",
  "bbox_at_crossing": [490, 250, 550, 350],
  "crossing_confidence": "high"
}
```

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `event_id` | int | Yes | Sequential unique identifier (1, 2, 3...) |
| `global_id` | string | Yes | **Must reference tracking GT** (GT_XXX) |
| `class` | string | Yes | Vehicle class at crossing |
| `frame_id` | int | Yes | Frame where crossing detected (first inside frame) |
| `timestamp` | float | Yes | `frame_id / 15.0` |
| `roi_point` | [x, y] | Yes | Bottom-center point at crossing frame |
| `direction` | string | Yes | `"entry"` (current pipeline) or `"exit"` (future) |
| `bbox_at_crossing` | [x1,y1,x2,y2] | Yes | Full bbox at crossing frame |
| `crossing_confidence` | string | Yes | **Objective score** — see Section 6.3.1 below |

### 6.3.1 Crossing Confidence — Objective Scoring Rule

`crossing_confidence` is assigned **deterministically** from observable properties at the crossing frame — **not** annotator judgment.

| Score | Rule (ALL conditions must hold) |
|-------|---------------------------------|
| **high** | `visibility ≥ 0.7` AND `occlusion ∈ {0, 1}` AND `truncated = false` AND bottom-center point fully inside ROI (not on boundary) |
| **medium** | `visibility ≥ 0.3` AND `occlusion ≤ 2` AND (bottom-center computable) AND NOT all `high` conditions |
| **low** | `visibility < 0.3` OR `occlusion = 3` OR `truncated = true` OR bottom-center on ROI boundary/vertex OR class `difficult = true` at crossing frame |

**No subjective assessment.** The annotator records the observable fields (`visibility`, `occlusion`, `truncated`, `difficult`, bbox geometry); the confidence score is computed by rule.

### 6.4 Duplicate-Event Prevention

| Rule | Implementation |
|------|----------------|
| **One entry per global_id** | Track `global_id` → at most one `direction: "entry"` event |
| **No double-count on re-entry** | If object exits and re-enters (> 30 frames gap = new `global_id`), new track = new potential count |
| **Event deduplication** | If multiple consecutive frames satisfy crossing condition, use **first** such frame as `frame_id` |

### 6.5 Handling Edge Cases

| Scenario | Policy | Reasoning |
|----------|--------|-----------|
| **Vehicle moving back-and-forth near boundary** | Count on **first** entry crossing; subsequent oscillations ignored (same `global_id`) | Prevents overcounting; matches pipeline intent |
| **Vehicle stopping on boundary** | Count when bottom-center **first enters** ROI (first frame where point ∈ ROI) | Clear temporal trigger |
| **Vehicle crossing during occlusion** | **Only count if visible at crossing frame** (visibility > 0.1, occlusion < 3). If fully occluded at crossing, **no count event** (cannot verify). | GT requires observable evidence |
| **Vehicle entering/exiting camera view (not ROI)** | No count event unless ROI crossing also occurs. Camera entry ≠ ROI entry. | ROI is counting boundary, not frame edge |
| **Partially visible vehicle at crossing** | Count if: bottom-center point computable AND visible fraction > 0.3. Mark `crossing_confidence: "medium"` or `"low"`. | Partial visibility reduces certainty |
| **Ambiguous crossing direction** (tangential) | Annotator judges: if trajectory clearly enters → `entry`; if exits → `exit`; if truly ambiguous → `crossing_confidence: "low"`, direction = best estimate. | Tangential crossings are rare in 3.mp4 (straight road) |
| **Multiple vehicles crossing simultaneously** | Each gets separate event with own `global_id`, own `frame_id` (may be same frame) | Independent identities |
| **Vehicle crosses, exits, re-enters within < 30 frames** | **Single count event** (same `global_id`). No new event on re-entry. | Short gap = same visit |

### 6.6 Derivation: Counting GT from Tracking GT

**Counting events are derived algorithmically from tracking GT, not annotated independently.**

Process:
1. For each track in tracking GT (with `global_id`, class, per-frame bboxes):
   - Compute bottom-center point per frame: `cx = (x1+x2)/2`, `cy = y2`
   - Test point-in-polygon against ROI for each frame
   - Find first frame `t` where: `P_{t-1} ∉ ROI` AND `P_t ∈ ROI`
   - If found AND class is countable → create count event
2. Collect all events → counting GT JSON
3. Compute `total_counts` by class aggregation

**This ensures:** Counting GT is perfectly consistent with tracking GT. No independent annotation drift.

### 6.7 Counting Edge Cases (Explicitly Documented)

| Edge Case | Policy | Unresolved? |
|-----------|--------|-------------|
| Vehicle bottom-center exactly on ROI vertex/edge | Count as crossing (point-in-polygon includes boundary) | No — standard geometry |
| Vehicle class changes at crossing frame | Use class at crossing frame; if ambiguous, `difficult: true` | Partial — rare |
| Two vehicles cross in same frame, one occludes other | Both counted if both have valid crossing; occlusion doesn't prevent counting if bottom-center visible | No |
| Motorcycle with rider — bottom-center on rider vs bike | Bottom-center of **vehicle bbox** (includes rider) | No — single bbox per 3.7 |
| Person crossing on foot | Counted if class=`person` and countable (config includes person) | No — config-driven |

### 6.8 Connection Between Tracking and Counting

| Principle | Implementation |
|-----------|----------------|
| **Counting GT references tracking GT** | Every count event has `global_id` matching a tracking GT track |
| **No ByteTrack `track_id` in counting GT** | Only `global_id` (GT_XXX) appears in counting events |
| **One-to-many: track → events** | One track can generate: 0 events (never crosses), 1 event (entry), or 2 events (entry + exit if bidirectional) |
| **Validation rule** | `count_events[].global_id` must exist in `tracks[].global_id` |
| **Pipeline evaluation** | Match predicted count events to GT count events via `global_id` (spatiotemporal matching), not `track_id` |

### 6.9 Future Graph Compatibility

The counting event schema preserves information required for:

| Future Use | Preserved Information |
|------------|----------------------|
| **Trajectory** | `global_id` + `frame_id` + `bbox_at_crossing` + `roi_point` → crossing location on path |
| **Zone Transition** | `roi_point` + `direction` + `global_id` → zone entry/exit events |
| **Traffic State** | `timestamp` + `class` + `global_id` → flow rate, occupancy per class |
| **Dynamic Traffic Graph** | `global_id` + sequential `roi_crossings` (if multi-zone) → origin-destination pairs |

**Current ROI = single zone.** Future multi-zone graphs will extend `roi_crossings` array per track with multiple zone polygons. No schema change needed — just additional polygons in metadata.

---

## 7. Temporal Sampling Protocol

This section defines the protocol for selecting which source video frames are annotated. Temporal sampling governs **annotation and evaluation dataset construction** only. It is a data-preparation decision and does not alter the production inference pipeline.

**Status:** 7.1–7.9 complete. 7.10 onward pending.

### 7.1 Purpose

Temporal sampling exists for two purposes:

1. **Annotation efficiency.** Annotating every source frame (621 frames at 15 FPS for `3.mp4`) is unnecessary for building reliable Ground Truth. A subset of frames, selected with explicit rules, captures the information needed to construct tracking GT, detection GT, and counting GT.
2. **Evaluation dataset construction.** The sampled frames define which frames contribute to detection mAP, tracking metrics (HOTA/IDF1), and counting metrics. Sampling is a dataset-design choice, not a pipeline behavior.

**Critical boundary:** Temporal sampling is applied **only to the Ground Truth creation workflow**. The production inference pipeline (YOLOv8m + ByteTrack + Entity Association + ROI Counting) runs on **every** source frame at full frame rate. Sampling does not:

- Reduce the frame rate at which the model runs
- Skip frames during inference
- Alter tracker state between frames
- Change any output of the production pipeline

Sampling decisions affect **what is annotated and what is evaluated**, never **what the pipeline computes**. Any downstream comparison between sampled GT and full-rate pipeline output must account for this asymmetry explicitly (see Section 7.12).

### 7.2 Sampling Units and Frame Indexing

This protocol distinguishes five frame categories. Each category is defined relative to the source video and to the annotation workflow. All frames are referenced by `frame_id`, the 0-based sequential index (0 to 620 for `3.mp4`), with `timestamp = frame_id / 15.0` seconds (see Section 2.2).

| Term | Definition | Produced by | Consumed by |
|------|-----------|-------------|-------------|
| **Source video frame** | Every frame in the raw video (`3.mp4`: 621 frames, 0–620). The full temporal domain. | Video file | Everything downstream |
| **Candidate frame** | A source frame that is eligible for annotation. All source frames are candidates unless explicitly excluded by a protocol rule. Candidate frames are *considered*, not necessarily *selected*. | Candidate enumeration (Section 7.3) | Sampling selection |
| **Sampled frame** | A candidate frame selected by the sampling protocol (baseline keyframe sampling and/or event-boosted sampling). A sampled frame is **scheduled for annotation**. | Sampling protocol (7.3–7.5) | Annotation scheduling |
| **Event-boosted frame** | A sampled frame selected specifically because an important event occurs near it. Event-boosted frames are a subset of sampled frames with `sampling_reason` set to an event-based value. | Event detection (7.4, 7.8–7.10) | Annotation scheduling |
| **Annotation frame** | A frame on which annotation work is actually performed and recorded. Every annotation frame is a sampled frame, but a sampled frame may be deferred or dropped (e.g., if annotation resources are exhausted), in which case it is no longer an annotation frame. | Annotation execution | Detection GT, tracking GT |

**Relationships:**

```
source video frames (all 621)
  └── candidate frames (all source frames, unless excluded)
        └── sampled frames (baseline + event-boosted)
              ├── event-boosted frames (event-based sampling_reason)
              └── baseline-only frames (sampling_reason = base_temporal)
                    └── annotation frames (actually annotated & recorded)
```

A frame is an **annotation frame** only if it is a **sampled frame**. A frame may be a **sampled frame** without being an **event-boosted frame** (baseline sampling suffices). A frame is a **candidate frame** if it has not been excluded by the protocol; candidate status is a precondition for being sampled, not a separate selection step.

**Frame indexing rules (consistent with Section 2.2):**

- `frame_id` is a 0-based integer, 0 to 620 for `3.mp4`.
- `timestamp` is derived: `timestamp = frame_id / 15.0`. It is recorded, never independently assigned.
- Frame identity never depends on sampling: a `frame_id` refers to the same source frame regardless of whether it is sampled, candidate, or annotated.
- Tracking GT `global_id` spans the full frame domain (Section 5.3, Scenario 12): a track exists continuously across all frames; sampling only reduces which frames carry an explicit annotation. Annotating a sampled subset does not create or destroy track identity.

**Scope boundary.** The categories above apply to the Ground Truth workflow. The production inference pipeline has its own per-frame processing loop with no concept of candidate, sampled, or annotation frames. The two pipelines are independent; Section 7.1 states this separation and Section 7.12 covers the consequences for evaluation.

### 7.3 Baseline Keyframe Sampling

The baseline sampling rule provides a uniform, deterministic temporal grid over the entire video. It is the default sampling density: every frame not selected by baseline sampling may still be selected by event-boosted sampling (Section 7.4), but no frame is annotated unless it is selected by at least one rule.

**Baseline rule:** Select every 5th source frame, using the frame index directly.

- **Interval:** 5 frames. For `3.mp4` at 15 FPS, this is 1/3 second between sampled frames.
- **Frame selection:** A source frame with `frame_id = f` is a baseline-sampled frame iff `f mod 5 == 0`.
- **Preserved identity:** The sampled frame retains its original `frame_id` and its original `timestamp = frame_id / 15.0`. Sampling does not renumber frames, does not create synthetic frames, and does not shift timestamps. A baseline-sampled frame at `frame_id = 100` is the same source frame the production pipeline processes at `frame_id = 100`.
- **Coverage:** The rule covers the full frame domain 0–620. For `3.mp4`, baseline-sampled frames are `0, 5, 10, ..., 620` (125 frames). Frame 620 satisfies `620 mod 5 == 0` and is baseline-sampled. Frames 616–619 are not baseline-sampled; they may still be selected by event boosting, or left unannotated.
- **Deterministic sampling:** The rule is a pure function of `frame_id`. Given the same video and the same interval, the same set of frames is selected every time. There is no randomness, no seed, and no dependence on annotation order, annotator choice, or runtime state.
- **Reproducible sampling:** Because the rule depends only on `frame_id` and the fixed interval, any implementation that applies `f mod 5 == 0` over the frame domain 0–620 produces an identical sampled set. Reproducibility is recorded in the sampling manifest (Section 7.11), which stores `base_interval` and the per-frame `sampling_reason`.

**Protocol parameters (not empirical facts):** The 5-frame interval is a protocol parameter chosen for annotation efficiency, not an observation about the video. It has not been validated against annotation quality or metric stability; that validation is deferred to the pilot dataset (Section 10) and is listed as requiring empirical validation in Section 7.12.5. If validation shows the interval is too coarse for the annotation task, the parameter is adjusted and the manifest regenerated; this is a parameter change, not a change to the sampling *method*.

**What baseline sampling does not do:**

- It does **not** sample based on object motion, events, density, occlusion, or illumination. Those criteria are handled by event-boosted sampling (Section 7.4) and stratification (Section 7.5).
- It does **not** prioritize frames. Every baseline-sampled frame is treated equally; no baseline frame is weighted above another.
- It does **not** alter the frame rate or drop frames from the pipeline. Baseline sampling selects frames for *annotation*; the production pipeline still processes all source frames (Section 7.1).

**Consistency with existing decisions:**

- Baseline-sampled frames are candidate frames (Section 7.2) and become sampled frames. Their `sampling_reason` in the sampling manifest is `base_temporal`.
- Baseline sampling preserves `frame_id` and `timestamp`, consistent with Section 2.2 frame referencing and with the tracking GT schema, which keys observations by `frame_id`.
- The interval of 5 frames is independent of the 30-frame short-gap threshold (Section 5.3). Five frames at 15 FPS is 1/3 second; the 30-frame threshold is 2 seconds. They serve different purposes: 5 frames governs annotation density, 30 frames governs identity continuity.

### 7.4 Event-Boosted Sampling

Baseline sampling (Section 7.3) is uniform and blind to scene content. It can miss short-lived or information-dense events that are disproportionately important for evaluating detection, tracking, and counting. Event-boosted sampling adds frames around such events. An event-boosted frame is a sampled frame whose `sampling_reason` is an event-based value (see Section 7.11 for the manifest vocabulary).

**Principle:** For each detected event, sample a local window of frames centered on the event. The window is a **protocol parameter**, not an observed quantity; its size has not been validated against annotation quality and is listed in Section 7.12.1.

**Event categories and rationale:**

| # | Event | Why it is boosted | Consistency with existing sections |
|---|-------|-------------------|-----------------------------------|
| **E1** | **ROI crossing** | The crossing frame is the direct evidence for a counting event (Section 6.2). Sampling near the crossing verifies the bottom-center transition and captures the object's appearance at the boundary. | Counting GT is derived from tracking GT (Section 6.6); a crossing frame anchors the `roi_point` and `direction` fields. |
| **E2** | **Object appearance / disappearance** | Birth and death of a `global_id` are identity-critical (Section 5.3, Scenarios 1 and 2). The first annotated frame establishes the class and bbox baseline; the last annotated frame confirms termination. | Appearance = new `global_id` assignment (Section 5.2.2); termination = `end_frame` (Section 5.3, Scenario 2). |
| **E3** | **Tracking identity ambiguity** | ID switches and re-identification decisions are the dominant source of tracking error. Frames where two objects cross, where a reappeared object must be associated, or where a >30-frame gap is closed are high-value. | Section 5.3, Scenarios 7, 8, 11; the 30-frame threshold governs whether a reappearance is same-ID or new-ID. |
| **E4** | **Heavy / severe occlusion** | Objects at occlusion level 2 or 3 are the hardest for detection and are a distinct evaluation stress test (Section 4.1). Frames at occlusion onset and recovery (object reappears) are both valuable. | Severe occlusion = `(0.0, 0.1]` visibility; `visibility = 0` means no bbox (Section 4.1, 5.3 Scenario 3). |
| **E5** | **Class ambiguity** | Frames where an object's class is uncertain (car vs truck, motorcycle vs person at distance) carry `difficult: true` (Section 2.4). Annotating them measures per-class error under ambiguity. | Class is immutable per `global_id` (Section 5.6); ambiguity is flagged, never resolved by relabeling. |
| **E6** | **Difficult traffic situations** | Dense clusters, simultaneous crossings, and unusual configurations stress both annotation and evaluation. | Multiple simultaneous crossings get separate events with distinct `global_id`s (Section 6.5). |

**Event-boosted frame selection rules (protocol parameters):**

- **Window size:** A protocol parameter (frames per side of the event). Not empirically established; see Section 7.12.1.
- **Centering:** The event frame is the center of the window when the event is a single frame (e.g., a crossing frame). For multi-frame events (e.g., an occlusion interval), the window covers the interval plus the parameterized margin on each side.
- **Overlap with baseline sampling:** An event-boosted frame may coincide with a baseline-sampled frame. In that case the frame is sampled once, and its `sampling_reason` records the event-based reason (event reasons take precedence over `base_temporal` for the primary reason field; the manifest schema in Section 7.11 supports one primary `sampling_reason` per sample).
- **No double annotation:** Each `frame_id` is annotated at most once, regardless of how many events triggered it. The manifest records one `sample_id` per `frame_id`.

**What event boosting does not do:**

- It does **not** alter the baseline grid. Baseline sampling remains the uniform floor; event boosting only *adds* frames.
- It does **not** change track identity. A `global_id` is unaffected by which frames are annotated (Section 7.2, Section 5.3 Scenario 12).
- It does **not** determine which frames the pipeline processes. It selects frames for annotation only (Section 7.1).

**Consistency note:** The `sampling_reason` vocabulary used here must match the enum in `sampling_manifest.schema.json`. The event-based values are: `roi_crossing`, `entry_event`, `exit_event`, `post_occlusion_appearance`, `pre_occlusion_disappearance`, `severe_occlusion`, `ambiguous_identity`, `class_ambiguity`, `high_density`. The mapping from the event categories above to manifest values is defined in Section 7.11.

### 7.5 Stratified Sampling Criteria

Stratification ensures the sampled set covers the conditions the evaluation must generalize across. It is a **labeling and auditing** criterion applied to sampled frames, not an independent sampling pass: every sampled frame is assigned stratum labels, and the manifest records them so the dataset composition can be audited against the strata.

**Strata to record per sampled frame** (all are protocol-defined categories; the actual distribution of frames across strata is **not** claimed here because it has not been measured — see Section 7.12.1).

| Stratum | Basis | Recorded field (manifest) | Relation to existing definitions |
|---------|-------|---------------------------|----------------------------------|
| **Object density** | Number of annotated objects in the frame | `traffic_density` ∈ {low, medium, high} | Density thresholds are protocol parameters, not observations. |
| **Occlusion level** | Distribution of `occlusion` values among objects in the frame | `occlusion` per annotation (0–3, Section 4.1) | Severe occlusion = `(0.0, 0.1]` visibility; level 3. |
| **Illumination / visibility** | Frame-level visibility conditions | `visibility` per annotation (0.0–1.0, Section 4.1) | `visibility = 0` → no bbox observation (Section 4.1). |
| **Traffic events** | Presence of any event from Section 7.4 | `sampling_reason` / `event_type` (manifest) | ROI crossing, appearance/disappearance, identity ambiguity, occlusion, class ambiguity, difficult traffic. |

**Stratification purpose:**

- **Audit dataset balance:** After sampling, the manifest is aggregated by stratum to verify coverage. If a stratum is under-represented, the sampling protocol is adjusted (more event boosting) or the limitation is documented.
- **Metric stratification:** Evaluation metrics (mAP, HOTA, IDF1, counting error) are reported per stratum, so performance under severe occlusion, high density, or class ambiguity is measured separately from overall performance.
- **No re-weighting of source frames:** Stratification labels frames; it does not change which frames are sampled and does not assign sampling weights that alter the baseline grid.

**Separating protocol parameters from observed values:**

| Item | Type | Status |
|------|------|--------|
| Baseline interval (5 frames) | **Protocol parameter** | Chosen for annotation efficiency; not validated. |
| Event-boosted window size | **Protocol parameter** | Not empirically established. |
| Density stratum thresholds (low/medium/high) | **Protocol parameter** | Not empirically established. |
| Difficulty stratum thresholds (easy/moderate/hard) | **Protocol parameter** | Not empirically established. |
| Distribution of frames across train/val/test | **Protocol parameter** | Defined by the temporal split (Section 7.6); not an observed distribution. |
| Actual traffic density per frame | **Empirically observed value** | Not measured; must not be claimed in this document. |
| Actual occlusion distribution in the video | **Empirically observed value** | Not measured; must not be claimed in this document. |
| Actual illumination/visibility conditions | **Empirically observed value** | Not measured; must not be claimed in this document. |
| Frequency of each event type | **Empirically observed value** | Not measured; must not be claimed in this document. |

**Rule:** Where this document states a threshold or interval, it is a protocol parameter unless explicitly labeled as measured. No claim about the video's actual density, occlusion, illumination, or event frequency appears in this section, because no such measurement has been performed or documented in the repository.

### 7.6 Temporal Train/Validation/Test Split

**Purpose.** Partition the sampled frames (Section 7.2) into train, validation, and test datasets for model training and evaluation. The split is a dataset-design decision (Section 7.1): it affects *which frames are used to train and evaluate the pipeline*, never *what the pipeline computes*.

**Approved split (protocol parameter).**

| Partition | frame_id range | Size | Purpose |
|-----------|---------------|------|---------|
| train | 0–249 | 250 frames | Model training |
| validation | 250–374 | 125 frames | Hyperparameter tuning, early stopping, model selection |
| test | 375–499 | 125 frames | Final evaluation only; no training or tuning on these frames |

**Assignment rule.** A frame's partition is a pure, deterministic function of `frame_id`:

```
split(frame_id):
    frame_id in [0,   249] -> train
    frame_id in [250, 374] -> validation
    frame_id in [375, 499] -> test
    frame_id in [500, 620] -> unassigned (excluded, see 7.6.1)
```

There is no shuffling, no random seed, and no stratified balancing across partitions. The rule is reproducible: given the same frame domain, the same assignment is produced every time. The `split` field is recorded per sample in the sampling manifest (`sampling_manifest.schema.json`, required field, enum `["train", "val", "test"]`).

**Why a contiguous temporal split (random splitting is forbidden).** Random frame-level splitting destroys the structure the evaluation must measure. A traffic video is a single continuous stream: a vehicle crosses the ROI over several consecutive frames, an occlusion episode spans a contiguous interval, and counting events are defined by frame-to-frame transitions (Section 6.2). Random splitting scatters these episodes across partitions, so:

- The same vehicle, occlusion episode, or crossing would appear in both train and test, inflating apparent performance — the model would be evaluated on the same physical situation it was trained on.
- Temporal correlation between adjacent frames would leak across partitions, violating the independence assumption underlying standard metric aggregation.
- The counting evaluation would become meaningless, because verifying a crossing requires the immediately preceding frame (Section 7.8).

A contiguous split keeps each partition as a self-contained temporal window. Train, val, and test cover disjoint, consecutive intervals of the video. This is the standard approach for time-series and video evaluation and is the only split consistent with the frame-to-frame definitions in this protocol.

**Protocol-parameter status.** The boundary positions (249/250 and 374/375) are chosen, not derived from the video. They are protocol parameters (Section 7.5). No claim is made about where traffic conditions change or about the distribution of events across partitions; such measurements have not been made and are listed in Section 7.12.1.

#### 7.6.1 Frames 500–620 Are Unassigned

The approved split covers `frame_id` 0–499. The source video `3.mp4` has 621 frames (0–620). **Frames 500–620 are not assigned to train, validation, or test** and are excluded from the annotation and evaluation datasets.

This is a gap in the protocol, not an observation about the video. It is recorded in Section 7.12 as an open item requiring resolution (extend the split, or formalize the exclusion). It must not be misread as "the last 121 frames contain no traffic": the production pipeline processes all 621 frames at full rate (Section 7.1); only the GT annotation and evaluation dataset is split. Baseline-sampled frames in 500–620 (Section 7.3) currently have no partition assignment and must not be annotated until the split is extended or the exclusion is formalized.

#### 7.6.2 Split and Sampling

The split applies to sampled frames (Section 7.2). A sampled frame is assigned a partition; an unsampled frame has none. Baseline-sampled frames and event-boosted frames are both assigned by the same `split(frame_id)` rule. The split does not alter *which* frames are sampled (Sections 7.3–7.5); it only labels the sampled ones.

### 7.7 Leakage Prevention

**Definition.** In this protocol, leakage means information from one dataset partition reaching the model during training or evaluation of another partition in a way that inflates performance or invalidates the evaluation. Two channels exist:

1. **Frame-content leakage:** frames from val/test being used in training, or val/test evaluation being conditioned on train frames.
2. **State leakage:** tracker identity or tracker internal state from one partition being used to resolve ambiguity in another.

**Core rule — one frame, one partition.** Every frame belongs to exactly one partition, determined by `frame_id` alone (Section 7.6). No frame is duplicated across partitions, relocated between partitions, or shared. At the manifest level this is enforced by three properties:

- `split` is a required field on every sample (`sampling_manifest.schema.json`).
- Each `frame_id` appears at most once in the manifest — one `sample_id` per frame (Section 7.4).
- No downstream step may reassign or copy a frame's partition.

**The boundary problem — event windows.** Event-boosted sampling (Section 7.4) selects a window of frames around each event, extending a protocol-defined number of frames to each side. An event near a partition boundary would, if the window were applied across the boundary, pull frames from the adjacent partition into the event's partition. Annotating val frames in the train set is direct leakage: the model would then be trained on frames it should only be evaluated on.

**Rule — clip, do not move.** An event-boosted window is clipped at the partition boundary. The window covers only frames within the event's own partition; frames beyond the boundary are dropped from that window. They are not relocated, not re-assigned, and not annotated for that event — they remain subject to their own partition's sampling rules.

| Event location | Naive window | Clipped window | Frames beyond boundary |
|---------------|--------------|----------------|------------------------|
| ROI crossing at frame 248 (train), window ±10 | 238–258 | 238–249 | 250–258 dropped; stay in val, sampled there only by val rules |
| Appearance at frame 250 (val, first val frame), window ±10 | 240–260 | 250–260 | 240–249 dropped; stay in train |
| Crossing at frame 370 (val), window ±10 | 360–380 | 360–374 | 375–380 dropped; stay in test |

The event itself is always annotated — it belongs to its own partition and its window is never empty. Clipping only shortens the window; it never removes the event frame.

**"Without moving frames across dataset partitions"** means exactly this: frames are dropped from an overhanging window, never moved. A frame's partition is an immutable property of its `frame_id`. No operation in this protocol changes a frame's partition.

**Identity continuity is not leakage.** A single `global_id` track spans the full video (Section 5.3, Scenario 12) and will legitimately carry annotations across partition boundaries — a car that appears in train and reappears in val is one track with observations in two partitions. This is not leakage because:

- `global_id` is ground-truth identity assigned by the annotator, not a model output. It carries no information the model could exploit.
- The model is never trained on val or test frames. During training it sees only train-partition observations; the track's val observations are not part of the training input.
- Tracking evaluation on val/test uses only val/test observations. The model's tracker is not fed train frames while evaluating val/test.

**Tracker-state boundary.** A separate but related question is whether the production tracker's internal state (ByteTrack active tracks, Kalman filters, feature memory) carries across a partition boundary during evaluation. If it did, val/test evaluation would be conditioned on train observations — state leakage. The protocol decision is: **tracker state is reset at each partition boundary during evaluation.** Each partition is tracked as an independent sequence. This is a protocol parameter (Section 7.12.2) because it affects tracking metrics (HOTA/IDF1) and must be reported alongside results. It does not affect GT construction: tracking GT is fixed and partition-independent.

**Counting-event attribution.** Counting events (Section 6) are attributed to the partition of their crossing `frame_id`. An event is never duplicated across partitions, and per-partition `total_counts` are computed only from events in that partition. A track that crosses the ROI in train and again in val generates two events attributed to their respective partitions — correct behavior, not double-counting, because each partition measures traffic in its own temporal window.

**Enforcement.** Frame-content leakage is prevented by the manifest `split` field, the one-`sample_id`-per-`frame_id` rule, and the evaluation scripts' obligation to never feed val/test frames into the training loop. State leakage is prevented by the tracker-state reset. Both are checked in the pilot acceptance criteria (Section 15).

**What leakage prevention does not do.** It does not re-assign `global_id`s per partition (that would fragment tracks and degrade tracking evaluation). It does not remove boundary-crossing tracks. It does not require partitions to be event-free at their edges. It only guarantees that no frame, annotation, or tracker state from one partition is used to train or evaluate another.

### 7.8 Handling ROI-Crossing Events

**Requirement.** ROI-crossing events must remain reconstructable from the appropriate temporal context without creating train/test leakage. This section defines how crossing events on or near partition boundaries are handled so that no ground-truth information is lost and no frame crosses a partition.

**Why boundary crossings are special.** A counting event (Section 6.2) is defined by a frame-to-frame transition:

```
Crossing at frame t  ⇔  P_{t-1} ∉ ROI  AND  P_t ∈ ROI
```

Verifying this transition requires two frames: the crossing frame `t` and the immediately preceding frame `t-1`. When `t` is the first frame of a partition (`t = 250` or `t = 375`), frame `t-1` belongs to the preceding partition. The two frames needed to reconstruct the event then sit in different partitions — exactly the situation Section 7.7 must resolve without losing the event.

**Options considered, and the chosen one.**

| Option | Problem |
|--------|---------|
| Move frame `t-1` into the partition of `t` | Violates "no moving frames across partitions" (Section 7.7). |
| Drop the crossing event | Loses ground truth; undercounts the partition. |
| Attribute the event to the partition of `t`, and reference `t-1` as a read-only anchor | Preserves the event; no frame moves; no leakage. **Chosen.** |

**Boundary-crossing attribution rule.**

1. A crossing event is attributed to the partition containing the crossing frame `t`. Its fields (`event_id`, `global_id`, `class`, `frame_id`, `timestamp`, `roi_point`, `direction`, `bbox_at_crossing`, `crossing_confidence`) are recorded in that partition's counting GT.
2. Frame `t-1`, when it lies in the preceding partition, is referenced as a **read-only geometric anchor** for crossing verification. It is not sampled into, not annotated in, and not used for training or evaluation in the partition of `t`. Reading its fixed ground-truth geometry leaks nothing: GT is constructed before any model runs, and the anchor is never part of the partition's input set.
3. `crossing_confidence` is computed from the observable fields at frame `t` only (Section 6.3.1), exactly as for any other crossing. The anchor frame is used solely to establish `P_{t-1} ∉ ROI`, never to score the event.

**Case table.**

| Case | Crossing frame `t` | Preceding frame `t-1` | Handling |
|------|--------------------|-----------------------|----------|
| 1. Crossing well inside a partition | e.g., 300 (val) | 299 (val) | Normal. Both frames in the same partition. No special handling. |
| 2. Crossing at the first frame of a partition | 250 (val) or 375 (test) | 249 (train) or 374 (val) | Event attributed to the partition of `t`. `t-1` is a read-only anchor from the preceding partition. Event recorded normally. |
| 3. Crossing at the last frame of a partition | 249 (train) or 374 (val) | 248 (train) or 373 (val) | For an entry event, both frames are in the same partition. Event attributed to the partition of `t`. No anchor needed. |
| 4. Track spans a boundary | crossing at 300 (val), track present in train | — | Event attributed to val. Train-partition observations of the same `global_id` are not part of val input (Section 7.7). No leakage. |

**What "the appropriate temporal context" means.** For a crossing event at frame `t`, the appropriate temporal context is the track's ground-truth geometry at frames `t-1` and `t`, together with the ROI polygon. Tracking GT is stored as one video-wide structure and split into per-partition evaluation views; the crossing event's own fields are self-describing and are recorded in the partition of `t`. The read-only anchor at `t-1` is resolved against the track record, not against the partition's evaluation set. Reconstruction therefore never requires adding a frame to a partition it does not belong to.

**Auditing the anchor.** To keep boundary crossings auditable, the counting-GT derivation (Section 6.6) records, for any event whose `t-1` lies in a different partition, an optional `anchor_frame_id` pointing to the preceding frame. This is a derivation-log concern, not a schema change: the event schema in `counting_ground_truth.schema.json` is unchanged, and `anchor_frame_id` is not part of the validated event. Pilot acceptance (Section 15) requires that every boundary crossing be reconstructable from the manifest plus the track record.

**Pipeline-evaluation asymmetry.** GT reconstruction is unaffected by how the production pipeline runs. The pipeline processes all 621 frames at full rate (Section 7.1), so when evaluated on the test partition (frames 375–499) its tracker may carry state from before frame 375. Section 7.7 mandates resetting tracker state at partition boundaries during evaluation, which resolves this for pipeline metrics. For GT, a crossing at frame 375 is reconstructed from fixed ground truth regardless of pipeline state, so the asymmetry does not affect GT correctness.

**Consistency.** This section moves no frames (7.7), re-assigns no `global_id`s, duplicates no counting events, and attributes every crossing event to exactly one partition. Together with 7.6 and 7.7, the guarantee is: every ROI-crossing event in the video is recorded in exactly one partition, is fully reconstructable from GT geometry, and no frame or tracker state from another partition enters the training or evaluation of that partition.

### 7.9 Handling Short Tracking Gaps and Occlusion

This section defines how temporal sampling interacts with frames affected by short tracking gaps, temporary occlusion, disappearance and reappearance, severe occlusion, and full invisibility. It governs **which frames are selected for annotation and how gaps are represented in the tracking GT record**. It does not alter the production inference pipeline (Section 7.1).

**Status:** 7.9 complete.

#### 7.9.1 Definitions of the Five Temporal States

Every source frame is classified, for each `global_id` track, into exactly one of the following states. These states are defined relative to the source video and to the annotation workflow; they are not properties of the production pipeline.

| # | State | Definition | Bbox Observation | `visibility` | `occlusion` |
|---|-------|------------|------------------|--------------|-------------|
| 1 | **Observed frame** | The object is visible and its visible extent can be enclosed in a tight box. A bbox annotation is recorded. | Yes — tight box around visible pixels (Section 3.1) | `(0.0, 1.0]` | 0–3 per Section 4.1 |
| 2 | **Occluded observation** | The object is partially or heavily occluded but still has a visible bbox. This is an observed frame whose `occlusion` level is 1, 2, or 3. | Yes — box encloses visible portions only (Section 3.2) | `(0.0, 1.0]` | 1, 2, or 3 |
| 3 | **Fully invisible gap** | The object has no visible pixels. No bbox can be drawn. | **No** — no bbox annotation for this frame (Section 4.1) | `0.0` | Not applicable |
| 4 | **Short gap** | A contiguous run of fully invisible frames lasting **≤ 30 frames** (2 seconds at 15 FPS). The object may be fully occluded behind another object or temporarily out of camera/ROI view. | No — no bbox in any gap frame | `0.0` throughout the gap | Not applicable |
| 5 | **Long disappearance** | A contiguous run of fully invisible frames lasting **> 30 frames** (more than 2 seconds at 15 FPS). The object has left the scene or camera view and has not returned within the approved short-gap window. | No — no bbox in any gap frame | `0.0` throughout the gap | Not applicable |

**Critical distinction.** States 1 and 2 both carry a bbox observation and differ only in the recorded `occlusion` level. States 3, 4, and 5 carry **no bbox observation**. The difference between a short gap (state 4) and a long disappearance (state 5) is solely the duration of the invisibility run, measured against the single approved threshold of 30 frames / 2 seconds.

#### 7.9.2 Approved Decisions Governing This Section

The following decisions, established in earlier sections, are the only rules applied here. No new thresholds or identity rules are introduced.

| Decision | Value | Source |
|----------|-------|--------|
| Short-gap threshold | 30 frames / 2 seconds at 15 FPS | Section 5.3, Audit A2 |
| Visibility = 0 | No bbox observation | Section 4.1, Audit A1 |
| Severe occlusion | `(0.0, 0.1]` visibility | Section 4.1, Audit A1 |
| global_id persistence through an approved short gap | Same `global_id` when identity continuity is established | Section 5.3, Scenarios 3–5 |
| global_id independent of ByteTrack track_id | Separate identity spaces; never mapped | Section 5.1 |
| No extrapolated bbox for fully invisible frames | No bbox created; no interpolation of box geometry across a gap | Section 3.2, Section 5.3 Scenario 3 |
| Sampling must not modify the production inference pipeline | Sampling selects frames for annotation only | Section 7.1 |

#### 7.9.3 Identity Continuity Across Gaps

**Short gap (≤ 30 frames).** A `global_id` persists through an approved short gap when identity continuity is established. Continuity is established by visual match on reappearance (appearance features, trajectory) and spatiotemporal plausibility (Section 5.2.2). During the gap, no bbox is recorded in any frame; the `frames` array in the tracking GT record contains a temporal gap. On reappearance, the same `global_id` resumes with a new observed entry.

**Long disappearance (> 30 frames).** A reappearance after a gap exceeding 30 frames is assigned a **new** `global_id` (Section 5.3, Scenario 6). The previous track terminates at its last observed frame. This is a conservative rule: it prefers track fragmentation over a false identity merge.

**Severe occlusion.** Severe occlusion (`visibility ∈ (0.0, 0.1]`) is an **observed state**, not a gap. A bbox is recorded around the barely-visible pixels, with `occlusion: 3`. It is distinct from a fully invisible gap, where no bbox exists. The severe-occlusion state is therefore sampled and annotated like any other observed frame; the fully invisible gap is not.

#### 7.9.4 Interaction Between Sampling and the Five States

Sampling (Sections 7.3–7.5) selects frames for annotation. Its interaction with each state is:

| State | Sampling interaction |
|-------|---------------------|
| **Observed frame** (1) | Eligible for baseline sampling (`f mod 5 == 0`) and event-boosted sampling like any other frame. Annotation produces a bbox. |
| **Occluded observation** (2) | Sampled identically to an observed frame. The annotation records the reduced `visibility` and elevated `occlusion` level. Event-boosted sampling (E4) may additionally select frames at occlusion onset and recovery. |
| **Fully invisible gap** (3) | **Not a candidate for annotation.** No bbox is created, and no annotation is recorded for this frame, regardless of whether the frame is baseline-sampled or event-boosted. The frame may still be selected by the sampling protocol for reasons unrelated to this track (e.g., another object is visible in the same frame); in that case the frame is annotated for the other objects only, and this track contributes no entry. |
| **Short gap** (4) | The gap as a whole is not annotated. The frames immediately preceding and following the gap are the annotation anchors. Sampling may select the reappearance frame via event-boosting (E2 appearance, E3 re-identification, E4 occlusion recovery). The gap itself contributes no annotation entries. |
| **Long disappearance** (5) | Same as a short gap for annotation purposes: no annotation during the disappearance. The reappearance frame starts a new `global_id` and is eligible for event-boosted sampling as a birth event (E2). |

**No extrapolation rule.** Sampling never creates, interpolates, or extrapolates a bbox for a fully invisible frame. A gap in the `frames` array is a literal gap: the track record contains observations at the frames before and after the gap, with no entries between them. Any downstream consumer that requires per-frame geometry must handle the gap explicitly; it is not filled by the annotation protocol.

**global_id is independent of sampling.** Which frames are sampled does not affect `global_id` assignment or continuity (Section 5.3, Scenario 12). A track that spans a short gap retains the same `global_id` whether the gap frames are sampled or not. Sampling only changes which frames carry an explicit annotation; it never creates or destroys track identity.

#### 7.9.5 Recording Requirements in Tracking GT

For every track affected by a gap or occlusion, the tracking GT record must support reconstruction of the five states. The minimum required fields are those defined in Section 5.5, with the following gap-specific behavior:

- **During an observed or occluded observation state:** each annotated frame records `frame_id`, `timestamp`, `bbox`, `center`, `visibility`, `occlusion`, `truncated`.
- **During a fully invisible gap:** no entry is recorded for that `frame_id`. The gap is represented by its absence from the `frames` array.
- **Gap duration** is derivable from the `frame_id` values of the surrounding entries: `gap_length = next_frame_id - previous_frame_id - 1`.
- **`start_frame` and `end_frame`** reflect the first and last annotated frames of the track, consistent with Section 5.3 Scenario 2. A track that goes fully invisible and reappears within 30 frames has `end_frame` equal to its last annotated frame before the gap and resumes at the reappearance frame under the same `global_id`; the track's temporal extent is the union of its annotated intervals.

**No schema change.** This section defines behavior using the existing tracking GT fields from Section 5.5. No new fields are added to the tracking GT record and no JSON schema is modified.

#### 7.9.6 Consistency with Counting Events

A counting event (Section 6.2) requires an observable crossing at frame `t`. Frames in a fully invisible gap or long disappearance carry no bbox and therefore cannot host a crossing event. This is consistent with Section 6.5, which counts only when the object is visible at the crossing frame (`visibility > 0.1`, `occlusion < 3`). A vehicle that crosses the ROI boundary while fully occluded generates **no count event**, because the crossing cannot be verified from ground truth.

Severe occlusion (`visibility ∈ (0.0, 0.1]`) may still host a crossing if the bottom-center point is computable from the recorded bbox; in that case `crossing_confidence` is assigned `"low"` by the deterministic rule in Section 6.3.1.

### 7.10 Handling Frames Near Important Events

This section defines how the temporal sampling protocol selects frames that lie near important events requiring additional temporal context. It covers only the event categories already established by Sections 4–6 and 7.4. It does not redefine any event category, identity rule, occlusion level, or counting condition defined in Sections 4–6, and it does not alter any rule in Sections 7.1–7.9.

**Status:** 7.10 complete.

#### 7.10.1 Two Sampling Modes

Every sampled frame is selected by exactly one of two sampling modes. The distinction between them is the basis on which the frame is chosen, not the annotation work performed on it.

| Mode | Basis | Determinism | Defined in |
|------|-------|-------------|------------|
| **`base_temporal`** | Pure function of `frame_id`: a frame is selected iff `frame_id mod 5 == 0`. | Deterministic. Given the same video and interval, the same frame set is produced every time; no seed, no randomness, no dependence on annotation order or runtime state. | Section 7.3 |
| **Event-boosted** | A local window of frames centered on (or spanning) an important event. The window is a protocol parameter, not an observed quantity. | Deterministic once the event set and window size are fixed. Event detection and window placement are reproducible; the window size is a protocol parameter listed in Section 7.12.1. | Section 7.4, 7.8–7.10 |

**Base sampling remains the uniform floor.** Baseline keyframe sampling (Section 7.3) selects frames on a fixed grid blind to scene content. It is unchanged by this section. Every baseline-sampled frame is a candidate for annotation regardless of whether any event occurs near it.

**Event boosting only adds frames.** Event-boosted sampling does not remove, displace, or re-weight any baseline-sampled frame. It adds frames around events that the uniform grid may miss. The sampled set is the union of baseline-sampled frames and event-boosted frames.

#### 7.10.2 Event Categories and Near-Event Frame Handling

The following are the only event categories this section addresses. Each is established elsewhere; this section states only how frames near each event are handled.

| # | Event category | Established in | Near-event frame handling |
|---|---------------|----------------|---------------------------|
| **E1** | **ROI crossing** | Section 6.2, 7.4 (E1), 7.8 | The crossing frame `t` and the immediately preceding frame `t-1` are the temporal context needed to reconstruct the transition `P_{t-1} ∉ ROI` → `P_t ∈ ROI`. Section 7.8 is authoritative for crossings on or near partition boundaries: the event is attributed to the partition of `t`, and `t-1` is a read-only geometric anchor when it lies in the preceding partition. The crossing frame is always sampled; the anchor frame is read for verification and is not sampled into the partition of `t`. |
| **E2** | **Object appearance** | Section 5.3 Scenario 1, 7.4 (E2) | The first annotated frame of a new `global_id` establishes the class and bbox baseline. Frames near the birth frame are sampled so the appearance is recorded with enough surrounding context to confirm the entry. The reappearance frame after a long disappearance (> 30 frames) is handled as a birth event and starts a new `global_id` (Section 5.3 Scenario 6). |
| **E3** | **Object disappearance** | Section 5.3 Scenario 2, 7.4 (E2) | The last annotated frame of a track (`end_frame`) confirms termination. Frames near the disappearance frame are sampled so the exit is recorded with enough context to confirm the object has left. No bbox is extrapolated beyond the last observed frame (Section 3.2, Section 5.3 Scenario 3). |
| **E4** | **Identity ambiguity** | Section 5.3 Scenarios 7, 8, 11, 7.4 (E3) | Frames where two objects cross, where a reappeared object must be associated, or where a > 30-frame gap is closed are sampled, because re-identification decisions dominate tracking error. The 30-frame threshold (Section 5.3) governs whether a reappearance is the same `global_id` or a new one; sampling does not change that rule. |
| **E5** | **Heavy / severe occlusion** | Section 4.1, 7.4 (E4) | Frames at occlusion onset and at recovery (object reappears) are both sampled. A severe-occlusion frame (`visibility ∈ (0.0, 0.1]`) is an observed state and is sampled and annotated like any other observed frame, with `occlusion: 3`. A fully invisible frame (`visibility = 0`) is not a candidate for annotation and contributes no bbox, regardless of whether the frame is sampled (Section 7.9.4). |
| **E6** | **Class ambiguity** | Section 2.4, 5.6, 7.4 (E5) | Frames where an object's class is uncertain carry `difficult: true` and are sampled so per-class error under ambiguity is measurable. Class is immutable per `global_id` (Section 5.6); ambiguity is flagged, never resolved by relabeling, and sampling does not alter the class assigned to a track. |
| **E7** | **Difficult traffic events** | Section 6.5, 7.4 (E6) | Dense clusters, simultaneous crossings, and unusual configurations are sampled. Multiple simultaneous crossings get separate events with distinct `global_id`s (Section 6.5); each is sampled independently and does not merge into one sampling record. |

**Window placement.** For a single-frame event (e.g., a crossing frame), the event frame is the center of the window. For a multi-frame event (e.g., an occlusion interval, or an appearance-to-disappearance run), the window spans the interval plus the protocol-defined margin on each side. The window size is a protocol parameter, not an observed quantity (Section 7.5; listed in Section 7.12.1).

**Event priority is deterministic.** When an event-boosted window overlaps a baseline-sampled frame, the frame is sampled once. Its primary `sampling_reason` records the event-based reason: event reasons take precedence over `base_temporal`. The precedence order among event reasons is fixed and deterministic; it does not depend on annotation order or runtime state. The manifest supports one primary `sampling_reason` per sample (Section 7.4).

#### 7.10.3 Preserved Rules and Invariants

This section does not modify, override, or re-derive any of the following. Each remains authoritative exactly as written.

| Preserved rule | Authority | How this section respects it |
|----------------|-----------|------------------------------|
| **Base sampling remains deterministic** | Section 7.3 | Base sampling is untouched; this section only adds event-boosted frames on top of the uniform grid. |
| **Event boosting does not modify production inference** | Section 7.1 | Event-boosted frames are selected for annotation only. The production pipeline (YOLOv8m + ByteTrack + Entity Association + ROI Counting) processes every source frame at full rate; no frame is skipped and no tracker state is altered. |
| **Event-boosted frames are dataset-construction only** | Section 7.1, 7.4 | Event-boosted frames feed detection GT, tracking GT, and counting GT construction and the evaluation dataset. They do not change what the pipeline computes or outputs. |
| **A frame must not belong to more than one sampling record** | Section 7.4 | Each `frame_id` is sampled at most once and carries one `sample_id` and one primary `sampling_reason`. Overlap between baseline and event-boosted selection resolves by sampling the frame once, not twice. |
| **Event priority must remain deterministic** | Section 7.4, 7.10.2 | Precedence between `base_temporal` and event-based reasons, and among event-based reasons, is a fixed order independent of annotation order or runtime state. |
| **ROI-crossing handling remains authoritative** | Section 7.8 | Section 7.10.2 (E1) defers entirely to Section 7.8 for boundary attribution, the read-only anchor at `t-1`, the case table, and the `anchor_frame_id` derivation log. No crossing rule is redefined here. |
| **Train/val/test partition rules remain authoritative** | Section 7.6 | Every sampled frame, whether base-sampled or event-boosted, is assigned its partition by the same deterministic `split(frame_id)` rule. An event-boosted window is clipped at the partition boundary per Section 7.7; it never moves a frame across a partition. |
| **Leakage prevention rules remain authoritative** | Section 7.7 | Near-event windows follow "clip, do not move." Frames beyond a partition boundary are dropped from the window and remain subject to their own partition's sampling rules. The event frame itself is always annotated in its own partition; clipping only shortens the window. |

**What this section does not do.** It does not redefine any occlusion level (Section 4), any identity rule (Section 5), any counting condition (Section 6), or any sampling rule in Sections 7.1–7.9. It does not introduce event categories beyond those established in Sections 4–6 and 7.4. It does not modify the sampling manifest schema, the tracking GT schema, or the counting GT schema. It does not define or modify Sections 7.11–7.12.

### 7.11 Sampling Manifest Requirements

This section defines the purpose and scope of the sampling manifest. It states what the manifest represents, why it is required, and how it relates to source frames, annotation decisions, and evaluation reproducibility. Subsection 7.11.2 defines the required manifest fields. Subsection 7.11.3 defines the semantics of the sampling-record fields. Subsection 7.11.4 defines the manifest's validation and consistency requirements. Record structure and validation rules belong to later sections and are not introduced here.

#### 7.11.1 Sampling Manifest Purpose and Scope

**What the sampling manifest represents.**

The sampling manifest is a record of the temporal sampling decisions made during Ground Truth construction. It captures, for every frame that the sampling protocol selects, the fact that the frame was selected, the rule that selected it, and the dataset partition the frame belongs to. It does not contain bounding boxes, class labels, occlusion levels, or any per-object annotation content. It is a frame-level index of sampling, not an annotation file.

The manifest represents the sampling protocol's output exactly as applied: which frames were sampled, why they were sampled, and how they are partitioned. It is the authoritative statement of the sampling configuration for this dataset. Two independent implementations of the protocol that produce the same manifest have produced the same sampling configuration.

**Why the sampling manifest is required.**

The manifest is required for three reasons.

1. **Reproducibility.** Sampling is defined by deterministic rules (Sections 7.3, 7.4, 7.6), but a rule is not a record. Without the manifest, reproducing a dataset means re-deriving which frames were selected, and any deviation — a changed interval, a changed window size, a changed partition boundary — would be invisible. The manifest makes the sampling configuration explicit and checkable, so a dataset can be regenerated identically or its differences diagnosed.

2. **Auditability.** The sampled set is the input to every downstream metric. Detection mAP, tracking HOTA/IDF1, and counting error are all computed over sampled frames. If which frames were sampled is unknown, the metrics are uninterpretable. The manifest allows the dataset composition to be audited against the sampling rules: which frames came from baseline sampling, which from event boosting, and how they distribute across train, validation, and test.

3. **Asymmetry management.** Sampling affects annotation and evaluation but not production inference (Section 7.1). The manifest records this boundary explicitly by storing, per sample, the sampling mode and reason. Any downstream comparison between sampled Ground Truth and full-rate pipeline output can consult the manifest to determine which frames were sampled and which were not, so the comparison is made knowingly rather than by assumption.

**Relationship between source frames and sampled frames.**

The manifest records the relationship between the full source frame domain and the sampled subset. Every sampled frame in the manifest refers to a source frame by its original `frame_id` (Section 7.2). Sampling does not renumber frames, does not create synthetic frames, and does not shift timestamps. A sampled entry at `frame_id = f` in the manifest is the same source frame the production pipeline processes at `frame_id = f`.

The relationship is one of selection, not transformation. The source frame domain is the full set of frames in the video. The sampled set is a subset of that domain, chosen by the baseline grid and/or event boosting. Frames not present in the manifest are not sampled and are not annotated. The manifest therefore defines, by its contents, the exact boundary between the source domain and the sampled domain.

A source frame may appear in the manifest at most once. Sampling selects a frame; it does not select it multiple times. If both baseline sampling and event boosting would select the same frame, the frame is sampled once and the manifest records one entry for it.

**Relationship between sampling decisions and annotation.**

Sampling decisions determine which frames are annotated, but they do not determine what is recorded on those frames. The manifest records the decision to sample a frame; annotation records the objects visible in that frame. These are separate outputs.

A frame must be sampled before it is annotated. No annotation is recorded for a frame that is not in the manifest. However, being in the manifest is not sufficient for an annotation to exist: a sampled frame that is fully invisible for a given track contributes no bbox for that track (Section 7.9.4), and a sampled frame may be deferred or dropped during annotation execution, in which case it is no longer an annotation frame (Section 7.2). The manifest records the sampling decision; it does not guarantee that annotation work was completed on every sampled frame.

Sampling decisions also do not alter annotation rules. The bounding box policy (Section 3), occlusion policy (Section 4), identity policy (Section 5), and counting policy (Section 6) apply identically to every annotated frame regardless of why it was sampled. A baseline-sampled frame and an event-boosted frame are annotated by the same rules.

**Relationship between sampling manifest and evaluation reproducibility.**

Evaluation reproducibility requires that the same dataset, regenerated from the same protocol, produces the same metrics. The sampling manifest supports this in two ways.

First, the manifest records the deterministic inputs to sampling. The baseline rule is a pure function of `frame_id` and the interval (Section 7.3). The partition rule is a pure function of `frame_id` (Section 7.6). Event boosting is deterministic once the event set and window size are fixed (Section 7.4, 7.10.2). The manifest records which of these applied to each sample, so the sampling configuration can be reconstructed and regenerated exactly.

Second, the manifest anchors the evaluation dataset. Metrics are computed over the frames recorded in the manifest. Given the same manifest and the same Ground Truth annotations, the same metrics are produced. Reproducibility therefore depends on the manifest being preserved alongside the dataset it describes; without it, the dataset's sampling configuration is lost and its metrics cannot be regenerated or meaningfully compared.

The manifest does not itself guarantee reproducibility of annotation quality. It records which frames were sampled, not how well they were annotated. Inter-annotator agreement and annotation correctness are assessed separately (Sections 11, 15).

**Scope boundary: what the manifest does not do.**

The sampling manifest is a dataset-construction artifact. It does not modify the production inference pipeline. Specifically:

- The manifest does not change which frames the production pipeline processes. The pipeline (YOLOv8m + ByteTrack + Entity Association + ROI Counting) runs on every source frame at full frame rate (Section 7.1).
- The manifest does not reduce the frame rate at which the model runs, skip frames during inference, or alter tracker state between frames.
- The manifest does not change any output of the production pipeline. Sampling decisions affect what is annotated and what is evaluated, never what the pipeline computes.
- The manifest is not consumed by the production pipeline at runtime. It is a preparation-time record used to build the Ground Truth and evaluation datasets.

The manifest records the sampling configuration for Ground Truth construction and evaluation. It has no role in, and no effect on, production inference.

**Out of scope for this section.**

This section defines the purpose and scope of the sampling manifest only. It does not define the manifest's record structure, field set, or schema. It does not define how sampling reasons are enumerated, how samples are validated, or how the manifest is regenerated when a protocol parameter changes. Those topics belong to later sections and are not introduced here.

#### 7.11.2 Required Manifest Fields

The required sampling-manifest fields are defined here. They are the fields that must appear in every valid sampling manifest and in every valid sample record. The field set is derived from `sampling_manifest.schema.json`, which is the authoritative machine-readable definition. Where this subsection and the schema agree, the schema is authoritative for exact types, constraints, and enums; this subsection states the purpose of each field and its relationship to the protocol defined in Sections 7.1–7.10.

**Manifest-level required fields.**

These fields describe the video and the sampling configuration at the top level of the manifest.

| Field | Purpose | Defined in |
|-------|---------|------------|
| `video_id` | Identifies the source video (e.g., `3.mp4`). Binds the manifest to a specific video so that sampling configuration cannot be confused across videos. | Section 2.1 |
| `total_frames` | The total number of source frames in the video (621 for `3.mp4`). Defines the full frame domain against which sampling coverage is measured. | Section 2.2 |
| `fps` | The video frame rate (15 for `3.mp4`). Used to convert between frame counts and durations; the 30-frame short-gap threshold (Section 5.3) and the 5-frame baseline interval (Section 7.3) are both expressed in frames and interpreted through this rate. | Section 2.2 |
| `base_interval` | The baseline sampling interval in frames (5). Records the protocol parameter that governs baseline keyframe sampling (Section 7.3). Storing it in the manifest makes the baseline grid reconstructable without consulting this document. | Section 7.3 |

**Sample-level required fields.**

Every sample record in the manifest's `samples` array must contain the following fields. Each field records one property of a single sampled frame.

| Field | Purpose | Defined in |
|-------|---------|------------|
| `sample_id` | Unique sample identifier, format `S_XXXX` (zero-padded 4-digit). Provides a stable key for the sample independent of `frame_id`, so that a sample can be referenced by annotation tooling, audit scripts, and evaluation code even if frame indexing were to change. | Section 7.4 |
| `frame_id` | The 0-based index of the source frame (0–620). Binds the sample to a specific source frame. Sampling does not renumber frames (Section 7.2); this field records the frame's original identity. | Section 2.2, 7.2 |
| `timestamp` | The frame's timestamp in seconds, `frame_id / 15.0`. Derived from `frame_id` and `fps`; recorded rather than independently assigned so that time and frame identity cannot drift apart. | Section 2.2 |
| `split` | The dataset partition: `train`, `val`, or `test`. Assigned by the deterministic `split(frame_id)` rule (Section 7.6). Required on every sample because it is the primary enforcement mechanism for leakage prevention (Section 7.7): every frame must belong to exactly one partition. | Section 7.6, 7.7 |
| `sampling_reason` | The primary reason the frame was sampled. Enumerated values include `base_temporal` for baseline keyframe sampling (Section 7.3) and event-based values for event-boosted sampling (Section 7.4). Records why the frame is in the dataset, which is essential for auditing which sampling rules contributed to the sampled set. | Section 7.3, 7.4 |
| `traffic_density` | The traffic-density stratum for the frame: `low`, `medium`, or `high`. A protocol-defined label (Section 7.5) used to audit dataset balance and to report metrics per stratum. | Section 7.5 |
| `difficulty` | The overall frame difficulty stratum: `easy`, `moderate`, or `hard`. A protocol-defined label (Section 7.5) used for the same audit and stratification purposes. | Section 7.5 |

**Optional sample-level fields.**

The schema permits additional fields on each sample record that are not required. The following are defined in the schema and are recorded when applicable.

| Field | Purpose | Defined in |
|-------|---------|------------|
| `event_type` | The event type associated with an event-based `sampling_reason`: `none`, `roi_crossing`, `entry`, `exit`, `occlusion_start`, `occlusion_end`, `high_density`, or `ambiguous`. Records the specific event that motivated sampling, complementing the broader `sampling_reason`. Required only when the sampling reason is event-based; set to `none` otherwise. | Section 7.4, 7.10.2 |

**Consistency with Sections 7.1–7.10.**

The required fields are consistent with the protocol established in earlier sections:

- `frame_id` and `timestamp` preserve source-frame identity (Section 7.2), so a manifest entry refers to the same source frame the production pipeline processes.
- `sampling_reason` records the sampling mode established in Sections 7.3 and 7.4, including the precedence rule that event-based reasons take precedence over `base_temporal` when both apply (Section 7.4, 7.10.2).
- `split` records the partition assigned by the deterministic rule in Section 7.6, and the one-`sample_id`-per-`frame_id` property (Section 7.4) means each `frame_id` appears at most once in the manifest, enforcing one-frame-one-partition (Section 7.7).
- `traffic_density` and `difficulty` record the strata defined in Section 7.5, enabling the dataset balance audit and per-stratum metric reporting described there.
- `base_interval` records the baseline protocol parameter (Section 7.3), supporting reproducibility as described in Section 7.11.1.

**What this subsection does not define.**

This subsection defines the required fields and their purpose. It does not define the manifest's JSON record structure, the ordering of fields, or the validation rules applied to the manifest. It does not define how the manifest is generated, how samples are validated against the schema, or how the manifest is regenerated when a protocol parameter changes. Those topics belong to later sections and are not introduced here.

#### 7.11.3 Sampling Record Semantics

This subsection defines the meaning of the sampling-record fields and the relationships between them. It restates no sampling rule from Sections 7.1–7.10 and introduces no new rules; it specifies how the fields defined in 7.11.2 relate to one another and to the protocol decisions that produced them.

**`frame_id` and `timestamp` — identity and time.**

`frame_id` is the identity of the sample. It is the 0-based index of the source frame (0–620 for `3.mp4`), and it is not assigned by sampling. Sampling selects a frame; it does not rename it. A sample with `frame_id = f` refers to the same source frame the production pipeline processes at `frame_id = f` (Section 7.1). Two samples in the manifest may never share a `frame_id` (Section 7.4): each frame is sampled at most once, so `frame_id` is unique across the manifest's `samples` array.

`timestamp` is derived from `frame_id`, never independently assigned: `timestamp = frame_id / fps`. It is recorded so that time and frame identity cannot drift apart. Because `frame_id` is immutable, `timestamp` is immutable too; changing a frame's position in the video would change its `frame_id`, which would make it a different sample.

The relationship is one-way: `frame_id` determines `timestamp`. A consumer that needs the time of a sample reads `timestamp`; a consumer that needs the frame of a sample reads `frame_id`. Neither field may be used to re-identify a frame across videos, because `frame_id` is only meaningful within the video named by `video_id`.

**`sampling_reason` and `event_type` — why the frame was sampled.**

`sampling_reason` states the primary rule that selected the frame. It is the field that connects the sample to the sampling protocol. The value `base_temporal` identifies a frame selected by the baseline grid (Section 7.3); every event-based value identifies a frame selected by event boosting (Section 7.4).

When a frame is selected by both baseline sampling and event boosting, it is sampled once (Section 7.4). Its `sampling_reason` records the event-based reason, because event reasons take precedence over `base_temporal` for the primary reason field. The manifest supports exactly one primary `sampling_reason` per sample; the baseline reason is not recorded as a second reason.

`event_type` complements `sampling_reason` by naming the specific event that motivated the sampling. It is meaningful only when `sampling_reason` is event-based; it is set to `none` otherwise. The relationship is that `event_type` refines `sampling_reason`: a `sampling_reason` of `roi_crossing` pairs with an `event_type` of `roi_crossing`; a `sampling_reason` of `entry_event` or `exit_event` pairs with `event_type` of `entry` or `exit`. Not every `sampling_reason` maps to a distinct `event_type`, and the two fields are not interchangeable — `sampling_reason` records the sampling rule, `event_type` records the event.

The event categories themselves are defined in Sections 7.4 and 7.10.2 (E1–E7). This subsection does not redefine them; it states only that `event_type` is the manifest's record of which event motivated a sample.

**`split` — which dataset partition the sample belongs to.**

`split` records the dataset partition assigned to the sample: `train`, `val`, or `test`. It is assigned by the deterministic `split(frame_id)` rule (Section 7.6), so it is a function of `frame_id` alone. Given the same `frame_id`, the same `split` is always produced; no shuffling, seed, or balancing changes it.

Because `split` is a function of `frame_id`, and `frame_id` is unique across the manifest, every sample belongs to exactly one partition. This is the manifest-level enforcement of one-frame-one-partition (Section 7.7): no frame is duplicated across partitions, and no downstream step may reassign a frame's partition.

`split` is also the field that makes leakage prevention auditable. The evaluation scripts' obligation to never feed val/test frames into the training loop can be checked by confirming that no `frame_id` with `split = "test"` or `split = "val"` appears in any training input.

**`sample_id` — the sample's own identifier.**

`sample_id` (format `S_XXXX`) is the manifest's key for the sample, independent of `frame_id`. It exists so that a sample can be referenced by annotation tooling, audit scripts, and evaluation code without depending on frame indexing. It is assigned in the order samples are recorded and is unique across the manifest.

`sample_id` and `frame_id` refer to the same sampling decision from different directions: `frame_id` identifies the source frame, `sample_id` identifies the sampling record. A change to either identifies a different sample. They are not interchangeable — `frame_id` is meaningful across the whole video, `sample_id` only within the manifest.

**`traffic_density` and `difficulty` — stratum labels.**

These fields record the strata defined in Section 7.5. `traffic_density` (`low`, `medium`, `high`) labels the frame's object-density stratum; `difficulty` (`easy`, `moderate`, `hard`) labels the frame's overall difficulty stratum. Both are protocol-defined categories assigned to sampled frames, not measurements of the video.

The relationship is that these labels enable the dataset balance audit and per-stratum metric reporting described in Section 7.5. They are recorded per sample so that the manifest can be aggregated by stratum. They do not affect which frames are sampled and do not assign sampling weights (Section 7.5).

**Relationships between fields.**

A sampling record ties together a frame, a reason, a partition, and strata. The essential relationships are:

- `frame_id` → `timestamp`: derived, one-way, immutable.
- `frame_id` → `split`: deterministic, one-to-one.
- `sampling_reason` → `event_type`: `event_type` refines `sampling_reason` when the reason is event-based; `event_type` is `none` otherwise.
- `frame_id` → `sample_id`: one-to-one, each frame has at most one sample.
- `traffic_density` and `difficulty`: independent stratum labels on the same sample, used for audit and stratified reporting.

No field in a sampling record depends on annotation content. The record describes the sampling decision and the frame's protocol properties; it does not describe what objects were annotated on that frame.

**What this subsection does not define.**

This subsection defines field semantics and relationships. It does not define the manifest's JSON record structure, field ordering, or validation rules. It does not define how the manifest is generated, how samples are validated against the schema, or how the manifest is regenerated when a protocol parameter changes. It does not introduce new sampling reasons, event categories, or strata. Those topics belong to later sections and are not introduced here.

#### 7.11.4 Manifest Validation and Consistency

This subsection defines how the sampling manifest must remain consistent with the protocol decisions in Sections 7.3–7.10, with the schema, and with reproducible dataset construction. It states what consistency means for the manifest and what must hold for the manifest to be valid. It introduces no new sampling rules; every requirement below is a consequence of a rule already established.

**Schema-level validation.**

The manifest must conform to `sampling_manifest.schema.json`, which is the authoritative machine-readable definition. Schema-level validation requires:

- The manifest object contains the required top-level fields (`video_id`, `total_frames`, `fps`, `samples`), and no additional top-level properties.
- Every sample record contains the required fields (`sample_id`, `frame_id`, `timestamp`, `split`, `sampling_reason`, `traffic_density`, `difficulty`), and no additional properties.
- `sample_id` matches the pattern `S_XXXX` (zero-padded 4-digit) and is unique across the `samples` array.
- `frame_id` is an integer in the range 0–620 for `3.mp4`.
- `timestamp` is a number in the range 0–41.4.
- `split` is one of `train`, `val`, or `test`.
- `sampling_reason` is one of the enumerated values: `base_temporal`, `roi_crossing`, `entry_event`, `exit_event`, `post_occlusion_appearance`, `pre_occlusion_disappearance`, `high_density`, `severe_occlusion`, `ambiguous_identity`, `class_ambiguity`.
- `event_type`, when present, is one of: `none`, `roi_crossing`, `entry`, `exit`, `occlusion_start`, `occlusion_end`, `high_density`, `ambiguous`.
- `traffic_density` is one of `low`, `medium`, `high`.
- `difficulty` is one of `easy`, `moderate`, `hard`.

Schema validation is necessary but not sufficient. A manifest may pass schema validation and still violate the protocol; the consistency requirements below close that gap.

**Consistency with baseline sampling (Section 7.3).**

Every sample whose `sampling_reason` is `base_temporal` must satisfy the baseline rule: its `frame_id` must be a multiple of the baseline interval. The interval is recorded in the manifest as `base_interval` (5 for `3.mp4`). A sample with `sampling_reason = "base_temporal"` and `frame_id mod base_interval ≠ 0` is inconsistent with Section 7.3.

The manifest must not contain a `base_temporal` sample at a `frame_id` that the baseline rule would not select. Conversely, a frame that the baseline rule selects is not required to appear with `sampling_reason = "base_temporal"`: if event boosting also selects it, it appears with the event-based reason instead (Section 7.4). The consistency requirement is directional — a `base_temporal` sample must be baseline-eligible, not that every baseline-eligible frame must be a `base_temporal` sample.

**Consistency with event-boosted sampling (Section 7.4, 7.10.2).**

Every sample whose `sampling_reason` is event-based must correspond to an event established in Sections 7.4 and 7.10.2. The event-based reasons are: `roi_crossing`, `entry_event`, `exit_event`, `post_occlusion_appearance`, `pre_occlusion_disappearance`, `severe_occlusion`, `ambiguous_identity`, `class_ambiguity`, `high_density`. A sample with an event-based reason must have an `event_type` that is consistent with that reason, and the event must be one the protocol recognizes.

When a frame is selected by both baseline sampling and event boosting, the manifest records it once with the event-based `sampling_reason`, because event reasons take precedence over `base_temporal` (Section 7.4). The manifest must not contain two records for the same `frame_id`; this is enforced by the uniqueness of `sample_id` and `frame_id` at the schema level and is restated here as a protocol requirement.

**Consistency with the train/val/test split (Section 7.6).**

Every sample's `split` must equal the result of the deterministic `split(frame_id)` rule:

- `frame_id` in [0, 249] → `train`
- `frame_id` in [250, 374] → `val`
- `frame_id` in [375, 499] → `test`

No sample may have a `split` that disagrees with its `frame_id`. Because `split` is a pure function of `frame_id`, and `frame_id` is unique across the manifest, every frame belongs to exactly one partition. This is the manifest-level enforcement of one-frame-one-partition (Section 7.7): no frame may appear in more than one partition, and no sample may be reassigned to a different partition.

Frames 500–620 are unassigned (Section 7.6.1) and must not appear in the manifest with any `split` value. Their absence from the manifest is itself a consistency requirement: the manifest's sampled set must be a subset of the assigned frame domain 0–499.

**Consistency with leakage prevention (Section 7.7).**

The manifest must support the leakage-prevention guarantees. Specifically:

- Each `frame_id` appears at most once, so no frame is duplicated across partitions.
- The `split` field on every sample allows the evaluation scripts to verify that no val/test frame was used in training.
- Event-boosted windows are clipped at partition boundaries (Section 7.7): a sample selected by event boosting near a boundary must lie within the event's own partition. The manifest's `frame_id` and `split` together allow this to be checked, because any sample whose `frame_id` falls outside its event's partition would indicate a window that was not clipped.

**Consistency with reproducible dataset construction (Section 7.11.1).**

Reproducibility requires that the manifest, together with the Ground Truth annotations it describes, can regenerate the same evaluation dataset and the same metrics. For this to hold:

- The manifest must record the deterministic inputs to sampling: `base_interval` for the baseline grid, `sampling_reason` for the rule that selected each sample, and `split` for the partition assignment. Given these, the sampling configuration is reconstructable.
- The manifest must be preserved alongside the dataset it describes. Without it, the sampling configuration is lost and the metrics cannot be regenerated or meaningfully compared.
- If a protocol parameter changes (for example, `base_interval` or the event-boosted window size), the manifest must be regenerated so that it reflects the configuration actually used. A manifest that records a stale parameter is inconsistent with the dataset it describes, even if it passes schema validation.

The manifest does not guarantee annotation quality. It records which frames were sampled, not how well they were annotated; inter-annotator agreement and annotation correctness are assessed separately (Sections 11, 15).

**What this subsection does not define.**

This subsection defines validation and consistency requirements. It does not define the manifest's JSON record structure, field ordering, or the exact validation scripts that enforce these checks. It does not define how the manifest is generated, how samples are validated against the schema in practice, or how the manifest is regenerated when a protocol parameter changes beyond the requirement that it be regenerated. It does not introduce new sampling reasons, event categories, strata, or thresholds. Those topics belong to later sections and are not introduced here.

- **Section 7.6–7.8** — Temporal train/val/test split, leakage prevention, ROI-crossing events at boundaries (this document)
- **Section 7.9: Data Schema** (this document)
- **Section 7.10–7.12** — Short tracking gaps and occlusion, frames near important events, sampling manifest requirements (7.11.1–7.11.4 complete), reproducibility requirements (this document)
- **Section 8: Annotation Tool Decision**
- **Section 9: Pilot Dataset Definition**
- **Section 10: Quality-Control Checklist**
- **Section 11: Inter-Annotator Agreement Procedure**
- **Section 12: Known Ambiguities**
- **Section 13: Acceptance Criteria**

---

## 7.12 Reproducibility Requirements

This section defines the requirements for reproducing the annotation and evaluation dataset. It specifies what must be recorded, preserved, and regenerated so that the dataset can be reconstructed identically and its metrics recomputed. It does not redefine any sampling rule from Sections 7.1–7.11; every requirement below is a consequence of a rule already established.

### 7.12.1 Deterministic Sampling Inputs

Reproducibility depends on the sampling configuration being a pure function of recorded inputs. Every input that determines which frames are sampled must be stored in the manifest or otherwise preserved alongside the dataset.

**Deterministic inputs:**

| Input | Where recorded | Determinism property |
|-------|----------------|---------------------|
| `video_id` | Manifest top level | Identifies the source video; sampling is meaningless without it. |
| `total_frames` | Manifest top level | Defines the full frame domain 0–620 for `3.mp4`. |
| `fps` | Manifest top level | Converts frame counts to durations; the 5-frame interval and 30-frame threshold are interpreted through it. |
| `base_interval` | Manifest top level | The baseline sampling interval (5). A pure function of `frame_id`: a frame is baseline-sampled iff `frame_id mod base_interval == 0` (Section 7.3). |
| `split(frame_id)` boundaries | Protocol (Section 7.6) | Frame ranges 0–249 (train), 250–374 (val), 375–499 (test). A pure function of `frame_id`. |
| Event set and window size | Derived from Ground Truth; `sampling_reason`/`event_type` recorded per sample | Event-boosted sampling is deterministic once the event set and window size are fixed (Section 7.4, 7.10.2). The window size is a protocol parameter. |

**What is not an input.** Annotation order, annotator identity, runtime state, and tool-internal randomness are not sampling inputs and must not affect the sampled set. Baseline sampling and partition assignment are independent of annotation order by definition (Sections 7.3, 7.6). Event boosting is independent of annotation order because event priority is a fixed deterministic order (Section 7.10.2).

**No randomness.** The sampling protocol uses no random seed, no shuffling, and no stratified balancing across partitions (Section 7.6). Given the same recorded inputs, the same sampled set is produced every time.

### 7.12.2 Protocol and Version Recording

The dataset must be associated with the exact protocol version that produced it, so that a regenerated dataset can be compared against the original and any difference attributed to a protocol change rather than to drift.

**Required recording:**

- **Protocol version.** The version of this document (`PHASE_1_3B_ANNOTATION_PROTOCOL.md`) that governed the dataset construction must be recorded. The version history (Section 17) tracks changes to sampling rules; a dataset must reference the version under which it was built.
- **Protocol parameters.** Every protocol parameter that affects sampling must be recorded with its value at the time of construction. These include `base_interval`, the event-boosted window size, the density stratum thresholds, the difficulty stratum thresholds, and the partition boundaries. Protocol parameters are distinguished from empirically observed values (Section 7.5): a parameter is a chosen value, not a measurement.
- **Schema version.** The version of `sampling_manifest.schema.json` that validated the manifest must be recorded, because schema changes can change what a manifest is required to contain.

**Change discipline.** When a protocol parameter or the protocol version changes, the dataset is considered a new construction. The manifest and Ground Truth must be regenerated to reflect the configuration actually used; a manifest that records a stale parameter is inconsistent with the dataset it describes (Section 7.11.4).

### 7.12.3 Manifest Preservation

The sampling manifest is the record of the sampling configuration and must be preserved with the dataset it describes.

**Preservation requirements:**

- The manifest must be stored alongside the Ground Truth annotations and the evaluation dataset, in a location that keeps them associated. Without the manifest, the sampling configuration is lost and the metrics cannot be regenerated or meaningfully compared (Section 7.11.1).
- The manifest must be preserved in machine-readable form. It is the authoritative statement of which frames were sampled, why, and into which partition.
- The manifest must not be edited after the dataset is finalized except through a full regeneration. Post-hoc edits to the manifest would break its consistency with the Ground Truth it describes.

**What the manifest does not preserve.** The manifest records which frames were sampled, not how well they were annotated. Annotation quality — inter-annotator agreement, annotation correctness — is assessed separately and is not recorded in the manifest (Sections 11, 15).

### 7.12.4 Dataset Regeneration Conditions

A dataset is reproducible if it can be regenerated identically from its recorded inputs. This section states when regeneration must occur and what must hold for the regenerated dataset to be considered identical.

**Regeneration is required when:**

- **The source video changes.** Sampling is a function of the video's frame domain (`video_id`, `total_frames`, `fps`). A different video produces a different dataset even under the same protocol.
- **A protocol parameter changes.** Any change to `base_interval`, the event-boosted window size, the partition boundaries, or the stratum thresholds changes which frames are sampled or how they are labeled.
- **The protocol version changes.** A change to a sampling rule in this document changes the sampling configuration.
- **The schema version changes.** A schema change may change what the manifest is required to contain.

**Regeneration is not required when:**

- **Only annotation content changes.** Re-annotation of an already-sampled frame (correcting a bounding box, revising an occlusion level) changes the Ground Truth annotations but not the sampling configuration. The manifest is unchanged; only the annotation files are updated.
- **Only evaluation code changes.** Changes to metric computation or evaluation scripts do not affect which frames were sampled and do not require regeneration.

**Identity condition.** A regenerated dataset is identical to the original iff the manifest is identical — same `sample_id`s, same `frame_id`s, same `sampling_reason`s, same `split` values, same strata. If the manifest is identical, the sampled set is identical, and the same Ground Truth annotations applied to the same frames produce the same metrics. Annotation content is independent of this condition: identical manifests with different annotation content produce different metrics, which is expected and correct.

### 7.12.5 Reproducibility Verification

Reproducibility must be verifiable, not assumed. This subsection states what must be checked and how.

**Verification checks:**

- **Manifest regeneration.** Given the recorded inputs (`video_id`, `total_frames`, `fps`, `base_interval`, partition boundaries, event set, window size), regenerate the manifest and compare it against the preserved manifest. The two must be identical.
- **Schema conformance.** The preserved manifest must pass validation against the recorded schema version (Section 7.11.4).
- **Protocol conformance.** The manifest must satisfy the consistency requirements in Section 7.11.4: `base_temporal` samples must be baseline-eligible; event-based samples must correspond to recognized events; `split` must equal `split(frame_id)`; frames 500–620 must not appear.
- **Annotation coverage.** Every sampled frame recorded in the manifest must have a corresponding annotation, and no annotation may exist for a frame not in the manifest. This links the manifest to the Ground Truth files.
- **Metric recomputation.** Given the preserved manifest and Ground Truth, the evaluation metrics must be recomputable. This is the ultimate test of reproducibility: the same inputs produce the same numbers.

**Verification scope.** These checks verify the reproducibility of the dataset construction and evaluation. They do not verify annotation quality, model performance, or the production inference pipeline. Those are assessed separately (Sections 11, 15).

**What this section does not define.**

This section defines reproducibility requirements. It does not define the manifest's JSON record structure, the exact regeneration procedure, or the validation scripts that enforce these checks. It does not introduce new sampling reasons, event categories, strata, or thresholds. It does not modify the sampling manifest schema, the tracking GT schema, or the counting GT schema.

- **Section 7.6–7.8** — Temporal train/val/test split, leakage prevention, ROI-crossing events at boundaries (this document)
- **Section 7.9: Data Schema** (this document)
- **Section 7.10–7.11** — Short tracking gaps and occlusion, frames near important events, sampling manifest requirements (this document)
- **Section 8: Annotation Tool Decision**
- **Section 9: Pilot Dataset Definition**
- **Section 10: Quality-Control Checklist**
- **Section 11: Inter-Annotator Agreement Procedure**
- **Section 12: Known Ambiguities**
- **Section 13: Acceptance Criteria**

### 7.13 Decision 2 — Low-Change Intervals Are Not a Sampling-Exclusion Criterion

**Decision 2 (human-approved, final): Option A — keep all sampled frames.**

A temporal-difference audit of `3.mp4` (Task 10.2 / 10.2B) identified five candidate low-change intervals — contiguous frame ranges with measurably low pixel-level change between consecutive frames:

| Interval (frame_id) | Approx. time | Partition |
|---------------------|--------------|-----------|
| 342–361 | ~22.8–24.1s | validation |
| 366–388 | ~24.4–25.9s | validation / test boundary |
| 431–446 | ~28.7–29.7s | test |
| 447–477 | ~29.8–31.8s | test |
| 510–525 | ~34.0–35.0s | unassigned (500–620) |

**AUDIT EVIDENCE — NOT A SAMPLING EXCLUSION RULE.**

These intervals are recorded as methodological audit evidence only. They are not machine-readable protocol structures, are not added to any schema, and do not enter the Sampling Manifest.

**Ruling.**

1. All frames selected by the authoritative baseline sampling rule (`frame_id mod 5 == 0`, Section 7.3) remain sampled.
2. Pixel-level low-change similarity is **not** a criterion for removing sampled frames.
3. Temporal redundancy is **not** an automatic criterion for removing sampled frames.
4. Evaluation sampling is not reduced, thinned, or altered because of low-change intervals.
5. No source video frames are deleted or physically removed by this decision or by the audit.
6. The evaluation partitions remain train 0–249, validation 250–374, test 375–499 (Section 7.6); frames 500–620 remain unassigned (Section 7.6.1).

**Evidentiary status.** Pixel similarity does not prove semantic redundancy: visually similar consecutive frames may still contain stopped vehicles and stable traffic states whose informativeness cannot be ruled out. At the time of the audit, no trusted Detection Ground Truth existed, so whether detector/tracker outputs would change meaningfully across these intervals could not be determined. The low-change evidence is therefore **insufficient to justify sampling exclusion**. This ruling does not assert that low-change frames are proven semantically important; it records only that the available evidence did not meet the threshold for introducing an exclusion rule.

The audit also recorded a distributional fact relevant to any future reconsideration: none of the five candidate intervals lies within the training partition, and four of five overlap validation or test. Any future exclusion rule based on low-change detection would act disproportionately on evaluation partitions and must account for that asymmetry explicitly.

**Scope boundary.** This decision changes nothing else in this protocol: it does not alter the baseline interval, event-boosted sampling, stratification, split boundaries, frame_id bounds, timestamp bounds, schemas, manifest generation, or validation rules. It defines no traffic-density policy, difficulty policy, or runtime traffic-control behavior. Revisiting low-change sampling would require a new human-approved decision amending this section.

---

## 8 Data Schema

This section describes the ground-truth schema layer: what the schemas represent, how they relate to one another, and how they relate to the protocol defined in Sections 1–7. It defines the architecture of the schema layer only. Detailed field definitions belong to later subsections and are not introduced here.

### 8.1 Data Schema Purpose and Architecture

**Purpose of the ground-truth schema layer.**

The ground-truth schema layer provides machine-readable, validated definitions of the Ground Truth data produced by the annotation protocol. Each schema constrains a distinct output of the annotation workflow so that the data can be checked, consumed, and compared deterministically. The schemas do not define how annotations are produced; they define what valid annotation output looks like.

The layer has four schemas, each corresponding to one output of the protocol:

| Schema | File | Output it constrains | Defined in |
|--------|------|---------------------|------------|
| Detection Ground Truth | `detection_ground_truth.schema.json` | Per-frame object annotations (JSONL) | Section 3, 4 |
| Tracking Ground Truth | `tracking_ground_truth.schema.json` | Video-wide object tracks with persistent identity | Section 5 |
| Counting Ground Truth | `counting_ground_truth.schema.json` | ROI-crossing counting events | Section 6 |
| Sampling Manifest | `sampling_manifest.schema.json` | Which frames were sampled and why | Section 7.11 |

**Relationship between the schemas.**

The four schemas form a derivation chain. Tracking Ground Truth is the central representation: it records per-object identity and per-frame geometry across the whole video. Detection Ground Truth is the per-frame view of the same annotations, flattened so that each line describes one frame's objects without identity. Counting Ground Truth is derived from Tracking Ground Truth by testing each track's bottom-center trajectory against the ROI polygon. The Sampling Manifest is orthogonal to the other three: it records which frames were sampled, not what was annotated on them.

The relationships are:

- **Detection → Tracking.** Every detection annotation corresponds to a frame observation in some tracking GT track. Detection GT is the per-frame projection of tracking GT; it carries the same `bbox`, `class`, `visibility`, `occlusion`, and `truncated` values but no identity. A detection annotation without a corresponding track observation is invalid.
- **Tracking → Counting.** Every counting event references a `global_id` that must exist in tracking GT. Counting events are derived algorithmically from tracking GT geometry (Section 6.6); they are not annotated independently. The `frame_id`, `bbox_at_crossing`, and `roi_point` in a counting event come from the track observation at the crossing frame.
- **Sampling Manifest → all three.** The sampling manifest identifies which frames carry annotations. Detection GT exists only for sampled frames; tracking GT observations exist only at sampled frames (with gaps at unsampled frames); counting events exist only at sampled crossing frames. The manifest is the index of the frame domain that the other three schemas cover.

**Role of `frame_id`.**

`frame_id` is the 0-based index of a source frame (0–620 for `3.mp4`) and is the primary temporal key across all four schemas. It appears in detection GT as the record key, in tracking GT as the key of each per-frame observation, in counting GT as the frame where a crossing occurred, and in the sampling manifest as the identity of each sampled frame.

`frame_id` is not assigned by the annotation workflow. It is a property of the source video, and sampling does not renumber it (Section 7.2). A `frame_id` refers to the same source frame in every schema and in the production pipeline. Because `frame_id` is shared across schemas, joins between detection, tracking, counting, and sampling records are possible on a common key.

`timestamp` is derived from `frame_id` (`frame_id / fps`) and is recorded alongside it in every schema so that time and frame identity cannot drift apart.

**Role of `global_id`.**

`global_id` is the persistent identity of a physical object, assigned by the annotator and immutable across the entire video. It is the primary key of tracking GT: each track is one `global_id`, and every per-frame observation in that track belongs to it. `global_id` is the link that connects a detection annotation to its track and a counting event to the object that crossed the ROI.

The `global_id` format is `GT_XXX` (zero-padded 3-digit, e.g., `GT_001`). It is assigned sequentially in order of first appearance and is scoped to the video named by `video_id`. A `global_id` track spans the full frame domain: it carries observations at sampled frames and gaps at unsampled or fully invisible frames, and its identity is unaffected by which frames were sampled (Section 5.3, Scenario 12).

**Distinction between `global_id` and ByteTrack `track_id`.**

`global_id` and ByteTrack `track_id` are separate identity spaces and must never be conflated.

| Property | `global_id` (Ground Truth) | ByteTrack `track_id` (pipeline output) |
|----------|----------------------------|----------------------------------------|
| Source | Human-annotated | Algorithmic tracker output |
| Scope | Entire video (0–620) | Per tracker session; resets on re-initialization |
| Stability | Immutable once assigned | Can change due to ID switches and fragmentation |
| Format | `GT_XXX` | Integer |
| Role | Evaluation ground truth | System under test output |

The schemas enforce this distinction structurally: `global_id` appears in tracking GT and counting GT; ByteTrack `track_id` appears in no ground-truth schema. Evaluation matches predictions to ground truth via `global_id` (spatiotemporal matching), never by mapping `track_id` to `global_id` (Section 5.1, 6.8).

**How the schemas support trajectory and future traffic-graph evaluation.**

The schemas preserve the minimum information required for trajectory analysis and for future multi-zone traffic graphs, without over-engineering for current needs.

- **Trajectory.** Tracking GT records per-frame `center` (derived from `bbox`) together with `frame_id` and `timestamp`, so an object's path through the frame is reconstructable. Counting GT records `roi_point` and `bbox_at_crossing` at each crossing, anchoring the trajectory to the ROI boundary.
- **Zone transition.** Tracking GT's `roi_crossings` array records each crossing with `frame_id`, `direction`, and `roi_point`. Counting GT records the same information at the event level. Together they support entry/exit event analysis for the current single-zone ROI.
- **Traffic state.** Counting GT aggregates events into `total_counts` by class, and each event carries `timestamp` and `class`, enabling flow rate and occupancy analysis per class.
- **Future traffic graph.** Tracking GT's `roi_crossings` array is structured to hold multiple zone crossings per track. Extending to a multi-zone ROI requires adding polygons to metadata; no schema change is needed, because each crossing records its own `frame_id`, `direction`, and `roi_point` (Section 6.9).

**Boundary between annotation schemas and production pipeline outputs.**

The ground-truth schemas define annotation data only. They are inputs to evaluation, not outputs of the production pipeline, and the two must not be confused.

- The production inference pipeline (YOLOv8m + ByteTrack + Entity Association + ROI Counting) produces its own outputs: per-frame detections, tracker `track_id`s, and predicted counting events. These outputs are not described by any ground-truth schema.
- The ground-truth schemas describe what the annotator produced: `global_id`s, per-frame bboxes, occlusion levels, and derived counting events. These are fixed before any model runs and do not change when the pipeline is re-run.
- Evaluation compares pipeline outputs to ground truth. The comparison uses `global_id` for tracking and counting, and per-frame class/bbox for detection. The schemas guarantee that the ground-truth side of this comparison is stable and reproducible, while the pipeline side is the system under test.
- The sampling manifest records which frames the ground-truth schemas cover. The production pipeline processes every source frame at full rate (Section 7.1); the manifest records the asymmetry, it does not create it.

**What this subsection does not define.**

This subsection defines the architecture and purpose of the schema layer. It does not define individual fields, required-field lists, enum values, or validation rules for any schema; those belong to later subsections and are not introduced here. It does not modify any JSON schema file.

- **Section 7.6–7.8** — Temporal train/val/test split, leakage prevention, ROI-crossing events at boundaries (this document)
- **Section 7.9: Data Schema** (this document)
- **Section 7.10–7.12** — Short tracking gaps and occlusion, frames near important events, sampling manifest requirements, reproducibility requirements (this document)
- **Section 8.1: Data Schema** (this document)

### 8.2 Detection Ground Truth Schema

This subsection defines the Detection Ground Truth schema: what it represents, how it relates to the annotation policies in Sections 3–5, and how it relates to Tracking Ground Truth and to model output. It defines the schema's purpose and scope only. Detailed field definitions belong to later subsections and are not introduced here.

#### 8.2.1 Purpose and Scope

**Purpose of Detection Ground Truth.**

Detection Ground Truth is the per-frame record of object annotations produced by the annotation protocol. It captures, for every sampled frame, the objects visible in that frame and their observable properties. Its purpose is to provide the ground-truth input for evaluating the detection component of the pipeline: it is the reference against which the model's per-frame detections are compared to compute detection metrics such as mAP.

The schema is the machine-readable definition of this output. It constrains what a valid detection annotation looks like so that the data can be validated, consumed, and compared deterministically. It does not define how annotations are produced; it defines what valid annotation output looks like.

**Relationship to Section 3 — Bounding Box Policy.**

Detection Ground Truth is the output that Section 3 governs. Every bounding box in a detection annotation is drawn according to the Bounding Box Policy: the tightest axis-aligned rectangle enclosing all visible pixels of the object, with no extrapolation of occluded or hidden portions (Section 3.1). The per-object box rules in Section 3.2–3.7 — handling of occluded regions, truncation at frame boundaries, overlapping vehicles, parked vehicles, class-specific size guidelines, and edge cases such as reflections, shadows, and rider-vehicle coupling — apply directly to each box recorded in Detection GT.

The schema records the box as `[x1, y1, x2, y2]` in the 1020×500 coordinate space, consistent with the coordinate system defined in Section 2.1. The minimum box size (10×10 pixels) from Section 2.6 is a property of what may be recorded. Detection GT records one box per object; it never merges two objects into one box and never splits one object into two (Section 3.4).

**Relationship to Section 4 — Occlusion Policy.**

Every detection annotation carries the occlusion properties defined by the Occlusion Policy. Each annotation records a `visibility` value (continuous 0.0–1.0, the estimated visible fraction) and an `occlusion` level (0–3: none, partial, heavy, severe), assigned per the measurement protocol in Section 4.1 and 4.4. The `difficult` flag is set per the rules in Section 4.6, distinguishing genuine occlusion from ambiguity, motion blur, and weather conditions.

The occlusion policy's central rule — that `visibility = 0` means no bbox annotation — is enforced structurally: a fully invisible object contributes no detection annotation in that frame. Detection GT records only frames where an object has a visible extent to enclose. The occlusion level and visibility recorded on an annotation are the values for that frame only; they are not forced consistent across frames (Section 4.5).

**Relationship to Section 5 — global_id Policy.**

Detection Ground Truth does not carry `global_id`. It is a per-frame, per-object record, and identity is not a property of a single frame. The `global_id` Policy in Section 5 governs how objects are identified across frames; that identity lives in Tracking Ground Truth, not in Detection GT.

The relationship is that every detection annotation corresponds to an observation in some tracking GT track. A detection annotation is the frame-level projection of a track observation: it carries the same `class`, `bbox`, `visibility`, `occlusion`, and `truncated` values, but not the identity that links those observations into a track. Detection GT is therefore downstream of Tracking GT in the derivation chain, not an independent annotation (Section 8.1).

**Relationship to Tracking Ground Truth.**

Detection Ground Truth and Tracking Ground Truth describe the same annotations from different viewpoints. Tracking GT is organized by object: one record per `global_id`, with a `frames` array of per-frame observations spanning the object's lifetime. Detection GT is organized by frame: one record per sampled frame, with an `annotations` array of the objects visible in that frame.

The content relationship is one-to-one at the observation level. Every element of a track's `frames` array has a corresponding detection annotation in the Detection GT record for that `frame_id`, and every detection annotation corresponds to exactly one track observation. The fields they share — `class`, `bbox`, `visibility`, `occlusion`, `truncated` — must agree between the two schemas for the same object at the same frame. Detection GT omits `global_id` and `center`; Tracking GT adds `global_id` and derives `center` from `bbox`.

This relationship means Detection GT is not annotated independently. It is the per-frame view of Tracking GT, and any inconsistency between the two is an annotation error, not a design choice.

**Detection annotation as frame-level object observations.**

A detection annotation is a statement about one object in one frame. It records the object's class, its bounding box, and the observable conditions under which it was seen in that frame. It is frame-level because detection evaluation compares the model's per-frame predictions to ground truth per frame; it does not require identity across frames, which is the tracking evaluation's concern.

Each detection record covers one frame and contains an array of annotations, one per object visible in that frame. Detection GT exists only for sampled frames (Section 7.2): a frame that is not sampled has no Detection GT record. Within a sampled frame, every object with a visible extent is annotated, including objects outside the ROI (Section 2.5), because detection evaluation covers the whole frame, not just the counting region.

**Distinction between detection GT and model detection output.**

Detection Ground Truth and the model's detection output are fundamentally different and must not be conflated.

| Property | Detection Ground Truth | Model detection output |
|----------|------------------------|------------------------|
| Source | Human annotation per the protocol in Sections 2–5 | YOLOv8m inference on the source frame |
| Stability | Fixed once produced; unchanged by re-running the pipeline | Changes with model weights, inference settings, and runtime state |
| Identity | No `global_id`; per-object, per-frame | May carry a tracker-assigned `track_id` |
| Coverage | Sampled frames only (Section 7.2) | Every source frame at full rate (Section 7.1) |
| Role | Evaluation reference (ground truth) | System under test output |

Detection GT is the reference. The model's detections are the predictions. Evaluation compares the two per frame — matching predicted boxes to ground-truth boxes by class and spatial overlap — and the result is a detection metric. The ground-truth side of this comparison is stable and reproducible; the prediction side is what is being measured.

The distinction is enforced structurally: no ground-truth schema contains model output, and no model output is validated against a ground-truth schema. The schemas define annotation data only (Section 8.1).

**What this subsection does not define.**

This subsection defines the purpose and scope of Detection Ground Truth. It does not define individual fields, required-field lists, enum values, or validation rules for the schema; those belong to later subsections and are not introduced here. It does not modify any JSON schema file.

- **Section 7.6–7.8** — Temporal train/val/test split, leakage prevention, ROI-crossing events at boundaries (this document)
- **Section 7.9: Data Schema** (this document)
- **Section 7.10–7.12** — Short tracking gaps and occlusion, frames near important events, sampling manifest requirements, reproducibility requirements (this document)
- **Section 8.1: Data Schema** (this document)
- **Section 8.2: Detection Ground Truth Schema** (this document)

#### 8.2.2 Detection Ground Truth Field Semantics

This subsection documents the semantic meaning and source policy of the Detection Ground Truth fields. The JSON schema is authoritative for field names and types; Sections 3–5 are authoritative for annotation semantics. No new fields are introduced.

**`frame_id`**

Purpose: identifies the source frame this detection record describes. It is the 0-based index of the frame in the video (0–620 for `3.mp4`) and is the record-level key of Detection GT: each record covers exactly one frame.

Governing policy: Section 2.2 (Frame Referencing) and Section 7.2 (Sampling Units). `frame_id` is a property of the source video, not of the annotation workflow. Sampling does not renumber it, so a `frame_id` refers to the same source frame in every schema and in the production pipeline (Section 7.2). Detection GT records exist only for sampled frames; an unsampled frame has no Detection GT record.

Schema meaning: integer, minimum 0, maximum 620.

**`timestamp`**

Purpose: records the time of the frame in seconds, derived as `frame_id / fps`. It is recorded alongside `frame_id` so that time and frame identity cannot drift apart.

Governing policy: Section 2.2. `timestamp` is derived, never independently assigned. It is consistent across all four schemas because it is a function of `frame_id` and `fps`.

Schema meaning: number, minimum 0, maximum 41.4.

**`object_id`**

Purpose: not present in the Detection Ground Truth schema. Detection annotations are per-object but not identified across frames; identity is not a property of a single detection.

Status: this field does not exist in `detection_ground_truth.schema.json`, and it is not introduced here. Object identity across frames is carried by Tracking Ground Truth's `global_id` (Section 5, 8.1). A detection annotation corresponds to one track observation, but the link is made through Tracking GT, not through a field on the detection record.

**`class`**

Purpose: states the object's class for the frame. It is the label used to compare the annotation against the model's predicted class when computing detection metrics.

Governing policy: Section 2.3 (Class Labels) and Section 2.4 (Ambiguous / Unclassifiable Objects). The value must be one of the five countable classes: `car`, `motorcycle`, `bus`, `truck`, `person`. If an object cannot be confidently assigned to one class, the annotation uses the most conservative class (`car`) and sets `difficult: true` with a note; no new classes are created (Section 2.4). Class is recorded per detection and may differ from the class of the same object's track only where the immutability rule in Section 5.6 applies.

Schema meaning: string, enum of the five countable classes.

**`bbox`**

Purpose: encloses the visible extent of the object in the frame. It is the geometry compared against the model's predicted boxes when computing detection metrics.

Governing policy: Section 3 (Bounding Box Policy). The box is the tightest axis-aligned rectangle enclosing all visible pixels of the object (Section 3.1). It does not include occluded or hidden portions and is not extrapolated from class knowledge. Sections 3.2–3.7 govern occluded regions, truncation at frame boundaries, overlapping vehicles, parked vehicles, class-specific size guidelines, and edge cases such as reflections, shadows, and rider-vehicle coupling. The minimum box size is 10×10 pixels (Section 2.6). One box per object; two objects are never merged and one object is never split (Section 3.4).

Schema meaning: array of four integers `[x1, y1, x2, y2]` in the 1020×500 coordinate space, each in range 0–1019.

**`visibility`**

Purpose: records the estimated visible fraction of the object in the frame, on a continuous 0.0–1.0 scale. It provides finer granularity than the categorical `occlusion` level and is used in the deterministic `crossing_confidence` rule for counting events (Section 6.3.1).

Governing policy: Section 4.1 (Occlusion Levels) and Section 4.4 (Measurement Protocol). The annotator estimates the visible fraction by eye by reconstructing the object's full extent from visible cues. `visibility = 0` means the object is fully hidden and no detection annotation is created for that frame; a value in `(0.0, 0.1]` indicates severe occlusion. The value is recorded per frame and is not forced consistent across frames (Section 4.5).

Schema meaning: number, minimum 0.0, maximum 1.0.

**`occlusion`**

Purpose: records the categorical occlusion level of the object in the frame, on a 4-level scale. It is used for stratified reporting of detection performance under occlusion.

Governing policy: Section 4.1 and Section 4.3. Levels are: `0` none (fully visible), `1` partial (1–50% obscured), `2` heavy (>50–90% obscured), `3` severe (>90% obscured). The level reflects how much of the object itself is hidden, assessed independently for each object even when objects occlude one another. `occlusion` is not set for truncation at the frame edge — that is recorded by `truncated` (Section 4.3). The value is recorded per frame and is not forced consistent across frames (Section 4.5).

Schema meaning: integer, enum [0, 1, 2, 3].

**`truncated`**

Purpose: records whether the object's bounding box touches a frame boundary. It flags objects that are partially outside the image and so may be incompletely observed.

Governing policy: Section 3.3 (Truncated Objects). Set `true` when the object touches the frame edge (x1=0 or x2=1019 or y1=0 or y2=499) or is partially outside the frame with only a corner visible; set `false` when the object is fully inside the frame with at least 1 pixel of margin. Truncation at the ROI boundary line is not truncation and does not set this flag (Section 3.3, 3.7). Truncation is distinct from occlusion and does not affect the `occlusion` level unless the object is also occluded by another object (Section 4.3).

Schema meaning: boolean.

**`difficult`**

Purpose: flags annotations where the object is ambiguous, so that per-class error under ambiguity can be measured separately from clear cases.

Governing policy: Section 2.4, Section 4.6, and Section 5.6. Set `true` when the object's class is uncertain, when there is motion blur, or when weather or illumination conditions make the object hard to judge. Severe occlusion alone does not set `difficult` unless the object is also ambiguous (Section 4.6). When `difficult` is true, the class follows the conservative rule in Section 2.4. Class ambiguity does not justify changing a track's class; the class remains immutable per `global_id` (Section 5.6).

Schema meaning: boolean.

**What this subsection does not define.**

This subsection documents the meaning and source policy of the existing fields. It does not define required-field lists, field ordering, enum values beyond those established in Sections 2–4, or validation rules; those belong to later subsections and are not introduced here. It does not modify any JSON schema file.

- **Section 7.6–7.8** — Temporal train/val/test split, leakage prevention, ROI-crossing events at boundaries (this document)
- **Section 7.9: Data Schema** (this document)
- **Section 7.10–7.12** — Short tracking gaps and occlusion, frames near important events, sampling manifest requirements, reproducibility requirements (this document)
- **Section 8.1: Data Schema** (this document)
- **Section 8.2: Detection Ground Truth Schema** (this document)
- **Section 8.2.3: Detection Ground Truth Validation Semantics** (this document)

---

#### 8.2.3 Detection Ground Truth Validation Semantics

**Purpose and scope.**

This subsection states how a detection ground truth record is checked for well-formedness before it enters evaluation. It restates the constraints already present in the authoritative JSON schema, paired with the annotation semantics established in Sections 3–5, so that a validator and an annotator read the same contract. It does not add new fields, new enum values, new thresholds, or new validation rules.

**Authoritative sources.**

- The JSON schema (`annotation/schema/detection_ground_truth.schema.json`) is authoritative for field names, required-vs-optional, types, and numeric ranges.
- Sections 3–5 are authoritative for annotation semantics (class policy, bounding box policy, occlusion policy).
- Section 7 is authoritative for which frames are sampled and how they are split.

**Required versus optional fields.**

At the record level, every line of the JSONL file must carry exactly three fields: `frame_id`, `timestamp`, and `annotations`. No other top-level field is permitted.

At the annotation level, every element of `annotations` must carry exactly six fields: `class`, `bbox`, `visibility`, `occlusion`, `truncated`, and `difficult`. No other per-annotation field is permitted, and no per-annotation field may be dropped.

There are no optional fields in this schema. A field is either present and required, or it is not part of the schema at all.

**Allowed types and ranges.**

- `frame_id` must be an integer in the range 0–620.
- `timestamp` must be a number in the range 0.0–41.4 and must equal `frame_id / 15.0`.
- `class` must be one of: `car`, `motorcycle`, `bus`, `truck`, `person`.
- `bbox` must be an array of exactly four integers, each in the range 0–1019.
- `visibility` must be a number in the range 0.0–1.0.
- `occlusion` must be an integer in the set {0, 1, 2, 3}.
- `truncated` must be a boolean.
- `difficult` must be a boolean.

**Bounding box constraints.**

A bbox is written as `[x1, y1, x2, y2]` in the 1020×500 resized pixel space. The schema enforces that each coordinate is an integer in 0–1019 and that exactly four coordinates are present. The annotation policy additionally requires `x1 < x2` and `y1 < y2`, and a minimum size of 10×10 pixels, so that a degenerate or zero-area box cannot be mistaken for a real object.

A box that touches the frame boundary — `x1 = 0`, `x2 = 1019`, `y1 = 0`, or `y2 = 499` — must have `truncated` set to `true`. A box that does not touch any boundary must have `truncated` set to `false`.

**Visibility, occlusion, truncated, and difficult constraints.**

`visibility` records the visible fraction of the object. The schema permits any value in 0.0–1.0, but the annotation policy draws a hard line at zero: a `visibility` of 0 means the object is fully hidden, and in that case no annotation is created at all. Every annotation that does exist must therefore have `visibility > 0`. The severe-occlusion band corresponds to `visibility` in (0.0, 0.1].

`occlusion` is an integer level with the meaning established in Section 4: 0 = none, 1 = partial (1–50%), 2 = heavy (>50–90%), 3 = severe (>90%). The level must be consistent with the recorded `visibility`: a higher occlusion level implies a lower visible fraction, and `occlusion = 3` must co-occur with `visibility ≤ 0.1`.

`truncated` and `difficult` are independent boolean flags. `truncated` is set from the box geometry alone, as stated above. `difficult` is set when the object is genuinely ambiguous to annotate — uncertain class, heavy motion blur, or severe weather — and it must not be used as a substitute for lowering `visibility` or raising `occlusion`.

**frame_id and timestamp consistency.**

`timestamp` is derived, not independent: it must equal `frame_id / 15.0`. A record whose `timestamp` does not match its `frame_id` at the video's 15 FPS is malformed, regardless of whether the value happens to fall inside the permitted 0.0–41.4 range.

Because the detection schema is per-frame, each record describes exactly one frame. The `frame_id` therefore identifies the frame unambiguously, and the `timestamp` is a redundant, derived representation of that same frame index.

**Per-frame uniqueness and annotation constraints.**

Each line of the JSONL file corresponds to one frame, and each frame must appear at most once. Two records carrying the same `frame_id` would describe the same frame twice and are not permitted.

Within a single record, the `annotations` array may contain any number of annotations, including zero for a frame in which no countable object is visible. There is no ordering requirement on the array; the annotations are an unordered set of per-object observations.

Two further constraints follow from the annotation policy rather than from the schema:

- Each annotation is an independent observation. The detection schema carries no object identifier, so it cannot express which annotations in successive frames belong to the same object. That identity information lives in the tracking ground truth (Section 8.2 is deliberately identifier-free).
- No annotation may be duplicated within a frame. Two annotations with identical `class` and `bbox` in the same record would be the same object recorded twice and are not permitted.

**Relationship to the authoritative schema.**

The JSON schema is the machine-checkable contract; this subsection is the human-readable interpretation of it. Where the two agree, either may be consulted. Where the schema is silent — for example on box orientation (`x1 < x2`, `y1 < y2`) or on the minimum box size — the annotation policy in Sections 3–5 fills the gap, and the schema's range checks (0–1019 per coordinate, exactly four coordinates) are the enforcement point.

This subsection does not define a validator, a checker, or a set of acceptance thresholds. It documents the constraints that any validator must enforce. It introduces no new fields, no new enum values, and no new rules beyond those already present in the schema and in Sections 3–5.

**What this subsection does not define.**

This subsection restates schema constraints; it does not define the tracking schema, the counting schema, or the sampling manifest. It does not define how detection predictions are scored against this ground truth, and it does not define the evaluation metrics. Those belong to later subsections and are not introduced here.

- **Section 3: Annotation Rules** — class policy, countable classes (this document)
- **Section 4: Bounding Box Policy** — box geometry, minimum size, boundary handling (this document)
- **Section 5: Occlusion Policy** — visibility, occlusion levels, severe occlusion (this document)
- **Section 7.6–7.8** — which frames are sampled and how they are split (this document)
- **Section 8.1: Data Schema** — schema architecture and cross-schema relationships (this document)
- **Section 8.2: Detection Ground Truth Schema** — field names, types, and per-field meaning (this document)
- **Section 8.3: Tracking Ground Truth Schema** (this document)

---

### 8.3 Tracking Ground Truth Schema

This subsection defines the Tracking Ground Truth schema: what it represents, how it relates to the annotation policies in Sections 1–7, and how it relates to Detection Ground Truth and Counting Ground Truth. It defines the schema's purpose and scope only. Detailed field definitions belong to later subsections and are not introduced here.

#### 8.3.1 Purpose and Scope

**Purpose of Tracking Ground Truth.**

Tracking Ground Truth is the video-wide record of object identity and per-frame geometry produced by the annotation protocol. It is organized by object rather than by frame: each record is one track, identified by a persistent `global_id`, and carries the observations of that object across the frames where it was annotated. Its purpose is to supply the identity-bearing representation that Detection Ground Truth and Counting Ground Truth are both derived from. Detection GT is the per-frame view of the same annotations, flattened so that identity is dropped; Counting GT is derived from each track's trajectory. Tracking GT is the central representation in the schema chain (Section 8.1).

Tracking GT is the ground-truth reference for the tracking component of the pipeline. It is the fixed, human-annotated identity against which the tracker's output is compared to compute tracking metrics. It does not define how tracking is performed; it defines what valid tracking ground truth looks like.

**Relationship to Section 5 — global_id Policy.**

Tracking Ground Truth is the record that Section 5 governs. Every track in Tracking GT is one `global_id`, and the `global_id` Policy in Section 5 applies to the whole schema: the identifier is assigned by the annotator, is immutable across the entire video, and is scoped to the video named by `video_id`. A track's `class` is likewise constant for the lifetime of the track, per the class immutability rule in Section 5.6.

The `global_id` format — `GT_XXX`, zero-padded 3-digit, assigned sequentially in order of first appearance — is a property of the tracking schema and of no other schema. Tracking GT is the only ground-truth schema that carries `global_id`; Counting GT references it, and Detection GT omits it entirely.

**Relationship to Detection Ground Truth.**

Tracking Ground Truth and Detection Ground Truth describe the same annotations from different organizational viewpoints (Section 8.1). Tracking GT is organized by object: one record per `global_id`, with a `frames` array of per-frame observations spanning the object's lifetime. Detection GT is organized by frame: one record per sampled frame, with an `annotations` array of the objects visible in that frame.

The content relationship is one-to-one at the observation level. Every element of a track's `frames` array has a corresponding detection annotation in the Detection GT record for that `frame_id`, and every detection annotation corresponds to exactly one track observation. The fields they share — `class`, `bbox`, `visibility`, `occlusion`, and `truncated` — must agree between the two schemas for the same object at the same frame. Detection GT omits `global_id` and `center`; Tracking GT carries `global_id` as the track key and derives `center` from `bbox` for each observation.

This relationship means Tracking GT is not annotated independently of Detection GT. Detection GT is the per-frame projection of Tracking GT, and any inconsistency between the two is an annotation error, not a design choice.

**Per-frame tracking observations.**

Each track is a sequence of per-frame observations collected in its `frames` array. Each observation records the object's geometry and observable conditions at one frame: `frame_id`, `timestamp`, `bbox`, `visibility`, `occlusion`, `truncated`, and a derived `center`. These observations carry the same per-frame meaning as a detection annotation — the same `class`, `bbox`, `visibility`, `occlusion`, and `truncated` values — plus the `center` point that trajectory and ROI-crossing analysis require.

The observations are not a continuous sample of the video. They exist only at sampled frames (Section 7.2), and the array is allowed to have gaps. A frame at which the object is fully invisible (`visibility = 0`) contributes no observation and appears as a gap in the array, consistent with the occlusion policy in Section 4 and the gap-handling rules in Section 7.9. Tracking GT therefore represents the object's trajectory at the sampled-frame rate, not at the full 15 FPS, and the gaps are part of the representation rather than missing data to be filled in.

**Trajectory continuity.**

A track expresses trajectory continuity through its persistent `global_id` and its ordered sequence of observations. The identity is continuous by construction: the same `global_id` is reused for every observation of the same physical object, across sampled frames, across gaps, and across the train/val/test partitions (Section 7.6). Continuity is not inferred by the schema; it is asserted by the annotator and recorded by the single identifier that spans the whole track.

The schema records the start and end of each track — `start_frame`/`end_frame` and the derived `start_timestamp`/`end_timestamp` — so that a track's temporal extent is explicit. Within that extent, the observations are ordered by `frame_id`, and the trajectory is reconstructable from the sequence of `center` points together with their `frame_id` and `timestamp` values.

**Distinction between GT `global_id` and ByteTrack `track_id`.**

Tracking Ground Truth carries `global_id`, which is a separate identity space from the ByteTrack `track_id` produced by the production tracker, and the two must never be conflated (Section 5.1).

| Property | `global_id` (Ground Truth) | ByteTrack `track_id` (pipeline output) |
|----------|----------------------------|----------------------------------------|
| Source | Human-annotated | Algorithmic tracker output |
| Scope | Entire video (0–620) | Per tracker session; resets on re-initialization |
| Stability | Immutable once assigned | Can change due to ID switches and fragmentation |
| Format | `GT_XXX` | Integer |
| Role | Evaluation ground truth | System under test output |

The distinction is enforced structurally: `global_id` appears in Tracking GT and in Counting GT, while ByteTrack `track_id` appears in no ground-truth schema. Evaluation matches tracker predictions to ground truth via spatiotemporal comparison against `global_id`; it never maps `track_id` to `global_id` (Section 5.1, 6.8). A track in Tracking GT is a ground-truth statement about identity, not a record of what the tracker decided.

**Relationship to Counting Ground Truth.**

Tracking Ground Truth is the input from which Counting Ground Truth is derived (Section 8.1). Every counting event references a `global_id` that must exist in a Tracking GT track, and the event's `frame_id`, `bbox_at_crossing`, and `roi_point` come from the track observation at the crossing frame. Counting events are not annotated independently; they are produced by testing each track's bottom-center trajectory against the ROI polygon (Section 6.6).

Tracking GT also carries an optional `roi_crossings` array on each track, which records each crossing with `frame_id`, `direction`, and `roi_point`. This array is the per-track mirror of the counting events and is the structure that supports entry/exit analysis and, in future, multi-zone traffic graphs (Section 6.9). The counting schema is authoritative for the event-level representation; the tracking schema's `roi_crossings` is the per-track view of the same crossings.

**Sampled-frame versus full-video track representation.**

Tracking GT is a full-video representation in the sense that each track spans the entire frame domain of the video: a track begins at the frame where the object first appears and ends at the frame where it last appears, and its `global_id` is meaningful across all frames 0–620. However, the observations themselves exist only at sampled frames. The track therefore combines two properties: a full-video identity scope with a sampled-frame observation set.

This is not a deficiency. The unsampled frames between two observations are handled by the gap rules in Section 7.9: a gap of up to 30 frames of full invisibility is permitted, and longer disappearances end the track. The track's identity is unaffected by which frames were sampled (Section 5.3). What Tracking GT does not do is interpolate or extrapolate geometry at unsampled frames; the `frames` array contains only observed frames, and no bbox is invented for a frame that was not annotated.

**Role in future trajectory, zone-transition, and traffic-graph evaluation.**

Tracking Ground Truth preserves the minimum information required for trajectory analysis and for future multi-zone traffic graphs, without over-engineering for current needs.

- **Trajectory.** Each observation records `center` (derived from `bbox`) together with `frame_id` and `timestamp`, so an object's path through the frame is reconstructable. The ordered sequence of observations, keyed by `global_id`, is the trajectory. Counting GT anchors the trajectory to the ROI boundary by recording `roi_point` and `bbox_at_crossing` at each crossing.
- **Zone transition.** Each track's `roi_crossings` array records every crossing with `frame_id`, `direction`, and `roi_point`. Counting GT records the same information at the event level. Together they support entry/exit event analysis for the current single-zone ROI, and the per-crossing structure is ready to support multiple zones without a schema change (Section 6.9).
- **Traffic state.** The sequence of observations, each carrying `timestamp` and `class`, supports flow rate and occupancy analysis per class. Counting GT aggregates crossings into `total_counts` by class for the counting metrics.
- **Future traffic graph.** The `roi_crossings` array is structured to hold multiple zone crossings per track. Extending to a multi-zone ROI requires adding polygons to metadata; no schema change is needed, because each crossing records its own `frame_id`, `direction`, and `roi_point` (Section 6.9).

**What this subsection does not define.**

This subsection defines the purpose and scope of Tracking Ground Truth. It does not define individual fields, required-field lists, enum values, or validation rules for the schema; those belong to later subsections and are not introduced here. It does not modify any JSON schema file.

- **Section 5: Ground Truth global_id Policy (Tracking Identity)** — identity assignment and immutability (this document)
- **Section 7.2, 7.6–7.9** — sampling units, train/val/test split, leakage prevention, gap and occlusion handling (this document)
- **Section 8.1: Data Schema** — schema architecture and cross-schema relationships (this document)
- **Section 8.2: Detection Ground Truth Schema** — per-frame projection of the same observations (this document)
- **Section 8.3: Tracking Ground Truth Schema** (this document)

---

#### 8.3.2 Tracking Ground Truth Field Semantics

This subsection documents the semantic meaning and role of the Tracking Ground Truth fields. The JSON schema is authoritative for field names and types; Sections 2–6 are authoritative for annotation semantics. No new fields are introduced.

**`global_id`**

Purpose: the persistent identity of a physical object, and the primary key of Tracking Ground Truth. Each track in the schema is exactly one `global_id`, and every per-frame observation in that track belongs to it.

Governing policy: Section 5 (global_id Policy). The identifier is assigned by the annotator in order of first appearance, is immutable across the entire video, and is scoped to the video named by `video_id`. The format is `GT_XXX` (zero-padded 3-digit).

Relationship to tracking identity: `global_id` is what makes a track a track. It is the single identifier that links all observations of the same object across sampled frames, across gaps, and across the train/val/test partitions. Identity continuity is asserted by this field, not inferred by the schema.

Relationship to ByteTrack `track_id`: `global_id` is a separate identity space and must never be conflated with the algorithmic `track_id` produced by the production tracker (Section 5.1). `global_id` is human-annotated, spans the whole video, is immutable, and carries the `GT_XXX` format; `track_id` is algorithmic, scoped to a tracker session, can change due to ID switches and fragmentation, and is an integer. ByteTrack `track_id` appears in no ground-truth schema. Evaluation matches tracker output to ground truth by spatiotemporal comparison against `global_id`, never by mapping `track_id` to `global_id`.

Relationship to counting: every counting event references a `global_id` that must exist in a Tracking GT track (Section 6.6). `global_id` is the link that connects a counting event to the object that crossed the ROI.

Schema meaning: string matching the pattern `^GT_\d{3}$`.

**`class`**

Purpose: the object's class, constant for the lifetime of the track. It is the label used to compare the annotation against the tracker's predicted class and against the counting event's class.

Governing policy: Section 2.3 (Class Labels) and Section 5.6 (class immutability). The value must be one of the five countable classes: `car`, `motorcycle`, `bus`, `truck`, `person`. Once assigned to a `global_id`, the class does not change for any observation in the track, even where the object becomes ambiguous (Section 2.4, 5.6).

Relationship to tracking identity: class is a property of the identity, not of the frame. Because it is immutable per `global_id`, the class recorded on any observation can be trusted to be the class of the whole track.

Relationship to counting: the counting schema's per-event `class` must agree with this track's `class`, and `total_counts` are aggregated by this value.

Schema meaning: string, enum of the five countable classes.

**`frames`**

Purpose: the ordered set of per-frame observations of the object, spanning the track's lifetime. It is the core content of the track: the geometry and observable conditions of the object at each frame where it was annotated.

Governing policy: Section 7.2 (Sampling Units) governs which frames may carry observations; Section 7.9 (Short Tracking Gaps and Occlusion) governs what gaps are permitted. Each observation carries the per-frame fields defined below.

Relationship to trajectory: the sequence of observations, ordered by `frame_id`, is the object's trajectory. Each observation supplies the `center` point, `frame_id`, and `timestamp` from which the path is reconstructed.

Relationship to counting: each observation's geometry is tested against the ROI polygon to detect crossings. The `roi_crossings` array, when present, records the crossings found in this track.

Schema meaning: array of observation objects. Gaps are permitted for full invisibility (visibility = 0) up to 30 frames. Each observation must have a unique `frame_id` within the track.

**Observation fields: `frame_id`, `timestamp`, `bbox`, `visibility`, `occlusion`, `truncated`, `center`**

Each element of `frames` is one per-frame observation. Its fields carry the same per-frame meaning as the corresponding detection annotation fields (Section 8.2.2), with two differences: the observation carries `center`, and it is scoped to a track by `global_id`.

- **`frame_id`** — the 0-based index of the source frame (0–620 for `3.mp4`). It is the temporal key of the observation and the key that joins the observation to the Detection GT record for the same frame and to any counting event at that frame. Governing policy: Section 2.2 (Frame Referencing), Section 7.2. Schema meaning: integer, minimum 0, maximum 620.
- **`timestamp`** — the time of the frame in seconds, derived as `frame_id / fps`. It is recorded alongside `frame_id` so that time and frame identity cannot drift apart, consistent across all four schemas. Governing policy: Section 2.2. Schema meaning: number, minimum 0, maximum 41.4.
- **`bbox`** — the bounding box `[x1, y1, x2, y2]` enclosing the visible extent of the object, in the 1020×500 coordinate space. It must agree with the detection annotation for the same object at the same frame. Governing policy: Section 3 (Bounding Box Policy). Schema meaning: array of four integers, each in 0–1019; minimum size 10×10 pixels.
- **`visibility`** — the estimated visible fraction of the object, on a continuous 0.0–1.0 scale. A value of 0 means the object is fully hidden and no observation is created; such frames appear as gaps in `frames`. Governing policy: Section 4.1, 4.4. Schema meaning: number, minimum 0.0, maximum 1.0. Note: visibility = 0 frames are NOT in this array (track gap).
- **`occlusion`** — the categorical occlusion level: 0 none, 1 partial (1–50%), 2 heavy (>50–90%), 3 severe (>90%). Governing policy: Section 4.1, 4.3. Schema meaning: integer, enum [0, 1, 2, 3].
- **`truncated`** — whether the object's bounding box touches a frame boundary. Governing policy: Section 3.3 (Truncated Objects). Schema meaning: boolean.
- **`center`** — the derived center point `[cx, cy] = [(x1+x2)/2, (y1+y2)/2]`. It is not an independently annotated value; it is computed from `bbox`. It is the point used for trajectory reconstruction and for ROI-crossing detection, where the bottom-center of the box is tested against the ROI polygon. Schema meaning: array of two numbers, minItems 2, maxItems 2.

Relationship to trajectory: `center`, `frame_id`, and `timestamp` together make the trajectory reconstructable. The ordered sequence of these points, keyed by `global_id`, is the object's path through the frame.

Relationship to counting: the crossing test operates on the observation's geometry at each frame. The `roi_crossings` array records the crossings derived from this sequence.

**`start_frame` and `end_frame`**

Purpose: the temporal extent of the track. `start_frame` is the first frame where the object appears (its first annotated observation); `end_frame` is the last frame where it appears (its last annotated observation).

Governing policy: Section 5.3 (track extent). These values are derived from the `frames` array — they are the minimum and maximum `frame_id` in the array — and are recorded explicitly so that the track's lifetime is stated unambiguously.

Relationship to trajectory: they bound the trajectory. The trajectory exists only between `start_frame` and `end_frame`; outside that range the object is not present in the video.

Schema meaning: integer, minimum 0, maximum 620.

**`start_timestamp` and `end_timestamp`**

Purpose: the temporal extent of the track in seconds, derived as `start_frame / 15.0` and `end_frame / 15.0`. They are the time-domain counterparts of `start_frame` and `end_frame`, recorded so that time and frame identity cannot drift apart.

Governing policy: Section 2.2. These values are derived, never independently assigned, consistent with the derivation rule applied to `timestamp` throughout the schema layer.

Relationship to trajectory: they bound the trajectory in time, consistent with the frame bounds.

Schema meaning: number, minimum 0, maximum 41.4.

**`roi_crossings` (optional)**

Purpose: the per-track record of ROI-crossing events for this object. Each entry records one crossing with `frame_id`, `direction`, and `roi_point`. It is the per-track mirror of the counting events recorded in Counting Ground Truth.

Status: optional. Its presence is not required for a valid track, and a track with no crossings may omit the array entirely.

Governing policy: Section 6.6 (derivation of counting events), Section 6.9 (multi-zone readiness). The crossings are derived from the track's bottom-center trajectory, not annotated independently.

Relationship to counting: every entry in `roi_crossings` corresponds to a counting event for this `global_id`, and every counting event for a `global_id` corresponds to an entry here. Where both exist, the `frame_id`, `direction`, and `roi_point` must agree. The counting schema is authoritative for the event-level representation; this array is the per-track view of the same crossings.

Relationship to trajectory: the crossings anchor the trajectory to the ROI boundary. They mark the frames at which the object's bottom-center path crossed from outside to inside the ROI, and they are the points at which the trajectory enters the counting region.

Relationship to future traffic-graph evaluation: the array is structured to hold multiple zone crossings per track. Extending to a multi-zone ROI requires adding polygons to metadata; no schema change is needed, because each crossing records its own `frame_id`, `direction`, and `roi_point` (Section 6.9).

Schema meaning: array of objects, each required `["frame_id", "direction", "roi_point"]`, with `direction` an enum of `entry`/`exit` for the current single-zone ROI.

**What this subsection does not define.**

This subsection documents the meaning and source policy of the existing fields. It does not define required-field lists, field ordering, enum values beyond those established in Sections 2–6, or validation rules; those belong to later subsections and are not introduced here. It does not modify any JSON schema file.

- **Section 2: Annotation Rules (General)** — class labels, frame referencing, coordinate system (this document)
- **Section 3: Bounding Box Policy** — box geometry, truncation, minimum size (this document)
- **Section 4: Occlusion Policy** — visibility, occlusion levels (this document)
- **Section 5: Ground Truth global_id Policy (Tracking Identity)** — identity assignment, immutability, class immutability (this document)
- **Section 6: Counting Event Policy** — counting event derivation, crossing confidence, multi-zone readiness (this document)
- **Section 7.2, 7.6–7.9** — sampling units, train/val/test split, leakage prevention, gap and occlusion handling (this document)
- **Section 8.1: Data Schema** — schema architecture and cross-schema relationships (this document)
- **Section 8.2: Detection Ground Truth Schema** — per-frame projection of the same observations (this document)
- **Section 8.3.1: Tracking Ground Truth Schema** — purpose and scope of this schema (this document)
- **Section 8.3.2: Tracking Ground Truth Field Semantics** — per-field meaning and source policy (this document)
- **Section 8.3.3: Tracking Ground Truth Validation Semantics** (this document)

---

#### 8.3.3 Tracking Ground Truth Validation Semantics

**Purpose and scope.**

This subsection states how a tracking ground truth record is checked for well-formedness before it enters evaluation. It restates the constraints already present in the authoritative JSON schema, paired with the annotation semantics established in Sections 3–7, so that a validator and an annotator read the same contract. It does not add new fields, new enum values, new thresholds, or new validation rules.

**Authoritative sources.**

- The JSON schema (`annotation/schema/tracking_ground_truth.schema.json`) is authoritative for field names, required-vs-optional, types, and numeric ranges.
- Sections 3–5 are authoritative for annotation semantics (bounding box policy, occlusion policy, global_id policy).
- Section 6 is authoritative for counting event derivation.
- Section 7 is authoritative for which frames are sampled and how they are split.

**Required versus optional fields.**

At the track level, every track object must carry exactly seven required fields: `global_id`, `class`, `frames`, `start_frame`, `end_frame`, `start_timestamp`, and `end_timestamp`. No other track-level field is permitted.

The `roi_crossings` array is the only optional field at the track level. A track may omit it entirely, and its absence is not a validation failure.

At the observation level, every element of `frames` must carry exactly seven required fields: `frame_id`, `timestamp`, `bbox`, `visibility`, `occlusion`, `truncated`, and `center`. No other per-observation field is permitted, and no per-observation field may be dropped.

There are no optional fields at the observation level. Within the schema, a field is either present and required, or it is not part of the schema at all.

**Field types, ranges, and enums.**

- `global_id` must be a string matching the pattern `^GT_\d{3}$` (e.g., `GT_001`).
- `class` must be a string from the enum: `car`, `motorcycle`, `bus`, `truck`, `person`.
- `frames` must be an array of observation objects.
- `start_frame` and `end_frame` must be integers in the range 0–620.
- `start_timestamp` and `end_timestamp` must be numbers in the range 0.0–41.4.
- Observation `frame_id` must be an integer in the range 0–620.
- Observation `timestamp` must be a number in the range 0.0–41.4.
- Observation `bbox` must be an array of exactly four integers, each in the range 0–1019.
- Observation `visibility` must be a number in the range 0.0–1.0.
- Observation `occlusion` must be an integer in the set {0, 1, 2, 3}.
- Observation `truncated` must be a boolean.
- Observation `center` must be an array of exactly two numbers.
- `roi_crossings`, when present, must be an array of objects, each carrying `frame_id` (integer 0–620), `direction`, and `roi_point` (array of two numbers).

The `direction` enum differs between the tracking and counting schemas and must not be flattened into a single value. The tracking schema permits `entry` and `exit`; the counting schema currently permits `entry` only (Section 6.2). A tracking `roi_crossings` entry may record an `exit` that has no corresponding counting event, because the counting schema does not yet represent exits. This is a known schema asymmetry, not a validation error in either file.

**global_id format and uniqueness.**

Every track is identified by exactly one `global_id`, and the format `GT_XXX` (zero-padded 3-digit) is enforced by the schema pattern. Within a tracking ground truth file, each `global_id` must appear exactly once as a track key. Two tracks sharing the same `global_id` would describe the same physical object under two separate records and are not permitted.

Uniqueness is scoped to the video: the `global_id` space belongs to one video, and the same identifier is not reused across videos. The assignment order — sequential by first appearance — is a convention of Section 5, not a schema constraint, so a validator checks format and uniqueness but not ordering.

**frames ordering and frame_id/timestamp consistency.**

The `frames` array is ordered by `frame_id`. Each observation's `frame_id` must be unique within its track: two observations with the same `frame_id` would describe the same frame twice and are not permitted. This is the per-track counterpart of the per-frame uniqueness rule in the detection schema.

`timestamp` is derived, not independent: it must equal `frame_id / 15.0`. An observation whose `timestamp` does not match its `frame_id` at the video's 15 FPS is malformed, regardless of whether the value falls inside the permitted 0.0–41.4 range. The same derivation rule applies to the track-level `start_timestamp`/`end_timestamp`, which must equal `start_frame / 15.0` and `end_frame / 15.0` respectively.

Gaps in the `frames` array are structural, not errors. A frame at which the object is fully invisible (`visibility = 0`) contributes no observation and appears as a gap. Gaps of up to 30 frames of full invisibility are permitted (Section 7.9); a longer disappearance ends the track rather than producing a gap. The validator checks that a gap is explicable by invisibility — it does not require the array to be contiguous.

**bbox, visibility, occlusion, truncated, and center consistency.**

Each observation's `bbox` is `[x1, y1, x2, y2]` with `x1 < x2` and `y1 < y2`, a minimum size of 10×10 pixels, and each coordinate an integer in 0–1019 (Section 3). The box must agree with the detection annotation for the same object at the same frame, because the detection schema is the per-frame projection of this track (Section 8.1).

`visibility` is in 0.0–1.0, and a value of 0 means the object is fully hidden — in which case no observation exists and the frame is a gap, not an observation with `visibility = 0`. Every observation that does exist must have `visibility > 0`. The severe-occlusion band corresponds to `visibility` in (0.0, 0.1].

`occlusion` is an integer level: 0 none, 1 partial (1–50%), 2 heavy (>50–90%), 3 severe (>90%) (Section 4). It must be consistent with the recorded `visibility`: a higher occlusion level implies a lower visible fraction, and `occlusion = 3` must co-occur with `visibility ≤ 0.1`.

`truncated` is set from the box geometry alone: `true` when the box touches a frame boundary (`x1 = 0`, `x2 = 1019`, `y1 = 0`, or `y2 = 499`), `false` otherwise (Section 3.3).

`center` is derived from `bbox` as `[(x1+x2)/2, (y1+y2)/2]`. It is not an independently annotated value, so a `center` that is inconsistent with its own `bbox` is a validation failure. `center` is the point used for trajectory reconstruction and for the ROI-crossing test.

**start_frame/end_frame and timestamp consistency.**

`start_frame` must be the minimum `frame_id` in the track's `frames` array, and `end_frame` must be the maximum. A `start_frame` lower than the first observation's `frame_id`, or an `end_frame` higher than the last observation's `frame_id`, would describe a track extent that the observations do not support and is not permitted.

`start_timestamp` and `end_timestamp` are derived from those bounds at 15 FPS and must agree with them. Together they state the track's temporal extent explicitly; the trajectory exists only between them.

**roi_crossings consistency with the existing counting policy.**

When present, each `roi_crossings` entry records a crossing at a `frame_id` that must exist among the track's observations — a crossing attributed to a frame the track does not observe is not supported. The `roi_point` is the bottom-center point at that frame, derived from the observation's `bbox`, and must be consistent with it.

Each entry's `direction` is `entry` or `exit`, per the tracking schema. Every `entry` crossing for a `global_id` must have a corresponding counting event in Counting Ground Truth, because counting events are derived from exactly this trajectory test (Section 6.6). An `exit` crossing has no counterpart in the counting schema, which currently represents `entry` only (Section 6.2); that asymmetry is recorded in the Known Ambiguities section and is not a validation failure here.

The counting schema is authoritative for the event-level representation, and the tracking `roi_crossings` array is the per-track view of the same crossings. Where both exist for the same `global_id` and `frame_id`, the `frame_id`, `direction`, and `roi_point` must agree.

**additionalProperties and schema authority.**

Both the track level and the observation level enforce `additionalProperties: false`. No field beyond those listed above may appear in a track object or an observation object. A field that is not in the schema cannot be validated, because the schema is the only definition of what the data may contain.

The schema is authoritative for field names, required-vs-optional, types, and numeric ranges. Where the schema is silent — for example on box orientation (`x1 < x2`, `y1 < y2`), minimum box size, or the derivation of `center` from `bbox` — the annotation policy in Sections 3–5 fills the gap, and the schema's range checks are the enforcement point.

This subsection does not define a validator, a checker, or a set of acceptance thresholds. It documents the constraints that any validator must enforce.

**What this subsection does not define.**

This subsection restates schema constraints; it does not define how tracking predictions are scored against this ground truth, how tracker output is matched to tracks, or the tracking metrics. It does not define the detection, counting, or sampling schemas. It introduces no new fields, no new enum values, and no new rules beyond those already present in the schema and in Sections 3–7.

- **Section 3: Bounding Box Policy** — box geometry, truncation, minimum size (this document)
- **Section 4: Occlusion Policy** — visibility, occlusion levels, severe occlusion (this document)
- **Section 5: Ground Truth global_id Policy (Tracking Identity)** — identity assignment, immutability, class immutability (this document)
- **Section 6: Counting Event Policy** — counting event derivation, crossing confidence, multi-zone readiness (this document)
- **Section 7.2, 7.6–7.9** — sampling units, train/val/test split, leakage prevention, gap and occlusion handling (this document)
- **Section 8.1: Data Schema** — schema architecture and cross-schema relationships (this document)
- **Section 8.2: Detection Ground Truth Schema** — per-frame projection of the same observations (this document)
- **Section 8.3.1: Tracking Ground Truth Schema** — purpose and scope of this schema (this document)
- **Section 8.3.2: Tracking Ground Truth Field Semantics** — per-field meaning and source policy (this document)
- **Section 8.3.3: Tracking Ground Truth Validation Semantics** (this document)
- **Section 8.4: Counting Ground Truth Schema** (this document)

---

### 8.4 Counting Ground Truth Schema

This subsection defines the Counting Ground Truth schema: what it represents, how it relates to the annotation policies in Sections 1–7, and how it relates to Tracking Ground Truth and to model output. It defines the schema's purpose and scope only. Detailed field definitions belong to later subsections and are not introduced here.

#### 8.4.1 Purpose and Scope

**Purpose of Counting Ground Truth.**

Counting Ground Truth is the record of ROI-crossing events derived from the annotation protocol. It is the terminal output of the ground-truth derivation chain: Tracking Ground Truth supplies the object identity and per-frame geometry, and Counting Ground Truth records, for each object that crossed the ROI, the event at which it crossed. Its purpose is to provide the ground-truth reference for the counting component of the pipeline — the fixed set of crossing events against which the production ROI counter's predictions are compared to compute counting metrics.

Counting GT does not annotate objects or crossings independently. Every event in it is derived algorithmically from Tracking GT geometry (Section 6.6). It defines what valid counting ground truth looks like, not how crossings are detected.

**Role as the reference for counting-event evaluation.**

Counting GT is the ground truth for the counting stage. The production pipeline (YOLOv8m + ByteTrack + Entity Association + ROI Counting) produces its own predicted counting events; Counting GT is the fixed, human-annotated reference against which those predictions are compared. The comparison is event-level: each predicted event is matched to a ground-truth event, and counting metrics such as agreement rate are computed from the match.

Counting GT is stable and reproducible. It is produced from Tracking GT before any model runs and does not change when the pipeline is re-run. The prediction side — the pipeline's counting output — is what is being measured.

**Relationship to Tracking Ground Truth via `global_id`.**

Counting GT is downstream of Tracking GT in the derivation chain (Section 8.1). Every counting event references a `global_id` that must exist in a Tracking GT track, and the event's `frame_id`, `bbox_at_crossing`, and `roi_point` come from the track observation at the crossing frame. `global_id` is the link that connects a counting event to the physical object that crossed the ROI, and through it to the object's whole trajectory.

Because counting events are derived from tracking geometry and not annotated independently, a counting event is valid only if its `global_id` exists in Tracking GT and its frame data agrees with the corresponding track observation. This is a derivation relationship, not an independent annotation relationship.

**Relationship to ROI-crossing policy in Section 6.**

Counting Ground Truth is the record that Section 6 governs. The ROI-crossing policy defines what counts as a crossing — the frame at which an object's bottom-center first enters the ROI, the `roi_point` at that frame, and the `direction` of travel (Section 6.2, 6.6). Each counting event is one such crossing, recorded with the `crossing_confidence` determined by the deterministic rule in Section 6.3.1 from the observable fields at the crossing frame.

The current pipeline represents `entry` crossings only (outside → inside the ROI); `exit` crossings are recorded in Tracking GT's `roi_crossings` array but have no counterpart here. That asymmetry is a property of the counting schema and is not resolved or redesigned by this subsection (Section 6.2).

**Relationship to sampling and partition rules in Section 7.**

Counting events exist only at sampled frames. A crossing that occurs at an unsampled frame has no counting event, because there is no track observation at that frame from which the event could be derived (Section 7.2). The sampling manifest is the index of the frame domain that the counting schema covers.

The temporal train/val/test split in Section 7.6 governs which counting events belong to which partition. A crossing is attributed to the partition of its crossing frame, and the leakage-prevention rules in Section 7.7 apply: an event window is clipped at a partition boundary rather than moved, and the read-only anchor at `t-1` is not available across a boundary (Section 7.8).

**Distinction between GT counting events and production pipeline counting predictions.**

Counting Ground Truth and the production pipeline's counting predictions are fundamentally different and must not be conflated.

| Property | Counting Ground Truth | Production counting predictions |
|----------|------------------------|--------------------------------|
| Source | Derived from human-annotated Tracking GT | YOLOv8m + ByteTrack + Entity Association + ROI Counting pipeline output |
| Stability | Fixed once produced; unchanged by re-running the pipeline | Changes with model weights, tracker state, and runtime conditions |
| Identity | References `global_id` from Tracking GT | References tracker-assigned identifiers, not `global_id` |
| Coverage | One entry event per `global_id` that entered the ROI | Depends on tracker performance; may miss or duplicate events |
| Role | Evaluation reference (ground truth) | System under test output |

The distinction is enforced structurally: no ground-truth schema contains pipeline output, and no pipeline output is validated against a counting schema. Evaluation matches predicted events to ground-truth events; the ground-truth side is stable and the pipeline side is what is being measured (Section 8.1).

**Field semantics and validation rules are deferred.**

This subsection defines the purpose and scope of Counting Ground Truth only. It does not define individual field semantics, required-field lists, enum values, or validation rules for the schema; those belong to later subsections and are not introduced here. The field-level meaning of `event_id`, `global_id`, `class`, `frame_id`, `timestamp`, `roi_point`, `direction`, `bbox_at_crossing`, and `crossing_confidence`, and the well-formedness constraints on them, are deferred to later 8.4 subsections.

**What this subsection does not define.**

This subsection defines the purpose and scope of Counting Ground Truth. It does not define how counting predictions are scored against this ground truth, how predicted events are matched to ground-truth events, or the counting metrics. It does not define the detection or tracking schemas. It does not resolve or redesign any existing ground-truth asymmetry, including the entry-only `direction` enum or the relationship between tracking `roi_crossings` and counting events. It introduces no new fields, no new enum values, no new thresholds, and no new policies beyond those already present in the schema and in Sections 5–7.

- **Section 5: Ground Truth global_id Policy (Tracking Identity)** — identity assignment and immutability (this document)
- **Section 6: Counting Event Policy** — ROI-crossing definition, event derivation, crossing confidence, multi-zone readiness (this document)
- **Section 7.2, 7.6–7.9** — sampling units, train/val/test split, leakage prevention, gap and occlusion handling (this document)
- **Section 8.1: Data Schema** — schema architecture and cross-schema relationships (this document)
- **Section 8.2: Detection Ground Truth Schema** — per-frame projection of the same observations (this document)
- **Section 8.3: Tracking Ground Truth Schema** — identity-bearing input to counting events (this document)
- **Section 8.4: Counting Ground Truth Schema** (this document)

---

#### 8.4.2 Counting Ground Truth Field Semantics

This subsection documents the semantic meaning and role of the Counting Ground Truth fields. The JSON schema is authoritative for field names and types; Sections 5 and 6 are authoritative for annotation semantics. No new fields are introduced, no enum is changed, and no existing policy is redesigned.

**`video_id`**

Purpose: identifies the video this counting ground truth describes. It is the video-level key of the schema and scopes every event and every count in the file to one source video.

Governing policy: consistent with the video identifier used across all four schemas. It is recorded so that counting data from different videos cannot be conflated and so that the ROI polygon and counts are understood as belonging to one specific source.

Schema meaning: string (e.g., `3.mp4`).

**`roi_polygon`**

Purpose: the ROI polygon against which each track's bottom-center trajectory is tested to detect crossings. It is the counting boundary for the whole file, recorded once rather than repeated on every event.

Governing policy: Section 6.1 (Counting Boundary / ROI). The polygon is the region whose entry crossings produce counting events. It is stated in the 1020×500 coordinate space, consistent with the coordinate system used by every schema.

Schema meaning: array of four vertices `[[x1,y1], [x2,y2], [x3,y3], [x4,y4]]`, each coordinate an integer.

**`countable_classes`**

Purpose: the list of classes that generate counting events. It states explicitly which object classes are counted, so that a consumer of the file knows which events are in scope without inspecting every event.

Governing policy: Section 2.3 (Class Labels). The value is the set of five countable classes: `car`, `motorcycle`, `bus`, `truck`, `person`. A track whose `class` is not in this list produces no counting event, even if it crosses the ROI.

Schema meaning: array of strings, each from the class enum.

**`events`**

Purpose: the array of counting events — one per object that entered the ROI. It is the core content of the schema: the record of each ROI-crossing event derived from tracking ground truth.

Governing policy: Section 6.6 (Derivation: Counting GT from Tracking GT). Events are derived algorithmically from tracking GT, not annotated independently. For each track, the bottom-center point is computed per frame and tested against the ROI polygon; the first frame where the point moves from outside to inside the ROI produces one event, provided the class is countable. `total_counts` is the aggregation of this array by class.

Relationship to tracking: each event corresponds to exactly one track observation at the crossing frame, and its `global_id` must reference a track in Tracking GT. At most one `entry` event exists per `global_id` (Section 6.4).

Schema meaning: array of event objects.

**Event fields: `event_id`, `global_id`, `class`, `frame_id`, `timestamp`, `roi_point`, `direction`, `bbox_at_crossing`, `crossing_confidence`**

Each event records one ROI-crossing with the following fields.

- **`event_id`** — a sequential unique identifier (1, 2, 3...) for the event within the file. It orders events but carries no independent meaning about the crossing itself. Schema meaning: integer, minimum 1.
- **`global_id`** — the persistent identity of the object that crossed, referencing a track in Tracking GT (Section 5). It is the link from the counting event to the object's whole trajectory and to the track observation at the crossing frame. Schema meaning: string matching `^GT_\d{3}$`.
- **`class`** — the object's class at the crossing frame. It must agree with the `class` of the referenced track, which is immutable for the lifetime of that `global_id` (Section 5.6). Schema meaning: string, enum of the five countable classes.
- **`frame_id`** — the frame at which the crossing was detected: the first frame where the bottom-center point is inside the ROI (Section 6.2, 6.5). It is the temporal key that joins the event to the track observation at the crossing frame and to the Detection GT record for that frame. Schema meaning: integer, 0–620.
- **`timestamp`** — the time of the crossing frame, derived as `frame_id / 15.0`. It is recorded alongside `frame_id` so that time and frame identity cannot drift apart, consistent across all four schemas. Schema meaning: number, 0.0–41.4.
- **`roi_point`** — the bottom-center point at the crossing frame, `[cx, y2]`, where `cx = (x1+x2)/2` and `y2` is the bottom edge of the crossing observation's `bbox` (Section 6.2). It is the geometric evidence for the crossing and must be consistent with the referenced track observation's `bbox`. Schema meaning: array of two numbers.
- **`direction`** — the direction of travel at the crossing. The schema defines this enum as `["entry"]` for the current pipeline, representing outside → inside the ROI. **This enum is unchanged from the existing schema.** An `exit` crossing is recorded in Tracking GT's `roi_crossings` array but has no counterpart here; that asymmetry is a property of the counting schema and is not redesigned or resolved by this subsection (Section 6.2). Schema meaning: string, enum `["entry"]`.
- **`bbox_at_crossing`** — the full bounding box `[x1, y1, x2, y2]` of the object at the crossing frame. It must agree with the referenced track observation's `bbox` and, through it, with the detection annotation for the same object at the same frame. Schema meaning: array of four integers, each 0–1019.
- **`crossing_confidence`** — the deterministic confidence score for the crossing, assigned by the objective rule in Section 6.3.1 from the observable fields at the crossing frame (`visibility`, `occlusion`, `truncated`, `difficult`, and bbox geometry). The three tiers are `high`, `medium`, and `low`, each defined by explicit AND/OR conditions. No annotator judgment is involved. Schema meaning: string, enum `["high", "medium", "low"]`.

**Relationship of event fields to Tracking GT.**

Counting events are the event-level projection of Tracking GT. Each event's `global_id` references a track; its `class` must match the track's immutable `class`; its `frame_id` must be one of the track's observed frames; its `timestamp` must equal that `frame_id / 15.0`; its `bbox_at_crossing` must equal the track observation's `bbox` at that frame; and its `roi_point` must equal the bottom-center derived from that same `bbox`. The `crossing_confidence` is computed from that same observation's observable fields.

An event is valid only where all of these hold, because counting GT is derived from tracking GT and is not annotated independently (Section 6.6). Where the tracking schema's optional `roi_crossings` array exists for the same `global_id`, an `entry` crossing there must correspond to a counting event, and the `frame_id`, `direction`, and `roi_point` must agree.

**Relationship to Section 6 counting-event policy.**

Counting Ground Truth is the record that Section 6 governs. Section 6.1 defines the ROI boundary recorded here as `roi_polygon`; Section 6.2 defines the crossing condition that determines `frame_id`, `roi_point`, and `direction`; Section 6.3 and 6.3.1 define the event fields and the deterministic `crossing_confidence` rule; Section 6.4 prevents duplicate events (at most one `entry` per `global_id`, first qualifying frame wins); Section 6.5 handles edge cases at the crossing frame; and Section 6.6 defines the derivation from Tracking GT that makes every event consistent with its track.

**Distinction between GT fields and production counting outputs.**

The fields in this schema are ground-truth fields and must not be confused with the fields of the production pipeline's counting output. Counting GT references `global_id` from human-annotated Tracking GT, is fixed once produced, covers exactly one entry event per object that entered the ROI, and serves as the evaluation reference. The production counter's output references tracker-assigned identifiers, changes with model weights and tracker state, may miss or duplicate events, and is the system under test. No ground-truth schema contains pipeline output, and no pipeline output is validated against a counting schema (Section 8.1).

**Validation rules are deferred.**

This subsection documents the meaning and source policy of the existing fields. It does not define required-field lists, field ordering, enum values beyond those already established in Sections 2 and 6, or validation rules; those belong to the later 8.4.3 subsection and are not introduced here.

**What this subsection does not define.**

This subsection documents field semantics only. It does not define how counting predictions are scored against this ground truth, how predicted events are matched to ground-truth events, or the counting metrics. It does not define the detection or tracking schemas. It introduces no new fields, no new enum values, no new thresholds, and no new policies. It does not change the `direction` enum from its existing entry-only definition, and it does not redesign or resolve the asymmetry between tracking `roi_crossings` and counting events.

- **Section 2: Annotation Rules (General)** — class labels, countable classes (this document)
- **Section 5: Ground Truth global_id Policy (Tracking Identity)** — identity assignment, immutability, class immutability (this document)
- **Section 6: Counting Event Policy** — ROI boundary, crossing condition, event fields, crossing confidence, duplicate prevention, derivation from tracking GT (this document)
- **Section 7.2, 7.6–7.9** — sampling units, train/val/test split, leakage prevention, gap and occlusion handling (this document)
- **Section 8.1: Data Schema** — schema architecture and cross-schema relationships (this document)
- **Section 8.2: Detection Ground Truth Schema** — per-frame projection of the same observations (this document)
- **Section 8.3: Tracking Ground Truth Schema** — identity-bearing input to counting events (this document)
- **Section 8.4.1: Counting Ground Truth Schema** — purpose and scope of this schema (this document)
- **Section 8.4.2: Counting Ground Truth Field Semantics** — per-field meaning and source policy (this document)
- **Section 8.4.3: Counting Ground Truth Validation Semantics** (this document)

---

#### 8.4.3 Counting Ground Truth Validation Semantics

**Purpose and scope.**

This subsection states how a counting ground truth record is checked for well-formedness before it enters evaluation. It restates the constraints already present in the authoritative JSON schema, paired with the counting-event semantics established in Sections 5 and 6, so that a validator and an annotator read the same contract. It does not add new fields, new enum values, new thresholds, or new validation rules.

**Authoritative sources.**

- The JSON schema (`annotation/schema/counting_ground_truth.schema.json`) is authoritative for field names, required-vs-optional, types, patterns, and numeric ranges.
- Section 5 is authoritative for `global_id` policy.
- Section 6 is authoritative for counting-event derivation, the crossing condition, and `crossing_confidence`.
- Section 7 is authoritative for which frames are sampled and how they are split.

**Required versus optional top-level fields.**

At the top level, every counting ground truth record must carry exactly five required fields: `video_id`, `roi_polygon`, `countable_classes`, `events`, and `total_counts`. No other top-level field is permitted.

All five are required. The schema enforces no optional top-level field.

**Required versus optional event fields.**

Every element of `events` must carry exactly nine required fields: `event_id`, `global_id`, `class`, `frame_id`, `timestamp`, `roi_point`, `direction`, `bbox_at_crossing`, and `crossing_confidence`. No other per-event field is permitted, and no per-event field may be dropped.

There are no optional fields at the event level. Within the schema, a field is either present and required, or it is not part of the schema at all.

**Types, ranges, patterns, and enums.**

- `video_id` must be a string.
- `roi_polygon` must be an array of exactly four vertices; each vertex is an array of exactly two integers.
- `countable_classes` must be an array of strings, each from the class enum.
- `events` must be an array of event objects.
- `total_counts` must be an object whose keys are drawn from the five class names.
- `event_id` must be an integer, minimum 1.
- `global_id` must be a string matching the pattern `^GT_\d{3}$`.
- `class` must be a string from the enum: `car`, `motorcycle`, `bus`, `truck`, `person`.
- `frame_id` must be an integer in the range 0–620.
- `timestamp` must be a number in the range 0.0–41.4.
- `roi_point` must be an array of exactly two numbers.
- `direction` must be a string from the enum `["entry"]`.
- `bbox_at_crossing` must be an array of exactly four integers, each in the range 0–1019.
- `crossing_confidence` must be a string from the enum `["high", "medium", "low"]`.
- Each `total_counts` value must be an integer, minimum 0.

**event_id uniqueness and structure.**

The schema constrains `event_id` to an integer with minimum 1; it does not itself enforce uniqueness or ordering. Uniqueness is a protocol-level requirement supported by Section 6.4, which defines `event_id` as a sequential unique identifier (1, 2, 3...) assigned to each counting event. Two events sharing the same `event_id` would be indistinguishable as records and are not permitted under that protocol.

The schema also does not require `event_id` values to be contiguous or to start at 1. A validator checks the type and minimum; contiguity is a convention of the derivation process, not a schema constraint.

**global_id consistency with Tracking GT.**

Every event's `global_id` must match the pattern `^GT_\d{3}$`, which the schema enforces. Beyond the pattern, the schema cannot verify that the identifier exists in Tracking GT, because the two files are separate. That check is a protocol-level consistency requirement supported by Section 6.6 and 6.8: counting events are derived from tracking GT, so every `global_id` in counting GT must reference a track in Tracking GT, and every countable track that entered the ROI must have exactly one event.

The schema also does not enforce the one-entry-per-`global_id` rule. That rule belongs to Section 6.4 (Duplicate-Event Prevention) and is a protocol-level requirement, not a schema constraint.

**frame_id/timestamp consistency.**

`timestamp` is derived, not independent: it must equal `frame_id / 15.0`. An event whose `timestamp` does not match its `frame_id` at the video's 15 FPS is malformed, regardless of whether the value falls inside the permitted 0.0–41.4 range. The schema enforces the ranges on both fields separately; the derivation relationship is a protocol-level requirement consistent with the rule applied in every other schema.

The schema also constrains `frame_id` to 0–620. The protocol further requires that the crossing frame be a sampled frame, because counting events are derived from track observations that exist only at sampled frames (Section 7.2). The schema cannot verify sampling, so this is a protocol-level consistency requirement.

**bbox_at_crossing and roi_point consistency with the crossing observation.**

The schema constrains `bbox_at_crossing` to four integers in 0–1019 and `roi_point` to two numbers; it does not relate them to any other data. The consistency requirement is protocol-level and supported by Section 6.6: `bbox_at_crossing` must equal the referenced track observation's `bbox` at the crossing `frame_id`, and `roi_point` must equal the bottom-center point `[cx, y2]` derived from that same `bbox`, where `cx = (x1+x2)/2` and `y2` is the box's bottom edge.

An event is consistent with Tracking GT only where both hold, because counting GT is derived from tracking GT and is not annotated independently.

**direction consistency with the authoritative schema.**

The schema defines `direction` as an enum of `["entry"]`. Every event's `direction` must therefore be `"entry"`. This is the existing, unchanged definition: the current pipeline represents outside → inside the ROI crossings only.

The schema does not permit `"exit"`. An `exit` crossing is recorded in Tracking GT's optional `roi_crossings` array (which permits `entry` and `exit`) but has no counterpart in counting GT. That asymmetry is a property of the two schemas and is preserved here, not converted into a validation error. A counting record containing a `direction` value outside the enum is a schema violation; a tracking record containing an `exit` is not.

**crossing_confidence consistency with Section 6.3.1.**

The schema constrains `crossing_confidence` to the enum `["high", "medium", "low"]`. The assignment of the value is governed by the deterministic rule in Section 6.3.1, which computes the score from the observable fields at the crossing frame — `visibility`, `occlusion`, `truncated`, `difficult`, and bbox geometry — with explicit AND/OR conditions for each tier. No annotator judgment is involved.

The schema cannot verify that the recorded score matches the rule, because it does not have access to the crossing observation's fields. That check is a protocol-level consistency requirement: the score must be the value the rule produces for the crossing observation referenced by the event's `global_id` and `frame_id`.

**total_counts consistency with the events and counting policy.**

The schema constrains `total_counts` to an object whose values are non-negative integers, and it permits any subset of the five class keys — including none. It does not require all five keys to be present, and it does not require the values to match the events.

The consistency requirement is protocol-level and supported by Section 6.6: `total_counts` is the aggregation of the `events` array by `class`. For each of the five countable classes, the recorded value must equal the number of events in `events` whose `class` is that class. A class that has no events may be omitted from `total_counts` or recorded as 0; both are consistent with the aggregation. A value that disagrees with the event count is an annotation error, not a design choice.

**additionalProperties and schema authority.**

Both the top level and the event level enforce `additionalProperties: false`. No field beyond those listed above may appear in the record or in an event object. A field that is not in the schema cannot be validated, because the schema is the only definition of what the data may contain.

The schema is authoritative for field names, required-vs-optional, types, patterns, and numeric ranges. Where the schema is silent — for example on the derivation of `timestamp` from `frame_id`, on the relationship between `bbox_at_crossing` and the track observation, or on the aggregation behind `total_counts` — the annotation policy in Sections 5–7 fills the gap, and the schema's type and range checks are the enforcement point.

This subsection does not define a validator, a checker, or a set of acceptance thresholds. It documents the constraints that any validator must enforce.

**What this subsection does not define.**

This subsection restates schema constraints and the consistency requirements already supported by Sections 5–7. It does not define how counting predictions are scored against this ground truth, how predicted events are matched to ground-truth events, or the counting metrics. It does not define the detection or tracking schemas. It introduces no new fields, no new enum values, no new thresholds, and no new rules. It does not change the `direction` enum from its existing entry-only definition, and it does not redesign or resolve the asymmetry between tracking `roi_crossings` and counting events.

- **Section 5: Ground Truth global_id Policy (Tracking Identity)** — identity assignment and immutability (this document)
- **Section 6: Counting Event Policy** — ROI boundary, crossing condition, event fields, crossing confidence, duplicate prevention, derivation from tracking GT (this document)
- **Section 7.2, 7.6–7.9** — sampling units, train/val/test split, leakage prevention, gap and occlusion handling (this document)
- **Section 8.1: Data Schema** — schema architecture and cross-schema relationships (this document)
- **Section 8.2: Detection Ground Truth Schema** — per-frame projection of the same observations (this document)
- **Section 8.3: Tracking Ground Truth Schema** — identity-bearing input to counting events (this document)
- **Section 8.4.1: Counting Ground Truth Schema** — purpose and scope of this schema (this document)
- **Section 8.4.2: Counting Ground Truth Field Semantics** — per-field meaning and source policy (this document)
- **Section 8.4.3: Counting Ground Truth Validation Semantics** (this document)
- **Section 8.5: Sampling Manifest Schema** (this document)

---

### 8.5 Sampling Manifest Schema

This subsection defines the Sampling Manifest schema: what it represents, how it relates to the annotation policies in Sections 1–7, and how it relates to the other three ground-truth schemas. It defines the schema's purpose and scope only. Detailed field definitions belong to later subsections and are not introduced here.

#### 8.5.1 Purpose and Scope

**Purpose of the Sampling Manifest.**

The Sampling Manifest is the record of which frames were sampled for annotation and why. It is the index of the frame domain that the three ground-truth schemas cover: Detection Ground Truth exists only for sampled frames, Tracking Ground Truth observations exist only at sampled frames, and Counting Ground Truth events exist only at sampled crossing frames. The manifest records the asymmetry between the sampled annotation domain and the full source video — the production pipeline processes every source frame at full rate, while the ground-truth schemas cover the sampled subset (Section 7.1).

Its purpose is to make the sampling decision explicit and reproducible. Each sample record carries the frame it identifies, the dataset split it belongs to, the reason it was sampled, and the traffic-density and difficulty strata assigned to it. Together these records state what the annotation domain is, so that evaluation can be scoped correctly and so that the sampling can be regenerated from the rules in Section 7.

**Relationship to the other three schemas.**

The Sampling Manifest is orthogonal to the Detection, Tracking, and Counting schemas. It records which frames were sampled, not what was annotated on them. It is the index of the frame domain, and the other three schemas are the content within that domain.

- **Manifest → Detection.** Detection GT records exist only for sampled frames. A frame that is not sampled has no Detection GT record, and a Detection GT record must correspond to a sampled frame recorded in the manifest.
- **Manifest → Tracking.** Tracking GT observations exist only at sampled frames, with gaps at unsampled frames. A track observation's `frame_id` must be a sampled frame.
- **Manifest → Counting.** Counting GT events exist only at sampled crossing frames. A crossing that occurs at an unsampled frame has no counting event, because there is no track observation at that frame from which the event could be derived (Section 7.2).

The manifest does not annotate objects, geometry, identity, or crossings. Those belong to the other three schemas.

**Relationship to Section 7 — Temporal Sampling Protocol.**

The Sampling Manifest is the machine-readable output of the sampling rules defined in Section 7. Section 7.2 defines the sampling units and frame indexing; Section 7.3 defines baseline keyframe sampling; Section 7.4 defines event-boosted sampling; Section 7.5 defines the stratified sampling criteria; Section 7.6 defines the temporal train/val/test split; and Section 7.11 defines the manifest requirements themselves. Every sample record in the manifest is produced by applying those rules, and the `sampling_reason` recorded on each sample states which rule produced it.

The manifest is not an independent annotation. It is a derived record of the sampling decision, and it must agree with the rules in Section 7. Where the manifest and the rules disagree, the rules are authoritative and the manifest is wrong.

**Distinction from production pipeline outputs.**

The Sampling Manifest describes the ground-truth annotation domain. It is not a production pipeline output and must not be confused with one.

The production pipeline (YOLOv8m + ByteTrack + Entity Association + ROI Counting) processes every source frame at full rate and produces per-frame detections, tracker `track_id`s, and predicted counting events. The manifest records which frames the annotator covered. The pipeline's frame coverage is complete; the manifest's coverage is the sampled subset. The manifest records this asymmetry, it does not create it (Section 7.1).

The manifest is fixed once produced and does not change when the pipeline is re-run. It is the record of a sampling decision made during annotation, not a measurement of the system under test.

**Field semantics and validation rules are deferred.**

This subsection defines the purpose and scope of the Sampling Manifest only. It does not define individual field semantics, required-field lists, enum values, or validation rules for the schema; those belong to later subsections and are not introduced here. The field-level meaning of `video_id`, `total_frames`, `fps`, `base_interval`, and the sample-record fields — `sample_id`, `frame_id`, `timestamp`, `split`, `sampling_reason`, `event_type`, `traffic_density`, and `difficulty` — and the well-formedness constraints on them, are deferred to later 8.5 subsections.

**What this subsection does not define.**

This subsection defines the purpose and scope of the Sampling Manifest. It does not define how annotations are produced on the sampled frames, how the sampling rules are applied in detail, or how the manifest is regenerated. It does not define the detection, tracking, or counting schemas. It introduces no new fields, no new enum values, no new thresholds, and no new policies beyond those already present in the schema and in Sections 1–7.

- **Section 7.1–7.6, 7.11** — sampling units, baseline and event-boosted sampling, stratification, train/val/test split, manifest requirements (this document)
- **Section 8.1: Data Schema** — schema architecture and cross-schema relationships (this document)
- **Section 8.2: Detection Ground Truth Schema** — per-frame content of sampled frames (this document)
- **Section 8.3: Tracking Ground Truth Schema** — per-object content of sampled frames (this document)
- **Section 8.4: Counting Ground Truth Schema** — event content of sampled frames (this document)
- **Section 8.5.1: Sampling Manifest Purpose and Scope** (this document)

---

#### 8.5.2 Sampling Manifest Field Semantics

This subsection documents the semantic meaning and role of the Sampling Manifest fields. The JSON schema (`sampling_manifest.schema.json`) is authoritative for field names and types; Sections 2 and 7 are authoritative for annotation and sampling semantics. No new fields are introduced.

**`video_id`**

Purpose: identifies the source video this manifest describes (e.g., `3.mp4`). It is the manifest-level key that binds the sampling configuration to one specific video, so that sampling data from different videos cannot be confused.

Governing policy: Section 2.1. It is recorded once at the top level and scopes every sample record and every derived sampling decision in the file.

Schema meaning: string.

**`total_frames`**

Purpose: the total number of source frames in the video (621 for `3.mp4`). It defines the full frame domain against which sampling coverage is measured — the denominator of the sampled subset.

Governing policy: Section 2.2 (Frame Referencing). It states the extent of the source domain; the sampled set recorded in `samples` is a subset of the frames 0 to `total_frames - 1`.

Schema meaning: integer.

**`fps`**

Purpose: the video frame rate (15 for `3.mp4`). It is the conversion factor between frame counts and durations, and it governs how frame-based thresholds are interpreted in time.

Governing policy: Section 2.2. The 30-frame short-gap threshold (Section 5.3) and the 5-frame baseline interval (Section 7.3) are both expressed in frames and are understood through this rate. It is also the divisor used to derive `timestamp` from `frame_id` on every sample record.

Schema meaning: number.

**`base_interval`**

Purpose: the baseline sampling interval in frames (5). It records the protocol parameter that governs baseline keyframe sampling, stored in the manifest so that the baseline grid is reconstructable without consulting this document.

Governing policy: Section 7.3 (Baseline Keyframe Sampling). It is the parameter applied by the `f mod interval == 0` rule.

Status: optional. A manifest may omit it, in which case the baseline configuration is not recorded in the file.

Schema meaning: integer.

**Sample-record fields**

Each element of `samples` is one sampled frame. Its fields record one property of that single sampling decision.

**`sample_id`**

Purpose: the manifest's own key for the sample, independent of `frame_id`. Format `S_XXXX` (zero-padded 4-digit). It exists so that a sample can be referenced by annotation tooling, audit scripts, and evaluation code without depending on frame indexing.

Governing policy: Section 7.4. It is assigned in the order samples are recorded and is unique across the manifest.

Relationship to identity: `sample_id` and `frame_id` refer to the same sampling decision from different directions — `frame_id` identifies the source frame, `sample_id` identifies the sampling record. They are not interchangeable.

Schema meaning: string matching the pattern `^S_\d{4}$`.

**`frame_id`**

Purpose: the 0-based index of the source frame (0–620 for `3.mp4`). It binds the sample to a specific source frame and is the key that joins the sample to the Detection GT record, the Tracking GT observations, and the Counting GT events for that frame.

Governing policy: Section 2.2 and Section 7.2. Sampling does not renumber frames; a sample with `frame_id = f` refers to the same source frame the production pipeline processes at `frame_id = f`.

Relationship to identity: `frame_id` is unique across the manifest's `samples` array — each frame is sampled at most once (Section 7.4), which is the manifest-level reflection of one-frame-one-partition (Section 7.7).

Schema meaning: integer, minimum 0, maximum 620.

**`timestamp`**

Purpose: the frame's timestamp in seconds, derived as `frame_id / fps`. It is recorded rather than independently assigned so that time and frame identity cannot drift apart.

Governing policy: Section 2.2. The relationship is one-way: `frame_id` determines `timestamp`. Because `frame_id` is immutable, `timestamp` is immutable too.

Relationship to identity: `timestamp` is meaningful only within the video named by `video_id`; it may not be used to re-identify a frame across videos.

Schema meaning: number, minimum 0, maximum 41.4.

**`split`**

Purpose: the dataset partition the sample belongs to — `train`, `val`, or `test`. It is the primary enforcement mechanism for leakage prevention (Section 7.7): every frame must belong to exactly one partition.

Governing policy: Section 7.6 (Temporal Train/Val/Test Split). It is assigned by the deterministic `split(frame_id)` rule, so it is a function of `frame_id` alone. Given the same `frame_id`, the same `split` is always produced; no shuffling, seed, or balancing changes it.

Relationship to identity: because `split` is a function of `frame_id` and `frame_id` is unique across the manifest, every sample belongs to exactly one partition. No frame is duplicated across partitions and no downstream step may reassign a partition.

Schema meaning: string, enum `["train", "val", "test"]`.

**`sampling_reason`**

Purpose: the primary reason the frame was sampled. It connects the sample to the sampling protocol by naming the rule that selected it.

Governing policy: Section 7.3 and Section 7.4. The value `base_temporal` identifies a frame selected by the baseline grid; every event-based value identifies a frame selected by event boosting. The event-based vocabulary is: `roi_crossing`, `entry_event`, `exit_event`, `post_occlusion_appearance`, `pre_occlusion_disappearance`, `severe_occlusion`, `ambiguous_identity`, `class_ambiguity`, `high_density`.

Relationship to identity: when a frame is selected by both baseline sampling and event boosting, it is sampled once and its `sampling_reason` records the event-based reason, because event reasons take precedence over `base_temporal` (Section 7.4, 7.10.2). The manifest supports exactly one primary `sampling_reason` per sample.

Schema meaning: string, enum of the ten values above.

**`traffic_density`**

Purpose: the traffic-density stratum for the frame — `low`, `medium`, or `high`. A protocol-defined label used to audit dataset balance and to report metrics per stratum.

Governing policy: Section 7.5 (Stratified Sampling Criteria). It is a category assigned to sampled frames, not a measurement of the video.

Schema meaning: string, enum `["low", "medium", "high"]`.

**`difficulty`**

Purpose: the overall frame difficulty stratum — `easy`, `moderate`, or `hard`. A protocol-defined label used for the same audit and stratification purposes as `traffic_density`.

Governing policy: Section 7.5. It is a category assigned to sampled frames, not a measurement of the video.

Schema meaning: string, enum `["easy", "moderate", "hard"]`.

**`event_type` (optional)**

Purpose: the specific event type that motivated an event-based sample, complementing the broader `sampling_reason`. Values: `none`, `roi_crossing`, `entry`, `exit`, `occlusion_start`, `occlusion_end`, `high_density`, `ambiguous`.

Governing policy: Section 7.4 and Section 7.10.2 (event categories E1–E7). It is meaningful only when `sampling_reason` is event-based; it is set to `none` otherwise.

Relationship to identity: `event_type` refines `sampling_reason` but is not interchangeable with it. `sampling_reason` records the sampling rule; `event_type` records the event. Not every `sampling_reason` maps to a distinct `event_type`.

Status: optional. It is recorded only when applicable.

Schema meaning: string, enum of the eight values above.

**Consistency with the protocol.**

The fields are consistent with Sections 2 and 7: `frame_id` and `timestamp` preserve source-frame identity (Section 7.2); `sampling_reason` records the sampling mode established in Sections 7.3 and 7.4, including the precedence rule that event-based reasons take precedence over `base_temporal` when both apply; `split` records the partition assigned by the deterministic rule in Section 7.6, and the one-`sample_id`-per-`frame_id` property means each `frame_id` appears at most once, enforcing one-frame-one-partition (Section 7.7); `traffic_density` and `difficulty` record the strata defined in Section 7.5; and `base_interval` records the baseline protocol parameter (Section 7.3), supporting reproducibility as described in Section 7.11.1.

**Validation rules are deferred.**

This subsection documents the meaning and source policy of the existing fields. It does not define required-field lists, field ordering, enum values beyond those already established in Sections 2 and 7, or validation rules; those belong to the later 8.5.3 subsection and are not introduced here.

**What this subsection does not define.**

This subsection documents field semantics only. It does not define how the manifest is generated, how samples are validated against the schema, or how the manifest is regenerated when a protocol parameter changes. It does not define the detection, tracking, or counting schemas. It introduces no new fields, no new enum values, no new thresholds, and no new policies beyond those already present in the schema and in Sections 1–7.

- **Section 2: Annotation Rules (General)** — class labels, frame referencing, coordinate system (this document)
- **Section 7.1–7.6, 7.11** — sampling units, baseline and event-boosted sampling, stratification, train/val/test split, manifest requirements (this document)
- **Section 8.1: Data Schema** — schema architecture and cross-schema relationships (this document)
- **Section 8.2: Detection Ground Truth Schema** — per-frame content of sampled frames (this document)
- **Section 8.3: Tracking Ground Truth Schema** — per-object content of sampled frames (this document)
- **Section 8.4: Counting Ground Truth Schema** — event content of sampled frames (this document)
- **Section 8.5.2: Sampling Manifest Field Semantics** — per-field meaning and source policy (this document)

#### 8.5.3 Sampling Manifest Validation Semantics

**Purpose and scope.**

This subsection states how a sampling manifest record is checked for well-formedness before it is accepted as the record of a sampling decision. It restates the constraints already present in the authoritative JSON schema, paired with the sampling and reproducibility semantics established in Sections 7.11 and 7.12, so that a validator and an annotator read the same contract. It does not add new fields, new enum values, new thresholds, or new validation rules.

**Authoritative sources.**

- The JSON schema (`annotation/schema/sampling_manifest.schema.json`) is authoritative for field names, required-vs-optional, types, patterns, and numeric ranges.
- Section 7.11 is authoritative for manifest requirements and consistency with the sampling protocol.
- Section 7.12 is authoritative for reproducibility, preservation, and regeneration conditions.

**Distinction between schema validation and protocol consistency validation.**

Schema validation answers whether the record conforms to the JSON schema. Protocol consistency validation answers whether the manifest correctly represents the authoritative Section 7 sampling protocol. Schema conformance is necessary but not sufficient: a manifest may pass schema validation and still violate the protocol, because the schema cannot observe sampling decisions, partition assignments, or event membership. The two checks are separate and both are required.

### Schema Validation

**Required versus optional top-level fields.**

At the top level, every sampling manifest record must carry exactly four required fields: `video_id`, `total_frames`, `fps`, and `samples`. No other top-level field is permitted.

`base_interval` is the only optional top-level field. A manifest may omit it, in which case the baseline configuration is not recorded in the file.

**Required versus optional sample-record fields.**

Every element of `samples` must carry exactly seven required fields: `sample_id`, `frame_id`, `timestamp`, `split`, `sampling_reason`, `traffic_density`, and `difficulty`. No other per-sample field is permitted, and no per-sample field may be dropped.

`event_type` is the only optional per-sample field. It is recorded only when applicable.

**Types, patterns, ranges, and enums.**

- `video_id` must be a string.
- `total_frames` must be an integer.
- `fps` must be a number.
- `base_interval`, when present, must be an integer.
- `samples` must be an array of sample-record objects.
- `sample_id` must be a string matching the pattern `^S_\d{4}$`.
- `frame_id` must be an integer in the range 0–620.
- `timestamp` must be a number in the range 0.0–41.4.
- `split` must be a string from the enum `["train", "val", "test"]`.
- `sampling_reason` must be a string from the enum: `base_temporal`, `roi_crossing`, `entry_event`, `exit_event`, `post_occlusion_appearance`, `pre_occlusion_disappearance`, `high_density`, `severe_occlusion`, `ambiguous_identity`, `class_ambiguity`.
- `event_type`, when present, must be a string from the enum: `none`, `roi_crossing`, `entry`, `exit`, `occlusion_start`, `occlusion_end`, `high_density`, `ambiguous`.
- `traffic_density` must be a string from the enum `["low", "medium", "high"]`.
- `difficulty` must be a string from the enum `["easy", "moderate", "hard"]`.

**sample_id uniqueness and assignment order.**

The schema constrains `sample_id` to the pattern `^S_\d{4}$`; it does not itself enforce uniqueness across the `samples` array. Uniqueness is a protocol-level requirement supported by Section 7.4, which defines `sample_id` as an identifier assigned in the order samples are recorded. Two records sharing the same `sample_id` would be indistinguishable as records and are not permitted under that protocol.

The schema also does not require `sample_id` values to be contiguous or to start at `S_0001`. Contiguity is a convention of the recording process, not a schema constraint.

**frame_id and timestamp ranges.**

The schema constrains `frame_id` to the integer range 0–620 and `timestamp` to the numeric range 0.0–41.4. These ranges state the extent of the source frame domain for `3.mp4` (Section 2.2). A value outside either range is a schema violation.

**additionalProperties behavior.**

Both the top level and each sample-record object enforce `additionalProperties: false`. No field beyond those listed above may appear in the record or in a sample object. A field that is not in the schema cannot be validated, because the schema is the only definition of what the data may contain.

The schema is authoritative for field names, required-vs-optional, types, patterns, and numeric ranges. Where the schema is silent — for example on the derivation of `timestamp` from `frame_id`, on the relationship between `sampling_reason` and `event_type`, or on the aggregation of the sampled set — the annotation policy in Sections 2 and 7 fills the gap, and the schema's type, pattern, range, and enum checks are the enforcement point.

### Protocol Consistency Validation

Protocol consistency validation checks that the manifest correctly represents the authoritative Section 7 sampling protocol. Every requirement below is a consequence of a rule already established; none is new.

**Schema validation is necessary but not sufficient.**

A manifest may pass every schema check above and still be inconsistent with the protocol. The consistency requirements in this subsection close that gap. They are not enforced by the schema, because the schema cannot observe sampling decisions, partition assignments, or event membership.

**Consistency with baseline sampling (Section 7.3).**

Every sample whose `sampling_reason` is `base_temporal` must satisfy the baseline rule: its `frame_id` must be a multiple of the baseline interval. The interval is recorded in the manifest as `base_interval` (5 for `3.mp4`). A sample with `sampling_reason = "base_temporal"` and `frame_id mod base_interval ≠ 0` is inconsistent with Section 7.3.

The manifest must not contain a `base_temporal` sample at a `frame_id` that the baseline rule would not select. Conversely, a frame that the baseline rule selects is not required to appear with `sampling_reason = "base_temporal"`: if event boosting also selects it, it appears with the event-based reason instead (Section 7.4). The consistency requirement is directional — a `base_temporal` sample must be baseline-eligible, not that every baseline-eligible frame must be a `base_temporal` sample.

**Consistency with event-boosted sampling (Section 7.4, 7.10.2).**

Every sample whose `sampling_reason` is event-based must correspond to an event established in Sections 7.4 and 7.10.2. The event-based reasons are: `roi_crossing`, `entry_event`, `exit_event`, `post_occlusion_appearance`, `pre_occlusion_disappearance`, `severe_occlusion`, `ambiguous_identity`, `class_ambiguity`, `high_density`. A sample with an event-based reason must have an `event_type` that is consistent with that reason, and the event must be one the protocol recognizes.

When a frame is selected by both baseline sampling and event boosting, the manifest records it once with the event-based `sampling_reason`, because event reasons take precedence over `base_temporal` (Section 7.4). The manifest must not contain two records for the same `frame_id`; this is enforced by the uniqueness of `sample_id` and `frame_id` at the schema level and is restated here as a protocol requirement.

**Consistency with the train/val/test split (Section 7.6).**

Every sample's `split` must equal the result of the deterministic `split(frame_id)` rule:

- `frame_id` in [0, 249] → `train`
- `frame_id` in [250, 374] → `val`
- `frame_id` in [375, 499] → `test`

No sample may have a `split` that disagrees with its `frame_id`. Because `split` is a pure function of `frame_id`, and `frame_id` is unique across the manifest, every frame belongs to exactly one partition. This is the manifest-level enforcement of one-frame-one-partition (Section 7.7): no frame may appear in more than one partition, and no sample may be reassigned to a different partition.

Frames 500–620 are unassigned (Section 7.6.1) and must not appear in the manifest with any `split` value. Their absence from the manifest is itself a consistency requirement: the manifest's sampled set must be a subset of the assigned frame domain 0–499.

**Consistency with leakage prevention (Section 7.7).**

The manifest must support the leakage-prevention guarantees. Specifically:

- Each `frame_id` appears at most once, so no frame is duplicated across partitions.
- The `split` field on every sample allows the evaluation scripts to verify that no val/test frame was used in training.
- Event-boosted windows are clipped at partition boundaries (Section 7.7): a sample selected by event boosting near a boundary must lie within the event's own partition. The manifest's `frame_id` and `split` together allow this to be checked, because any sample whose `frame_id` falls outside its event's partition would indicate a window that was not clipped.

**Consistency with deterministic dataset construction (Section 7.11.1, 7.12.1).**

Reproducibility requires that the manifest, together with the Ground Truth annotations it describes, can regenerate the same evaluation dataset and the same metrics. For this to hold:

- The manifest must record the deterministic inputs to sampling: `base_interval` for the baseline grid, `sampling_reason` for the rule that selected each sample, and `split` for the partition assignment. Given these, the sampling configuration is reconstructable.
- The manifest must be preserved alongside the dataset it describes. Without it, the sampling configuration is lost and the metrics cannot be regenerated or meaningfully compared.
- If a protocol parameter changes (for example, `base_interval` or the event-boosted window size), the manifest must be regenerated so that it reflects the configuration actually used. A manifest that records a stale parameter is inconsistent with the dataset it describes, even if it passes schema validation.

The manifest does not guarantee annotation quality. It records which frames were sampled, not how well they were annotated; inter-annotator agreement and annotation correctness are assessed separately (Sections 11, 15).

**Manifest preservation and regeneration consistency (Section 7.12.3, 7.12.4).**

The manifest is the record of the sampling configuration and must be preserved with the dataset it describes. Specifically:

- The manifest must be stored alongside the Ground Truth annotations and the evaluation dataset, in a location that keeps them associated.
- The manifest must be preserved in machine-readable form. It is the authoritative statement of which frames were sampled, why, and into which partition.
- The manifest must not be edited after the dataset is finalized except through a full regeneration. Post-hoc edits to the manifest would break its consistency with the Ground Truth it describes.

Regeneration is required when an already-established source, protocol, or schema condition changes: the source video changes (`video_id`, `total_frames`, `fps`); a protocol parameter changes (`base_interval`, the event-boosted window size, the partition boundaries, or the stratum thresholds); the protocol version changes; or the schema version changes. Regeneration is not required when only annotation content changes or only evaluation code changes, because neither alters which frames were sampled.

**Asymmetry between tracking and counting schemas.**

This subsection does not redesign the existing relationship between the Tracking GT and Counting GT schemas. Tracking GT's optional `roi_crossings` array may contain `entry` and `exit`; Counting GT's `direction` is `entry` only. Sampling Manifest validation concerns the manifest alone and does not convert that asymmetry into a validation error or resolve it.

**What this subsection does not define.**

This subsection restates schema constraints and the consistency requirements already supported by Sections 7.11 and 7.12. It does not define the manifest's JSON record structure, field ordering, or the exact validation scripts that enforce these checks. It does not define how the manifest is generated, how samples are validated against the schema in practice, or how the manifest is regenerated when a protocol parameter changes beyond the requirement that it be regenerated. It does not introduce new sampling reasons, event categories, strata, or thresholds. It does not modify the sampling manifest schema.

- **Section 2: Annotation Rules (General)** — class labels, frame referencing, coordinate system (this document)
- **Section 7.1–7.6, 7.11** — sampling units, baseline and event-boosted sampling, stratification, train/val/test split, manifest requirements (this document)
- **Section 7.11.4: Manifest Validation and Consistency** — the protocol-level consistency rules restated above (this document)
- **Section 7.12: Reproducibility Requirements** — deterministic inputs, preservation, and regeneration conditions (this document)
- **Section 8.1: Data Schema** — schema architecture and cross-schema relationships (this document)
- **Section 8.2: Detection Ground Truth Schema** — per-frame content of sampled frames (this document)
- **Section 8.3: Tracking Ground Truth Schema** — per-object content of sampled frames (this document)
- **Section 8.4: Counting Ground Truth Schema** — event content of sampled frames (this document)
- **Section 8.5.1: Sampling Manifest Schema** — purpose and scope of this schema (this document)
- **Section 8.5.2: Sampling Manifest Field Semantics** — per-field meaning and source policy (this document)
- **Section 8.5.3: Sampling Manifest Validation Semantics** (this document)

### 8.6 Annotation Tool Decision Boundary

**Status:** 8.6 complete (decision-boundary amendment only).

**Purpose and scope.**

This subsection defines the boundary between three distinct categories of
protocol text, so that a future reader can tell them apart:

1. **Existing annotation / data-contract requirements** — rules already
   established in Sections 1–8.5. These are authoritative and enforceable.
2. **Annotation-tool selection decisions** — decisions that have not yet
   been made. These are recorded here as OPEN or DEFERRED so that no later
   task can mistake an unspecified capability for an authorized protocol
   rule.
3. **Future workflow decisions** — decisions belonging to later protocol
   tasks (Sections 9–13). These are recorded here as DEFERRED only.

This subsection does NOT select an annotation tool. It does NOT recommend a
tool. It does NOT authorize any annotation software. It does NOT define how
annotations are produced; Section 8.1 already states that schemas "do not
define how annotations are produced; they define what valid annotation
output looks like." This subsection adds no new annotation semantics, no
new data fields, and no new validation rules.

**A. Existing mandatory constraints (restated, not newly invented).**

The following are already required by the protocol and remain in force.
They are restated here so that tool evaluation has a single reference point.
Every item below traces to an existing section; none is a new requirement.

- **Frame identity preservation.** `frame_id` is the 0-based source-frame
  index (0–620) and is not renumbered by sampling (Section 2.2, 7.2). A tool
  must preserve the source `frame_id` of every observation it records.
- **Sampled-frame restriction.** Annotation exists only on sampled frames
  (Section 7.2, 7.11.1, 8.3.1). A frame not present in the Sampling Manifest
  is not sampled and is not annotated.
- **Coordinate preservation.** Every bbox is `[x1, y1, x2, y2]` in the
  1020×500 integer coordinate space, origin top-left (Section 2.1, 3.1).
- **Manual `global_id` identity.** `global_id` is assigned by the
  annotator, is immutable across the entire video, and uses the `GT_XXX`
  format (Section 5.2.1, 8.3.1).
- **Required annotation fields.** Every observation must carry `frame_id`,
  `timestamp`, `bbox`, `visibility`, `occlusion`, `truncated`, and `center`
  (Section 8.3.3). Every track must carry `global_id`, `class`, `frames`,
  `start_frame`, `end_frame`, `start_timestamp`, and `end_timestamp`.
- **Prohibition of interpolation.** No bbox is created, interpolated, or
  extrapolated for a fully invisible frame. A gap in the `frames` array is
  a literal gap and is not filled (Section 7.9.2, 7.9.4, 7.9.5).
- **Prohibition of model/tracker-derived Ground Truth.** No Ground Truth
  schema contains model output, and no model output is validated against a
  Ground Truth schema (Section 8.1, 8.2.1). Detection Ground Truth source
  is human annotation; model output is the system under test.
- **Derived-field semantics.** `timestamp`, `center`, `truncated`,
  `start_frame`, `end_frame`, `start_timestamp`, `end_timestamp`, and
  `roi_crossings` are derived, never independently annotated (Section 2.2,
  3.3, 6.6, 8.3.3).
- **Final schema validation.** Every artifact must pass Layer 1 (JSON
  Schema) and, where applicable, Layer 2 (protocol consistency)
  validation before it enters evaluation (Section 8.3.3).

**B. Existing prohibitions (restated, not newly invented).**

The following are already forbidden by the protocol and remain in force.
None is weakened by this subsection.

- No annotation of unsampled frames (Section 7.2, 7.11.1, 8.3.1).
- No annotation of the currently unassigned frames 500–620 (Section 7.6.1).
- No automatic `global_id` assignment (Section 5.2.1, 8.3.3: "Continuity is
  not inferred by the schema; it is asserted by the annotator").
- No use of ByteTrack `track_id` as Ground Truth identity; the two identity
  spaces must never be conflated (Section 5.1, 8.3.1).
- No use of YOLO or ByteTrack model output as authoritative Ground Truth
  (Section 8.1, 8.2.1).
- No interpolation or extrapolation of bounding boxes (Section 7.9.2,
  7.9.4, 7.9.5).
- No independent manual annotation of ROI crossings; they are derived from
  the track's bottom-center trajectory (Section 6.6, 8.3.3).
- No independent annotation of Detection Ground Truth; it is the per-frame
  projection of Tracking Ground Truth (Section 8.2.1).
- No independent annotation of Counting Ground Truth; it is derived
  algorithmically from Tracking Ground Truth geometry (Section 6.6, 8.4.1).

**C. OPEN DECISIONS — not currently specified by the protocol.**

The following decisions are unresolved. They are recorded here so that no
future task treats an unspecified capability as authorized. None is
decided by this subsection.

| ID | Open decision | Status |
|----|---------------|--------|
| O1 | Annotation tool identity | OPEN — no tool is specified or authorized |
| O2 | Tool selection criteria | OPEN — no criteria are encoded in the protocol |
| O3 | Sampling Manifest integration mechanism | OPEN — how the manifest is supplied to the annotator is unspecified |
| O4 | Intermediary / export format | OPEN — the export *contract* is specified (Section 8.3.3); the export *path* is not |
| O5 | Custom converter authorization | OPEN — a converter is new production code and has no authorization |
| O6 | Evidence retention requirements | OPEN — no requirement to preserve tool-internal annotation state exists |
| O7 | Human correction workflow | OPEN — the protocol contemplates no correction workflow |
| O8 | Tool-side enforcement of the sampled-frame-only restriction | OPEN — the restriction is mandated; the enforcement mechanism is unspecified |
| O9 | `traffic_density` / `difficulty` assignment workflow | OPEN — the strata are defined (Section 7.5); the assignment procedure is not |
| O10 | Tool crash recovery / intermediate storage | OPEN — unspecified |
| O11 | Annotation authoring order | OPEN — the derivation dependency is specified; the authoring sequence is not |
| O12 | Tool-specific UI / interaction behavior | OPEN — no UI requirement exists in the protocol |

**D. DEFERRED DECISIONS — belonging to later protocol tasks.**

The following are explicitly deferred to later tasks. Their procedures are
not written here and must not be inferred from this subsection.

- Tool comparison — deferred to a future tool-selection task.
- Tool selection — deferred; no tool is selected by this protocol.
- Quality-control procedure — deferred to Section 10 (not yet written).
- Inter-annotator agreement procedure — deferred to Section 11 (not yet
  written).
- Pilot dataset definition — deferred to Section 9 (not yet written).
- Acceptance criteria — deferred to Section 13 (not yet written).

**E. Authorization boundary.**

Until the open decisions required for tool selection are resolved, no
annotation software is authorized as the project annotation tool. This
subsection does not name any candidate, does not imply that any existing
software is approved, and does not authorize the installation of any
annotation platform.

**F. Future selection rule.**

A future tool-selection task MAY evaluate candidate tools against the
existing constraints restated in Part A and Part B of this subsection,
once the decision boundary established here has been accepted. That task
must not define scoring weights, rank products, or recommend a specific
platform, and must not convert any OPEN decision into a requirement.

**What this subsection does not define.**

This subsection restates existing rules and records open and deferred
decisions. It does not select a tool, define an intermediary format, specify
a converter, define a correction workflow, define evidence-retention
requirements, define a UI, or define QC, IAA, pilot, or acceptance
procedures. It introduces no new annotation semantics, no new data fields,
no new enum values, no new thresholds, and no new validation rules. It does
not modify any JSON schema.

- **Section 2: Annotation Rules (General)** — class labels, frame referencing, coordinate system (this document)
- **Section 5: Ground Truth global_id Policy (Tracking Identity)** — identity assignment and immutability (this document)
- **Section 6: Counting Event Policy** — ROI-crossing derivation (this document)
- **Section 7: Temporal Sampling Protocol** — sampling, manifest, reproducibility (this document)
- **Section 8.1–8.5: Data Schema** — schema architecture and field semantics (this document)
- **Section 8.6: Annotation Tool Decision Boundary** (this document)

---

## 9 Evaluation Protocol

### 9.1 Purpose and Scope

**Purpose.**

This section defines the purpose and scope of the Evaluation Protocol. It establishes what the evaluation protocol governs and what it does not govern. It does not define evaluation metrics, formulas, thresholds, pass/fail criteria, benchmark procedures, statistical rules, confidence intervals, error categories, or implementation details. Those belong to later subsections only if explicitly requested.

**Scope.**

The Evaluation Protocol governs the comparison of production predictions against the established Ground Truth. It is the framework for interpreting, measuring, and reporting the quality of pipeline output relative to the annotated reference data.

**Ground Truth is the reference, and it is already defined.**

Evaluation is performed against the established Ground Truth. The Ground Truth is defined by Section 8 and is not redefined here:

- **Detection Ground Truth** — Section 8.2: per-frame object observations in sampled frames.
- **Tracking Ground Truth** — Section 8.3: identity-bearing observations keyed by `global_id`.
- **Counting Ground Truth** — Section 8.4: entry events derived from tracking geometry.
- **Sampling Manifest** — Section 8.5: the index of the sampled frame domain.

Evaluation consumes these definitions. It does not create competing definitions, and it does not reinterpret the fields, enums, ranges, or identity spaces that Sections 8.2–8.5 establish.

**Protocol definitions are authoritative.**

Evaluation must respect the protocol definitions already established in Sections 1–7. Those sections remain authoritative for annotation policy, bounding boxes, occlusion, identity, counting events, temporal sampling, partitioning, leakage prevention, ROI crossing, and reproducibility. Evaluation does not override, relax, or restate those rules; it applies them as written.

**Ground Truth and production predictions remain separate.**

Production predictions are produced by the production pipeline and remain separate from Ground Truth. Production output is not validated against a Ground Truth schema, and Ground Truth is not validated against a production schema. The two domains do not merge, and evaluation treats them as distinct inputs throughout.

**What this subsection does not define.**

This subsection defines only purpose and scope. It does not define metrics, formulas, thresholds, pass/fail criteria, benchmark procedures, statistical significance, confidence intervals, error categories, or implementation details. It does not change production inference behavior. It does not redefine any rule established in Sections 1–8.

### 9.2 Evaluation Inputs

**Purpose.**

This subsection identifies the categories of inputs that the evaluation process consumes. It separates those inputs into a Ground Truth domain and a production prediction domain, and it identifies the shared temporal context that links them. It does not define how the inputs are matched, scored, or compared.

**Ground Truth inputs.**

Ground Truth inputs are the annotated reference data defined by Section 8. Evaluation consumes them as fixed reference records; it does not modify them.

- **Detection Ground Truth** — Section 8.2: per-frame object observations in sampled frames, including class, bounding box, visibility, occlusion, truncated, and difficult.
- **Tracking Ground Truth** — Section 8.3: identity-bearing observations keyed by `global_id`, including per-frame observations, start and end frames, and ROI-crossing events.
- **Counting Ground Truth** — Section 8.4: entry events derived from tracking geometry, each referencing a `global_id` from Tracking Ground Truth, plus aggregated per-class totals.
- **Sampling Manifest** — Section 8.5: the index of the sampled frame domain, recording which frames belong to the dataset, their split, sampling reason, traffic density, and difficulty.

**Production prediction inputs.**

Production prediction inputs are the outputs of the production pipeline. They are produced independently of Ground Truth and are described only at the level already established by Sections 1–8.

- **Model detections** — per-frame object predictions produced by the production detector, corresponding in kind to the Detection Ground Truth observations.
- **Production tracking outputs** — identity-bearing predictions produced by the production tracker, keyed by the production `track_id`.
- **Production counting and event outputs** — counting events and predicted events produced at runtime by the production pipeline.

**Shared temporal context.**

Ground Truth inputs and production prediction inputs share a common temporal frame of reference, so that records from the two domains can be located within the same video. This context is defined by Sections 2 and 7.

- **`frame_id`** — frame index, 0–620, shared across all Ground Truth domains and consistent with production frame indexing.
- **`timestamp`** — derived as `frame_id / 15.0`, recorded so the two cannot drift.
- **Video identity** — the video identifier shared by Ground Truth records and production outputs.
- **Sampled-frame domain** — where applicable, the set of frames defined by the Sampling Manifest; Ground Truth exists only for sampled frames.

**Identity spaces remain separate.**

`global_id` and `track_id` are different identity spaces and are never equated. `global_id` is the Ground Truth identity defined by Section 8.3; `track_id` is the production identity produced by the production tracker. Evaluation treats them as distinct and does not merge them.

**The Sampling Manifest is a dataset-construction artifact.**

The Sampling Manifest is an input to evaluation only as a record of the sampled-frame domain. It is not runtime sampling control, not production inference configuration, not a prediction output, and not a model input that changes inference behavior.

**What this subsection does not define.**

This subsection identifies and separates input domains. It does not define matching, scoring, or comparison. It does not define IoU thresholds, confidence thresholds, matching thresholds, temporal tolerances, ID matching rules, precision, recall, mAP, MOTA, IDF1, HOTA, counting accuracy, F1, or pass/fail thresholds. It does not define benchmark procedures, statistical tests, confidence intervals, or error categories. It does not introduce new schema fields, new prediction fields, or new annotation policies. It does not redefine any rule established in Sections 1–8.

### 9.3 Detection Evaluation

#### 9.3.1 Purpose and Scope

**Purpose.**

This subsection defines the purpose and scope of detection evaluation. It establishes what detection evaluation governs and what it does not govern. It does not define detection metrics, matching rules, thresholds, formulas, or pass/fail criteria. Those belong to later subsections only if explicitly requested.

**Scope.**

Detection evaluation compares production detection outputs against Detection Ground Truth, within the frame domain established for evaluation. It is the framework for interpreting the quality of the production detector relative to the annotated reference data.

**Ground Truth is the reference, and it is already defined.**

Detection evaluation is performed against the Detection Ground Truth defined by Section 8.2. Detection evaluation consumes the Detection Ground Truth as a fixed reference record and does not modify it. Detection Ground Truth is defined by Sections 8.2.1, 8.2.2, and 8.2.3, which establish its purpose and scope, its field semantics, and its validation semantics. Detection evaluation does not redefine Detection Ground Truth annotation policy.

**Annotation policy is governed by Sections 2–4.**

Detection annotation policy remains governed by Sections 2–4. Detection evaluation applies that policy as written and does not override, relax, or restate it.

**Ground Truth and production detections remain separate.**

Detection Ground Truth is the human annotation reference. Production detections are model-generated predictions produced by the production detector. Detection evaluation treats them as distinct inputs and does not equate Ground Truth annotation with YOLO detection.

**Identity is not a detection concern.**

Detection Ground Truth does not contain `object_id`, and detection evaluation does not introduce `track_id` or `global_id` into the detection domain as detection identity fields. Tracking identity belongs to the Tracking Ground Truth domain defined by Section 8.3 and is not a detection evaluation concern.

**The evaluation frame domain is established by Section 7 and Section 8.5.**

Detection evaluation operates within the sampled and partitioned frame domain established by Section 7 and recorded by the Sampling Manifest defined by Section 8.5. Detection evaluation consumes that domain as established; it does not redesign it, does not change the baseline sampling interval, does not redefine partition boundaries, does not redefine excluded frames, and does not introduce a new evaluation sampling interval.

**Production behavior is unchanged.**

Detection evaluation is an analysis and evaluation layer only. It does not change YOLO inference, does not change the production frame rate, does not change ByteTrack behavior, and does not change runtime tracking or runtime counting.

**What this subsection does not define.**

This subsection defines only purpose and scope. It does not define IoU thresholds, confidence thresholds, matching thresholds, precision, recall, F1, mAP, AP calculation, class averaging, TP/FP/FN matching rules, confidence ranking, PR curves, AP@IoU, mAP@50, mAP@50:95, pass/fail criteria, benchmark targets, statistical significance, confidence intervals, or error taxonomies. It does not introduce new fields, new metrics, new thresholds, new formulas, new datasets, new matching policies, new annotation rules, or new production behavior. It does not redefine any rule established in Sections 1–8.

#### 9.3.2 Detection Matching Semantics

**Purpose.**

This subsection defines the conceptual semantics of matching production detections against Detection Ground Truth. It establishes what matching means, what matching is scoped to, and what matching is not. It does not define the numerical matching criterion.

**Matching domain.**

Matching operates between Detection Ground Truth annotations and production detection predictions. Detection Ground Truth is defined by Section 8.2. Production detections are the model-generated predictions described in Section 9.2. Matching relates records from these two domains within the evaluation framework.

**Matching is frame-local.**

Matching is performed within the same evaluation frame. A prediction from one frame is matched against a ground-truth annotation from the same frame. A prediction from one frame must not be matched against a ground-truth annotation from another frame. The evaluation frame domain is established by Section 7 and Section 9.2, and matching does not change it.

**Matching is object-level, not identity-level.**

Matching is object-level. It relates individual ground-truth annotations to individual predictions. It does not establish object identity, and it does not operate across frames. Detection Ground Truth does not contain `global_id`, and matching does not use `global_id`. Production `track_id` must not be used as Detection Ground Truth identity. Detection matching is conceptually distinct from tracking identity, and tracking correctness must not be inferred from detection matching.

**One-to-one matching.**

A ground-truth object can match at most one prediction. A prediction can match at most one ground-truth object. Matching is a one-to-one relationship at the object level within a single frame.

**Unmatched records.**

An unmatched ground-truth object remains a false-negative candidate. An unmatched prediction remains a false-positive candidate. The classification of these candidates into final true-positive, false-positive, and false-negative outcomes is a metric concern and is not defined here.

**What this subsection does not define.**

This subsection defines conceptual matching semantics only. It does not define the numerical matching criterion, and it does not invent one. It does not define IoU thresholds, confidence thresholds, distance thresholds, matching formulas, score cutoffs, class-matching formulas, greedy matching algorithms, Hungarian matching, NMS behavior, AP calculation, precision, recall, F1, mAP, TP/FP/FN numerical definitions beyond the conceptual unmatched/matched relationship, confidence ranking, PR curves, AP@IoU, mAP@50, mAP@50:95, pass/fail criteria, benchmark targets, statistical significance, confidence intervals, error taxonomies, tracking metrics, identity metrics, temporal matching, or cross-frame matching. It does not introduce new fields, new prediction fields, new annotation policies, or new sampling rules. It does not redefine any rule established in Sections 1–8.

- **Section 2: Annotation Rules (General)** — class labels, frame referencing, coordinate system (this document)
- **Section 7: Temporal Sampling and Dataset Construction** — sampling units, baseline and event-boosted sampling, stratification, train/val/test split (this document)
- **Section 8.2: Detection Ground Truth Schema** — per-frame content of sampled frames (this document)
- **Section 9.2: Evaluation Inputs** — evaluation input domains and shared temporal context (this document)
- **Section 9.3.1: Detection Evaluation Purpose and Scope** — detection-evaluation scope (this document)
- **Section 9.3.3: Detection Metrics Semantics** — conceptual role and scope of detection metrics (this document)

#### 9.3.3 Detection Metrics Semantics

**Purpose.**

This subsection defines the conceptual role and scope of detection metrics. It establishes what detection metrics evaluate, what they are scoped to, and what they are not. It does not define numerical metric parameters.

**What detection metrics evaluate.**

Detection metrics evaluate production detections against Detection Ground Truth. Detection Ground Truth is defined by Section 8.2. Production detections are the model-generated predictions described in Section 9.2. Detection metrics operate within the detection evaluation domain established by Sections 9.1–9.3.2.

**Matching semantics are defined by Section 9.3.2.**

Detection metrics consume the matching semantics established by Section 9.3.2. Matching is frame-local, object-level, and one-to-one within a single frame. Detection metrics do not redefine matching and do not introduce a numerical matching criterion.

**Detection evaluation is distinct from tracking evaluation.**

Detection metrics are distinct from tracking metrics. Detection metrics must not use `global_id`, must not use `track_id`, must not use cross-frame identity, and must not use track continuity. Tracking metrics belong to the tracking evaluation domain and are not defined here.

**Conceptual layers.**

Detection evaluation distinguishes four layers, and this subsection addresses only the conceptual role of the first three:

1. **Conceptual metric inputs** — the Detection Ground Truth annotations and production detections that metrics consume, as identified by Section 9.2.
2. **Matching semantics** — the one-to-one, frame-local, object-level relationship defined by Section 9.3.2.
3. **Numerical metric definitions** — the formal definitions of precision, recall, F1, AP, mAP, and any other numerical parameters.
4. **Implementation details** — the scripts, code, and runtime procedures that compute metrics.

**Numerical definitions are outside the scope of this subsection.**

The exact numerical definitions of detection metrics are outside the scope of this subsection and must be specified before implementation. This subsection does not define IoU thresholds, confidence thresholds, matching thresholds, distance thresholds, score cutoffs, precision formulas, recall formulas, F1 formulas, AP interpolation rules, AP calculation variants, mAP averaging rules, macro/micro averaging rules, class-weighting rules, per-frame aggregation formulas, dataset-level aggregation formulas, confidence calibration rules, PR-curve construction rules, NMS rules, top-K rules, ranking rules, duplicate-prediction rules, metric aggregation windows, statistical confidence intervals, or statistical significance tests.

**TP / FP / FN are conceptual, not formal.**

The terms true positive, false positive, and false negative appear in Section 9.3.2 only as conceptual matched or unmatched candidates: a matched prediction is a true-positive candidate, an unmatched prediction is a false-positive candidate, and an unmatched ground-truth object is a false-negative candidate. This subsection does not turn these terms into formal metric definitions, and it does not assume their exact metric-level treatment beyond that conceptual relationship. Their formal treatment remains to be specified.

**Aggregation is not defined here.**

Metric results may be reported per class and/or across the complete evaluation set only if such aggregation is already established elsewhere in the protocol. The existing protocol references metric reporting per stratum in Section 7.5, but it does not establish per-class or dataset-level aggregation rules for detection metrics. No such rule is introduced here.

**What this subsection does not define.**

This subsection defines only the conceptual role and scope of detection metrics. It does not define any numerical metric parameter, any formula, any threshold, any averaging rule, any aggregation rule, any calibration rule, any statistical rule, any matching rule, any implementation detail, any tracking metric, any identity matching, any sampling rule, or any production behavior. It does not redefine any rule established in Sections 1–8 or in Sections 9.1–9.3.2.

- **Section 2: Annotation Rules (General)** — class labels, frame referencing, coordinate system (this document)
- **Section 7: Temporal Sampling and Dataset Construction** — sampling units, baseline and event-boosted sampling, stratification, train/val/test split (this document)
- **Section 8.2: Detection Ground Truth Schema** — per-frame content of sampled frames (this document)
- **Section 9.2: Evaluation Inputs** — evaluation input domains and shared temporal context (this document)
- **Section 9.3.1: Detection Evaluation Purpose and Scope** — detection-evaluation scope (this document)
- **Section 9.3.2: Detection Matching Semantics** — matching semantics consumed by detection metrics (this document)
- **Section 9.4: Tracking Evaluation** — tracking-evaluation domain, distinct from detection evaluation (this document)

### 9.4 Tracking Evaluation

#### 9.4.1 Purpose and Scope

**Purpose.**

This subsection defines the purpose and scope of tracking evaluation. It establishes what tracking evaluation governs and what it does not govern. It does not define tracking metrics, matching criteria, formulas, thresholds, or pass/fail criteria. Those belong to later subsections only if explicitly requested.

**Scope.**

Tracking evaluation compares Tracking Ground Truth against production tracking output. It is the framework for interpreting the quality of the production tracker relative to the annotated identity reference data.

**Ground Truth is the identity reference, and it is already defined.**

Tracking evaluation is performed against the Tracking Ground Truth defined by Section 8.3. Tracking Ground Truth is the authoritative human-annotated identity reference. Tracking evaluation consumes it as a fixed reference record and does not modify it.

**Production tracking output is algorithm-generated.**

Production tracking output is algorithm-generated and may contain runtime tracking identities such as the production `track_id`. Production tracking output is produced independently of Ground Truth and is described only at the level already established by Sections 1–8.

**`global_id` and `track_id` are different identity spaces.**

`global_id` is the Ground Truth identity defined by Section 8.3. `track_id` is the production or algorithmic tracking identity produced by the production tracker. They are different identity spaces and are never equated. Tracking evaluation treats them as distinct and does not merge them, and it does not introduce another identity field or an identity mapping.

**Tracking evaluation evaluates identity and continuity at the tracking-evaluation level.**

Tracking evaluation evaluates identity correspondence and track continuity at the tracking-evaluation level. It concerns identity-bearing Ground Truth and production tracks, and it is the next evaluation layer after detection evaluation.

**Detection evaluation remains a separate domain.**

Detection evaluation, defined by Section 9.3, remains a separate domain. Detection evaluation is frame-local and identity-free. Tracking evaluation does not redefine detection evaluation, and detection correctness must not be inferred from tracking evaluation.

**Ground Truth and production behavior are unchanged.**

Tracking evaluation must not modify Ground Truth. Tracking evaluation must not modify production tracking behavior, and it does not change the production tracker, its configuration, or its runtime output.

**The evaluation frame domain is consumed as established.**

Tracking evaluation consumes the established evaluation frame domain from Sections 7 and 9.2. It does not redesign that domain, does not change the baseline sampling interval, does not redefine partition boundaries, does not redefine excluded frames, and does not introduce a new evaluation sampling interval.

**The Sampling Manifest is a dataset-construction artifact.**

The Sampling Manifest, defined by Section 8.5, is a dataset-construction artifact. It is not runtime tracking control, not production inference configuration, not a prediction output, and not a model input that changes tracking behavior.

**What this subsection does not define.**

This subsection defines only purpose and scope. It does not define IoU thresholds, distance thresholds, temporal overlap thresholds, track matching thresholds, IDF1, MOTA, MOTP, HOTA, ID switch formulas, fragmentation formulas, precision, recall, F1, AP, mAP, confidence thresholds, score thresholds, track initialization rules, track termination rules, ByteTrack configuration, tracker parameters, matching algorithms, or identity matching rules. It does not define benchmark procedures, statistical tests, confidence intervals, or error categories. It does not introduce new fields, new schema fields, new annotation rules, new sampling rules, or new production behavior. It does not redefine any rule established in Sections 1–8 or in Sections 9.1–9.3.

- **Section 2: Annotation Rules (General)** — class labels, frame referencing, coordinate system (this document)
- **Section 7: Temporal Sampling and Dataset Construction** — sampling units, baseline and event-boosted sampling, stratification, train/val/test split (this document)
- **Section 8.3: Tracking Ground Truth Schema** — per-object content of sampled frames (this document)
- **Section 9.2: Evaluation Inputs** — evaluation input domains and shared temporal context (this document)
- **Section 9.3: Detection Evaluation** — detection-evaluation domain, distinct from tracking evaluation (this document)
- **Section 9.4.2: Tracking Matching Semantics** — track-level matching semantics consumed by tracking evaluation (this document)

#### 9.4.2 Tracking Matching Semantics

**Purpose.**

This subsection defines the conceptual matching relationship between Tracking Ground Truth tracks and production tracking tracks. It establishes what matching governs, what identity spaces it relates, and what it does not define. It does not define numerical tracking metrics, metric formulas, final evaluation thresholds, or implementation-specific tracker behavior.

**Matching is performed between Ground Truth tracks and production tracks.**

Matching is performed between Ground Truth tracks and production tracking tracks within the established evaluation frame domain. Both sides are track-level entities: a Ground Truth track is the identity-bearing annotation record defined by Section 8.3, and a production tracking track is the algorithm-generated track produced by the production tracker.

**Ground Truth identity is represented by `global_id`.**

Ground Truth identity is represented by `global_id`, as defined by Section 8.3. `global_id` is the authoritative human-annotated identity and is carried by the Tracking Ground Truth record.

**Production tracking identity is represented by `track_id`.**

Production tracking identity is represented by `track_id`, which is the runtime tracking identity produced by the production tracker. `track_id` is algorithm-generated and is carried by the production tracking output.

**`global_id` and `track_id` belong to different identity spaces.**

`global_id` and `track_id` belong to different identity spaces. `global_id` is the Ground Truth identity space; `track_id` is the production tracking identity space. They are not interchangeable, and no identity conversion between them is defined here.

**Association requires an explicit evaluation matching process.**

A Ground Truth track may be associated with production tracking observations only through an explicit evaluation matching process. This process is the evaluation matching layer; it is not an identity assignment, and it does not merge the two identity spaces.

**A matching relationship does not mean `global_id == track_id`.**

The existence of a matching relationship between a Ground Truth track and a production tracking track does not mean `global_id == track_id`. It does not mean that the production `track_id` equals the Ground Truth `global_id`, and it does not mean that the production tracker produced the Ground Truth identity. The two identity spaces remain distinct even when a correspondence is established.

**Matching concerns track-level correspondence across frames.**

Matching concerns track-level correspondence across frames rather than the frame-local object matching used in Section 9.3.2. Section 9.3.2 defines one-to-one, frame-local, object-level matching between production detections and Detection Ground Truth within a single frame. Tracking matching operates on tracks, which are sequences of observations spanning multiple frames, and it does not reuse the frame-local detection matching semantics.

**Matching must respect the established evaluation frame domain.**

Matching must respect the established evaluation frame domain from Sections 7 and 9.2. It consumes that domain as-is and does not redesign it, does not change the baseline sampling interval, does not redefine partition boundaries, does not redefine excluded frames, and does not introduce a new evaluation sampling interval.

**Missing observations, partial overlap, fragmentation, and identity disagreement may affect correspondence.**

Missing observations, partial overlap, track fragmentation, and identity disagreement may affect whether a correspondence can be established or maintained. These conditions are recognized as factors in track-level correspondence; their treatment as numerical cases is not defined here.

**The exact numerical matching criterion is not defined here.**

The exact numerical matching criterion is not defined in this subsection unless it is already explicitly established by Sections 1–7.12. No IoU criterion, distance criterion, temporal overlap criterion, center-distance criterion, confidence criterion, matching threshold, or score threshold is defined here.

**What this subsection does not define.**

This subsection defines only conceptual matching semantics. It does not define IoU thresholds, distance thresholds, temporal overlap thresholds, center-distance thresholds, confidence thresholds, matching thresholds, score thresholds, MOTA, MOTP, IDF1, HOTA, ID switch formulas, fragmentation formulas, track precision, track recall, F1, AP, mAP, Hungarian matching, greedy matching, ByteTrack internals, tracker parameters, track initialization rules, track termination rules, association thresholds, Kalman filter behavior, runtime modifications, benchmark procedures, statistical tests, confidence intervals, or error categories. It does not introduce new fields, new schema fields, new annotation rules, new sampling rules, new identity namespaces, or new production behavior. It does not redefine any rule established in Sections 1–8 or in Sections 9.1–9.4.1.

- **Section 2: Annotation Rules (General)** — class labels, frame referencing, coordinate system (this document)
- **Section 7: Temporal Sampling and Dataset Construction** — sampling units, baseline and event-boosted sampling, stratification, train/val/test split (this document)
- **Section 8.3: Tracking Ground Truth Schema** — per-object content of sampled frames (this document)
- **Section 9.2: Evaluation Inputs** — evaluation input domains and shared temporal context (this document)
- **Section 9.3: Detection Evaluation** — detection-evaluation domain, distinct from tracking evaluation (this document)
- **Section 9.4.1: Tracking Evaluation Purpose and Scope** — tracking-evaluation scope (this document)
- **Section 9.4.3: Tracking Metrics Semantics** — conceptual metric layer consumed by tracking evaluation (this document)

#### 9.4.3 Tracking Metrics Semantics

**Purpose.**

This subsection defines the conceptual role and scope of metrics used for tracking evaluation. It establishes what tracking metrics evaluate, what they consume, and what they do not define. It does not invent numerical metric formulas.

**Tracking metrics operate on the relationship established by Section 9.4.2.**

Tracking metrics operate on the relationship between Tracking Ground Truth, production tracking output, and the matching/correspondence established by Section 9.4.2. Tracking Ground Truth is defined by Section 8.3. Production tracking output is the algorithm-generated track output described in Section 9.4.1. The matching semantics defined by Section 9.4.2 provide the correspondence relationship that tracking metrics consume. Tracking metrics do not redefine the matching process and do not introduce a new matching algorithm.

**Logical sequence.**

The relationship is:

Tracking Ground Truth + Production Tracking Output
    ↓
Section 9.4.2: Tracking Matching Semantics
    ↓
Section 9.4.3: Tracking Metrics Semantics

Tracking metrics consume the correspondence established by Section 9.4.2. They do not redefine matching, and they do not bypass it.

**Tracking metrics evaluate track-level properties.**

Tracking metrics evaluate properties such as track correspondence, identity consistency, identity disagreement, continuity, fragmentation, and association quality. These are evaluated at the conceptual level. They concern identity-bearing Ground Truth and production tracks, and they operate across frames within the established evaluation frame domain.

**Tracking metrics are distinct from detection metrics.**

Tracking metrics are distinct from the detection metrics defined conceptually in Section 9.3. Detection metrics are frame-local and identity-free. Tracking metrics are identity-bearing and track-level. Tracking metrics do not reuse detection matching semantics, do not redefine detection evaluation, and detection correctness must not be inferred from tracking evaluation.

**Metric families are named only as conceptual examples.**

Metric families and concepts such as IDF1, MOTA, MOTP, HOTA, identity switches, fragmentation, and track-level precision/recall may be named as examples of tracking evaluation metric families. When named, they remain conceptual. Their formulas are not defined here, their exact computation is not defined here, their thresholds are not defined here, and their aggregation procedures are not defined here. No metric family is selected as mandatory, and no claim is made that any particular metric is required by the project unless that requirement is explicitly established elsewhere in the document.

**No numerical definitions are introduced here.**

This subsection does not define IoU thresholds, distance thresholds, temporal overlap thresholds, confidence thresholds, score thresholds, association thresholds, identity-switch thresholds, fragmentation thresholds, minimum track length, minimum overlap duration, metric pass/fail thresholds, numerical formulas, weighting rules, macro/micro aggregation, averaging rules, statistical significance, confidence intervals, or benchmark targets. It does not define the MOTA formula, MOTP formula, IDF1 formula, HOTA formula, ID-switch formula, fragmentation formula, or precision/recall formula. It does not define tracker implementation, ByteTrack parameters, or runtime tracking behavior.

**Ground Truth and production behavior are unchanged.**

Tracking Ground Truth remains the evaluation reference. Production tracking output remains model/system-generated output. Evaluation is a comparison process only. Evaluation does not modify Ground Truth, does not modify production tracks, does not retrain the model, does not change tracker behavior, does not change sampling, and does not create new annotations.

**The evaluation domain is consumed as established.**

Tracking metrics consume the established evaluation frame domain from Sections 7 and 9.2. They do not change the sampling interval, event-boosted sampling, partition boundaries, excluded frames, leakage rules, or Sampling Manifest semantics. They do not alter the dataset.

**What this subsection does not define.**

This subsection defines only the conceptual role and scope of tracking metrics. It does not define any numerical metric parameter, any formula, any threshold, any averaging rule, any aggregation rule, any matching rule, any statistical rule, any benchmark target, any implementation detail, any tracking matching criterion, any sampling rule, or any production behavior. It does not introduce new fields, new schema fields, new annotation rules, new identity namespaces, or new production behavior. It does not redefine any rule established in Sections 1–8 or in Sections 9.1–9.4.2.

- **Section 2: Annotation Rules (General)** — class labels, frame referencing, coordinate system (this document)
- **Section 7: Temporal Sampling and Dataset Construction** — sampling units, baseline and event-boosted sampling, stratification, train/val/test split (this document)
- **Section 8.3: Tracking Ground Truth Schema** — per-object content of sampled frames (this document)
- **Section 9.2: Evaluation Inputs** — evaluation input domains and shared temporal context (this document)
- **Section 9.3: Detection Evaluation** — detection-evaluation domain, distinct from tracking evaluation (this document)
- **Section 9.4.1: Tracking Evaluation Purpose and Scope** — tracking-evaluation scope (this document)
- **Section 9.4.2: Tracking Matching Semantics** — track-level matching semantics consumed by tracking evaluation (this document)

### 9.5 Counting Evaluation

#### 9.5.1 Purpose and Scope

**Purpose.**

This subsection defines the purpose and scope of counting evaluation. It establishes what counting evaluation governs and what it does not govern. It does not define counting matching semantics, counting metrics, numerical formulas, thresholds, aggregation formulas, event matching algorithms, or new counting rules. Those belong to later subsections and are not defined here.

**Scope.**

Counting evaluation compares Counting Ground Truth against production/runtime counting output. It is the framework for interpreting the quality of the production counting result relative to the annotated counting reference data.

**Counting Ground Truth is the reference domain, and it is already defined.**

Counting evaluation is performed against the Counting Ground Truth defined by Section 8.4. Counting Ground Truth is the authoritative human-annotated counting reference. Counting evaluation consumes it as a fixed reference record and does not modify it, and it does not redefine how Counting Ground Truth is constructed.

**Production counting output is runtime/model-derived.**

Production counting output is the runtime or model-derived counting result. It is produced independently of Counting Ground Truth and is described only at the level already established by Sections 1–8.

**Ground Truth counting events and production predicted counting events are distinct.**

Counting evaluation distinguishes Ground Truth counting events from production predicted counting events. Ground Truth counting events are annotation-derived and belong to the Counting Ground Truth domain defined by Section 8.4. Production predicted counting events are runtime/model-derived and belong to the production counting domain. They are not the same thing, and counting evaluation does not merge them.

**Counting Ground Truth is the terminal Ground Truth counting domain.**

Counting Ground Truth is the terminal Ground Truth counting domain defined by Section 8.4. It is reached through the established derivation chain:

Detection Ground Truth
    → Tracking Ground Truth
    → ROI-crossing determination
    → Counting Ground Truth

Counting evaluation consumes Counting Ground Truth as its reference domain. It does not redefine the ROI-crossing algorithm, does not redefine entry/exit semantics, does not redefine crossing confidence, does not redefine duplicate prevention, and does not redefine event aggregation. Those rules already belong to Sections 6 and 8.4.

**Production counting remains a separate runtime domain.**

Production counting remains a separate runtime domain from Counting Ground Truth. It is generated by the runtime pipeline and is evaluated against Counting Ground Truth. It does not become Counting Ground Truth, and Counting Ground Truth is not generated by the production tracker or the production counting logic.

**`global_id` and `track_id` remain separate identity spaces.**

Counting Ground Truth uses `global_id` as the Ground Truth identity reference inherited from Tracking Ground Truth, as defined by Section 8.3. Production tracking uses `track_id` as an algorithmic runtime identity. `global_id` and `track_id` belong to different identity spaces and are never equated. Counting evaluation does not introduce another identity namespace, and any identity correspondence required for evaluation remains conceptual and is not defined numerically here.

**Counting evaluation is distinct from detection and tracking evaluation.**

Counting evaluation is distinct from detection evaluation in Section 9.3 and from tracking evaluation in Section 9.4. It is not detection evaluation and it is not tracking evaluation. Detection metrics must not be defined here, and tracking metrics must not be defined here. Counting correctness must not be inferred from detection evaluation or from tracking evaluation.

**The evaluation frame/event domain is consumed as established.**

Counting evaluation consumes the established evaluation frame and event domain from Sections 7, 8.5, and 9.2. It does not change the sampling interval, does not change event-boosted sampling, does not redefine split boundaries, does not redefine excluded frames, does not change leakage rules, and does not change manifest regeneration. It does not introduce runtime sampling behavior.

**The Sampling Manifest remains a dataset-construction artifact.**

The Sampling Manifest, defined by Section 8.5, is a dataset-construction artifact. It is not a runtime counting controller, not production inference configuration, not a prediction output, and not a model input that changes counting behavior.

**Ground Truth and production behavior are unchanged.**

Counting Ground Truth is a fixed annotation/reference domain, independent of model execution. Production counting output is generated by the runtime pipeline, evaluated against Ground Truth, and does not modify Ground Truth. Counting evaluation must not modify Counting Ground Truth, must not modify production counting logic, must not modify runtime counting behavior, and must not modify production tracking behavior.

**What this subsection does not define.**

This subsection defines only purpose and scope. It does not define precision, recall, F1, accuracy, AP, mAP, MAE, RMSE, count error formulas, event matching thresholds, IoU thresholds, temporal thresholds, confidence thresholds, duplicate-event thresholds, mandatory metrics, or aggregation formulas. It does not define counting matching semantics, counting metrics, numerical formulas, thresholds, event matching algorithms, or new counting rules. It does not introduce new fields, new schema fields, new annotation rules, new sampling rules, new identity namespaces, or new production behavior. It does not redefine any rule established in Sections 1–8 or in Sections 9.1–9.4.

- **Section 6: Counting Events and ROI Semantics** — counting event rules and ROI-crossing semantics (this document)
- **Section 7: Temporal Sampling and Dataset Construction** — sampling units, baseline and event-boosted sampling, stratification, train/val/test split (this document)
- **Section 8.4: Counting Ground Truth Schema** — counting reference domain (this document)
- **Section 8.5: Sampling Manifest Schema** — dataset-construction artifact (this document)
- **Section 9.2: Evaluation Inputs** — evaluation input domains and shared temporal context (this document)
- **Section 9.3: Detection Evaluation** — detection-evaluation domain, distinct from counting evaluation (this document)
- **Section 9.4: Tracking Evaluation** — tracking-evaluation domain, distinct from counting evaluation (this document)
- **Section 9.5.2: Counting Matching Semantics** — counting-event matching semantics consumed by counting evaluation (this document)

#### 9.5.2 Counting Matching Semantics

**Purpose.**

This subsection defines the conceptual matching/correspondence semantics between Counting Ground Truth and production counting output. It establishes what counting matching governs, what attributes it relates, and what it does not define. It does not invent a numerical matching criterion, a metric formula, a threshold, an assignment algorithm, or an aggregation rule.

**Counting evaluation operates at the counting-event level.**

Counting matching operates at the counting-event level. It concerns correspondence between individual counting events, not between tracks and not between detections. A Ground Truth counting event is one entry crossing recorded in Counting Ground Truth. A production counting event is one predicted/runtime crossing recorded by the production counting logic.

**Counting Ground Truth is the reference event domain.**

Counting Ground Truth, defined by Section 8.4, is the reference event domain. It is the authoritative human-annotated counting reference derived from Tracking Ground Truth. Counting matching consumes it as a fixed reference record and does not modify it, and it does not redefine the Counting Ground Truth schema.

**Production counting output is the predicted/runtime event domain.**

Production counting output is the predicted or runtime event domain. It is generated by the production counting logic and is produced independently of Counting Ground Truth. It does not become Counting Ground Truth, and Counting Ground Truth is not generated by the production counting logic.

**A Ground Truth counting event is conceptually compared with a production counting event based on established event attributes.**

The correspondence between a Ground Truth counting event and a production counting event is established conceptually using the event attributes already defined by the protocol. These attributes include event identity, counted class, crossing frame and temporal location, ROI-crossing semantics, and entry direction. Matching consumes these attributes as established; it does not redefine them.

**The correspondence preserves the existing identity relationship.**

Counting Ground Truth uses `global_id` as the Ground Truth identity reference inherited from Tracking Ground Truth, as defined by Section 8.3. Production tracking uses `track_id` as an algorithmic runtime identity. `global_id` and `track_id` belong to different identity spaces and are never equated. Counting matching does not merge them and does not introduce any identity-conversion rule. It does not introduce `counting_id`, `event_id` used as a production identity, `evaluation_id`, `predicted_global_id`, `generated_global_id`, `matched_id`, or any other new identity namespace.

**The correspondence remains consistent with the existing counting protocol.**

The correspondence remains consistent with the counting protocol established by Sections 6 and 8.4. It respects event identity, counted class, crossing frame and temporal location, ROI-crossing semantics, entry direction, and the existing one-entry-per-`global_id` rule. It also respects the derivation chain from Tracking Ground Truth: Detection Ground Truth → Tracking Ground Truth → ROI-crossing determination → Counting Ground Truth. Counting Ground Truth is the terminal Ground Truth counting domain.

**Counting matching does not redefine established semantics.**

Counting matching does not redefine the Counting Ground Truth schema, does not redefine Section 6 counting semantics, does not redefine Tracking Ground Truth semantics, and does not redefine sampling or partition rules. It does not redefine the ROI-crossing algorithm, entry/exit semantics, crossing confidence, duplicate prevention, or event aggregation. Those rules already belong to Sections 6 and 8.4.

**Evaluation must not modify Ground Truth or production behavior.**

Evaluation must not modify Counting Ground Truth, must not modify production tracking, must not modify production counting, must not modify runtime `track_id`, and must not modify runtime event generation.

**Event correspondence, identity correspondence, and numerical metric computation are distinct.**

Counting matching distinguishes three layers: event correspondence (which counting events relate to each other), identity correspondence (the relationship between `global_id` and `track_id`, which remains conceptual and is never an equality), and numerical metric computation (which consumes the established correspondence and is not defined here). These layers are separate, and none of them is defined numerically in this subsection.

**The exact numerical matching criterion is not defined here.**

The exact numerical matching criterion is not defined in this subsection unless it is already explicitly established by Sections 1–7.12. No IoU threshold, temporal tolerance, frame tolerance, confidence threshold, score threshold, distance threshold, ROI-point distance threshold, class similarity threshold, matching cost, assignment algorithm, Hungarian matching, greedy matching, nearest-neighbor matching, duplicate-event tolerance, event-window size, minimum duration, or minimum overlap is defined here.

**What this subsection does not define.**

This subsection defines only conceptual counting matching semantics. It does not define precision, recall, F1, accuracy, AP, mAP, MAE, RMSE, count error formulas, confusion matrices, or aggregation rules. It does not define IoU thresholds, temporal thresholds, confidence thresholds, score thresholds, duplicate-event thresholds, or any numerical cutoff. It does not define counting metrics, metric formulas, thresholds, event matching algorithms, or new counting rules. It does not introduce new fields, new schema fields, new annotation rules, new sampling rules, new identity namespaces, or new production behavior. It does not redefine any rule established in Sections 1–8 or in Sections 9.1–9.5.1.

- **Section 6: Counting Events and ROI Semantics** — counting event rules and ROI-crossing semantics (this document)
- **Section 6.4: Duplicate-Event Prevention** — one-entry-per-`global_id` rule (this document)
- **Section 6.6: Derivation: Counting GT from Tracking GT** — derivation chain from Tracking Ground Truth (this document)
- **Section 6.8: Connection Between Tracking and Counting** — identity and counting relationship (this document)
- **Section 7: Temporal Sampling and Dataset Construction** — sampling units, baseline and event-boosted sampling, stratification, train/val/test split (this document)
- **Section 8.4: Counting Ground Truth Schema** — counting reference domain (this document)
- **Section 8.5: Sampling Manifest Schema** — dataset-construction artifact (this document)
- **Section 9.2: Evaluation Inputs** — evaluation input domains and shared temporal context (this document)
- **Section 9.5.1: Counting Evaluation Purpose and Scope** — counting-evaluation scope (this document)
- **Section 9.5.3: Counting Metrics Semantics** — conceptual metric layer consumed by counting evaluation (this document)

#### 9.5.3 Counting Metrics Semantics

**Purpose.**

This subsection defines the conceptual semantics and boundaries of counting evaluation metrics. It establishes what counting metrics evaluate, what layers they span, and what they do not define. It does not select a mandatory metric family and does not introduce numerical metric formulas.

**Evaluation inputs.**

Counting metrics consume the correspondence established by Section 9.5.2 between Counting Ground Truth events and production counting events. Counting Ground Truth is defined by Section 8.4. Production counting output is the predicted/runtime event domain described in Section 9.5.1. Counting metrics do not redefine the correspondence and do not introduce a new matching algorithm.

**Event-level evaluation.**

Counting evaluation concerns whether production counting events correspond to the Ground Truth counting-event domain. It operates at the counting-event level and consumes the event-level correspondence established by Section 9.5.2.

**Count-level evaluation.**

Counting evaluation may conceptually consider comparison between Ground Truth event counts and production event counts. This is a distinct layer from event correspondence. Aggregate count measurement does not replace event-level correspondence, and neither layer is defined numerically here.

**Class-level evaluation.**

Any class-level counting evaluation must remain within the existing `countable_classes` and class semantics already established by Section 8.4. It does not introduce new classes and does not redefine the existing class domain.

**Metric families are named only as conceptual examples.**

Metric families such as precision, recall, F1, accuracy, count error, MAE, RMSE, AP, and mAP may be named as examples of counting evaluation metric families. When named, they remain conceptual. Their formulas are not defined here, their thresholds are not defined here, their aggregation rules are not defined here, and no such family is selected as mandatory.

**Separation of layers.**

Counting evaluation distinguishes four layers, and this subsection addresses only the conceptual role of the first three:

1. **Event correspondence** — the conceptual relationship between Counting Ground Truth events and production counting events, established by Section 9.5.2.
2. **Count comparison** — the conceptual comparison between Ground Truth event counts and production event counts.
3. **Numerical metric definitions** — the formal definitions of precision, recall, F1, accuracy, count error, MAE, RMSE, AP, mAP, and any other numerical parameters.
4. **Implementation details** — the scripts, code, and runtime procedures that compute metrics.

**Numerical definitions are outside the scope of this subsection.**

The exact numerical definitions of counting metrics are outside the scope of this subsection and must be specified before implementation. This subsection does not define numerator/denominator rules, averaging rules, macro averaging, micro averaging, weighted averaging, class weighting, event weighting, temporal weighting, confidence weighting, normalization, rounding, clipping, epsilon handling, zero-denominator handling, aggregation across videos, aggregation across classes, or aggregation across partitions.

**No mandatory metric is selected.**

No metric family is selected as required, mandatory, authoritative, the official metric, the primary metric, the final metric, or the acceptance metric. No claim is made that any particular metric is required by the project unless that requirement is explicitly established elsewhere in the document.

**Counting Ground Truth is the reference domain.**

Counting Ground Truth, defined by Section 8.4, is the reference domain. It is the authoritative human-annotated counting reference derived from Tracking Ground Truth. Counting metrics consume it as a fixed reference record and do not modify it.

**Production counting output is the predicted/runtime domain.**

Production counting output is the predicted or runtime event domain. It is generated by the production counting logic and is evaluated against Counting Ground Truth. It does not become Counting Ground Truth, and Counting Ground Truth is not generated by the production counting logic.

**Identity separation is preserved.**

Counting Ground Truth uses `global_id` as the Ground Truth identity reference inherited from Tracking Ground Truth, as defined by Section 8.3. Production tracking uses `track_id` as an algorithmic runtime identity. `global_id` and `track_id` belong to different identity spaces and are never equated. Counting metrics do not merge them and do not introduce any identity-conversion rule. They do not introduce `counting_id`, `evaluation_id`, `predicted_global_id`, `generated_global_id`, `matched_id`, `production_global_id`, `event_identity`, `metric_id`, or any other new identity namespace. Counting Ground Truth `event_id` remains the schema-defined event identifier and is not reinterpreted as a production identity.

**Existing counting semantics are preserved.**

Counting metrics consume the correspondence established by Section 9.5.2 and do not redefine it. They do not redefine the Counting Ground Truth schema, do not redefine Section 6 counting semantics, do not redefine Tracking Ground Truth semantics, and do not redefine sampling or partition rules. Counting Ground Truth `direction` remains `entry` only; no `exit` semantics are introduced. The one-entry-per-`global_id` rule remains established by Section 6. Existing ROI-crossing semantics, crossing-frame semantics, and class semantics remain unchanged.

**Ground Truth and production behavior are unchanged.**

Counting Ground Truth is a fixed annotation/reference domain, independent of model execution. Production counting output is generated by the runtime pipeline, evaluated against Ground Truth, and does not modify Ground Truth. Counting evaluation must not modify Counting Ground Truth, must not modify production counting logic, must not modify runtime counting behavior, and must not modify production tracking behavior.

**The evaluation domain is consumed as established.**

Counting metrics consume the established evaluation frame and event domain from Sections 7, 8.5, and 9.2. They do not change the sampling interval, event-boosted sampling, partition boundaries, excluded frames, leakage rules, or manifest regeneration. They do not introduce runtime sampling behavior. The Sampling Manifest remains a dataset-construction artifact and evaluation-input record, not a runtime counting controller.

**What this subsection does not define.**

This subsection defines only the conceptual role and scope of counting metrics. It does not define precision, recall, F1, accuracy, count error, absolute error, relative error, MAE, RMSE, AP, mAP, event detection rate, missed-event rate, false-event rate, overcount, undercount, or any numerical metric parameter. It does not define any formula, any numerator/denominator rule, any averaging rule, any aggregation rule, any threshold, any matching rule, any matching algorithm, any statistical rule, any benchmark target, any implementation detail, any sampling rule, or any production behavior. It does not introduce new fields, new schema fields, new annotation rules, new identity namespaces, or new production behavior. It does not redefine any rule established in Sections 1–8 or in Sections 9.1–9.5.2.

- **Section 6: Counting Events and ROI Semantics** — counting event rules and ROI-crossing semantics (this document)
- **Section 6.4: Duplicate-Event Prevention** — one-entry-per-`global_id` rule (this document)
- **Section 6.6: Derivation: Counting GT from Tracking GT** — derivation chain from Tracking Ground Truth (this document)
- **Section 6.8: Connection Between Tracking and Counting** — identity and counting relationship (this document)
- **Section 7: Temporal Sampling and Dataset Construction** — sampling units, baseline and event-boosted sampling, stratification, train/val/test split (this document)
- **Section 8.4: Counting Ground Truth Schema** — counting reference domain (this document)
- **Section 8.5: Sampling Manifest Schema** — dataset-construction artifact (this document)
- **Section 9.2: Evaluation Inputs** — evaluation input domains and shared temporal context (this document)
- **Section 9.5.1: Counting Evaluation Purpose and Scope** — counting-evaluation scope (this document)
- **Section 9.5.2: Counting Matching Semantics** — counting-event matching semantics consumed by counting evaluation (this document)
- **Section 9.6.1: Evaluation Reporting and Comparison** — reporting and comparison layer consumed by evaluation (this document)

### 9.6 Evaluation Reporting and Comparison

#### 9.6.1 Purpose and Scope

**Purpose.**

This subsection defines the purpose and scope of evaluation reporting and comparison. It establishes what reporting governs, what it consumes, and what it does not define. It does not select a mandatory metric, introduce a numerical formula, define a threshold, or establish an acceptance criterion.

**Scope.**

Evaluation reporting is a presentation and interpretation layer built on the already-defined evaluation domains. It consumes evaluation results produced under the semantics established by Sections 9.3, 9.4, and 9.5:

- **Detection Evaluation** — Section 9.3
- **Tracking Evaluation** — Section 9.4
- **Counting Evaluation** — Section 9.5

Reporting does not redefine those evaluation domains and does not replace them.

**Reporting consumes evaluation results, not raw inputs.**

Reporting consumes the results produced by the evaluation domains established in Sections 9.3–9.5. It does not consume Ground Truth or production output directly as its own evaluation mechanism, and it does not introduce a new comparison process.

**Ground Truth and production output remain separate.**

Reporting preserves the distinction between the Ground Truth domain and the production output domain:

- **Ground Truth** — Detection Ground Truth (Section 8.2), Tracking Ground Truth (Section 8.3), Counting Ground Truth (Section 8.4).
- **Production output** — production detections, production tracking output, production counting output.

Reporting presents results about these two domains; it does not merge them and does not reinterpret their fields, enums, ranges, or identity spaces.

**`global_id` and `track_id` remain different identity spaces.**

`global_id` is the Ground Truth identity defined by Section 8.3. `track_id` is the production tracking identity produced by the production tracker. They are different identity spaces and are never equated. Reporting does not create an identity-conversion rule and does not merge the two identity spaces.

**Reporting does not redefine evaluation semantics.**

Reporting does not redefine detection matching, tracking matching, or counting event correspondence. It does not redefine metric formulas, metric thresholds, metric selection, or metric aggregation. It does not redefine sampling, partitioning, leakage rules, Ground Truth schemas, or production behavior.

**No mandatory or preferred metric is established.**

Reporting does not select a mandatory metric, a preferred metric, a new metric, an acceptance criterion, a ranking rule, a statistical test, confidence intervals, significance levels, confidence scores, weighting rules, macro/micro averaging, class weighting, temporal weighting, partition weighting, cross-video aggregation, normalization, rounding, clipping, epsilon handling, zero-denominator handling, benchmark ranking rules, model selection rules, or pass/fail criteria. It does not define "better model" mathematically, does not define how models are ranked, and does not define statistical significance. Any such concept is outside the scope of this subsection.

**Sampling is consumed as established.**

Reporting consumes the established evaluation frame domain from Sections 7, 8.5, and 9.2. It does not create samples, does not modify the Sampling Manifest, does not change sampling reasons, does not change split(frame_id), does not alter partition boundaries, does not change excluded frames, and does not control runtime frame processing. The Sampling Manifest remains a dataset-construction artifact and evaluation-input record, not a runtime controller, not a production output, and not a model prediction.

**Ground Truth and production behavior are unchanged.**

Ground Truth is fixed independently of model execution. Reporting does not modify Ground Truth, does not modify production outputs, does not modify YOLO inference, does not modify ByteTrack, and does not modify runtime counting. Reporting is not part of the production inference pipeline.

**What this subsection does not define.**

This subsection defines only purpose and scope. It does not define metrics, formulas, thresholds, acceptance criteria, ranking rules, statistical rules, confidence intervals, error categories, aggregation rules, matching rules, sampling rules, or production behavior. It does not introduce new fields, new schema fields, new annotation rules, new identity namespaces, or new production behavior. It does not redefine any rule established in Sections 1–8 or in Sections 9.1–9.5.

- **Section 2: Annotation Rules (General)** — class labels, frame referencing, coordinate system (this document)
- **Section 7: Temporal Sampling and Dataset Construction** — sampling units, baseline and event-boosted sampling, stratification, train/val/test split (this document)
- **Section 8.2: Detection Ground Truth Schema** — per-frame content of sampled frames (this document)
- **Section 8.3: Tracking Ground Truth Schema** — per-object content of sampled frames (this document)
- **Section 8.4: Counting Ground Truth Schema** — counting reference domain (this document)
- **Section 8.5: Sampling Manifest Schema** — dataset-construction artifact (this document)
- **Section 9.2: Evaluation Inputs** — evaluation input domains and shared temporal context (this document)
- **Section 9.3: Detection Evaluation** — detection-evaluation domain consumed by reporting (this document)
- **Section 9.4: Tracking Evaluation** — tracking-evaluation domain consumed by reporting (this document)
- **Section 9.5: Counting Evaluation** — counting-evaluation domain consumed by reporting (this document)
- Section 9.6.2: Evaluation Reporting Semantics

#### 9.6.2 Evaluation Reporting Semantics

**Purpose.**

This subsection defines the conceptual semantics of evaluation reporting. It explains how evaluation results produced by the already-established evaluation domains may be represented and recorded. It does not introduce a new evaluation metric, formula, threshold, ranking rule, statistical rule, or acceptance criterion.

**Scope.**

Reporting is a presentation and recording layer over evaluation results. It is strictly downstream of the evaluation domains established in Sections 9.3, 9.4, and 9.5, and of the purpose and scope established in Section 9.6.1. It consumes evaluation results; it does not produce them.

**Reporting consumes evaluation results, not raw inputs.**

Reporting consumes the evaluation results produced by detection evaluation (Section 9.3), tracking evaluation (Section 9.4), and counting evaluation (Section 9.5). It does not consume Ground Truth or production output directly as its own evaluation mechanism, and it does not introduce a new comparison process.

**Reporting is a presentation/recording layer, not a new annotation layer.**

Reporting represents and records evaluation results. It does not create new annotations, new annotation rules, or new evaluation domains. It does not replace detection evaluation, tracking evaluation, or counting evaluation.

**Reporting preserves the distinction between evaluation domains.**

Reporting must preserve the distinction between:

- Detection evaluation results
- Tracking evaluation results
- Counting evaluation results

Each result remains attributable to the evaluation domain that produced it. Reporting does not merge results from different domains into a single undifferentiated record.

**Reporting preserves the distinction between Ground Truth, production predictions, and evaluation results.**

Reporting must preserve the distinction between:

- Ground Truth
- Production predictions
- Evaluation results derived from their comparison

Reporting presents results about the Ground Truth domain and the production output domain. It does not merge these domains and does not reinterpret their fields, enums, ranges, or identity spaces.

**Reporting must not modify Ground Truth.**

Reporting does not modify Ground Truth. Ground Truth is fixed independently of model execution and of reporting.

**Reporting must not modify production behavior.**

Reporting does not modify production detections, production tracking, production counting, or runtime pipeline behavior. Reporting is not part of the production inference pipeline and does not affect YOLO inference, ByteTrack, or runtime counting.

**Reporting may identify evaluation domain and evaluation input context.**

Reporting may identify the evaluation domain that produced a result and the relevant evaluation input context. It must not invent new schema fields or new identity namespaces.

**Existing identities remain in their existing domains.**

- Ground Truth uses `global_id` where applicable.
- Production tracking uses `track_id`.
- Detection evaluation remains identity-free.
- Counting Ground Truth `event_id` remains the schema-defined Ground Truth event identifier.

`global_id` and `track_id` remain different identity spaces and are never equated. Reporting does not create an identity-conversion rule and does not merge the two identity spaces.

**Reporting preserves the established evaluation frame domain and partition context.**

Reporting consumes the established evaluation frame domain from Sections 7, 8.5, and 9.2. It preserves the established partition context and does not alter partition boundaries, split(frame_id), or excluded frames.

**Reporting must not create new samples or alter the Sampling Manifest.**

Reporting does not create samples, does not modify the Sampling Manifest, does not change sampling reasons, and does not control runtime frame processing. The Sampling Manifest remains a dataset-construction artifact and evaluation-input record, not a runtime controller, not a production output, and not a model prediction.

**Reporting preserves reproducibility context as established.**

Reporting preserves the reproducibility context already established by Sections 7, 8.5, and 9.2. It does not invent additional reproducibility requirements.

**Reporting must not silently combine evaluation domains.**

Reporting must not silently combine detection, tracking, and counting results into a new metric or a new evaluation domain. Each result remains attributable to the evaluation domain that produced it.

**Aggregation or comparison across evaluation domains is deferred.**

Any aggregation or comparison that spans evaluation domains remains conceptually separate from the metric-definition layer. Such aggregation or comparison is not defined here and is deferred to later subsections if needed.

**What this subsection does not define.**

This subsection defines only the conceptual semantics of evaluation reporting. It does not define metrics, metric formulas, precision, recall, F1, AP/mAP, MOTA/MOTP/IDF1/HOTA, MAE/RMSE, count-error formulas, event-detection formulas, normalization, averaging, weighting, macro/micro averaging, confidence weighting, class weighting, temporal weighting, partition weighting, cross-video aggregation, statistical tests, confidence intervals, p-values, significance levels, effect sizes, ranking rules, "better model" rules, acceptance criteria, pass/fail thresholds, minimum performance thresholds, regression thresholds, tolerance values, score cutoffs, matching thresholds, confidence thresholds, IoU thresholds, temporal tolerances, distance thresholds, new identities, new IDs, new schema fields, new schema constraints, new sampling rules, new leakage rules, or new production behavior. It does not redefine detection matching, tracking matching, or counting matching. It does not redefine any rule established in Sections 1–8 or in Sections 9.1–9.5.

- **Section 9.3: Detection Evaluation** — detection-evaluation domain consumed by reporting (this document)
- **Section 9.4: Tracking Evaluation** — tracking-evaluation domain consumed by reporting (this document)
- **Section 9.5: Counting Evaluation** — counting-evaluation domain consumed by reporting (this document)
- **Section 9.6.1: Evaluation Reporting and Comparison** — reporting and comparison purpose and scope (this document)
- Section 9.6.3: Evaluation Comparison Semantics

#### 9.6.3 Evaluation Comparison Semantics

**Purpose.**

This subsection defines the conceptual semantics of comparing already-produced evaluation results. It establishes what comparison means at the protocol level. It does not select a metric, a formula, a threshold, a ranking rule, a statistical test, an acceptance criterion, or a definition of which model is "better".

**Scope.**

Comparison is a conceptual layer that consumes the evaluation-result layer established by Section 9.6.2. It operates on evaluation results already produced by detection evaluation (Section 9.3), tracking evaluation (Section 9.4), and counting evaluation (Section 9.5). It does not produce evaluation results and does not replace the reporting layer.

**Comparison operates on already-generated evaluation results.**

Comparison operates on evaluation results. It does not operate on Ground Truth directly as a comparison mechanism, and it does not operate on production predictions directly as a comparison mechanism.

**Comparison does not generate new Ground Truth.**

Comparison does not generate new Ground Truth. Ground Truth is fixed independently of model execution and of comparison.

**Comparison does not generate new production predictions.**

Comparison does not generate new production predictions. It does not produce detections, tracking output, or counting output.

**Comparison does not alter the evaluation inputs.**

Comparison does not alter the evaluation inputs established in Section 9.2. It does not reinterpret their fields, enums, ranges, or identity spaces.

**Comparison does not alter the Sampling Manifest.**

Comparison does not modify the Sampling Manifest, does not change sampling reasons, and does not change split(frame_id). The Sampling Manifest remains a dataset-construction artifact and evaluation-input record.

**Comparison does not rerun or modify the production pipeline.**

Comparison does not rerun or modify the production pipeline. It does not affect YOLO inference, ByteTrack, or runtime counting. Comparison is not part of the production inference pipeline.

**Comparison preserves the evaluation domain of each result.**

Comparison must preserve the evaluation domain:

- Detection results remain detection results.
- Tracking results remain tracking results.
- Counting results remain counting results.

Each result remains attributable to the evaluation domain that produced it.

**Comparison must not silently merge evaluation domains.**

Results from different evaluation domains must not be silently treated as the same metric or the same evaluation target. Comparison does not combine detection, tracking, and counting results into a single undifferentiated comparison target.

**Comparison may place result sets side by side.**

A comparison may conceptually place two or more evaluation-result sets side by side, provided their evaluation domains and contexts remain identifiable. Comparison does not require result sets to share a metric definition or an evaluation target.

**Comparison preserves the provenance of each result set.**

Comparison must preserve the provenance and context of each result set, including the established evaluation domain and evaluation-input context. Each result set remains attributable to the evaluation domain and context that produced it.

**Comparison must not imply that Ground Truth has changed.**

Comparison must not imply that Ground Truth has changed merely because production results differ. Ground Truth is fixed. Differences between result sets remain differences in reported evaluation outcomes.

**Differences remain reported evaluation outcomes.**

Differences between result sets remain differences in reported evaluation outcomes unless a later subsection explicitly defines a formal decision procedure. This subsection does not define how such differences are resolved.

**Comparison preserves established identities.**

Comparison must preserve:

- `global_id` as the Ground Truth identity where applicable,
- `track_id` as the production tracking identity,
- identity-free detection evaluation,
- Counting Ground Truth `event_id` as a Ground Truth event identifier.

`global_id` and `track_id` remain different identity spaces and are never equated. Comparison does not create an identity-conversion rule and does not merge the two identity spaces.

**Comparison must not create a new identity namespace.**

Comparison must not create a new identity namespace for comparing results. It does not introduce comparison identifiers, result identifiers, model identifiers, or evaluation identifiers. It does not introduce `comparison_id`, `result_id`, `model_id`, `evaluation_id`, `matched_id`, `comparison_identity`, `predicted_global_id`, `production_global_id`, or `generated_global_id`.

**Comparison preserves partition and frame-domain context.**

Comparison must preserve the partition and frame-domain context already established by Sections 7, 8.5, 9.2, and 9.6.2. It consumes the established evaluation domain and does not alter partition boundaries, split(frame_id), or excluded frames.

**Comparison remains reproducible.**

Comparison must remain reproducible using the already-established evaluation inputs and reporting context. It does not introduce additional reproducibility requirements.

**Formal decision procedures are deferred.**

Any formal ranking, statistical decision, acceptance criterion, or "better/worse" determination must be explicitly deferred to a later subsection. This subsection does not define a ranking algorithm, a decision procedure, or a determination of which model is better.

**What this subsection does not define.**

This subsection defines only the conceptual semantics of comparing evaluation results. It does not define a preferred metric, a mandatory metric, a comparison metric, a score, a composite score, a weighted score, a ranking formula, a model leaderboard rule, "higher is better", "lower is better", "model A is better than model B", pass/fail criteria, acceptance thresholds, regression thresholds, minimum improvement thresholds, tolerance values, statistical tests, p-values, confidence intervals, significance levels, effect sizes, statistical power, hypothesis tests, confidence requirements, metric aggregation formulas, macro/micro averaging, weighted averaging, class weighting, temporal weighting, partition weighting, cross-video aggregation, cross-class aggregation, normalization, calibration, score normalization, ranking by precision, ranking by recall, ranking by F1, ranking by AP/mAP, ranking by MOTA/MOTP/IDF1/HOTA, ranking by MAE/RMSE, ranking by counting error, matching thresholds, IoU thresholds, confidence thresholds, temporal tolerances, distance thresholds, new schema fields, new IDs, new identity namespaces, new sampling rules, new leakage rules, or new production behavior. It does not redefine detection matching, tracking matching, counting matching, metric definitions, evaluation inputs, sampling, Ground Truth schemas, or production behavior. It does not redefine any rule established in Sections 1–8 or in Sections 9.1–9.6.2.

- **Section 9.3: Detection Evaluation** — detection-evaluation domain consumed by reporting and comparison (this document)
- **Section 9.4: Tracking Evaluation** — tracking-evaluation domain consumed by reporting and comparison (this document)
- **Section 9.5: Counting Evaluation** — counting-evaluation domain consumed by reporting and comparison (this document)
- **Section 9.6.1: Evaluation Reporting and Comparison** — reporting and comparison purpose and scope (this document)
- **Section 9.6.2: Evaluation Reporting Semantics** — reporting layer consumed by comparison (this document)
- Section 9.6.4: Statistical and Decision Semantics

#### 9.6.4 Statistical and Decision Semantics

**Purpose.**

This subsection defines the conceptual boundary between evaluation results, statistical analysis, and formal decision procedures. It states what a future formal statistical/decision layer would mean and what remains outside the current protocol. It does not select or prescribe a statistical test, significance threshold, confidence level, acceptance criterion, ranking rule, or "better model" rule.

**Scope.**

This subsection is the final conceptual boundary of the Evaluation Reporting and Comparison section. It is strictly downstream of evaluation and reporting. It consumes evaluation results as established by Sections 9.6.2 and 9.6.3 and does not produce them.

**Four-layer architecture.**

The Evaluation Reporting and Comparison section is composed of four conceptually distinct layers:

- **9.6.1** — explains why the reporting/comparison section exists.
- **9.6.2** — explains what an evaluation report represents.
- **9.6.3** — explains what comparison of evaluation results represents.
- **9.6.4** — explains the conceptual boundary for statistical analysis and formal decision-making.

This subsection does not implement a statistical or decision procedure.

**Statistical analysis operates on already-generated evaluation results.**

Statistical analysis, when performed, operates on evaluation results. It does not operate on Ground Truth or production predictions directly as its own analysis mechanism.

**Statistical analysis does not create or modify Ground Truth.**

Statistical analysis does not create or modify Ground Truth. Ground Truth is fixed independently of model execution and of statistical analysis.

**Statistical analysis does not create or modify production predictions.**

Statistical analysis does not create or modify production predictions. It does not produce detections, tracking output, or counting output.

**Statistical analysis does not modify evaluation inputs.**

Statistical analysis does not modify the evaluation inputs established in Section 9.2. It does not reinterpret their fields, enums, ranges, or identity spaces.

**Statistical analysis does not modify the Sampling Manifest.**

Statistical analysis does not modify the Sampling Manifest, does not change sampling reasons, and does not change split(frame_id). The Sampling Manifest remains a dataset-construction artifact and evaluation-input record.

**Statistical analysis does not rerun or alter the production pipeline.**

Statistical analysis does not rerun or alter the production pipeline. It does not affect YOLO inference, ByteTrack, or runtime counting. Statistical analysis is not part of the production inference pipeline.

**Statistical analysis preserves the evaluation domain of the underlying results.**

Statistical analysis must preserve the evaluation domain of the underlying results:

- Detection results remain detection results.
- Tracking results remain tracking results.
- Counting results remain counting results.

**Statistical analysis must not silently combine evaluation domains.**

Statistical analysis must not silently combine fundamentally different evaluation domains. It does not merge detection, tracking, and counting results into a single undifferentiated analysis target.

**Statistical analysis preserves provenance and context.**

Any statistical analysis must preserve the provenance and context of the evaluation results being analyzed, including the established evaluation domain and evaluation-input context.

**Formal decision procedures operate on reported evaluation results.**

Any formal decision procedure must operate on reported evaluation results rather than changing the underlying Ground Truth or production outputs.

**A statistical difference must not be interpreted as a change to Ground Truth.**

A statistical difference, if established by a separately defined method, must not be interpreted as a change to Ground Truth. Ground Truth is fixed. A statistical difference remains a difference in reported evaluation outcomes.

**Statistical analysis and decision-making are downstream of evaluation and reporting.**

Statistical analysis and formal decision-making are conceptually downstream of evaluation and reporting. They consume evaluation results; they do not produce them.

**This subsection does not select a statistical test or decision rule.**

The current subsection does NOT select:

- a statistical test,
- a null hypothesis,
- an alternative hypothesis,
- a significance level,
- a p-value threshold,
- a confidence level,
- a confidence interval method,
- an effect-size threshold,
- a power requirement,
- a multiple-comparison correction,
- or an acceptance criterion.

**This subsection does not define model quality or deployment status.**

The current subsection does NOT define what constitutes:

- a better model,
- a worse model,
- an acceptable model,
- an unacceptable model,
- a regression,
- an improvement,
- or a deployment decision.

**Formal statistical and decision procedures are deferred.**

Formal statistical and decision procedures, if required later, must be specified separately without altering the established Ground Truth, production, evaluation, or sampling semantics. This subsection does not define them.

**Statistical analysis preserves established identities.**

Statistical analysis must preserve:

- `global_id` as the Ground Truth identity where applicable,
- `track_id` as the production tracking identity,
- identity-free detection evaluation,
- Counting Ground Truth `event_id` as the Ground Truth event identifier.

`global_id` and `track_id` remain different identity spaces and are never equated. Statistical analysis does not create an identity-conversion rule and does not merge the two identity spaces.

**No new identity namespace is introduced.**

No new identity namespace may be introduced for statistical analysis or decision-making. This subsection does not introduce statistical identifiers, decision identifiers, comparison identifiers, result identifiers, model identifiers, or evaluation identifiers. It does not introduce `statistical_id`, `decision_id`, `comparison_id`, `result_id`, `model_id`, `evaluation_id`, `matched_id`, `analysis_id`, `hypothesis_id`, `predicted_global_id`, `generated_global_id`, or `production_global_id`.

**Statistical analysis preserves frame, partition, split, and evaluation-domain context.**

Statistical analysis must preserve the established frame, partition, split, and evaluation-domain context. It consumes the established evaluation domain and does not alter partition boundaries, split(frame_id), or excluded frames.

**Statistical analysis remains reproducible.**

Statistical analysis must remain reproducible from the established evaluation inputs and reported evaluation results. It does not invent additional reproducibility requirements. Statistical analysis must be traceable to the established evaluation results and their evaluation context.

**Statistical analysis must not retroactively change evaluation result generation.**

Statistical analysis must not retroactively change the evaluation result-generation process. Changing a statistical-analysis implementation must not silently change Ground Truth or production outputs.

**What this subsection does not define.**

This subsection defines only the conceptual boundary for statistical analysis and formal decision-making. It does not define a t-test, paired t-test, independent t-test, Wilcoxon test, Mann-Whitney test, bootstrap, permutation test, McNemar test, chi-square test, ANOVA, Bayesian test, or any named statistical test. It does not define a null hypothesis, an alternative hypothesis, a p-value, a p-value threshold, an alpha, a significance level, a confidence level, a confidence interval, an effect size, statistical power, a sample-size requirement, a multiple-comparison correction, a Bonferroni correction, a false-discovery-rate correction, or a hypothesis-testing rule. It does not define "statistically significant", "practically significant", "meaningful improvement", "meaningful regression", "better model", "worse model", "preferred model", "best model", "acceptable model", "production-ready", or "deployment-ready". It does not define a pass/fail threshold, a minimum improvement, a maximum regression, a tolerance, an acceptance threshold, a rejection threshold, a deployment threshold, a quality gate, a regression gate, a leaderboard rule, a ranking rule, or a score cutoff. It does not define metric formulas, comparison formulas, aggregation formulas, weighting formulas, normalization, macro/micro averaging, class weighting, temporal weighting, partition weighting, cross-video aggregation, or cross-class aggregation. It does not define new schema fields, new IDs, new identity namespaces, new sampling rules, new leakage rules, or new production behavior. It does not redefine detection matching, tracking matching, counting matching, metric definitions, evaluation inputs, sampling, Ground Truth schemas, or production behavior. It does not redefine any rule established in Sections 1–8 or in Sections 9.1–9.6.3.

- **Section 9.3: Detection Evaluation** — detection-evaluation domain consumed by reporting, comparison, and statistical analysis (this document)
- **Section 9.4: Tracking Evaluation** — tracking-evaluation domain consumed by reporting, comparison, and statistical analysis (this document)
- **Section 9.5: Counting Evaluation** — counting-evaluation domain consumed by reporting, comparison, and statistical analysis (this document)
- **Section 9.6.1: Evaluation Reporting and Comparison** — reporting and comparison purpose and scope (this document)
- **Section 9.6.2: Evaluation Reporting Semantics** — reporting layer consumed by comparison and statistical analysis (this document)
- **Section 9.6.3: Evaluation Comparison Semantics** — comparison layer consumed by statistical analysis (this document)
- **Section 9.7.1: Formal Statistical and Decision Procedures — Purpose and Scope** — formal statistical and decision layer, downstream of evaluation, reporting, and comparison (this document)

---

### 9.7 Formal Statistical and Decision Procedures

#### 9.7.1 Purpose and Scope

**Purpose.**

This subsection defines the purpose and scope of formal statistical and decision procedures. It establishes what a formal statistical/decision layer governs, what it consumes, and what it does not define. It does not select or prescribe a statistical test, a significance threshold, a confidence level, an acceptance criterion, a ranking rule, a decision rule, or a definition of which model is "better".

**Scope.**

Formal statistical and decision procedures are a downstream layer built on the already-established evaluation, reporting, and comparison layers. They consume evaluation results produced under the semantics established by Sections 9.3, 9.4, and 9.5, and reported/comparison-ready results established by Section 9.6. They do not produce evaluation results and do not replace the evaluation, reporting, or comparison layers.

**Formal statistical analysis operates on already-generated evaluation results.**

Formal statistical analysis operates on evaluation results. It does not operate on Ground Truth or production predictions directly as its own analysis mechanism, and it does not introduce a new evaluation process.

**Formal statistical analysis does not generate Ground Truth.**

Formal statistical analysis does not generate Detection Ground Truth, Tracking Ground Truth, or Counting Ground Truth. Ground Truth is fixed independently of model execution, evaluation, reporting, comparison, statistical analysis, and decision procedures.

**Formal statistical analysis does not generate production predictions.**

Formal statistical analysis does not generate production detections, production tracking output, or production counting output. It does not produce detections, tracking output, or counting output.

**Formal statistical analysis does not rerun or modify the production pipeline.**

Formal statistical analysis does not rerun, modify, or control the production pipeline. It does not affect YOLO inference, ByteTrack, runtime counting, production frame processing, or production runtime behavior. Formal statistical analysis is not part of the production inference pipeline.

**Ground Truth, production predictions, evaluation results, reported/comparison results, statistical analysis, and formal decision procedures remain distinct.**

The distinction between Ground Truth, production predictions, evaluation results, reported/comparison results, statistical analysis, and formal decision procedures must remain explicit. No layer merges these domains or reinterprets their fields, enums, ranges, or identity spaces.

**Detection evaluation remains identity-free.**

Detection evaluation remains identity-free. It does not use `global_id`, does not use `track_id`, and does not use cross-frame identity.

**Tracking Ground Truth continues to use `global_id`.**

Tracking Ground Truth continues to use `global_id` as the Ground Truth identity defined by Section 8.3.

**Production tracking continues to use `track_id`.**

Production tracking continues to use `track_id` as the production tracking identity produced by the production tracker.

**`global_id` and `track_id` remain different identity spaces.**

`global_id` and `track_id` remain different identity spaces and are never equated. Formal statistical analysis does not create an identity-conversion rule and does not merge the two identity spaces.

**No identity-conversion rule is introduced.**

No identity-conversion rule is introduced. `global_id`, `track_id`, and `event_id` are not redefined.

**Counting Ground Truth `event_id` remains the schema-defined Ground Truth event identifier.**

Counting Ground Truth `event_id` remains the schema-defined Ground Truth event identifier, as established by Section 8.4.

**No new identity namespace is introduced.**

No new identity namespace may be introduced for statistical analysis or decision-making. This subsection does not introduce statistical identifiers, decision identifiers, comparison identifiers, result identifiers, model identifiers, or evaluation identifiers. It does not introduce `statistical_id`, `decision_id`, `analysis_id`, `hypothesis_id`, `comparison_id`, `result_id`, `model_id`, `evaluation_id`, `matched_id`, `reporting_id`, `ranking_id`, `predicted_global_id`, `generated_global_id`, `production_global_id`, `comparison_identity`, or any other new identity namespace.

**Statistical analysis consumes the established evaluation frame domain and partition context.**

Statistical analysis consumes the established evaluation frame domain from Sections 7, 8.5, 9.2, and 9.6. It does not create new samples, does not redefine sampling, does not alter split(frame_id), does not alter partition boundaries, does not alter excluded frames, does not alter leakage rules, does not regenerate the Sampling Manifest, does not change runtime sampling, and does not change production frame rate.

**The Sampling Manifest remains a dataset-construction artifact and evaluation-input record.**

The Sampling Manifest remains a dataset-construction artifact and evaluation-input record. It is NOT a statistical-analysis controller, a decision controller, a runtime controller, a production output, or a model prediction.

**Formal statistical and decision procedures are downstream of evaluation and reporting.**

Formal statistical and decision procedures are conceptually downstream of evaluation and reporting. They consume established results rather than retroactively changing how those results were generated.

**Any formal procedure defined later must preserve provenance and evaluation-domain context.**

Any formal procedure defined later must preserve the provenance and evaluation-domain context of the results it analyzes, including the established evaluation domain and evaluation-input context.

**Detection, tracking, and counting results must remain distinguishable.**

Detection, tracking, and counting results must remain distinguishable. Formal statistical analysis must not silently merge detection, tracking, and counting into an undefined unified target.

**Reproducibility context remains preserved.**

Reproducibility context established by Sections 7, 8.5, 9.2, and 9.6 remains preserved. This subsection does not silently create new reproducibility requirements.

**What this subsection does not define.**

This subsection defines only purpose and scope. It does not define a statistical test, a null hypothesis, an alternative hypothesis, a significance level, a p-value threshold, a confidence level, a confidence interval method, an effect-size threshold, statistical power, a sample-size requirement, a multiple-comparison correction, a Bonferroni correction, a false-discovery-rate correction, or a hypothesis-testing rule. It does not define "statistically significant", "practically significant", "meaningful improvement", "meaningful regression", "better model", "worse model", "preferred model", "best model", "acceptable model", "unacceptable model", "production-ready", or "deployment-ready". It does not define a pass/fail decision, a regression gate, a quality gate, a deployment gate, a minimum improvement, a maximum regression, a tolerance, an acceptance criterion, a rejection criterion, a ranking rule, a leaderboard rule, a composite score, a decision score, a metric, a formula, an aggregation rule, a weighting rule, a normalization rule, or a ranking score. It does not define new schema fields, new IDs, new identity namespaces, new sampling rules, new leakage rules, or new production behavior. It does not redefine detection matching, tracking matching, counting matching, metric definitions, evaluation inputs, sampling, Ground Truth schemas, or production behavior. It does not redefine any rule established in Sections 1–8 or in Sections 9.1–9.6.

- **Section 9.3: Detection Evaluation** — detection-evaluation domain consumed by reporting, comparison, statistical analysis, and formal decision procedures (this document)
- **Section 9.4: Tracking Evaluation** — tracking-evaluation domain consumed by reporting, comparison, statistical analysis, and formal decision procedures (this document)
- **Section 9.5: Counting Evaluation** — counting-evaluation domain consumed by reporting, comparison, statistical analysis, and formal decision procedures (this document)
- **Section 9.6.1: Evaluation Reporting and Comparison** — reporting and comparison purpose and scope (this document)
- **Section 9.6.2: Evaluation Reporting Semantics** — reporting layer consumed by comparison and statistical analysis (this document)
- **Section 9.6.3: Evaluation Comparison Semantics** — comparison layer consumed by statistical analysis (this document)
- **Section 9.6.4: Statistical and Decision Semantics** — conceptual boundary consumed by formal statistical and decision procedures (this document)
- **Section 9.7.2: Formal Statistical and Decision Procedure Semantics** — procedure semantics consumed by later formal procedures (this document)

---

#### 9.7.2 Formal Statistical and Decision Procedure Semantics

**Purpose.**

This subsection defines the conceptual semantics of formal statistical analysis and decision procedures. It establishes what formal statistical and decision procedures mean at the protocol level, what they consume, and what they do not define. It does not select or prescribe a statistical test, a significance threshold, a confidence level, an acceptance criterion, a ranking rule, a decision rule, or a definition of which model is "better".

**Scope.**

Formal statistical and decision procedure semantics are a downstream conceptual layer. They are strictly downstream of evaluation, evaluation reporting, and evaluation comparison. They consume evaluation results as established by Sections 9.3, 9.4, and 9.5, and reported/comparison-ready results as established by Section 9.6. They do not produce evaluation results and do not replace the evaluation, reporting, or comparison layers.

**Formal statistical procedures operate on already-generated evaluation results.**

Formal statistical procedures operate on evaluation results. They do not operate on Ground Truth or production predictions directly as their own analysis mechanism, and they do not introduce a new evaluation process.

**Formal statistical procedures are downstream of evaluation, reporting, and comparison.**

Formal statistical procedures are conceptually downstream of evaluation (Sections 9.3–9.5), evaluation reporting (Section 9.6.2), and evaluation comparison (Section 9.6.3). They consume the outputs of those layers; they do not produce them.

**Formal statistical procedures do not generate or modify Ground Truth.**

Formal statistical procedures do not generate or modify Ground Truth. Ground Truth is fixed independently of model execution, evaluation, reporting, comparison, statistical analysis, and decision procedures.

**Formal statistical procedures do not generate or modify production predictions.**

Formal statistical procedures do not generate or modify production predictions. They do not produce detections, tracking output, or counting output.

**Formal statistical procedures do not rerun or alter the production pipeline.**

Formal statistical procedures do not rerun or alter the production pipeline. They do not affect YOLO inference, ByteTrack, runtime counting, production frame processing, or production runtime behavior. Formal statistical procedures are not part of the production inference pipeline.

**Formal statistical procedures do not alter evaluation inputs.**

Formal statistical procedures do not alter the evaluation inputs established in Section 9.2. They do not reinterpret their fields, enums, ranges, or identity spaces.

**Formal statistical procedures do not alter the Sampling Manifest.**

Formal statistical procedures do not modify the Sampling Manifest, do not change sampling reasons, and do not change split(frame_id). The Sampling Manifest remains a dataset-construction artifact and evaluation-input record.

**Formal statistical procedures preserve the evaluation domain of the analyzed results.**

Formal statistical procedures must preserve the evaluation domain of the underlying results:
- Detection results remain detection results.
- Tracking results remain tracking results.
- Counting results remain counting results.

**Detection evaluation remains identity-free.**

Detection evaluation remains identity-free. It does not use `global_id`, does not use `track_id`, and does not use cross-frame identity.

**`global_id` remains the Ground Truth identity.**

`global_id` remains the Ground Truth identity defined by Section 8.3.

**`track_id` remains the production tracking identity.**

`track_id` remains the production tracking identity produced by the production tracker.

**`event_id` remains the schema-defined Ground Truth counting-event identifier.**

Counting Ground Truth `event_id` remains the schema-defined Ground Truth event identifier, as established by Section 8.4.

**`global_id` and `track_id` remain separate identity spaces.**

`global_id` and `track_id` remain different identity spaces and are never equated. Formal statistical procedures do not create an identity-conversion rule and do not merge the two identity spaces.

**No identity-conversion rule is introduced.**

No identity-conversion rule is introduced. `global_id`, `track_id`, and `event_id` are not redefined.

**Statistical procedures must not silently merge detection, tracking, and counting domains.**

Statistical procedures must not silently merge detection, tracking, and counting results into a single undifferentiated analysis target. Detection, tracking, and counting results must remain distinguishable.

**A statistical procedure operates on reported/evaluation results rather than changing how they were generated.**

A statistical procedure operates on reported or evaluation results. It must not retroactively modify previously generated evaluation results. Changing a statistical-procedure implementation must not silently change Ground Truth or production outputs.

**A decision procedure consumes the outcome of the statistical/comparison layer without modifying the underlying data.**

A decision procedure consumes the outcome of the statistical or comparison layer. It does not modify the underlying Ground Truth, production predictions, or evaluation results.

**Statistical procedures and decision procedures are conceptually distinct from production runtime behavior.**

Statistical procedures and decision procedures are conceptually distinct from production runtime behavior. They are not part of the production inference pipeline and do not affect YOLO inference, ByteTrack, or runtime counting.

**Formal procedures must preserve provenance and evaluation context.**

Any formal procedure must preserve the provenance and evaluation-domain context of the results it analyzes, including the established evaluation domain and evaluation-input context.

**The frame domain, partition context, and evaluation-domain context remain attached to the analyzed results.**

The frame domain, partition context, and evaluation-domain context remain attached to the analyzed results. Formal procedures consume the established evaluation domain and do not alter partition boundaries, split(frame_id), or excluded frames.

**Existing reproducibility context remains applicable.**

Reproducibility context established by Sections 7, 8.5, 9.2, and 9.6 remains applicable. This subsection does not introduce additional reproducibility requirements.

**Decision procedures must not retroactively modify Ground Truth, production predictions, or evaluation results.**

Decision procedures must not retroactively modify Ground Truth, production predictions, or evaluation results. A decision outcome remains a decision about reported evaluation outcomes, not a change to the underlying data.

**Later formal procedures are analysis/decision rules applied to existing evaluation outputs.**

Any formal procedure selected later must be treated as an analysis or decision rule applied to existing evaluation outputs rather than as a new annotation rule, a new matching rule, a new sampling rule, or a new production rule.

**What this subsection does not define.**

This subsection defines only the conceptual semantics of formal statistical and decision procedures. It does not define a t-test, paired t-test, independent t-test, Wilcoxon test, Mann-Whitney test, bootstrap, permutation test, McNemar test, chi-square test, ANOVA, Bayesian test, or any named statistical test. It does not define a null hypothesis, an alternative hypothesis, a significance level, a p-value threshold, a confidence level, a confidence interval method, an effect-size threshold, statistical power, a sample-size requirement, a multiple-comparison correction, a Bonferroni correction, a false-discovery-rate correction, or a hypothesis-testing rule. It does not define "statistically significant", "practically significant", "meaningful improvement", "meaningful regression", "better model", "worse model", "preferred model", "best model", "acceptable model", "unacceptable model", "production-ready", or "deployment-ready". It does not define a pass/fail decision, an acceptance criterion, a rejection criterion, a quality gate, a regression gate, a deployment gate, a minimum improvement, a maximum regression, a tolerance, an acceptance threshold, a rejection threshold, a ranking rule, a leaderboard rule, a model ordering rule, a score cutoff, a composite score, a decision score, a metric, a metric formula, an aggregation formula, a weighting rule, a normalization rule, a calibration rule, a statistical scoring rule, a new matching rule, a new sampling rule, a new leakage rule, a new reproducibility requirement, a new schema field, a new ID, or a new identity namespace. It does not redefine detection matching, tracking matching, counting matching, metric definitions, evaluation inputs, sampling, Ground Truth schemas, or production behavior. It does not redefine any rule established in Sections 1–8 or in Sections 9.1–9.7.1.

- **Section 9.3: Detection Evaluation** — detection-evaluation domain consumed by reporting, comparison, statistical analysis, and formal decision procedures (this document)
- **Section 9.4: Tracking Evaluation** — tracking-evaluation domain consumed by reporting, comparison, statistical analysis, and formal decision procedures (this document)
- **Section 9.5: Counting Evaluation** — counting-evaluation domain consumed by reporting, comparison, statistical analysis, and formal decision procedures (this document)
- **Section 9.6.1: Evaluation Reporting and Comparison** — reporting and comparison purpose and scope (this document)
- **Section 9.6.2: Evaluation Reporting Semantics** — reporting layer consumed by comparison and statistical analysis (this document)
- **Section 9.6.3: Evaluation Comparison Semantics** — comparison layer consumed by statistical analysis (this document)
- **Section 9.6.4: Statistical and Decision Semantics** — conceptual boundary consumed by formal statistical and decision procedures (this document)
- **Section 9.7.1: Formal Statistical and Decision Procedures — Purpose and Scope** — purpose and scope consumed by formal procedure semantics (this document)
- **Section 9.7.3: Formal Statistical Procedure Requirements** — formal procedure requirements consumed by later procedure-specific subsections (this document)

#### 9.7.3 Formal Statistical Procedure Requirements

**Purpose.**

This subsection defines the conceptual requirements that any future formal statistical procedure must satisfy. It establishes the boundary conditions under which such a procedure may operate. It does not select or prescribe a statistical test, a significance threshold, a confidence level, an acceptance criterion, a ranking rule, a decision rule, or a definition of which model is "better". Selection of the formal statistical method is explicitly deferred to a later procedure-specific subsection.

**Scope.**

Formal statistical procedure requirements apply to any formal statistical procedure introduced downstream of evaluation, reporting, comparison, and procedure semantics. They apply to procedures that consume evaluation results as established by Sections 9.3, 9.4, and 9.5, reported/comparison-ready results as established by Section 9.6, and procedure semantics as established by Section 9.7.2.

**A formal statistical procedure operates only on already-generated evaluation results and/or comparison results.**

A formal statistical procedure operates on already-generated evaluation results and/or comparison results. It does not operate on Ground Truth or production predictions directly as its own analysis mechanism, and it does not introduce a new evaluation process.

**A formal statistical procedure must identify the evaluation domain of the analyzed results.**

A formal statistical procedure must identify the evaluation domain of the results it analyzes. The domain is one of:
- Detection results (Section 9.3)
- Tracking results (Section 9.4)
- Counting results (Section 9.5)

**A formal statistical procedure must preserve provenance and evaluation context.**

A formal statistical procedure must preserve the provenance and evaluation-domain context of the results it analyzes, including the established evaluation domain and evaluation-input context.

**A formal statistical procedure must preserve the layer distinction.**

A formal statistical procedure must preserve the distinction between Ground Truth, production predictions, evaluation results, reporting/comparison outputs, and statistical analysis. No layer is collapsed into another.

**A formal statistical procedure must not generate new Ground Truth.**

A formal statistical procedure must not generate new Ground Truth. Ground Truth is fixed independently of model execution, evaluation, reporting, comparison, statistical analysis, and decision procedures.

**A formal statistical procedure must not generate new production predictions.**

A formal statistical procedure must not generate new production predictions. It does not produce detections, tracking output, or counting output.

**A formal statistical procedure must not rerun, modify, or control production runtime behavior.**

A formal statistical procedure must not rerun, modify, or control YOLO inference, ByteTrack, runtime counting, production frame processing, or production runtime behavior. It is not part of the production inference pipeline.

**A formal statistical procedure must not modify previously generated evaluation results.**

A formal statistical procedure must not modify previously generated evaluation results. It operates on reported or evaluation results rather than changing how they were generated.

**A formal statistical procedure must not modify the Sampling Manifest.**

A formal statistical procedure must not modify the Sampling Manifest, must not change sampling reasons, and must not change split(frame_id). The Sampling Manifest remains a dataset-construction artifact and evaluation-input record.

**A formal statistical procedure must not create new evaluation samples.**

A formal statistical procedure must not create new evaluation samples. It does not introduce new annotation records, new matching records, new detection records, new tracking records, or new counting records.

**Existing frame-domain and partition context must remain identifiable.**

The frame domain, partition context, and evaluation-domain context must remain identifiable, including context established by Sections 7, 8.5, and 9.2. A formal statistical procedure must not alter partition boundaries, split(frame_id), or excluded frames.

**A formal statistical procedure must preserve existing identity semantics.**

A formal statistical procedure must preserve existing identity semantics:
- `global_id` remains the Ground Truth tracking identity (Section 8.3)
- `track_id` remains the production tracking identity
- `event_id` remains the schema-defined Ground Truth counting-event identifier (Section 8.4)
- Detection Evaluation remains identity-free

**`global_id` and `track_id` must remain separate identity spaces.**

`global_id` and `track_id` remain different identity spaces and are never equated. No identity-conversion rule may be introduced, and the two identity spaces must not be merged.

**No new identity namespace may be created.**

No new identity namespace may be created. `global_id`, `track_id`, and `event_id` are not redefined, and no new working identity is introduced.

**A formal statistical procedure must operate within the evaluation domain of its input results.**

A formal statistical procedure must operate within the evaluation domain represented by the input results. It does not reinterpret the fields, enums, or ranges of a different evaluation domain.

**Detection, tracking, and counting results must not be silently merged.**

A formal statistical procedure must not silently merge detection, tracking, and counting results into a single undifferentiated statistical target. Detection, tracking, and counting results must remain distinguishable.

**Any formal statistical procedure must be traceable to evaluation results and established provenance.**

Any formal statistical procedure must be traceable to the evaluation results it analyzes and to their established provenance and context. It must not introduce results that cannot be traced to evaluation results.

**Existing reproducibility context must be preserved.**

Reproducibility context established by Sections 7, 8.5, 9.2, and 9.6 must be preserved. This subsection does not introduce additional reproducibility requirements.

**This subsection defines requirements and boundaries only.**

This subsection defines requirements and boundaries only. It does not select a statistical test.

**Selection of the formal statistical method is deferred.**

Selection of the formal statistical method is explicitly deferred to a later procedure-specific subsection. No statistical test, significance rule, or decision rule is selected or prescribed by this subsection.

**What this subsection does not define.**

This subsection defines only formal statistical procedure requirements and boundaries. It does not define a t-test, paired t-test, independent t-test, Wilcoxon test, Mann-Whitney test, bootstrap, permutation test, McNemar test, chi-square test, ANOVA, Bayesian test, or any named statistical test. It does not define a null hypothesis, an alternative hypothesis, a significance level, a p-value threshold, a confidence level, a confidence interval method, an effect-size threshold, statistical power, a sample-size requirement, a multiple-comparison correction, a Bonferroni correction, a false-discovery-rate correction, or a hypothesis-testing rule. It does not define "statistically significant", "practically significant", "meaningful improvement", "meaningful regression", "better model", "worse model", "preferred model", "best model", "acceptable model", "unacceptable model", "production-ready", or "deployment-ready". It does not define a pass/fail decision, an acceptance criterion, a rejection criterion, a quality gate, a regression gate, a deployment gate, a minimum improvement, a maximum regression, a tolerance, an acceptance threshold, a rejection threshold, a ranking rule, a leaderboard rule, a model ordering rule, a score cutoff, a composite score, a decision score, a metric, a metric formula, an aggregation formula, a weighting rule, a normalization rule, a calibration rule, a statistical scoring rule, a new matching rule, a new sampling rule, a new leakage rule, a new reproducibility requirement, a new schema field, a new ID, or a new identity namespace. It does not redefine detection matching, tracking matching, counting matching, metric definitions, evaluation inputs, sampling, Ground Truth schemas, or production behavior. It does not redefine any rule established in Sections 1–8 or in Sections 9.1–9.7.2.

- **Section 9.7: Formal Statistical and Decision Procedures** — formal statistical and decision layer, downstream of evaluation, reporting, and comparison (this document)
- **Section 9.7.1: Formal Statistical and Decision Procedures — Purpose and Scope** — purpose and scope of formal statistical and decision procedures (this document)
- **Section 9.7.2: Formal Statistical and Decision Procedure Semantics** — procedure semantics consumed by formal procedure requirements (this document)
- **Section 9.7.4: Formal Decision Procedure Requirements** — formal decision requirements downstream of statistical/comparison analysis (this document)

#### 9.7.4 Formal Decision Procedure Requirements

**Purpose.**

This subsection defines the conceptual requirements and boundaries that any future formal decision procedure must satisfy. It establishes the boundary conditions under which such a procedure may operate. It does not select or prescribe a decision rule, an acceptance criterion, a rejection criterion, a gate, a threshold, a ranking rule, or a definition of which model is "better". Selection of the actual formal decision procedure is explicitly deferred to a later, dedicated specification.

**Scope.**

Formal decision procedure requirements apply to any formal decision procedure introduced downstream of evaluation, reporting, comparison, and statistical analysis. They apply to procedures that consume evaluation results as established by Sections 9.3, 9.4, and 9.5, reported/comparison-ready results as established by Section 9.6, statistical analysis outcomes as established by Sections 9.6.4 and 9.7, and procedure semantics as established by Section 9.7.2.

**A formal decision procedure operates only on already-generated evaluation, reporting, comparison, and/or statistical outputs.**

A formal decision procedure operates only on already-generated outputs from the established evaluation, reporting, comparison, and/or statistical layers. It does not operate on Ground Truth or production predictions directly as its own decision mechanism, and it does not introduce a new evaluation process.

**A formal decision procedure is downstream of evaluation and analysis.**

A formal decision procedure is conceptually downstream of evaluation (Sections 9.3–9.5), evaluation reporting (Section 9.6.2), evaluation comparison (Section 9.6.3), and statistical analysis (Sections 9.6.4 and 9.7). It consumes the outputs of those layers; it does not produce them.

**A formal decision procedure does not generate new Ground Truth.**

A formal decision procedure does not generate new Ground Truth. Ground Truth is fixed independently of model execution, evaluation, reporting, comparison, statistical analysis, and decision procedures.

**A formal decision procedure does not generate new production predictions.**

A formal decision procedure does not generate new production predictions. It does not produce detections, tracking output, or counting output.

**A formal decision procedure does not rerun, modify, control, or configure the production pipeline.**

A formal decision procedure does not rerun, modify, control, or configure the production pipeline. It does not affect YOLO inference, ByteTrack, runtime counting, production frame processing, or production runtime behavior. A formal decision procedure is not part of the production inference pipeline.

**A formal decision procedure does not modify YOLO inference, ByteTrack, runtime counting, production frame processing, or production runtime behavior.**

A formal decision procedure does not modify YOLO inference, ByteTrack, runtime counting, production frame processing, or production runtime behavior. It does not configure, tune, or gate any of these components.

**A formal decision procedure does not modify previously generated evaluation results.**

A formal decision procedure does not modify previously generated evaluation results. It operates on reported or analysis outcomes rather than changing how they were generated.

**A formal decision procedure does not modify reporting or comparison results retroactively.**

A formal decision procedure does not modify reporting or comparison results retroactively. A decision outcome remains a decision about reported evaluation or analysis outcomes, not a change to the underlying data.

**A formal decision procedure must preserve the evaluation domain of the inputs it consumes.**

A formal decision procedure must preserve the evaluation domain of the inputs it consumes:
- Detection results remain detection results (Section 9.3)
- Tracking results remain tracking results (Section 9.4)
- Counting results remain counting results (Section 9.5)

**A formal decision procedure must not silently merge detection, tracking, and counting into a new undifferentiated decision domain.**

A formal decision procedure must not silently merge detection, tracking, and counting results into a single undifferentiated decision target. Detection, tracking, and counting results must remain distinguishable, and no combined decision domain is created.

**A formal decision procedure must preserve provenance and evaluation context.**

A formal decision procedure must preserve the provenance and evaluation-domain context of the inputs it consumes, including the established evaluation domain and evaluation-input context.

**A formal decision procedure must preserve frame-domain, partition/split, Sampling Manifest, and reproducibility context.**

A formal decision procedure must preserve the frame-domain context, the partition and split(frame_id) context, the Sampling Manifest context, and the reproducibility context established by Sections 7, 8.5, 9.2, and 9.6. It must not alter partition boundaries, split(frame_id), or excluded frames.

**A formal decision procedure does not create new evaluation samples.**

A formal decision procedure does not create new evaluation samples. It does not introduce new annotation records, new matching records, new detection records, new tracking records, or new counting records.

**A formal decision procedure does not modify temporal sampling, event-boosted sampling, split, partition boundaries, excluded frames, leakage rules, or Sampling Manifest generation.**

A formal decision procedure does not modify temporal sampling, event-boosted sampling, split(frame_id), partition boundaries, excluded frames, leakage rules, or Sampling Manifest generation. Sampling is already defined elsewhere and is not redefined here.

**The Sampling Manifest remains a dataset-construction artifact and evaluation-input record.**

The Sampling Manifest remains a dataset-construction artifact and evaluation-input record. It is not a decision controller, not a runtime controller, not production output, and not a model prediction.

**Existing identity semantics remain unchanged.**

A formal decision procedure must preserve existing identity semantics:
- `global_id` remains the Ground Truth tracking identity (Section 8.3)
- `track_id` remains the production tracking identity
- `event_id` remains the schema-defined Ground Truth counting-event identifier (Section 8.4)
- Detection Evaluation remains identity-free

**`global_id` and `track_id` remain separate identity spaces.**

`global_id` and `track_id` remain different identity spaces and are never equated. No identity-conversion rule may be introduced, and the two identity spaces must not be merged.

**No new identity namespace is introduced.**

No new identity namespace is introduced. `global_id`, `track_id`, and `event_id` are not redefined, and no new working identity is created.

**No new schema field, enum, validation rule, or schema responsibility is introduced.**

No new schema field, enum, validation rule, or schema responsibility is introduced. Established schema semantics remain authoritative.

**A formal decision procedure may conceptually consume a previously established statistical or comparison outcome.**

A formal decision procedure may conceptually consume a previously established statistical or comparison outcome. This subsection does not select the actual decision rule, and consuming an outcome does not modify it.

**Selection of the actual formal decision procedure is deferred.**

Selection of the actual formal decision procedure is explicitly deferred to a later, dedicated specification. No decision rule, acceptance criterion, rejection criterion, gate, threshold, or ranking rule is selected or prescribed by this subsection.

**Future formal decision procedures are downstream analysis/decision logic, not annotation, matching, sampling, production, or schema rules.**

Any formal decision procedure selected later must be treated as downstream analysis or decision logic applied to existing evaluation outputs rather than as a new annotation rule, a new matching rule, a new sampling rule, a new production rule, or a new schema rule.

**Reproducibility remains based on the established protocol context.**

Reproducibility remains based on the established protocol context. This subsection does not introduce new seeds, dataset-generation rules, runtime configuration, or execution requirements.

**What this subsection does not define.**

This subsection defines only formal decision procedure requirements and boundaries. It does not define a pass/fail decision, an acceptance criterion, a rejection criterion, a quality gate, a regression gate, a deployment gate, a deployment decision, production-readiness, or deployment-readiness. It does not define "better model", "worse model", "preferred model", "best model", "acceptable model", "unacceptable model", "meaningful improvement", "meaningful regression", "minimum improvement", "maximum regression", a tolerance, an acceptance threshold, a rejection threshold, a decision threshold, a ranking rule, a leaderboard rule, a model ordering rule, a score cutoff, a decision score, or a composite score. It does not define any metric, any metric formula, any comparison formula, any statistical test, a null hypothesis, an alternative hypothesis, an alpha, a significance level, a p-value threshold, a confidence level, a confidence interval method, an effect-size threshold, statistical power, a sample-size requirement, a multiple-comparison correction, a Bonferroni correction, a false-discovery-rate correction, a weighting rule, a normalization rule, a calibration rule, or an aggregation rule. It does not define any IoU threshold, confidence threshold, temporal threshold, distance threshold, matching threshold, event threshold, minimum duration, or minimum overlap. It does not introduce a new identity namespace or identifier such as a decision_id, decision_identity, result_id, evaluation_id, statistical_id, analysis_id, hypothesis_id, comparison_id, matched_id, model_id, reporting_id, ranking_id, predicted_global_id, generated_global_id, or production_global_id. It does not redefine detection matching, tracking matching, counting matching, metric definitions, evaluation inputs, sampling, Ground Truth schemas, or production behavior. It does not redefine any rule established in Sections 1–8 or in Sections 9.1–9.7.3.

- **Section 9.3: Detection Evaluation** — detection-evaluation domain consumed by reporting, comparison, statistical analysis, and formal decision procedures (this document)
- **Section 9.4: Tracking Evaluation** — tracking-evaluation domain consumed by reporting, comparison, statistical analysis, and formal decision procedures (this document)
- **Section 9.5: Counting Evaluation** — counting-evaluation domain consumed by reporting, comparison, statistical analysis, and formal decision procedures (this document)
- **Section 9.6.1: Evaluation Reporting and Comparison** — reporting and comparison purpose and scope (this document)
- **Section 9.6.2: Evaluation Reporting Semantics** — reporting layer consumed by comparison and statistical analysis (this document)
- **Section 9.6.3: Evaluation Comparison Semantics** — comparison layer consumed by statistical analysis (this document)
- **Section 9.6.4: Statistical and Decision Semantics** — conceptual boundary consumed by formal statistical and decision procedures (this document)
- **Section 9.7: Formal Statistical and Decision Procedures** — formal statistical and decision layer, downstream of evaluation, reporting, and comparison (this document)
- **Section 9.7.1: Formal Statistical and Decision Procedures — Purpose and Scope** — purpose and scope of formal statistical and decision procedures (this document)
- **Section 9.7.2: Formal Statistical and Decision Procedure Semantics** — procedure semantics consumed by formal procedure requirements (this document)
- **Section 9.7.3: Formal Statistical Procedure Requirements** — formal procedure requirements consumed by formal decision procedure requirements (this document)
- **Section 9.7.5: Formal Procedure Traceability and Reproducibility** — traceability and reproducibility requirements for later formal procedures (this document)

#### 9.7.5 Formal Procedure Traceability and Reproducibility

**Purpose.**

This subsection defines the conceptual traceability and reproducibility boundaries that any later formal statistical or decision procedure must satisfy. It establishes what must remain traceable and reproducible, and what must not be altered. It does not select or prescribe a statistical test, a decision rule, a metric, a formula, a threshold, a ranking rule, an acceptance criterion, or a production control mechanism.

**Scope.**

Formal procedure traceability and reproducibility requirements apply to any later formal statistical or decision procedure introduced downstream of evaluation, reporting, comparison, and analysis. They apply to procedures that consume evaluation results as established by Sections 9.3, 9.4, and 9.5, reported/comparison-ready results as established by Section 9.6, and procedure requirements and semantics as established by Sections 9.7.2, 9.7.3, and 9.7.4.

**Later formal procedures operate on already-established evaluation/reporting/comparison outputs.**

Later formal statistical and decision procedures operate on already-established evaluation, reporting, comparison, and analysis outputs. They do not operate on Ground Truth or production predictions directly as their own analysis or decision mechanism, and they do not introduce a new evaluation process.

**Any later formal procedure must remain traceable to the evaluation results and their established provenance/context.**

Any later formal procedure must remain traceable to the evaluation results it analyzes and to the provenance and evaluation context established for those results. A procedure outcome must not be presented as Ground Truth or as a production output.

**Traceability must preserve the evaluation domain.**

Traceability must preserve the evaluation domain of the inputs it consumes:
- Detection results remain detection results (Section 9.3)
- Tracking results remain tracking results (Section 9.4)
- Counting results remain counting results (Section 9.5)

**Traceability must preserve the evaluation frame domain and partition/split context.**

Traceability must preserve the evaluation frame domain and the partition and split(frame_id) context established by Sections 7, 8.5, 9.2, and 9.6. The frame domain, partition context, and evaluation-domain context remain attached to the analyzed results.

**Traceability must preserve the layer distinction.**

Traceability must preserve the distinction between Ground Truth, production predictions, evaluation results, reporting/comparison outputs, statistical analysis, and decision analysis. No layer is collapsed into another.

**A later formal procedure must not imply that a downstream analysis layer became the source of Ground Truth.**

A later formal procedure must not imply that a downstream analysis, reporting, or comparison layer became the source of Ground Truth. Ground Truth remains fixed independently of model execution, evaluation, reporting, comparison, statistical analysis, and decision procedures.

**A later formal procedure must not modify Ground Truth.**

A later formal procedure must not modify Ground Truth. Ground Truth is fixed and is not altered by any downstream procedure.

**A later formal procedure must not modify production predictions.**

A later formal procedure must not modify production predictions. It does not produce detections, tracking output, or counting output.

**A later formal procedure must not retroactively modify evaluation results.**

A later formal procedure must not retroactively modify previously generated evaluation results. It operates on reported or analysis outcomes rather than changing how they were generated.

**A later formal procedure must not rerun or alter the production pipeline.**

A later formal procedure must not rerun or alter YOLO inference, ByteTrack, runtime counting, production frame processing, or production runtime behavior. It is not part of the production inference pipeline.

**Reproducibility must remain grounded in the already-established inputs and context.**

Reproducibility must remain grounded in the already-established evaluation inputs and context. A later formal procedure must be reproducible from established inputs and context without changing how those inputs were generated.

**Existing reproducibility context must be preserved.**

Reproducibility context established by Sections 7, 8.5, 9.2, and 9.6 must be preserved. This subsection does not introduce additional reproducibility requirements.

**No new seeds, execution settings, dataset-generation rules, sampling rules, runtime configuration, or model-execution requirements are introduced.**

This subsection does not introduce new random seeds, execution settings, dataset-generation rules, sampling rules, runtime configuration, or model-execution requirements. Reproducibility rests on the protocol context already established.

**The Sampling Manifest remains a dataset-construction artifact and evaluation-input record.**

The Sampling Manifest remains a dataset-construction artifact and evaluation-input record. It is not a traceability controller, not a reproducibility controller, not a decision controller, not a runtime controller, not production output, and not a model prediction.

**A formal statistical or decision procedure must not modify sampling-related artifacts.**

A formal statistical or decision procedure must not modify the Sampling Manifest, split(frame_id), partition boundaries, excluded frames, sampling reasons, leakage rules, runtime sampling, or production frame rate. Sampling is already defined elsewhere and is not redefined here.

**Traceability must preserve existing identity semantics.**

Traceability must preserve existing identity semantics:
- `global_id` remains the Ground Truth tracking identity (Section 8.3)
- `track_id` remains the production tracking identity
- `event_id` remains the schema-defined Ground Truth counting-event identifier (Section 8.4)
- Detection Evaluation remains identity-free

**`global_id` and `track_id` remain separate identity spaces.**

`global_id` and `track_id` remain different identity spaces and are never equated. No identity-conversion rule may be introduced, and the two identity spaces must not be merged.

**No new identity namespace is introduced.**

No new identity namespace is introduced. `global_id`, `track_id`, and `event_id` are not redefined, and no new working identity is created.

**No new schema field, enum, constraint, validation rule, or identity field is introduced.**

No new schema field, enum, constraint, validation rule, or identity field is introduced. Established schema semantics remain authoritative.

**A later formal procedure must remain reproducible from established inputs/context.**

A later formal procedure must remain reproducible from established inputs and context without altering how those inputs were generated, sampled, split, or validated.

**Traceability is a provenance/boundary concept only.**

Traceability is a provenance and boundary concept only. It must not become a new evaluation metric, a new statistical test, a new decision rule, a new ranking rule, a new acceptance criterion, or a new production control mechanism.

**What this subsection does not define.**

This subsection defines only formal procedure traceability and reproducibility requirements and boundaries. It does not define a t-test, paired t-test, independent t-test, Wilcoxon test, Mann-Whitney test, bootstrap, permutation test, McNemar test, chi-square test, ANOVA, Bayesian test, or any named statistical test. It does not define a null hypothesis, an alternative hypothesis, an alpha, a significance level, a p-value, a p-value threshold, a confidence level, a confidence interval method, an effect-size threshold, statistical power, a sample-size requirement, a multiple-comparison correction, a Bonferroni correction, a false-discovery-rate correction, or a hypothesis-testing rule. It does not define "statistically significant", "practically significant", "meaningful improvement", "meaningful regression", "better model", "worse model", "preferred model", "best model", "acceptable model", "unacceptable model", "production-ready", or "deployment-ready". It does not define a pass/fail decision, an acceptance criterion, a rejection criterion, a quality gate, a regression gate, a deployment gate, a minimum improvement, a maximum regression, a tolerance, an acceptance threshold, a rejection threshold, a decision threshold, a ranking rule, a leaderboard rule, a model ordering rule, a score cutoff, a decision score, or a composite score. It does not define any metric, any metric formula, any comparison formula, an aggregation formula, a weighting rule, a normalization rule, a calibration rule, a statistical scoring rule, a new matching rule, a new IoU threshold, a new confidence threshold, a new temporal threshold, a new distance threshold, a new event threshold, a new minimum duration, or a new minimum overlap. It does not introduce a new sampling rule, a new leakage rule, a new reproducibility requirement, a new seed, a new execution setting, a new dataset-generation rule, a new runtime configuration, or a new model-execution requirement. It does not introduce a new schema field, a new enum, a new constraint, a new validation rule, a new ID, or a new identity namespace. It does not redefine detection matching, tracking matching, counting matching, metric definitions, evaluation inputs, sampling, Ground Truth schemas, or production behavior. It does not redefine any rule established in Sections 1–8 or in Sections 9.1–9.7.4.

- **Section 9.3: Detection Evaluation** — detection-evaluation domain consumed by reporting, comparison, statistical analysis, and formal decision procedures (this document)
- **Section 9.4: Tracking Evaluation** — tracking-evaluation domain consumed by reporting, comparison, statistical analysis, and formal decision procedures (this document)
- **Section 9.5: Counting Evaluation** — counting-evaluation domain consumed by reporting, comparison, statistical analysis, and formal decision procedures (this document)
- **Section 9.6.1: Evaluation Reporting and Comparison** — reporting and comparison purpose and scope (this document)
- **Section 9.6.2: Evaluation Reporting Semantics** — reporting layer consumed by comparison and statistical analysis (this document)
- **Section 9.6.3: Evaluation Comparison Semantics** — comparison layer consumed by statistical analysis (this document)
- **Section 9.6.4: Statistical and Decision Semantics** — conceptual boundary consumed by formal statistical and decision procedures (this document)
- **Section 9.7: Formal Statistical and Decision Procedures** — formal statistical and decision layer, downstream of evaluation, reporting, and comparison (this document)
- **Section 9.7.1: Formal Statistical and Decision Procedures — Purpose and Scope** — purpose and scope of formal statistical and decision procedures (this document)
- **Section 9.7.2: Formal Statistical and Decision Procedure Semantics** — procedure semantics consumed by formal procedure requirements (this document)
- **Section 9.7.3: Formal Statistical Procedure Requirements** — formal procedure requirements consumed by formal decision procedure requirements (this document)
- **Section 9.7.4: Formal Decision Procedure Requirements** — formal decision requirements consumed by formal procedure traceability and reproducibility (this document)
- **Section 9.7.6: Formal Procedure Output and Reporting Boundaries** — downstream formal-procedure output and reporting boundary semantics (this document)

#### 9.7.6 Formal Procedure Output and Reporting Boundaries

**Purpose.**

This subsection defines the conceptual boundary between established evaluation/reporting/analysis layers and formal-procedure outputs. It establishes what formal statistical and decision procedures may conceptually produce as downstream analytical/reporting outputs, and what those outputs must not become. It does not select or prescribe a statistical test, a decision rule, a metric, a formula, a threshold, a ranking rule, an acceptance criterion, or a production control mechanism.

**Scope.**

Formal procedure output and reporting boundaries apply to any formal statistical or decision procedure introduced downstream of evaluation, reporting, comparison, and analysis. They apply to procedures that consume evaluation results as established by Sections 9.3, 9.4, and 9.5, reported/comparison-ready results as established by Section 9.6, and procedure requirements and semantics as established by Sections 9.7.2 through 9.7.5.

**Formal procedure outputs are downstream of established evaluation results and analysis.**

Formal procedure outputs are downstream of established evaluation results and of established statistical, comparison, and decision analysis. They consume the outputs of those layers; they do not produce them.

**Formal procedure outputs must not create or modify Ground Truth.**

Formal procedure outputs must not create or modify Ground Truth. Ground Truth is fixed independently of model execution, evaluation, reporting, comparison, statistical analysis, decision procedures, and formal-procedure outputs.

**Formal procedure outputs must not create or modify production predictions.**

Formal procedure outputs must not create or modify production predictions. They do not produce detections, tracking output, or counting output.

**Formal procedure outputs must not modify already-generated evaluation results.**

Formal procedure outputs must not modify already-generated evaluation results. They operate on reported or analysis outcomes rather than changing how those results were generated.

**Formal procedure outputs must not regenerate evaluation inputs.**

Formal procedure outputs must not regenerate evaluation inputs. They do not re-create the evaluation inputs established in Section 9.2 and do not reinterpret their fields, enums, ranges, or identity spaces.

**Formal procedure outputs must not modify the Sampling Manifest.**

Formal procedure outputs must not modify the Sampling Manifest, must not change sampling reasons, and must not change split(frame_id).

**Formal procedure outputs must not create new evaluation samples.**

Formal procedure outputs must not create new evaluation samples. They do not introduce new annotation records, new matching records, new detection records, new tracking records, or new counting records.

**Formal procedure outputs must not rerun or control the production pipeline.**

Formal procedure outputs must not rerun or control the production pipeline. They do not affect YOLO inference, ByteTrack, runtime counting, production frame processing, or production runtime behavior.

**Formal procedure outputs must not alter YOLO inference, ByteTrack, runtime counting, production frame processing, or production runtime behavior.**

Formal procedure outputs must not alter YOLO inference, ByteTrack, runtime counting, production frame processing, or production runtime behavior. They are not part of the production inference pipeline and do not configure, tune, or gate any of these components.

**Formal procedure outputs must preserve the evaluation domain.**

Formal procedure outputs must preserve the evaluation domain of the inputs they consume:
- Detection results remain detection results (Section 9.3)
- Tracking results remain tracking results (Section 9.4)
- Counting results remain counting results (Section 9.5)

**Formal procedure outputs must not silently merge Detection, Tracking, and Counting into a new evaluation domain.**

Formal procedure outputs must not silently merge detection, tracking, and counting results into a single undifferentiated output target. Detection, tracking, and counting results must remain distinguishable, and no combined evaluation domain is created.

**Detection evaluation remains identity-free.**

Detection evaluation remains identity-free. It does not use `global_id`, does not use `track_id`, and does not use cross-frame identity.

**Tracking identity semantics remain unchanged.**

Tracking identity semantics remain unchanged:
- `global_id` remains the Ground Truth tracking identity (Section 8.3)
- `track_id` remains the production tracking identity

**`global_id` and `track_id` remain separate identity spaces.**

`global_id` and `track_id` remain different identity spaces and are never equated. No identity-conversion rule may be introduced, and the two identity spaces must not be merged.

**Counting identity semantics remain unchanged.**

Counting Ground Truth `event_id` remains the schema-defined Ground Truth counting-event identifier, as established by Section 8.4.

**Formal procedure outputs must not create a new identity namespace.**

Formal procedure outputs must not create a new identity namespace. `global_id`, `track_id`, and `event_id` are not redefined, and no new working identity is created.

**No prohibited identifiers are introduced as working identities.**

No statistical identity, decision identity, reporting identity, comparison identity, result identity, analysis identity, or model identity is introduced. The identifiers `statistical_id`, `decision_id`, `analysis_id`, `hypothesis_id`, `comparison_id`, `result_id`, `model_id`, `evaluation_id`, `matched_id`, `reporting_id`, `ranking_id`, `decision_identity`, `comparison_identity`, `predicted_global_id`, `generated_global_id`, and `production_global_id` are not introduced as working identities.

**Formal procedure outputs must preserve context and provenance.**

Formal procedure outputs must preserve the frame-domain context, the partition context, the split(frame_id) context, the evaluation-domain context, the provenance of the analyzed results, and the established reproducibility context from Sections 7, 8.5, 9.2, and 9.6.

**Formal procedure outputs must remain traceable to established inputs and upstream results.**

Formal procedure outputs must remain traceable to the established inputs and upstream evaluation/analysis results. An output must not be presented as Ground Truth, as a production prediction, or as a regenerated evaluation input.

**Formal procedure outputs must not redefine sampling.**

Formal procedure outputs must not redefine temporal sampling, event-boosted sampling, sampling intervals, sampling windows, split(frame_id), partition boundaries, excluded frames, sampling reasons, leakage rules, Sampling Manifest generation, runtime sampling, or production frame rate.

**Formal procedure outputs must not redefine leakage rules.**

Formal procedure outputs must not redefine leakage rules. The leakage prevention established in Section 7.7 is not altered by any formal-procedure output.

**Formal procedure outputs must not redefine matching semantics.**

Formal procedure outputs must not redefine detection matching, tracking matching, or counting matching. Matching semantics are established by the evaluation layers and are not redefined here.

**Formal procedure outputs must not redefine schema semantics.**

Formal procedure outputs must not redefine schema semantics. Established schema semantics remain authoritative.

**Formal procedure outputs must not introduce new schema elements.**

Formal procedure outputs must not introduce new schema fields, new enums, new constraints, new validation rules, or new identity fields.

**Formal procedure outputs must not define a new metric.**

Formal procedure outputs must not define a new metric. No metric is established, made mandatory, or made preferred by this subsection.

**Formal procedure outputs must not define a new metric formula.**

Formal procedure outputs must not define a new metric formula, comparison formula, aggregation formula, weighting rule, normalization rule, calibration rule, or composite scoring rule.

**Formal procedure outputs must not define statistical methodology.**

Formal procedure outputs must not define statistical tests, null hypotheses, alternative hypotheses, significance levels, p-value thresholds, confidence levels, confidence interval methods, effect-size thresholds, statistical power requirements, sample-size requirements, multiple-comparison corrections, Bonferroni corrections, or false-discovery-rate corrections.

**Formal procedure outputs must not define decision or deployment rules.**

Formal procedure outputs must not define a pass/fail decision, an acceptance criterion, a rejection criterion, a better model, a worse model, a preferred model, a best model, an acceptable model, an unacceptable model, a minimum improvement, a maximum regression, a tolerance, a quality gate, a regression gate, a deployment gate, a ranking rule, a leaderboard rule, a model ordering rule, a score cutoff, a decision score, or a composite decision score.

**Formal procedure outputs must not be interpreted as production control instructions.**

Formal procedure outputs must not be interpreted as production control instructions. They are analytical and reporting artifacts, not commands to the production pipeline.

**Formal procedure outputs must not automatically change configuration or production behavior.**

Formal procedure outputs must not automatically change model configuration, runtime configuration, sampling configuration, or production behavior.

**Future formal output formats remain deferred.**

Any future formal output format remains deferred unless explicitly defined by a later subsection. This subsection does not prescribe an output format.

**Formal procedure outputs must preserve the distinction between analytical output, reporting representation, production output, evaluation input, and Ground Truth.**

Formal procedure outputs must preserve the distinction between analytical output, reporting representation, production output, evaluation input, and Ground Truth. No analytical output is collapsed into any other category.

**Formal procedure outputs must remain reproducible from established inputs and context.**

Formal procedure outputs must remain reproducible from established inputs and context without changing how those inputs were generated, sampled, split, or validated.

**No new reproducibility requirements may be introduced here.**

No new reproducibility requirements may be introduced here. Reproducibility rests on the protocol context already established.

**What this subsection does not define.**

This subsection defines only formal procedure output and reporting boundaries. It does not define a t-test, paired t-test, independent t-test, Wilcoxon test, Mann-Whitney test, bootstrap, permutation test, McNemar test, chi-square test, ANOVA, Bayesian test, or any named statistical test. It does not define a null hypothesis, an alternative hypothesis, an alpha, a significance level, a p-value, a p-value threshold, a confidence level, a confidence interval method, an effect-size threshold, statistical power, a sample-size requirement, a multiple-comparison correction, a Bonferroni correction, a false-discovery-rate correction, or a hypothesis-testing rule. It does not define "statistically significant", "practically significant", "meaningful improvement", "meaningful regression", "better model", "worse model", "preferred model", "best model", "acceptable model", "unacceptable model", "production-ready", or "deployment-ready". It does not define a pass/fail decision, an acceptance criterion, a rejection criterion, a quality gate, a regression gate, a deployment gate, a minimum improvement, a maximum regression, a tolerance, an acceptance threshold, a rejection threshold, a decision threshold, a ranking rule, a leaderboard rule, a model ordering rule, a score cutoff, a decision score, or a composite score. It does not define any metric, any metric formula, any comparison formula, an aggregation formula, a weighting rule, a normalization rule, a calibration rule, a statistical scoring rule, a new matching rule, a new IoU threshold, a new confidence threshold, a new temporal threshold, a new distance threshold, a new event threshold, a new minimum duration, or a new minimum overlap. It does not introduce a new sampling rule, a new leakage rule, a new reproducibility requirement, a new seed, a new execution setting, a new dataset-generation rule, a new runtime configuration, or a new model-execution requirement. It does not introduce a new schema field, a new enum, a new constraint, a new validation rule, a new ID, or a new identity namespace such as a `statistical_id`, `decision_id`, `analysis_id`, `hypothesis_id`, `comparison_id`, `result_id`, `model_id`, `evaluation_id`, `matched_id`, `reporting_id`, `ranking_id`, `decision_identity`, `comparison_identity`, `predicted_global_id`, `generated_global_id`, or `production_global_id`. It does not redefine detection matching, tracking matching, counting matching, metric definitions, evaluation inputs, sampling, Ground Truth schemas, or production behavior. It does not redefine any rule established in Sections 1–8 or in Sections 9.1–9.7.5.

- **Section 9.3: Detection Evaluation** — detection-evaluation domain consumed by reporting, comparison, statistical analysis, and formal decision procedures (this document)
- **Section 9.4: Tracking Evaluation** — tracking-evaluation domain consumed by reporting, comparison, statistical analysis, and formal decision procedures (this document)
- **Section 9.5: Counting Evaluation** — counting-evaluation domain consumed by reporting, comparison, statistical analysis, and formal decision procedures (this document)
- **Section 9.6.1: Evaluation Reporting and Comparison** — reporting and comparison purpose and scope (this document)
- **Section 9.6.2: Evaluation Reporting Semantics** — reporting layer consumed by comparison and statistical analysis (this document)
- **Section 9.6.3: Evaluation Comparison Semantics** — comparison layer consumed by statistical analysis (this document)
- **Section 9.6.4: Statistical and Decision Semantics** — conceptual boundary consumed by formal statistical and decision procedures (this document)
- **Section 9.7: Formal Statistical and Decision Procedures** — formal statistical and decision layer, downstream of evaluation, reporting, and comparison (this document)
- **Section 9.7.1: Formal Statistical and Decision Procedures — Purpose and Scope** — purpose and scope of formal statistical and decision procedures (this document)
- **Section 9.7.2: Formal Statistical and Decision Procedure Semantics** — procedure semantics consumed by formal procedure requirements (this document)
- **Section 9.7.3: Formal Statistical Procedure Requirements** — formal procedure requirements consumed by formal decision procedure requirements (this document)
- **Section 9.7.4: Formal Decision Procedure Requirements** — formal decision requirements consumed by formal procedure traceability and reproducibility (this document)
- **Section 9.7.5: Formal Procedure Traceability and Reproducibility** — traceability and reproducibility requirements consumed by formal procedure output and reporting boundaries (this document)

---

## 10. Quality-Control Checklist

### 10.1 Quality-Control Purpose, Scope, and Boundary

**Status:** DRAFT — Section 10.1 purpose, scope, and boundary defined. Subsequent subsections (10.2 onward) not yet written.

**Purpose.**

Section 10 establishes the quality-control framework for checking annotation correctness and dataset-construction consistency. Its purpose is to verify that Ground Truth artifacts satisfy requirements already defined by this protocol — not to define new requirements. Every check in Section 10 traces to a rule established in Sections 1–9. Section 10 is a verification layer; it is NOT an authoring layer and is NOT a source of new protocol semantics.

**Scope.**

At the protocol level, the quality-control scope covers:

- **annotation correctness** — whether annotations match the intent established by the Phase 1.3A Ground Truth Specification and this protocol.
- **schema conformance** — whether artifacts satisfy the schemas defined in Section 8.
- **temporal and frame consistency** — whether per-frame annotation state is internally consistent, including the temporal regimes and frame-indexing rules established in Section 7.
- **identity consistency** — whether `global_id` semantics, class immutability, and identity-continuity rules from Sections 5 and 7 are satisfied.
- **counting-event consistency** — whether counting events are derivable from tracking Ground Truth per Sections 6 and 7.8.
- **sampling-manifest consistency** — whether the sampling manifest satisfies the field semantics and validation rules established in Sections 7.11 and 8.5.
- **reproducibility-related consistency** — whether dataset-construction inputs and recording satisfy the reproducibility requirements of Section 7.12.
- **detection / tracking / counting relationship consistency** — whether the three Ground Truth layers relate as required by Sections 8.2–8.4 and the counting-derivation rules of Section 6.

Each listed area maps to requirements already established in Sections 1–9. Section 10 does not expand the definition of any of these areas.

**Boundary.**

Section 10 MUST NOT silently introduce any of the following:

- new annotation semantics
- new class labels
- new enums
- new schema fields
- new coordinate systems
- new geometry
- new Decision 3 semantics
- new counting semantics
- new traffic-density formula
- new queue definition
- new waiting-time definition
- new traffic-direction semantics
- new signal/control semantics

If a future quality-control requirement would require changing one of the items above, that change must be treated as a separate specification or decision task. It MUST NOT be introduced silently by the quality-control checklist. A QC check that detects a deficiency in an existing rule reports the deficiency; it does not rewrite the rule.

**Relationship to existing schemas.**

Quality control validates artifacts against the schemas already defined in Section 8 (Sections 8.2–8.5). It does not modify, redefine, or extend those schemas. When a QC check requires information not present in an existing schema, that is a schema-gap finding to be escalated — not a reason to add a field ad hoc to the checklist.

**Relationship to earlier protocol sections.**

The authority hierarchy established by Sections 1–9 is preserved and is NOT altered by Section 10:

- Section 7 temporal sampling rules REMAIN authoritative.
- Section 8 schema definitions REMAIN authoritative.
- Section 9 evaluation and formal-procedure definitions REMAIN authoritative.

Section 10 defines quality-control checks *against* those rules. It does not replace them, does not supersede them, and does not reinterpret them. Where a QC check appears to conflict with an earlier section, the earlier section governs and the conflict is escalated rather than resolved by the checklist.

**Known schema asymmetry — QC treatment.**

A documented asymmetry exists between `tracking_ground_truth.roi_crossings` and the `counting_ground_truth` representation of exits (see Section 8.3 / 8.4 and the asymmetry note in Section 8.5). This asymmetry is intentional and documented; it is NOT a validation error in either schema.

Quality control MUST distinguish:

- a genuine violation of an existing requirement

from

- an intentional or documented schema asymmetry.

A QC check that encounters the exit asymmetry must classify it as the latter and must NOT report it as a failure. The asymmetry itself is out of scope for Section 10 and is not resolved here.

**Failure interpretation.**

A quality-control failure means an artifact or annotation does not satisfy a requirement already defined by this protocol. Failure is always reported against the specific requirement that was violated, with the violating artifact identified.

Section 10.1 does NOT define numeric acceptance thresholds, pass/fail scores, or severity levels for failures. Those are handled by later Section 10 subsections if and only if they are explicitly required. No threshold defined here may be used as a binding acceptance criterion.

**Explicit exclusions.**

Section 10 does NOT cover:

- model performance or inference quality
- annotation-tool selection (deferred, see Section 8.6)
- inter-annotator agreement (deferred to Section 11)
- pilot dataset definition (deferred)
- acceptance criteria for the pilot dataset (deferred to Section 13)
- any Decision 3 downstream semantic, including density, queue, waiting time, traffic direction, signal/control, visualization, or persistence

Decision 3 remains a closed, implemented, spatial-classification-only branch with no downstream consumer. Section 10 must not connect QC findings to Decision 3 region labels.

### 10.2 Quality-Control Checklist Structure and Requirement Traceability

**Status:** DRAFT — checklist structure and traceability rule defined. Individual checks not yet enumerated.

**Structure rule.**

Every quality-control check MUST be expressed as a traceable requirement check. A check is only valid when it identifies all of the following:

1. **what is being checked** — the artifact or annotation property under examination;
2. **the requirement being checked** — the specific rule that authorizes the check;
3. **the authoritative source** — the section and subsection where that requirement is defined;
4. **the evidence examined** — the concrete artifact, field, or relationship that is inspected;
5. **the pass/fail determination** — whether the evidence satisfies the requirement;
6. **the requirement violated on failure** — the exact rule that a failing check is reported against.

A check that cannot identify its authoritative source is NOT a valid QC check and MUST NOT be listed. This rule prevents a checklist entry from silently becoming a new requirement.

**Traceability requirement.**

Each QC check MUST trace to a requirement already defined in Sections 1–9. Section 10.2 does not define requirements; it defines how checks reference them.

If a requirement is not already defined in Sections 1–9, Section 10.2 MUST NOT silently define it as a QC requirement. Any such case is escalated as a specification gap and is resolved by the authoritative section that owns that requirement — not by the checklist.

**Check categories.**

QC checks are organized into the following categories. Each category maps to requirements already established in Sections 1–9 and does not introduce new categories of its own:

- **schema/conformance checks** — validate artifacts against the schemas defined in Section 8 (Sections 8.2–8.5). These checks examine field presence, enum membership, type, and constraint satisfaction as defined by the schema, not any additional rule.
- **temporal/frame consistency checks** — validate per-frame annotation state against the temporal regimes, frame-indexing rules, and temporal constraints established in Section 7.
- **identity/tracking consistency checks** — validate `global_id` semantics, class immutability, identity continuity, and tracking-layer rules established in Sections 5 and 7.
- **counting-event consistency checks** — validate counting events against the counting-derivation rules and ROI-crossing handling established in Sections 6 and 7.8.
- **sampling-manifest consistency checks** — validate the sampling manifest against the field semantics and validation rules established in Sections 7.11 and 8.5.
- **reproducibility/consistency checks** — validate dataset-construction inputs and recording against the reproducibility requirements of Section 7.12.
- **cross-layer consistency checks** — validate relationships between Ground Truth layers (detection, tracking, counting) against Section 8 and the counting-derivation rules of Section 6.

A check belongs to exactly one category for bookkeeping purposes. Categorization does not change the authority of the underlying requirement.

**Authority hierarchy.**

The following sections remain authoritative for their respective requirements, and Section 10 does NOT redefine, override, or reinterpret them:

- Section 7 temporal sampling rules REMAIN authoritative.
- Section 8 schema definitions REMAIN authoritative.
- Section 9 evaluation and formal-procedure definitions REMAIN authoritative.

Section 10 verifies compliance with these requirements. When a QC check appears to conflict with an earlier section, the earlier section governs. The conflict is escalated; it is NOT resolved by the checklist.

**Check validity constraints.**

A QC check MUST NOT become a new semantic definition merely because it is listed in the checklist. Listing a check does not authorize the concepts it examines to be redefined.

A QC check MUST NOT introduce:

- new schema fields
- new enum values
- new coordinate systems
- new geometry
- new traffic semantics
- density definitions
- queue definitions
- waiting-time definitions
- direction definitions
- signal/control semantics
- Decision 3 downstream semantics
- new numerical acceptance thresholds

A QC check MAY reference an existing numeric value that is already defined in Sections 1–9 (for example, the 30-frame threshold of Section 7.9 or the severe-occlusion interval of Section 7.9). It MUST NOT invent a new tolerance, percentage, pass rate, confidence threshold, or statistical criterion. No numerical acceptance threshold is defined anywhere in Section 10.2.

**Known schema asymmetry — traceability treatment.**

The documented asymmetry between `tracking_ground_truth.roi_crossings` and the `counting_ground_truth` representation of exits (see Section 10.1, and the asymmetry note in Sections 8.3, 8.4, and 8.5) is preserved unchanged. A QC check that examines this area MUST classify an `exit` present in tracking but absent from counting as an intentional or documented schema asymmetry, NOT as a failure. This asymmetry is out of scope for Section 10 and is not resolved or amended here.

**Escalation.**

A QC check that detects a deficiency in an existing requirement reports the deficiency against that requirement and escalates it to the authoritative section. It does not rewrite the requirement. A QC check that detects a deficiency where no requirement exists is not a valid check and is not listed.

---

### 10.3 Schema Conformance QC Checks

**Schema conformance objective.**

Schema-conformance QC verifies that an annotation artifact conforms to the applicable existing schema defined by Section 8. The QC check verifies conformance against the schema that already governs the artifact. It does not create a new schema and does not define new schema rules.

**Four-schema coverage.**

Schema-conformance QC covers the four existing schema layers, each tied to its existing Section 8 schema subsection:

- Detection Ground Truth — governed by the Section 8 detection ground truth schema.
- Tracking Ground Truth — governed by the Section 8 tracking ground truth schema.
- Counting Ground Truth — governed by the Section 8 counting ground truth schema.
- Sampling Manifest — governed by the Section 8 sampling manifest schema.

No new schema layer is introduced by Section 10.3.

**Structural conformance.**

QC may check already-defined structural requirements, including that:

- required fields are present;
- prohibited additional fields are absent where the schema specifies that;
- field names match the existing schema;
- data types conform to the existing schema;
- existing enum constraints are respected;
- existing nested structures conform to the schema;
- existing pattern constraints are respected;
- existing numeric bounds are respected.

These are checks against existing schema rules only. Section 10.3 introduces no new structural rule.

**Cross-schema conformance.**

QC may verify relationships between artifacts where those relationships are already defined by Sections 7-9 and Section 8. Examples may include:

- frame_id consistency where already required;
- timestamp consistency where already defined;
- split consistency where already defined;
- identity relationships where already defined;
- counting-event references to tracking identities where already defined;
- sampling-manifest references to sampled frames where already defined.

No new cross-schema relationship is introduced by Section 10.3.

**Schema-versus-protocol distinction.**

JSON Schema conformance does NOT by itself prove semantic correctness. Passing schema validation does NOT prove temporal correctness, identity correctness, counting correctness, or annotation correctness. Those checks belong to their respective Section 10 QC categories and are not redefined here.

**Authority rule.**

When a schema rule and protocol text appear inconsistent, the QC process must NOT silently invent a reconciliation. The discrepancy must be traced to the authoritative source and escalated or documented according to Section 10.1 and 10.2. An unresolved schema ambiguity is not resolved in this subsection.

**Known tracking/counting exit asymmetry.**

The protocol already records a known asymmetry concerning tracking `roi_crossings` and counting events. QC must detect and report this asymmetry as a known schema/protocol asymmetry if encountered. It MUST NOT:

- add an exit event to the counting schema;
- modify the tracking schema;
- modify the counting schema;
- invent an exit-counting rule;
- reinterpret existing direction semantics.

The asymmetry is treated as an existing known issue only and is not resolved here.

**Failure interpretation.**

A schema-conformance failure means an already-defined schema requirement is violated. The QC report should identify:

- artifact/layer;
- violated schema requirement;
- authoritative schema;
- relevant field/path;
- observed condition;
- pass/fail determination.

No numeric acceptance threshold is defined for schema conformance.

**No new semantics.**

Section 10.3 preserves the Section 10.1 boundary and MUST NOT introduce:

- new schema fields;
- new enums;
- new coordinate systems;
- new geometry;
- new counting semantics;
- new traffic-direction semantics;
- density semantics;
- queue semantics;
- waiting-time semantics;
- signal/control semantics;
- Decision 3 downstream semantics.

---

### 10.4 Temporal and Frame Consistency QC Checks

**Frame identity consistency.**

QC verifies that `frame_id` is used consistently as the authoritative temporal key. QC verifies that frame references remain consistent with the applicable video. No QC rule invents an alternative frame identity.

**Timestamp consistency.**

QC verifies existing timestamp requirements only. Where the protocol already defines timestamp derivation, QC verifies consistency with that existing definition. QC MUST NOT introduce a new timestamp tolerance, a new rounding rule, or a new FPS rule.

**Frame-range validity.**

QC verifies that annotation and sampling frame references remain within the frame domain already established by Sections 7-9 and the schemas. QC MUST NOT introduce a new frame range or alter existing frame boundaries.

**Partition consistency.**

QC verifies the existing train / val / test partition requirements. QC confirms that a frame belongs to the correct existing partition, that the existing `split(frame_id)` authority is respected, that "one frame, one partition" remains satisfied, and that no QC procedure creates a new partition rule. QC MUST NOT modify partition boundaries.

**Sampling consistency.**

QC verifies sampled-frame records against the existing deterministic sampling protocol. QC may check sampled-frame membership, expected sampling interval, sampling manifest consistency, deterministic reproducibility requirements, and consistency with the existing sampling-reason values. QC MUST NOT create a new sampling algorithm, change the base interval, remove or suppress sampled frames, or introduce a temporal redundancy criterion. The existing Decision 2 is authoritative: all sampled frames are retained.

**Temporal ordering.**

Where Sections 7-9 require temporal ordering, QC may verify that frame references are ordered where ordering is required, that timestamps correspond to frame order, that tracking observations do not contain impossible temporal ordering, and that event frame references remain temporally consistent with their corresponding observations. QC MUST NOT invent a new temporal-ordering rule where the protocol does not already define one.

**Short tracking gaps and occlusion.**

QC verifies existing Section 7.9 requirements concerning short tracking gaps and occlusion. QC determines whether an annotation follows the already-defined procedure. QC MUST NOT create a new maximum gap, change the existing 30-frame threshold, or introduce a new occlusion policy.

**Frames near important events.**

QC verifies existing Section 7.10 requirements concerning frames near important events. QC may verify that the required event-adjacent sampling/annotation requirements are satisfied according to the existing protocol. QC MUST NOT introduce a new event window or change existing event-window semantics.

**Manifest consistency.**

QC verifies consistency between sampling manifest `frame_id`, timestamp, split, `sampling_reason`, and existing event-related fields where applicable. The check validates against the existing manifest requirements. QC MUST NOT add fields to the manifest or alter the schema.

**Reproducibility.**

QC verifies existing Section 7.12 reproducibility requirements. QC may verify that construction inputs and outputs remain consistent with the already-defined deterministic protocol. QC MUST NOT introduce a random seed requirement, a new hash requirement, or new reproducibility metadata.

**Traceability requirement.**

Every QC category in this subsection identifies its authoritative source in Sections 1-9 using the structure established by Section 10.2:

1. What is checked
2. Requirement checked
3. Authoritative section/subsection
4. Evidence examined
5. Pass/fail determination
6. Requirement violated on failure

A proposed check that cannot be traced to an existing requirement is NOT turned into a new requirement. The issue must be escalated rather than silently creating a rule.

**Failure interpretation.**

A QC failure means an already-defined requirement from Sections 1-9 is not satisfied. QC MUST NOT define numeric acceptance thresholds, percentage pass rates, statistical tolerances, annotation-quality scores, new confidence thresholds, or new temporal tolerances. These belong to later acceptance/validation decisions and are outside this subsection.

**Known tracking/counting exit asymmetry.**

The known asymmetry concerning tracking `roi_crossings` and counting events remains an existing known issue. QC MUST NOT resolve it, add an exit event to the counting schema, modify the tracking or counting schema, invent an exit-counting rule, or reinterpret existing direction semantics.

---

### 10.5 Identity and Tracking Consistency QC Checks

**global_id consistency.**

QC verifies that each ground-truth identity follows the existing `global_id` convention. QC verifies that the same identity is not assigned conflicting `global_id` values. QC MUST NOT create a new identity format or alter the existing `global_id` convention.

**Identity continuity.**

QC verifies that observations belonging to the same established identity remain internally consistent. QC verifies that identity continuity does not contradict the existing tracking protocol. QC MUST NOT introduce new tracking heuristics.

**Frame membership.**

QC verifies that identity observations reference valid existing `frame_id` values. QC verifies consistency with the existing temporal/frame rules. QC MUST NOT introduce new frame ranges.

**bbox / observation consistency.**

QC verifies that tracking observations use the existing bbox and observation semantics. QC MUST NOT redefine the observation point. QC MUST NOT introduce new coordinate systems or transformations.

**Identity uniqueness / collision checks.**

QC detects cases where one frame would assign incompatible observations to the same ground-truth identity. QC detects impossible duplicate identity assignments only when already prohibited by Sections 7-9. QC MUST NOT invent new matching thresholds or IoU rules.

**Tracking-to-counting relationship.**

QC verifies consistency between Tracking Ground Truth identities and existing Counting Ground Truth references where applicable. QC preserves the existing rule that Counting Ground Truth is derived from Tracking Ground Truth. QC MUST NOT create new counting semantics.

**track_id vs global_id boundary.**

QC explicitly preserves the existing distinction between production tracker `track_id` and annotation `global_id`. QC MUST NOT treat `track_id` as ground-truth identity. QC MUST NOT introduce a new mapping semantic beyond what is already defined.

**Missing / duplicated observations.**

QC identifies structurally invalid or contradictory identity observations. QC treats the finding as a QC failure only when an existing requirement is violated. QC MUST NOT invent numerical tolerances.

**Traceability requirement.**

Every QC check in this subsection follows the Section 10.2 traceability structure:

1. What is checked
2. Requirement checked
3. Authoritative section/subsection
4. Evidence examined
5. Pass/fail determination
6. Requirement violated on failure

Every check MUST have an authoritative source in Sections 1-9. A proposed check that cannot be traced to an existing requirement is NOT invented, is NOT added as a new rule, and is marked as an escalation or undefined requirement. It is not silently promoted into an acceptance criterion.

**Failure interpretation.**

A QC failure means an already-defined requirement from Sections 1-9 is not satisfied. QC MUST NOT define numeric acceptance thresholds, percentage pass rates, statistical tolerances, annotation-quality scores, or new confidence thresholds.

**Known tracking/counting exit asymmetry.**

The known asymmetry concerning tracking `roi_crossings` and counting events remains an existing known issue. QC MUST NOT resolve it, resolve the track_id/global_id boundary through it, add an exit event to the counting schema, modify the tracking or counting schema, invent an exit-counting rule, or reinterpret existing direction semantics. If relevant to identity/tracking QC, it is referenced only as an existing known asymmetry and preserves the existing escalation treatment.

---

### 10.6 Counting-Event Consistency QC Checks

**Counting-event traceability.**

Every counting-event QC check MUST identify:

- what is checked
- the existing requirement being checked
- the authoritative section/subsection
- evidence examined
- pass/fail determination
- requirement violated if failed

This follows the traceability structure established in Section 10.2.

**Tracking-to-counting derivation.**

QC verifies that Counting Ground Truth remains derived from Tracking Ground Truth according to the existing Section 8 architecture. QC verifies consistency between tracking identity, counting event identity, class, `frame_id`, timestamp, ROI crossing information, and event-level representation, using only already-defined relationships. QC MUST NOT introduce a new derivation rule.

**Counting event identity.**

QC verifies that each existing counting event references the appropriate existing global identity. QC preserves the distinction `global_id` != `track_id`. QC MUST NOT introduce `track_id` into Counting Ground Truth. QC MUST NOT create a new identity format or redefine `global_id`.

**Frame / timestamp consistency.**

QC verifies that counting-event `frame_id` and timestamp remain consistent with the already-defined temporal rules. QC MUST NOT introduce a new temporal tolerance, a new timestamp calculation, or a new frame-selection rule.

**ROI crossing consistency.**

QC verifies that counting events are consistent with the already-defined ROI-crossing semantics. QC may verify existing evidence such as the crossing frame, ROI point, `direction` field, and relationship to the crossing observation. QC MUST NOT create a new crossing definition, modify the existing ROI-crossing definition, or introduce additional directions.

**Direction semantics.**

QC preserves the existing Counting Ground Truth rule for countable crossing-event semantics. QC MUST NOT reinterpret `direction`. QC MUST NOT introduce APPROACH_A as a direction, APPROACH_B as a direction, JUNCTION as a direction, a Decision 3 region to direction mapping, movement classes, lane assignment, or signal/control semantics. Decision 3 remains completely outside this subsection.

**Counting event uniqueness / double counting.**

QC may verify that counting-event records do not contradict the already-defined single-transition counting semantics. QC MUST NOT invent a new duplicate-event threshold, introduce a new numerical tolerance, or create a new counting algorithm. The checklist verifies only compliance with an already-defined rule.

**Tracking/counting asymmetry.**

The known asymmetry between Tracking Ground Truth `roi_crossings` and Counting Ground Truth events MUST remain preserved exactly as already documented. QC MUST NOT add exit events to Counting Ground Truth, modify either schema, invent an exit-counting rule, reinterpret direction, or use the asymmetry to introduce new semantics. If encountered during QC, the asymmetry is reported as an existing documented asymmetry, not silently fixed.

**Failure interpretation.**

A QC failure means an already-defined requirement is not satisfied. The failure MUST be reported against the specific existing requirement. QC MUST NOT define new acceptance thresholds, pass percentages, statistical tolerances, confidence thresholds, or numerical scoring systems. Any requirement not already defined in Sections 1-9 MUST be escalated rather than invented inside Section 10.6.

---

### 10.7 Sampling-Manifest Consistency QC Checks

**Manifest structure and required-field presence.**

QC verifies that the sampling manifest conforms to the existing manifest structure and that the already-defined required fields are present, using the existing Section 8.5 schema as the authoritative reference.

**sample_id uniqueness and existing format requirements.**

QC verifies that `sample_id` values are unique and conform to the existing `S_XXXX` format requirement. QC MUST NOT create a new sample identifier format.

**frame_id validity and consistency with the existing sampled-frame domain.**

QC verifies that manifest `frame_id` values remain valid within the existing sampled-frame domain. QC MUST NOT introduce a new frame range.

**Timestamp consistency with the existing frame/time relationship.**

QC verifies that manifest `timestamp` values remain consistent with the existing frame/time relationship. QC MUST NOT introduce a new timestamp calculation or tolerance.

**Split consistency with the authoritative partition rules.**

QC verifies that manifest `split` values are consistent with the authoritative partition rules. QC MUST NOT introduce a new split boundary.

**sampling_reason consistency with the existing sampling protocol.**

QC verifies that `sampling_reason` values are consistent with the existing sampling protocol. QC MUST NOT introduce a new sampling reason.

**traffic_density and difficulty values against their EXISTING schema enums.**

QC verifies that `traffic_density` and `difficulty` values conform to their existing schema enums. QC MUST NOT introduce a new traffic-density category or a new difficulty category.

**event_type consistency against its EXISTING schema enum, where present.**

QC verifies that `event_type` values conform to the existing schema enum where present. QC MUST NOT introduce a new event type.

**Consistency between manifest samples and the already-defined temporal sampling protocol.**

QC verifies consistency between manifest samples and the already-defined temporal sampling protocol. QC MUST NOT create a new sampling algorithm, change the base interval, or introduce new frame-selection criteria.

**Preservation of deterministic sampling requirements.**

QC verifies that the existing deterministic sampling requirements are preserved. QC MUST NOT introduce new randomization, hash, seed, or reproducibility mechanisms.

**Reproducibility-related consistency of the manifest.**

QC verifies existing Section 7.12 reproducibility requirements. QC may verify that manifest construction inputs and outputs remain consistent with the already-defined deterministic protocol. QC MUST NOT introduce new reproducibility metadata, versioning requirements, or deterministic mechanisms.

**Consistency with Decision 2 — all sampled frames are retained.**

QC verifies that sampled frames required by the existing protocol are present, that low-change intervals have not been removed, that sampling is deterministic, and that no temporal-redundancy exclusion criterion has been introduced. Decision 2 ("Option A — keep all sampled frames") is preserved unchanged. QC MUST NOT introduce any new criterion for deciding whether a frame should be sampled or excluded, and MUST NOT reinterpret Decision 2.

**Cross-layer consistency with the sampled frame domain used by Detection Ground Truth.**

QC may verify consistency between the sampling manifest, the sampled frame domain, and Detection Ground Truth frame records. QC MUST NOT redesign the relationship or create new cross-layer semantics.

**Traceability requirement.**

Every QC check in this subsection follows the Section 10.2 traceability structure:

1. What is checked
2. Requirement checked
3. Authoritative section/subsection
4. Evidence examined
5. Pass/fail determination
6. Requirement violated on failure

A QC check without an existing authoritative requirement is INVALID. If a desired check cannot be traced to Sections 1-9 or the existing schema, it is NOT invented; the issue must be escalated as an undefined requirement.

**Failure interpretation.**

A QC failure means an already-defined requirement is not satisfied. QC MUST NOT define new thresholds, tolerances, percentages, statistical criteria, confidence thresholds, or acceptance criteria.

**Known schema asymmetry.**

The known asymmetry between Tracking Ground Truth `roi_crossings` and Counting Ground Truth events remains an existing known issue. QC MUST NOT modify tracking_ground_truth.schema.json or counting_ground_truth.schema.json, add exit events, invent exit-counting semantics, or reinterpret direction semantics. If encountered, it is preserved and escalated as an existing documented issue.

**Decision 3 boundary.**

Decision 3 remains CLOSED and completely outside this subsection. QC MUST NOT introduce APPROACH_A, APPROACH_B, JUNCTION, region semantics, density derived from Decision 3, direction derived from Decision 3, or sampling derived from Decision 3.

---

### 10.8 Reproducibility Consistency QC Checks

**Deterministic sampling consistency.**

QC verifies that sampling remains deterministic according to the existing Section 7.12 requirements. QC MUST NOT introduce a new deterministic algorithm, new randomization, a new seed, a new hash, or a new checksum.

**Reproducibility of the sampled-frame domain from existing authoritative inputs.**

QC verifies that the sampled-frame domain remains reproducible from the existing authoritative inputs and protocol parameters already defined by Section 7.12. QC MUST NOT introduce new reproducibility inputs or new metadata fields.

**Consistency of existing reproducibility inputs.**

QC may verify consistency of `video_id`, `total_frames`, `fps`, `base_interval`, split boundaries, the existing event set, and the existing event-window parameters, only where these are already defined as reproducibility inputs by Section 7.12. QC MUST NOT introduce a new event set, a new event-window parameter, or a new split boundary.

**Absence of randomness.**

QC verifies the absence of randomness where the existing protocol requires deterministic sampling. QC MUST NOT introduce a new randomization requirement.

**Absence of annotation-order dependence.**

QC verifies the absence of annotation-order dependence where already prohibited by the existing protocol. QC MUST NOT introduce a new ordering rule.

**Identity condition.**

QC verifies that identical authoritative manifest inputs and protocol parameters produce an identical manifest, exactly as already defined by Section 7.12. QC MUST NOT introduce a new identity condition.

**Regeneration requirements.**

QC verifies only the already-defined circumstances under which regeneration is required, as stated by Section 7.12. QC MUST NOT introduce a new regeneration requirement.

**Non-regeneration circumstances.**

QC verifies only the circumstances already stated by Section 7.12 in which regeneration is not required. QC MUST NOT introduce a new non-regeneration circumstance.

**Consistency between reproducibility requirements and the Sampling Manifest output.**

QC verifies consistency between the existing reproducibility requirements and the Sampling Manifest output. QC MUST NOT introduce a new reproducibility mechanism or modify the existing manifest schema.

**Preservation of Decision 2.**

QC verifies that reproducibility verification does not result in removal of low-change frames, suppression of sampled frames, temporal-redundancy filtering, or a new sampling-exclusion criterion. Decision 2 ("Option A — keep all sampled frames") is preserved unchanged. QC MUST NOT introduce any new sampling-selection rule or reinterpret Decision 2.

**Traceability requirement.**

Every QC check in this subsection follows the Section 10.2 traceability structure:

1. What is checked
2. Requirement checked
3. Authoritative section/subsection
4. Evidence examined
5. Pass/fail determination
6. Requirement violated on failure

A QC check without an existing authoritative requirement is INVALID. If a desired reproducibility check is not already defined in Sections 1-9, it is NOT invented; the issue must be escalated as an undefined requirement.

**Failure interpretation.**

A QC failure means an already-defined requirement is not satisfied. QC MUST NOT define new thresholds, tolerances, acceptance criteria, statistical criteria, hashes, checksums, seeds, version identifiers, or metadata requirements.

**Decision 3 boundary.**

Decision 3 remains CLOSED and completely outside this subsection. QC MUST NOT connect reproducibility QC to APPROACH_A, APPROACH_B, JUNCTION, region classification, geometry, traffic direction, density, queue, waiting time, or signal/control.

**Known schema asymmetry.**

The known asymmetry between Tracking Ground Truth `roi_crossings` and Counting Ground Truth events remains an existing known issue. QC MUST NOT use this subsection to resolve it, modify either schema, add exit events, or invent exit-counting semantics. If encountered, it is preserved under the existing documented treatment.

---

## 11. Inter-Annotator Agreement Procedure

### 11.1 Inter-Annotator Agreement Purpose, Scope, and Boundary

**Purpose.**

Inter-Annotator Agreement (IAA) is a verification procedure for assessing consistency between independent annotation results against requirements already established in the protocol. IAA evaluates annotation consistency. It is not an annotation-authoring procedure. It does not redefine Ground Truth semantics. It does not replace the authoritative annotation protocol. It does not replace schema validation. It does not replace Quality Control from Section 10. IAA operates against already-defined annotation requirements.

**Scope.**

IAA covers consistency between independent annotators for already-defined annotation layers and requirements, including where applicable:

- Detection Ground Truth
- Tracking Ground Truth
- Counting Ground Truth
- Sampling Manifest consistency where independently annotated or verified
- frame selection consistency
- object/category labeling consistency
- bounding-box consistency
- visibility / occlusion / truncation / difficult-label consistency
- identity consistency
- counting-event consistency
- already-defined temporal consistency

Every concept remains subordinate to the authoritative definitions in Sections 1-10.

**Authority.**

Sections 1-9 remain authoritative for annotation definitions, schemas, sampling, identity, counting, and reproducibility. Section 10 remains authoritative for the existing Quality-Control framework. Section 11 defines how agreement between independent annotation results is assessed. Section 11 MUST NOT redefine requirements from Sections 1-10. If an IAA concept requires a rule that does not already exist in Sections 1-10, it must be treated as a future decision or escalation item, not silently invented here.

**Relationship to Section 10 QC.**

Section 10 defines the Quality-Control checklist for verifying annotation artifacts against existing requirements. Section 11 assesses agreement between independent annotation results. Section 11 does not replace Section 10, and Section 10 does not subsume Section 11.

**Relationship to annotation schemas.**

IAA operates against already-defined schema requirements. It does not add fields, enums, constraints, or relationships to any schema.

**Independence of annotation results.**

IAA requires independently produced annotation results. Operational procedures for achieving independence are not defined in this subsection and belong to later Section 11 subsections if explicitly defined. No tooling, randomization, blinding, assignment algorithm, or annotator scheduling is introduced here.

**Disagreement as an observed consistency issue.**

A disagreement is treated as an observed inconsistency between independent annotation results relative to an already-defined requirement. A disagreement does NOT automatically establish that a new rule is needed. If the protocol does not already define how the disagreement should be resolved, it must be escalated as an unresolved specification issue. The resolution is not invented here.

**Escalation when no authoritative rule exists.**

An IAA concept that requires a rule not present in Sections 1-10 is escalated as a future decision or escalation item. It is not silently introduced, not added as a new requirement, and not promoted into an acceptance criterion.

**Exclusions / boundary.**

Section 11.1 MUST NOT introduce: new schema fields; new enums; new labels; new coordinate systems; new geometry; new sampling intervals; new sampling-selection rules; new exclusion criteria; new identity rules; new counting semantics; new traffic-direction semantics; new density semantics; new queue semantics; new waiting-time semantics; new signal/control semantics; new Decision 3 semantics; new thresholds; new tolerances; new percentages; new statistical formulas; new IoU thresholds; new matching thresholds; new confidence thresholds; new acceptance criteria; or new pass/fail thresholds. No numerical IAA metric, Cohen's kappa, IoU threshold, F1 threshold, agreement percentage, matching tolerance, or acceptance threshold is defined in this subsection. Those require a separate explicit decision or task if not already defined by the authoritative protocol.

**Decision 2 protection.**

Decision 2 ("Option A — keep all sampled frames") is preserved unchanged. Section 11.1 must not introduce any mechanism that removes, suppresses, filters, or excludes sampled frames based on temporal redundancy or low-change content.

**Decision 3 boundary.**

Decision 3 is CLOSED. Section 11.1 must not connect IAA to APPROACH_A, APPROACH_B, JUNCTION, Decision 3 region classification, Decision 3 geometry, Counting ROI, density, queue, waiting time, traffic direction, or signal/control. Decision 3 is mentioned only as an explicit boundary: it remains CLOSED and outside the IAA procedure.

**Known tracking/counting exit asymmetry.**

The known asymmetry between Tracking Ground Truth `roi_crossings` and Counting Ground Truth events remains preserved. Section 11.1 must not resolve it, add exit events to Counting Ground Truth, modify either schema, invent exit-counting semantics, or reinterpret direction semantics. If referenced, it is treated only as an existing documented asymmetry.

---

### 11.2 IAA Comparison Units and Agreement Targets

**Comparison targets, not metrics.**

A comparison unit identifies WHAT annotation output is compared. An agreement metric determines HOW agreement is quantified. Section 11.2 defines comparison targets only. No numerical agreement metric is defined in this subsection. Numerical agreement metrics belong to a later subsection or task.

**Detection-level comparison.**

Detection-level comparison is defined in terms of already-existing annotation concepts: sampled frame identity, object/category labeling, bounding-box annotation, visibility, occlusion, truncation, and difficult status. The existing Detection Ground Truth schema and Section 8 definitions are authoritative. Section 11.2 MUST NOT define an IoU threshold, spatial tolerance, matching algorithm, confidence threshold, percentage agreement, or pass/fail threshold.

**Tracking-level comparison.**

Tracking-level comparison uses already-defined concepts: `global_id`, frame membership of a track, continuity of an annotated identity, and already-defined identity consistency and observation relationships. The existing distinction between `global_id` (Ground Truth identity) and `track_id` (production tracker identity) is preserved. Section 11.2 MUST NOT introduce or redefine this distinction, define a matching algorithm between annotations, introduce identity tolerances, or introduce new identity labels.

**Counting-event comparison.**

Counting-event comparison uses existing Counting Ground Truth concepts, where already applicable: event existence, `global_id` reference, `class`, `frame_id`, `timestamp`, `roi_point`, `direction`, `bbox_at_crossing`, and `crossing_confidence`. Only fields already defined by the authoritative Counting Ground Truth schema and protocol are compared. Section 11.2 MUST NOT add exit events, new event types, new direction semantics, new crossing rules, new event tolerances, or new temporal windows.

**Sampling / frame-domain comparison.**

IAA may verify that independently produced annotation results operate on the same already-defined sampled-frame domain. The existing deterministic sampling protocol is preserved. Decision 2 ("Option A — keep all sampled frames") remains unchanged. Section 11.2 MUST NOT introduce frame removal, low-change exclusion, temporal redundancy filtering, an alternate sampling interval, random sampling, or new sampling criteria. The comparison is against the existing sampling manifest and frame domain, not a new sampling policy.

**Cross-layer comparison.**

Cross-layer comparison is defined only where relationships already exist: Detection Ground Truth to Tracking Ground Truth, Tracking Ground Truth to Counting Ground Truth, and Sampling Manifest to the sampled Detection Ground Truth frame domain. The existing Section 8 schema relationship architecture is authoritative. Section 11.2 MUST NOT create new cross-layer semantics or infer new fields or relationships merely because two schemas contain similarly named information.

**Missing / extra / conflicting annotations.**

The conceptual classes of disagreement may be identified: an annotation present in one result but absent in the other; an annotation absent in one result but present in the other; the same annotation target represented differently; identity assignment disagreement; event correspondence disagreement; or frame-domain disagreement. Section 11.2 MUST NOT define numerical treatment of these disagreements, how they are scored, thresholds, or which annotator is correct. If resolution requires a rule not already defined by Sections 1-10, the issue must be escalated rather than invented.

**Authority.**

Sections 1-9 are authoritative for annotation definitions, schemas, sampling, identity, counting, and reproducibility. Section 10 is authoritative for the QC verification framework. Section 11 is the IAA procedure only. Section 11.2 MUST NOT override any earlier section.

**Traceability.**

Authoritative sources include Section 5 (Ground Truth identity policy), Section 6 (counting semantics), Section 7 (temporal sampling and reproducibility), Section 8 (data schemas and schema relationships), Section 10.1 (QC purpose and boundary), Section 10.2 (QC traceability structure), and Sections 10.3-10.8 (existing QC categories). No subsection is cited unless it actually exists.

**Boundary.**

Section 11.2 MUST NOT introduce: new schema fields; new enums; new labels; new coordinate systems; new geometry; new sampling rules; new identity semantics; new counting semantics; new direction semantics; new density semantics; new queue semantics; new waiting-time semantics; new signal/control semantics; new Decision 3 semantics; IoU thresholds; matching thresholds; confidence thresholds; temporal tolerances; spatial tolerances; agreement percentages; kappa; F1; precision/recall; statistical tests; acceptance criteria; or pass/fail thresholds.

**Decision 2 protection.**

Decision 2 ("Option A — keep all sampled frames") is preserved unchanged. Section 11.2 must not create any IAA mechanism that changes the sampled-frame domain.

**Decision 3 boundary.**

Decision 3 is CLOSED. Section 11.2 must not connect IAA comparison targets to APPROACH_A, APPROACH_B, JUNCTION, region classification, Decision 3 geometry, Counting ROI, density, queue, waiting time, traffic direction, or signal/control. Decision 3 is mentioned only as an explicit boundary: it remains CLOSED and outside the IAA procedure.

**Known tracking/counting exit asymmetry.**

The known asymmetry between Tracking Ground Truth `roi_crossings` and Counting Ground Truth events remains preserved. Section 11.2 must not resolve it, add exit events to Counting Ground Truth, modify either schema, invent exit-counting semantics, or reinterpret direction semantics. If referenced, it is treated only as an existing documented asymmetry.

---

### 11.3 IAA Correspondence and Comparison-Pairing Rules

**Correspondence, not measurement.**

Section 11.3 defines WHICH annotation units are considered corresponding or comparable between independent annotation results. It does NOT define how agreement is scored, aggregated, or numerically measured. No numerical IAA metric is defined in this subsection. Numerical IAA measurement remains outside the scope of Section 11.3.

**Detection-level correspondence.**

A detection comparison unit is an annotated object within one sampled frame. Correspondence may be established using existing Detection Ground Truth identifiers and fields: `frame_id`, `class`, `bbox`, `visibility`, `occlusion`, `truncated`, and `difficult`. The existing sampled-frame domain and Detection Ground Truth schema are authoritative. When correspondence cannot be established from these existing rules, the case is reported as an unresolved detection correspondence and escalated; no new matching rule is invented.

**Tracking-level correspondence.**

A tracking comparison unit is a Ground Truth track. Correspondence is established using existing `global_id` and the existing frame membership of a track. The existing distinction `global_id` (Ground Truth identity) versus `track_id` (production tracker identity) is preserved and must not be redefined. Production tracker `track_id` is NOT used as an IAA Ground Truth identity key. When correspondence cannot be established from existing identity rules, the case is reported as an unresolved identity correspondence and escalated; no new identity-mapping rule or tolerance is invented.

**Counting-event correspondence.**

A counting-event comparison unit is an existing Counting Ground Truth event. Correspondence is established using existing Counting Ground Truth identifiers and fields: `global_id`, `class`, `frame_id`, `timestamp`, `roi_point`, `direction`, `bbox_at_crossing`, and `crossing_confidence`. The existing Counting Ground Truth schema and protocol are authoritative. When correspondence cannot be established from existing event rules, the case is reported as an unresolved event correspondence and escalated; no new event-matching rule or temporal window is invented.

**Sampling / frame-domain correspondence.**

Sampling correspondence is established against the existing deterministic Sampling Manifest and the existing sampled-frame domain, using existing manifest identifiers and fields: `video_id`, `total_frames`, `fps`, `base_interval`, `sample_id`, `frame_id`, `timestamp`, `split`, `sampling_reason`, `traffic_density`, `difficulty`, and where present `event_type`. Decision 2 ("Option A — keep all sampled frames") is preserved. A difference in sampled-frame domain is treated as an existing protocol/domain inconsistency, not resolved by inventing a new sampling rule, frame removal, temporal redundancy filtering, low-change exclusion, alternate sampling interval, random sampling, or new sampling criteria.

**Cross-layer correspondence.**

Cross-layer correspondence is established only where relationships already exist in the existing Section 8 schema architecture: Detection Ground Truth to Tracking Ground Truth, Tracking Ground Truth to Counting Ground Truth, and Sampling Manifest to the sampled Detection Ground Truth frame domain. Existing schema fields and relationships are authoritative. No new cross-layer field or relationship is inferred merely because two schemas contain similarly named information. When correspondence cannot be established from existing relationships, the case is escalated.

**Unresolved correspondence.**

When an existing rule is insufficient to establish correspondence for any comparison unit, the case is reported as unresolved and escalated for an explicit protocol decision. It is NOT resolved by inventing a correspondence rule, matching algorithm, tolerance, or threshold.

**Authority.**

Sections 1-9 are authoritative for annotation definitions, schemas, sampling, identity, counting, and reproducibility. Section 10 is authoritative for the QC verification framework. Section 11 is the IAA procedure only. Section 11.3 MUST NOT override any earlier section.

**Traceability.**

Authoritative sources include Section 5 (Ground Truth identity policy), Section 6 (counting semantics), Section 7 (temporal sampling and reproducibility), Section 8 (data schemas and schema relationships), Section 10.1 (QC purpose and boundary), Section 10.2 (QC traceability structure), Sections 10.3-10.8 (existing QC categories), and Section 11.2 (IAA comparison units). No subsection is cited unless it actually exists.

**Boundary.**

Section 11.3 MUST NOT introduce: new schema fields; new enums; new labels; new coordinate systems; new geometry; new sampling rules; new identity semantics; new counting semantics; new direction semantics; new density semantics; new queue semantics; new waiting-time semantics; new signal/control semantics; new Decision 3 semantics; IoU thresholds; spatial-distance thresholds; centroid-distance thresholds; temporal matching windows; frame tolerances; confidence thresholds; percentage thresholds; matching scores; Hungarian matching; greedy matching; nearest-neighbor matching; F1; precision; recall; Cohen's kappa; Fleiss' kappa; agreement percentages; statistical tests; numerical IAA metrics; or acceptance thresholds.

**Decision 2 protection.**

Decision 2 ("Option A — keep all sampled frames") is preserved unchanged. Section 11.3 introduces no mechanism that changes the sampled-frame domain.

**Decision 3 boundary.**

Decision 3 is CLOSED, IMPLEMENTED AND VALIDATED, and remains SPATIAL CLASSIFICATION ONLY with NO DOWNSTREAM CONSUMER. Section 11.3 MUST NOT connect IAA correspondence to APPROACH_A, APPROACH_B, JUNCTION, Decision 3 region labels, Decision 3 geometry, Decision 3 observation point, Counting ROI, density, queue, waiting time, traffic direction semantics, or signal/control semantics. Decision 3 is not reopened or audited here.

**Known tracking/counting exit asymmetry.**

The known asymmetry between Tracking Ground Truth `roi_crossings` and Counting Ground Truth events remains preserved. Section 11.3 must not resolve it, add exit events to Counting Ground Truth, modify either schema, invent exit-counting semantics, or reinterpret direction semantics. If referenced, it is treated only as an existing documented asymmetry.

---

### 11.4 IAA Disagreement Classification and Resolution Boundary

**Purpose.**

Disagreement classification identifies what kind of disagreement occurred between independent annotation results before any attempt at resolution. It is a procedural classification step, not a new annotation rule. It does not author new annotation semantics.

**Disagreement classes.**

Disagreement categories are derived only from already-existing concepts in Sections 1-11.3. The categories are:

- schema/conformance disagreement;
- temporal/frame-domain disagreement;
- detection annotation disagreement;
- identity/tracking disagreement;
- counting-event disagreement;
- sampling-manifest disagreement;
- cross-layer consistency disagreement;
- reproducibility-related disagreement.

No new annotation concept is created by defining these categories.

**Disagreement classification principle.**

A disagreement must first be classified against the existing authoritative requirement that governs the affected annotation or artifact. The classification identifies:

- affected object/artifact;
- affected field or existing concept;
- disagreement category;
- authoritative requirement;
- evidence examined;
- whether the disagreement is resolvable using an already-defined requirement.

This is a procedural classification structure only.

**Resolution boundary.**

If an existing requirement unambiguously determines the correct outcome, the disagreement may be resolved by applying that existing requirement. If existing requirements are insufficient, ambiguous, contradictory, or do not define the disputed case, the disagreement MUST be escalated. The annotator MUST NOT invent a new rule during disagreement resolution. Escalation must preserve the unresolved state rather than silently converting an interpretation into protocol authority.

**Distinction between classification, resolution, and protocol amendment.**

Section 11.4 may define classification and resolution procedurally, but MUST NOT itself amend the protocol. Any genuinely missing rule, contradictory authority, new semantic interpretation, new schema behavior, or unresolved ambiguity must be escalated for a separate protocol-level decision.

**Relation to Section 10.**

Section 10 QC findings and Section 11 IAA disagreements are related but distinct. Section 10 verifies compliance with existing requirements. Section 11 identifies and manages disagreement between annotators. Neither section becomes a source of new annotation semantics. Existing authority in Sections 1-9 remains authoritative.

**Relation to Section 11.3.**

Section 11.3 is the correspondence foundation for Section 11.4. If annotators disagree about whether two annotations can be compared or corresponded using existing identifiers, fields, or relationships, that disagreement must be classified and, if unresolved by existing authority, escalated. No new matching algorithm is introduced.

**Authority rule.**

Sections 1-9 remain authoritative for annotation, identity, counting, sampling, reproducibility, and schema semantics. Section 10 is a verification layer. Section 11 is an IAA procedural layer. Neither Section 10 nor Section 11 may silently redefine Sections 1-9. If a disagreement cannot be resolved from an existing authoritative requirement, ESCALATE — DO NOT INVENT.

**No numerical IAA rule.**

Section 11.4 MUST NOT define any numerical IAA metric. It MUST NOT define kappa, IoU, F1, precision, recall, percentage agreement, matching score, statistical significance, or acceptance threshold. The numerical IAA methodology, if required later, remains outside this subsection.

**Known tracking/counting exit asymmetry.**

The known asymmetry between Tracking Ground Truth `roi_crossings` and Counting Ground Truth events remains preserved as an existing documented issue. A disagreement involving this asymmetry is classified and escalated according to existing authority. Section 11.4 MUST NOT resolve the asymmetry, add exit events, modify Tracking Ground Truth, modify Counting Ground Truth, invent exit-counting semantics, or reinterpret direction semantics.

**Decision 3 boundary.**

Decision 3 remains completely outside Section 11.4. Section 11.4 MUST NOT introduce APPROACH_A, APPROACH_B, JUNCTION, region classification semantics, Decision 3 geometry, observation-point semantics, Counting ROI mapping, density, queue, waiting time, traffic direction, or signal/control semantics.

**Decision 2 protection.**

Decision 2 ("Option A — keep all sampled frames") is preserved unchanged. Section 11.4 introduces no sampled-frame removal, suppression, filtering, low-change exclusion, alternate interval, random sampling, or new sampling criterion.

**Boundary.**

Section 11.4 MUST NOT introduce: Cohen's kappa; Fleiss' kappa; Krippendorff's alpha; IoU thresholds; F1 / precision / recall metrics; agreement percentages; matching scores; spatial-distance thresholds; temporal tolerances; frame-distance thresholds; confidence thresholds; acceptance thresholds; statistical tests; annotator sample-size requirements; new pass/fail criteria; new annotation fields; new schema fields; new enums; new coordinate systems; new geometry; new ROI semantics; new direction semantics; new density semantics; new queue semantics; new waiting-time semantics; new signal/control semantics; new counting semantics; new identity semantics; new sampling rules; or new reproducibility requirements.

---

### 11.5 IAA Execution Preconditions and Deferred Methodology

**Purpose.**

Section 11.5 records the execution preconditions for the
Inter-Annotator Agreement procedure and the decisions that remain
deferred. It does NOT define the IAA methodology. It does NOT define
any numerical agreement metric, matching algorithm, or annotator
workflow. Every statement in this subsection is a boundary, a
preservation, or a deferral record — never a new rule.

**What Sections 11.1–11.4 already establish.**

The following are already defined by Sections 11.1–11.4 and are NOT
redefined here:

- IAA purpose, scope, and boundary (Section 11.1).
- the five IAA comparison targets: detection-level, tracking-level,
  counting-event, sampling/frame-domain, and cross-layer
  (Section 11.2).
- the correspondence and comparison-pairing boundary, limited to
  existing identifiers and schema relationships (Section 11.3).
- the eight disagreement classes and the resolution boundary
  "apply an existing requirement, or ESCALATE — DO NOT INVENT"
  (Section 11.4).

**Numerical IAA methodology is NOT defined in this subsection.**

Section 11.5 introduces no numerical IAA methodology. No agreement
metric, scoring rule, or calculation procedure is defined here.

Section 11.5 MUST NOT define, and explicitly preserves as undefined:

- IoU methodology;
- Hungarian matching;
- greedy matching;
- nearest-neighbor matching;
- centroid-distance matching;
- Cohen's kappa calculation;
- Fleiss' kappa calculation;
- Krippendorff's alpha calculation;
- F1 calculation;
- precision calculation;
- recall calculation;
- percent-agreement calculation;
- matching score;
- statistical test;
- numerical acceptance threshold;
- matching tolerance;
- spatial-distance threshold;
- temporal tolerance;
- frame-distance threshold;
- confidence threshold;
- annotator sample-size requirement;
- statistical population;
- aggregation method;
- scoring method;
- pass/fail rule.

These remain outside the scope of Section 11 and are NOT introduced
here. Any one of them requires a separate explicit decision or task,
consistent with Section 11.1.

**Annotator assignment, independence, and operational procedures are deferred.**

Section 11.1 records that operational procedures for achieving
independence are not defined and belong to later Section 11
subsections only if explicitly defined. Section 11.5 confirms that
position and does NOT resolve it.

Section 11.5 MUST NOT define, and explicitly preserves as deferred:

- annotator assignment;
- annotator scheduling;
- blinding procedure;
- randomization procedure;
- assignment algorithm;
- annotator count beyond what is already stated in Section 15;
- independence operationalization.

These procedures must NOT be invented here. They remain dependent on
the tool-selection decision, which is itself deferred (protocol
Section 8.6 records that tool comparison and tool selection are
deferred and that no tool is selected by this protocol).

**Formal adjudication / consensus is NOT introduced.**

Section 11.5 does NOT introduce a formal adjudication procedure,
consensus workflow, adjudicator role, or third-party resolution
mechanism.

The existing escalation rules in Section 11.1 and Section 11.4
remain the sole mechanism for disagreements that cannot be
resolved by an existing authoritative requirement. Where existing
requirements are insufficient, ambiguous, contradictory, or do not
define the disputed case, the disagreement MUST be escalated for a
separate protocol-level decision. The annotator MUST NOT invent a
new rule during disagreement resolution.

**Section 15 criterion is recorded as an existing, unresolved target.**

Section 15 contains the existing pilot acceptance criterion:

- **Occlusion level agreement** — Cohen's κ ≥ 0.75 between two
  annotators.

Section 11.5 records this criterion as it exists. It does NOT
implement it, does NOT define how the κ value is calculated, does NOT
define the population, comparison unit, pairing method, aggregation
method, or calculation procedure required to evaluate it, and does
NOT reinterpret, delete, modify, or replace it.

The Section 15 criterion currently exists as an unresolved /
deferred target. Its operational calculation depends on future
explicit methodology decisions that are not made here. It is NOT
elevated into IAA authority, and Section 15 is NOT used as authority
for any IAA calculation method.

**Decision 2 is preserved.**

Decision 2 ("Option A — keep all sampled frames") is preserved
unchanged. Section 11.5 introduces no mechanism that removes,
suppresses, filters, or excludes sampled frames. It MUST NOT
introduce: low-change exclusion; temporal redundancy filtering; frame
suppression; alternate sampling interval; random sampling; or any
new sampling criterion. It MUST NOT reinterpret Decision 2.

**Decision 3 is CLOSED.**

Decision 3 remains CLOSED, IMPLEMENTED AND VALIDATED, and remains
SPATIAL CLASSIFICATION ONLY with NO DOWNSTREAM CONSUMER. Section 11.5
MUST NOT connect IAA to APPROACH_A, APPROACH_B, JUNCTION, region
classification semantics, Decision 3 geometry, observation-point
semantics, Counting ROI mapping, density, queue, waiting time, traffic
direction, or signal/control semantics. Decision 3 is not reopened or
audited here.

**The known tracking/counting exit asymmetry is preserved.**

The known asymmetry between Tracking Ground Truth `roi_crossings` and
Counting Ground Truth events remains preserved as an existing
documented asymmetry. Section 11.5 MUST NOT resolve it, add exit
events to Counting Ground Truth, modify Tracking Ground Truth, modify
Counting Ground Truth, invent exit-counting semantics, or reinterpret
direction semantics. If an IAA comparison involves this area, it is
classified and escalated according to existing authority.

**No new schema, data product, or reporting artifact.**

Section 11.5 MUST NOT introduce: new schema fields; new enums; new
constraints; new data products; new comparison datasets; new
reporting schemas; new matching algorithms; new coordinate systems;
new geometry; new ROI semantics; new direction semantics; new density
semantics; new queue semantics; new waiting-time semantics; new
signal/control semantics; new counting semantics; new identity
semantics; or new reproducibility requirements.

**Authority rule.**

Sections 1–9 remain authoritative for annotation, identity, counting,
sampling, reproducibility, and schema semantics. Section 10 is a
verification layer. Sections 11.1–11.4 are authoritative for the
current IAA framework. Section 11.5 is a preconditions and deferral
record only. It MUST NOT redefine any requirement from Sections
1–11.4. If a precondition requires a rule not present in Sections
1–11.4, it is escalated as a future decision or escalation item and
is NOT invented here.

---

## 14. Known Ambiguities (Current)

| # | Ambiguity | Impact | Resolution Approach |
|---|-----------|--------|---------------------|
| **A1** | **Occlusion visibility threshold for counting** — Is `visibility > 0.1` sufficient to confirm crossing during occlusion? | May miss valid crossings or create false positives | Pilot annotation on 10 frames; measure inter-annotator agreement |
| **A2** | **Long disappearance threshold (30 frames / 2 sec)** — Is this appropriate for 15 FPS video with occasional stops? | Affects track fragmentation vs. false merge tradeoff | Analyze 3.mp4: measure typical stop durations; adjust if needed |
| **A3** | **Similar vehicle re-identification** — After >30 frame gap, same visual appearance: new ID or same? | Directly affects IDF1/HOTA | Conservative: new ID unless distinctive features (damage, roof rack) |
| **A4** | **Tangential ROI crossing** — Vehicle skims boundary without fully entering | Low frequency in 3.mp4 (straight road) | Annotator judgment + `crossing_confidence: "low"` |
| **A5** | **Class ambiguity at distance** — Car vs truck, motorcycle vs person at far range | Affects per-class counting metrics | `difficult: true` + most conservative class (`car` for vehicles) |
| **A6** | **Partial frame sampling effect on crossing detection** — If crossing occurs between annotated frames | May miss exact crossing frame | Interpolation for crossing frame; or annotate ±10 frames around crossings (Sec 12) |
| **A7** | **Person class in custom model** — Phase 1.3A notes `person` not in custom model; comes from pretrained if enabled | Counting GT includes person but detection may not | Flag in evaluation: person counting = upper bound only |

---

## 15. Acceptance Criteria (For Pilot Dataset)

| Criterion | Target |
|-----------|--------|
| **Occlusion level agreement** | Cohen's κ ≥ 0.75 between 2 annotators |
| **Global_id consistency** | Zero identity merges (two objects same ID) or splits (one object two IDs) in audit |
| **Counting event agreement** | 100% match on `global_id` + `frame_id` for unambiguous crossings |
| **Schema validation** | 100% of tracks/events pass JSON schema validation |
| **Cross-reference integrity** | Every `count_events.global_id` exists in `tracks.global_id` |
| **Completeness** | All sampled frames annotated; all ROI crossings in sampled frames captured |

---

## 16. Consistency Audit — Sections 4–6 (Checkpoint 2.5)

This audit was performed after defining Bounding Box (Sec 3), Occlusion (Sec 4), global_id (Sec 5), and Counting Event (Sec 6) policies. No redesign — only clarifications to resolve internal inconsistencies.

| Audit | Issue Found | Decision Made | Section Changed |
|-------|-------------|---------------|-----------------|
| **A1: Visibility = 0** | Severe occlusion interval included `[0.0, 0.1]`, implying bbox exists at visibility = 0 | **Visibility = 0 → no bbox annotation.** Full invisibility frames are gaps in `frames` array; `global_id` persists without observation. Severe occlusion = `(0.0, 0.1]` (barely detectable). Three temporal regimes defined: temporary occlusion (visibility=0, ≤30 frames), short disappearance (left view, ≤30 frames, visual match on return), long disappearance (>30 frames = new ID). | 4.1, 5.3 |
| **A2: Short-gap re-entry threshold** | "Short-gap" mentioned but threshold not defined | **30 frames / 2 seconds** is the single threshold for all gap-based decisions: temporary occlusion, short disappearance, long disappearance. Based on 15 FPS video and ByteTrack `stale_frames=30` config. | 5.3 (added regime table) |
| **A3: crossing_confidence** | Subjective field with no scoring rule | **Objective deterministic rule** based on observable fields at crossing frame: `visibility`, `occlusion`, `truncated`, `difficult`, bbox geometry. Three tiers: high/medium/low with explicit AND/OR conditions. No annotator judgment. | 6.3 (field description), 6.3.1 (new subsection) |
| **A4: Class change** | Edge case allowed "terminate old, start new" but also "mark difficult on continuing track" — contradictory | **Class is immutable per `global_id`.** Genuine class change → new `global_id`. Uncertainty (distance/occlusion) → same `global_id`, original class, `difficult: true` on affected frames. No class change within a track. | 5.6 (updated edge case) |
| **A5: Tracking → Counting consistency** | Counting derivation referenced `global_id` + frame data — verified consistent | **Confirmed:** Every count event derivable from tracking GT (`global_id`, per-frame `bbox`/`center`, `frame_id`, `timestamp`) + ROI geometry. No ByteTrack `track_id` required. Counting GT is algorithmically derived from tracking GT. | 6.2, 6.6, 6.8 (verified) |
| **A6: Future trajectory compatibility** | Track schema includes `center`, `timestamp`, `frame_id`, `bbox`, `global_id`, `class`, `roi_crossings` | **Sufficient.** Minimal representation supports: trajectory (center + timestamp), zone transition (roi_crossings + direction), dwell time (timestamp differences within zone), traffic state (class + timestamp + zone), dynamic graph (global_id + sequential zone transitions). No additional fields needed. | 5.5, 6.9 (verified) |

**Remaining Ambiguities (require pilot annotation to resolve):**
- A1: Occlusion visibility threshold for counting (pilot κ measurement)
- A2: 30-frame threshold appropriateness for 3.mp4 stop durations (empirical analysis)
- A3: Similar vehicle re-identification after >30 frames (conservative = new ID)
- A4: Tangential ROI crossing (low frequency in 3.mp4)
- A5: Class ambiguity at distance (difficult + conservative class)
- A6: Sampling effect on crossing detection (±10 frame window)
- A7: Person class detection gap (evaluation flag)

---

## 17. Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2026-08-17 | — | Initial draft: Sections 1–4 (Scope, Annotation Rules, Bounding Box Policy, Occlusion Policy) |
| 0.2 | 2026-08-17 | — | Fixed occlusion visibility ranges (non-overlapping intervals); Added Section 5 (global_id Policy); Added Section 6 (Counting Event Policy); Added Section 14 (Known Ambiguities); Added Section 15 (Acceptance Criteria) |
| 0.3 | 2026-08-17 | — | Consistency Audit (Checkpoint 2.5): Fixed visibility=0 semantics (no bbox); Defined 3 temporal regimes with 30-frame threshold; Added objective crossing_confidence scoring rule; Enforced class immutability per global_id; Verified tracking→counting derivation; Verified future trajectory compatibility; Added Audit section |
| 0.4 | 2026-08-18 | — | Added Section 7 (Temporal Sampling Protocol): 7.1 Purpose (annotation/evaluation scope, no pipeline modification); 7.2 Sampling Units and Frame Indexing (source/candidate/sampled/event-boosted/annotation frames); 7.3 Baseline Keyframe Sampling (every 5th frame, f mod 5 == 0, deterministic, reproducible, protocol parameter not empirical fact) |
| 0.5 | 2026-08-18 | — | Added 7.4 Event-Boosted Sampling (E1 ROI crossing, E2 appearance/disappearance, E3 identity ambiguity, E4 heavy/severe occlusion, E5 class ambiguity, E6 difficult traffic; window size = protocol parameter); Added 7.5 Stratified Sampling Criteria (density/occlusion/illumination/traffic-event strata; explicit table separating protocol parameters from empirically observed values; no unmeasured distributions claimed) |
| 0.6 | 2026-08-18 | — | Added 7.6 Temporal Train/Validation/Test Split (approved split 0–249 train, 250–374 val, 375–499 test; contiguous temporal split, random frame-level split forbidden; deterministic `split(frame_id)` rule; frames 500–614 unassigned, recorded as open item); Added 7.7 Leakage Prevention (frame-content leakage via one-frame-one-partition + clipped event windows, identity continuity is not leakage, tracker-state reset at partition boundaries, counting-event attribution); Added 7.8 Handling ROI-Crossing Events (boundary crossing attribution rule, read-only anchor at t−1, case table, anchor_frame_id derivation log, pipeline-evaluation asymmetry) |

---
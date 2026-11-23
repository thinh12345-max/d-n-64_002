# PHASE 1.3B STATE

## Phase
1.3B — Annotation Protocol & Tool Design

## Completed Sections
- Section 1: Scope
- Section 2: Annotation Rules (General)
- Section 3: Bounding Box Policy
- Section 4: Occlusion Policy
- Section 5: Ground Truth global_id Policy (Tracking Identity)
- Section 6: Counting Event Policy
- Section 16: Consistency Audit (Sections 4–6)
- Section 14: Known Ambiguities (Current)
- Section 15: Acceptance Criteria (For Pilot Dataset)
- Section 17: Version History

## Current Section
Sections 1–9.7.6 complete. No authoritative next edit task currently exists.

## Existing Schemas
- annotation/schema/counting_ground_truth.schema.json
- annotation/schema/sampling_manifest.schema.json
- annotation/schema/detection_ground_truth.schema.json
- annotation/schema/tracking_ground_truth.schema.json

## Missing Schemas
- None currently (all four schemas present as of latest check)

## Important Decisions
- Temporal split: frames 0–249 train, 250–374 validation, 375–499 test
- Never random frame-level splitting
- Baseline keyframe sampling: every 5th frame
- Event boosting around ROI entry, appearance/disappearance, identity changes, severe occlusion, ambiguous identity, class ambiguity, difficult traffic
- Stratification by density, occlusion, illumination, traffic events
- 30 frames / 2 seconds = short-gap threshold (15 FPS)
- global_id independent of ByteTrack track_id
- class immutable per global_id
- counting events derived algorithmically from tracking GT
- visibility = 0 means no bbox observation
- severe occlusion = (0.0, 0.1]

## Known Ambiguities
- A1: Occlusion visibility threshold for counting (pilot κ measurement)
- A2: 30-frame threshold appropriateness for stop durations
- A3: Similar vehicle re-identification after >30 frames
- A4: Tangential ROI crossing (low frequency)
- A5: Class ambiguity at distance (difficult + conservative class)
- A6: Partial frame sampling effect on crossing detection (±10 frame window)
- A7: Person class detection gap (evaluation flag)

## Next Planned Checkpoints
- Checkpoint 3B: Section 8 — Annotation Tool Decision
- Section 9: Data Schema
- Section 10: Pilot Dataset Definition
- Section 11: Quality-Control Checklist
- Section 12: Inter-Annotator Agreement Procedure
- Section 13: Known Ambiguities (updated)
- Section 14: Acceptance Criteria (final)
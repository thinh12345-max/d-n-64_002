# D-06.32 — HUMAN SCIENTIFIC DECISION REVISION

**Date:** 2026-09-14
**Status:** RECORDED

---

## REVISION OF D-06.27

This decision revises D-06.27 based on new evidence from D-06.31 direct stream decoding.

---

## AUTHORITATIVE VIDEO 3 SOURCE DECISION (REVISED)

| Property | Previous (D-06.27) | Revised (D-06.32) |
|----------|-------------------|-------------------|
| Source file | `public/3.mp4` | `public/3.mp4` |
| Frame count | 615 | 621 |
| Frame range | 0-614 | 0-620 |
| FPS | 15.0 | 15.0 |
| Dimensions | 1280x720 | 1280x720 |

---

## EVIDENCE FROM D-06.31

| Finding | Status |
|---------|--------|
| Direct stream decoding performed | YES |
| Successfully decodable frames | 621 |
| Actual readable frame range | 0-620 |
| Frames 615-620 valid/unique/non-empty | YES |
| Sequence continuity | CONFIRMED |
| Timestamp continuity | VALID |
| Last six frames are padding/duplicates | NO |
| Discrepancy cause | Incorrect container metadata (615) |

---

## KEY FINDINGS

1. **METADATA_FRAME_COUNT**: 615 (INCORRECT)
2. **ACTUAL_DECODED_FRAME_COUNT**: 621
3. **DECODED_STREAM_IS_AUTHORITATIVE**: YES (over metadata)
4. **STREAM_CONTINUITY**: CONFIRMED (0-620 continuous)
5. **STREAM_EOF_AFTER_FRAME**: 620 (read index 621)
6. **TRAJECTORY_1_TO_621**: VALID_FOR_621_FRAME_STREAM (consistent with 1-based stored frame_id convention)

---

## REQUIRED OUTPUT

```
D-06.32_STATUS: PASS

DECISION_TYPE: REVISION_OF_D-06.27

AUTHORITATIVE_SOURCE: public/3.mp4

PREVIOUS_FRAME_COUNT: 615
REVISED_FRAME_COUNT: 621

PREVIOUS_FRAME_RANGE: 0-614
REVISED_FRAME_RANGE: 0-620

METADATA_FRAME_COUNT: 615
ACTUAL_DECODED_FRAME_COUNT: 621

METADATA_IS_AUTHORITATIVE: NO
DECODED_STREAM_IS_AUTHORITATIVE: YES

LAST_SIX_FRAMES_VALID: YES
STREAM_CONTINUITY: CONFIRMED
STREAM_EOF_AFTER_FRAME: 620

TRAJECTORY_1_TO_621_STATUS: VALID_FOR_621_FRAME_STREAM
TRAJECTORY_REGENERATION_REQUIRED: NO
FRAME_ADAPTER_REQUIRED: NO_AT_THIS_STAGE

ORIGINAL_D-06.27_PRESERVED: YES
D-06.27_REVISED: YES

PROTOCOL_CORRECTION_REQUIRED: YES
TRACKING_GT_CREATION_ALLOWED_NOW: NO
TRACKING_EVALUATION_ALLOWED_NOW: NO

PROTOCOL_MODIFIED: NO
TRAJECTORY_MODIFIED: NO
RUNTIME_CODE_MODIFIED: NO
GT_CREATED: NO
TRACKING_EVALUATION_RUN: NO

FILES_MODIFIED: protocol/tracking_evaluation_protocol_D06.32_human_decision_revision.md (NEW)

HUMAN_DECISION_RECORDED: YES

NEXT_REQUIRED_ACTION: Protocol correction to reflect 621-frame authoritative count for future reference

FINAL_AUDIT: PASS
```

---

## PRESERVATION NOTES

- Original D-06.27 decision preserved in `tracking_evaluation_protocol_D06.27_human_decision.md`
- D-06.32 creates NEW revision record, does NOT overwrite D-06.27
- trajectory.json with frame IDs 1-621 remains VALID (1-based stored frame_id convention)
- No runtime code modifications performed
- No trajectory regeneration required
- No frame adapter created

---

**RECORDED:** YES

**HUMAN_SCIENTIFIC_DECISION:** REVISION_OF_D-06.27_FRAME_COUNT_615_TO_621

**REVISION_REASON:** D-06.31 evidence proves metadata (615) is incorrect; decoded stream (621) is authoritative

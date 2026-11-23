# D-06.27 — HUMAN SCIENTIFIC DECISION RECORDING

**Date:** 2025-09-13
**Status:** RECORDED

---

## AUTHORITATIVE VIDEO 3 SOURCE DECISION

The HUMAN PROJECT OWNER has made the following scientific decision:

### Authoritative Video 3 Source

| Property | Value |
|----------|-------|
| Source file | `public/3.mp4` |
| Frame count | 615 |
| Frame range | 0-614 |
| FPS | 15.0 |
| Dimensions | 1280x720 |
| Git status | Tracked blob unchanged since first commit |

### Provenance Findings

| Finding | Status |
|---------|--------|
| 621-frame Video 3 source identified | NO |
| 621-frame expectation supported | NO |
| trajectory.json (621 IDs) matches current video | NO |
| 621-frame claim origin | Incorrect documentation assumption |

### Decisions

1. **AUTHORITATIVE_FRAME_COUNT**: 615 (NOT 621)
2. **AUTHORITATIVE_FRAME_RANGE**: 0-614 (NOT 0-620)
3. **621_FRAME_EXPECTATION**: REJECTED
4. **TRAJECTORY_621_1_TO_621**: REJECTED as current Video 3 evidence

### Required Actions (Subsequent Tasks)

| Action | Required |
|--------|----------|
| Protocol correction (621→615) | YES |
| trajectory.json regeneration | YES |
| Tracking GT creation | NOT YET (regeneration must happen first) |
| Tracking evaluation | NOT YET |

### Evidence

- Git-tracked `public/3.mp4`: 615 frames, 0-614, unchanged since first commit
- No 621-frame video source found in project
- `outputs/trajectory.json` is untracked, generated locally, provenance unknown
- Protocol's 621-frame claim appears in untracked docs without source verification

---

**RECORDED:** YES

**HUMAN_SCIENTIFIC_DECISION:** AUTHORITATIVE_VIDEO_3_IS_PUBLIC_3_MP4_615_FRAMES

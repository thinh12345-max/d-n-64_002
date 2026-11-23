# Claude Prompt History

## Entry 001
Date:
Task:
Result:
Files changed:
Status:

## Entry 002
Date: 2026-08-19
Task: PHASE 1.3B — SECTION 7.9 ONLY (TEMPORAL SAMPLING — PART 5): add "7.9 Handling Short Tracking Gaps and Occlusion" to docs/PHASE_1_3B_ANNOTATION_PROTOCOL.md, inserted after Section 7.8 and before the "Section 7.9–7.12" outline listing.
Result: Section 7.9 written with five defined states (observed frame, occluded observation, fully invisible gap, short gap, long disappearance), the approved 30-frame/2-second short-gap threshold, visibility=0 = no bbox, severe occlusion = (0.0, 0.1], global_id persistence through approved short gaps, global_id independence from ByteTrack track_id, no extrapolated bbox for fully invisible frames, sampling interaction per state, tracking GT recording requirements, and counting-event consistency. No rules in Sections 1–6 or 7.1–7.8 modified; no 7.10+ subsections created; no JSON schema changed; no production code touched. ACTIVE_CONTEXT.md updated (7.9 = COMPLETE, Current Task = 7.10).
Files changed:
- docs/PHASE_1_3B_ANNOTATION_PROTOCOL.md (added Section 7.9; updated document status line)
- docs/claude_context/ACTIVE_CONTEXT.md (Current Task, Missing, Section 7 Progress)
Status: COMPLETE

## Entry 003
Date: 2026-08-19
Task: PHASE 1.3B — SECTION 7.10 ONLY (TEMPORAL SAMPLING — PART 6): add "7.10 Handling Frames Near Important Events" to docs/PHASE_1_3B_ANNOTATION_PROTOCOL.md, inserted immediately after the complete existing Section 7.9 and before the "Section 7.6–7.8" outline listing.
Result: Section 7.10 written with two sampling modes (base_temporal vs event-boosted), near-event frame handling for the seven established categories (E1 ROI crossing, E2 appearance, E3 disappearance, E4 identity ambiguity, E5 heavy/severe occlusion, E6 class ambiguity, E7 difficult traffic events), deterministic event priority and one-frame-one-sampling-record resolution, and an explicit preserved-rules table. ROI-crossing handling defers to Section 7.8; train/val/test partition rules defer to Section 7.6; leakage prevention rules defer to Section 7.7. No rules in Sections 1–6 or 7.1–7.9 modified; no 7.11 or 7.12 created; no JSON schema changed; no production code touched. ACTIVE_CONTEXT.md updated (7.10 = COMPLETE, Current Task = 7.11).
Files changed:
- docs/PHASE_1_3B_ANNOTATION_PROTOCOL.md (added Section 7.10; updated document status line)
- docs/claude_context/ACTIVE_CONTEXT.md (Current Task, Missing, Section 7 Progress)
- docs/claude_context/PROMPT_HISTORY.md (this entry)
Status: COMPLETE
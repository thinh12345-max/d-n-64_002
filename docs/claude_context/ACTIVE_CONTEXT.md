# ACTIVE PROJECT CONTEXT

## Current Phase
Phase 1.3B — Annotation Protocol

## Current Checkpoint
Checkpoint 4 — Evaluation Protocol and Formal Procedures (Sections 8–9 complete)

## Completed
- Phase 1.1 configuration completed
- Phase 1.2 performance benchmark completed
- Phase 1.3A annotation specification completed
- Sections 1–6 of PHASE_1_3B_ANNOTATION_PROTOCOL.md completed
- Sections 4–6 consistency audit completed
- Section 7 (Temporal Sampling Protocol) complete (7.1–7.13)
- Section 8 (Data Schema) complete (8.1–8.6)
- Section 9 (Evaluation Protocol) complete (9.1–9.7)
- Section 10 (Quality-Control Checklist) COMPLETE (10.1–10.8)
- Section 11 (Inter-Annotator Agreement Procedure) IN PROGRESS (11.1–11.4 complete; 11.5 NOT started)
- counting_ground_truth.schema.json exists
- sampling_manifest.schema.json exists

## Current Task
Sections 8–9 complete. Section 10 (Quality-Control Checklist) is COMPLETE
(10.1–10.8). Section 11 (Inter-Annotator Agreement Procedure) is IN PROGRESS:
11.1–11.4 are COMPLETE; 11.5 has NOT been started and is NOT authorized by this
synchronization. No authoritative next edit task has been authorized; the next
main roadmap task is not yet authorized / pending planning decision.

## Missing
None. All four annotation schemas exist and are verified:
- counting_ground_truth.schema.json
- sampling_manifest.schema.json
- detection_ground_truth.schema.json
- tracking_ground_truth.schema.json

## Section 7 Progress
- 7.1 Purpose — complete
- 7.2 Sampling Units and Frame Indexing — complete
- 7.3 Baseline Keyframe Sampling — complete
- 7.4 Event-Boosted Sampling — complete
- 7.5 Stratified Sampling Criteria — complete
- 7.6 Temporal Train/Val/Test Split — complete (0–249 train, 250–374 val, 375–499 test; contiguous; deterministic; frames 500–614 unassigned)
- 7.7 Leakage Prevention — complete (one-frame-one-partition; clip event windows at boundary, do not move; tracker-state reset; identity continuity is not leakage)
- 7.8 Handling ROI-Crossing Events — complete (boundary attribution to partition of crossing frame t; read-only anchor at t−1; case table; anchor_frame_id derivation log)
- 7.9 Handling Short Tracking Gaps and Occlusion — complete (five states: observed / occluded observation / fully invisible gap / short gap / long disappearance; 30-frame threshold; no extrapolated bbox; global_id persistence; sampling interaction; counting event consistency)
- 7.10 Handling Frames Near Important Events — complete (base_temporal vs event-boosted sampling modes; E1 ROI crossing / E2 appearance / E3 disappearance / E4 identity ambiguity / E5 heavy-severe occlusion / E6 class ambiguity / E7 difficult traffic events; deterministic event priority; preserved rules: base sampling deterministic, boosting is dataset-construction only, one frame one sampling record, 7.8 ROI-crossing authoritative, 7.6 partition rules authoritative, 7.7 leakage rules authoritative)
- 7.11 Sampling Manifest Requirements — complete (7.11.1 purpose and scope; 7.11.2 required manifest fields; 7.11.3 sampling record semantics; 7.11.4 manifest validation and consistency)
- 7.12 Reproducibility Requirements — complete (7.12.1 deterministic sampling inputs; 7.12.2 protocol and version recording; 7.12.3 manifest preservation; 7.12.4 dataset regeneration conditions; 7.12.5 reproducibility verification)

## Important Decisions
- Temporal split: 0–249 train, 250–374 validation, 375–499 test
- Never random frame-level split
- Baseline keyframe interval: every 5th frame
- 30 frames = 2 seconds at 15 FPS
- global_id is independent from ByteTrack track_id
- class is immutable per global_id
- counting derives from tracking GT
- visibility = 0 means no bbox observation
- severe occlusion = (0.0, 0.1]

## Current Rule
Claude must perform small atomic tasks.
Claude must not scan the entire repository.
Claude must not modify unrelated files.

## Protected / Preserved State (unchanged)
- Decision 2 remains: "Option A — keep all sampled frames." No low-change exclusion,
  temporal redundancy filtering, frame suppression, alternate interval, random
  sampling, or new sampling criterion.
- Decision 3 remains CLOSED, IMPLEMENTED AND VALIDATED, SPATIAL CLASSIFICATION ONLY
  with NO DOWNSTREAM CONSUMER. No density, queue, waiting time, traffic direction,
  or signal/control semantics.
- The known tracking/counting exit asymmetry (tracking `roi_crossings` may record
  `exit` while Counting GT is entry-only) remains preserved as an existing
  documented asymmetry; it is not resolved.
- Section 10 remains a QC / verification layer and does NOT redefine Sections 1–9.
- Section 11.1–11.4 remain within their established boundaries; they define
  verification/comparison procedures only, not annotation semantics.
- No schema, code, geometry, or sampling rule change is authorized by this file.

## Document Authority
`docs/PHASE_1_3B_ANNOTATION_PROTOCOL.md` is the authoritative content source.
This file is a compact project-state / roadmap file only; it does not replace,
restate, or supersede the protocol document. Any conflict is resolved by the
protocol document. Existing unresolved ambiguities (protocol Section 14) remain
unresolved.

## Decision Authority (GD-01)

**Project Decision Authority: HUMAN PROJECT OWNER** (human-confirmed, 2026-08-29).

The human project owner holds final decision authority for project-level
decisions, including: project scope; protocol amendments; methodology
decisions; authorization of major project tasks; and reopening of
protected or previously ratified decisions.

This record establishes WHO decides. It does NOT itself authorize any
particular pending decision. Existing OPEN, DEFERRED, PROHIBITED, PRESERVED,
and NOT-FRAMED states remain unchanged.

These four concepts are deliberately NOT conflated:

- **Decision authority** — the human project owner. Makes binding project
  decisions.
- **Document authority** — `docs/PHASE_1_3B_ANNOTATION_PROTOCOL.md` (see
  "Document Authority", above). Authoritative content source; is NOT a
  decision-maker.
- **Execution / analysis authority** — Claude Code. Inspects authorized
  material, performs authorized analysis, implements explicitly authorized
  changes, and reports blockers. Is NOT the decision authority and may NOT
  independently resolve, authorize, amend, or reopen any decision.
- **Advisory role** — analysis that recommends options. A recommendation
  is NOT authorization. The final project decision remains with the
  Project Decision Authority.

Claude Code remains an execution / analysis / verification agent.

## Decision Authority Scope (GD-02)

**Status:** COMPLETE — AUTHORITY SCOPE RECORDED (2026-08-29).

**Project Decision Authority:** HUMAN PROJECT OWNER (see Decision Authority,
GD-01, above).

GD-02 defines **WHAT CATEGORIES** of project decisions the Project Decision
Authority may make or authorize. It does NOT itself make, authorize, or
resolve any decision.

**AUTHORITY TO DECIDE ≠ DECISION ALREADY MADE.** Recording that the Project
Decision Authority *may* decide a category does NOT mean any decision in
that category has been made. Nothing in GD-02 resolves, authorizes, or
changes the state of D-01 through D-06 or any other pending item.

**The Project Decision Authority has final authority over project-level
decisions in the following categories, subject to existing protocol
boundaries and explicitly preserved decisions:**

1. **Project scope** — changes to project scope, objectives, or governing
   project boundaries.
2. **Protocol amendments** — authorization of changes to the authoritative
   protocol document. This records authority to authorize an amendment;
   GD-02 does NOT itself amend the protocol.
3. **Methodology decisions** — authorization or decision-making concerning
   methodology that is explicitly deferred or outside the currently
   authorized scope. GD-02 does NOT define any methodology and does NOT
   resolve κ methodology.
4. **Annotation-tool selection** — final authorization/decision concerning
   the project annotation tool. GD-02 does NOT select a tool.
5. **Reopening protected or ratified decisions** — authorization to reopen
   a previously protected, preserved, or ratified project decision when
   such reopening is explicitly intended. GD-02 does NOT reopen Decision 2,
   Decision 3, or any other preserved decision.
6. **Major project task authorization** — authorization of future major
   project tasks requiring explicit project-level approval. GD-02 does NOT
   authorize any specific pending task.
7. **Resolution of deferred project decisions** — final authority to
   resolve project-level decisions that are explicitly deferred and
   require a future decision. GD-02 does NOT resolve D-01, D-02, D-03,
   D-04, D-05, or D-06.

**GD-02 does NOT itself:**

- authorize any pending decision;
- change the state of D-01 through D-06;
- define κ methodology;
- define comparison population, comparison unit, pairing, aggregation,
  matching, thresholds, tolerances, scoring, or acceptance methodology;
- select an annotation tool;
- amend the protocol;
- modify Section 15;
- reopen Decision 2 or Decision 3;
- resolve the tracking/counting exit asymmetry;
- authorize Section 11.5, Section 11.6, or any other specific next edit;
- or create a decision log, approval workflow, quorum, voting rules,
  approval thresholds, review board, committee, sign-off procedure,
  amendment workflow, escalation hierarchy, or additional decision-maker.

**Constraints preserved.** Individual decisions may still require an
explicit decision, a separately authorized task, a protocol amendment, a
scope change, or other prerequisites already established by the protocol.
Existing protocol constraints, protected states, and preserved decisions
remain authoritative unless separately changed through an explicitly
authorized decision.

**Claude Code** remains execution / analysis / verification authority only
and does NOT gain decision authority from GD-02. Recommendations from
analysis remain advisory and require the Project Decision Authority's
decision or authorization where applicable.

## Decision Recording & Effectiveness (GD-03)

**Status:** COMPLETE — DECISION RECORDING & EFFECTIVENESS SEMANTICS RECORDED (2026-08-29).

GD-03 establishes governance semantics only. It does NOT make, authorize, or resolve any project decision.

**Four-way distinction.** These are deliberately NOT conflated:

1. **Analysis** — inspection, comparison, and interpretation of authorized material. Analysis is NOT a decision.
2. **Recommendation** — an option suggested by analysis. A recommendation is NOT a decision.
3. **Explicit decision** — a binding project decision. A project decision must come from the Project Decision Authority (HUMAN PROJECT OWNER, per GD-01). No other person or system may make one.
4. **Authorization to implement** — an explicit grant, from the Project Decision Authority, permitting implementation of a decision. Implementation authorization is NOT implied merely because a topic was discussed, analyzed, or recommended.

**Claude Code may NOT:** convert a recommendation into a decision; infer an unstated decision; treat discussion, analysis, recommendation, implication, precedent, previous implementation, or its own interpretation as an explicit project decision; or treat wording such as "probably", "should", or "we can" as a decision. If implementation authorization is not explicit, Claude Code must treat the matter as unresolved for implementation purposes.

**Minimum explicit decision record.** Where applicable, an explicit decision record contains, as supported by the recording context:

- decision identifier or reference;
- decision subject;
- explicit decision statement;
- authority/source = HUMAN PROJECT OWNER;
- decision status;
- effective implementation authorization, if explicitly granted;
- date/time or equivalent recording context, if already supportable.

No additional mandatory fields are established. No decision log, approval workflow, quorum, voting system, approval board, committee, sign-off procedure, amendment workflow, escalation hierarchy, or additional decision-maker is created.

**Recording location.** An explicit decision is recorded in `docs/claude_context/ACTIVE_CONTEXT.md`. No separate decision-log file, governance document, or protocol amendment is created for recording purposes.

**Recording a decision does NOT itself resolve unrelated decisions.** Recording the authority, scope, or recording semantics does NOT change the state of D-01 through D-06, does NOT authorize Section 11.5 or 11.6, and does NOT authorize any specific next task.

**GD-03 does NOT:** authorize a specific next task; authorize Section 11.6; authorize Section 11.5+; select an annotation tool; define methodology; amend the protocol; change Section 15; resolve exit asymmetry; reopen Decision 2; reopen Decision 3; resolve D-01 through D-06; create a governance committee; or create another decision authority.

**Protected states** (Decision 2, Decision 3, exit asymmetry, Section 10 QC rules, Section 11.1–11.5 boundaries, Section 15 acceptance criteria, sampling interval, temporal sampling rules, schema definitions, existing code state) remain unchanged.

## D-02 Human Project Owner Input Record (D-02-C)

**Status:** RECORDED (2026-08-29). HUMAN PROJECT OWNER inputs for D-02 only. This record does NOT decide D-02.

### Candidate Set

The HUMAN PROJECT OWNER has explicitly supplied the following candidate set for the bounded D-02 evaluation:

- **Roboflow**

Roboflow is the **only** candidate currently authorized for consideration within this bounded D-02 evaluation.

**This is a candidate-set declaration, NOT selection or authorization of Roboflow.** Roboflow is NOT the selected project annotation tool and is NOT authorized as the project annotation tool by this record. D-02 remains undecided until a separate explicit decision is made.

### Selection Criteria

The HUMAN PROJECT OWNER has explicitly supplied the following criteria for the bounded D-02 evaluation. Recorded exactly as supplied; no criterion added, removed, or weighted.

1. Compatibility with the project's existing annotation workflow.
2. Preservation and traceability of source `frame_id`.
3. Compatibility with the project's bounding-box coordinate contract.
4. Support for manual identity annotation/management compatible with the project's `global_id` semantics.
5. The workflow must not make model or tracker output authoritative Ground Truth.
6. The workflow must not require changing the established Sampling Protocol.
7. The workflow must not conflict with Decision 2.
8. The workflow must not conflict with Decision 3.
9. The workflow must provide a feasible path to export or convert annotation data into the project's authoritative schemas.
10. The resulting data must remain compatible with Layer 1 JSON Schema validation and Layer 2 protocol-consistency validation.
11. Derived fields must remain derived according to the protocol and must not be silently converted into independently annotated Ground Truth fields.
12. The workflow must remain operationally compatible with the way the project is currently using Roboflow.

**Roboflow compatibility safety:** the purpose of these criteria is compatibility evaluation. No protocol requirement has been reinterpreted in a way that automatically disqualifies Roboflow; no capabilities have been invented for Roboflow; and no claim is made that Roboflow satisfies or fails any criterion. The protocol remains authoritative and has not been modified to accommodate, weaken, or strengthen for Roboflow.

### Section 8.6 Boundary Acceptance

The HUMAN PROJECT OWNER has explicitly accepted the Section 8.6 decision boundary as the scope for a future bounded D-02 annotation-tool evaluation task.

This acceptance:
- permits Section 8.6 to be used as the boundary for the future bounded D-02 evaluation;
- does NOT select an annotation tool;
- does NOT authorize an annotation tool;
- does NOT resolve O2–O12;
- does NOT resolve D-01, D-03, D-04, D-05, or D-06.

### Governance Status

- **D-02 remains OPEN / UNDECIDED.**
- Roboflow is a **candidate only** — not the selected project annotation tool.
- **No annotation tool is authorized** by this record.
- No tool evaluation has been performed.
- No recommendation has been made.
- No scoring or ranking has been performed.

**D-02-C does NOT:** decide D-02; select or authorize an annotation tool; resolve O2–O12; resolve D-01, D-03, D-04, D-05, or D-06; modify Section 15; reopen Decision 2; reopen Decision 3; resolve exit asymmetry; define methodology; amend the protocol; or authorize any specific next task.

## External Roboflow Test Authorization Boundary (D-02-D4)

**Status:** RECORDED (2026-08-29). Authorization boundary only. This record does NOT authorize any external Roboflow action.

### Context

D-02-D3 established an authorization gap: there is no recorded authorization allowing Claude Code to access, create, modify, or use an external Roboflow account, workspace, project, API, web UI, credential, or external state. D-02-D3 was therefore classified **NOT VERIFIED — SYNTHETIC TEST COULD NOT BE SAFELY EXECUTED**, and no empirical test was performed.

This record records ONLY the boundary of what external Roboflow action, if any, has been explicitly authorized by the HUMAN PROJECT OWNER. It does NOT authorize any external action.

### Authorization Determination

**EXTERNAL ROBOFLOW TEST AUTHORIZATION = ABSENT**

No explicit authorization exists in the authorized record for any of the following categories:

- **A. NO EXTERNAL ROBOFLOW ACCESS** — effectively in force. Claude Code may not access any Roboflow account, workspace, project, API, web UI, credential, or external state.
- **B. EXISTING ROBOFLOW ENVIRONMENT MAY BE USED** — NOT AUTHORIZED.
- **C. SYNTHETIC TEST ENVIRONMENT MAY BE CREATED** — NOT AUTHORIZED.

### What Was NOT Inferred

Claude Code did NOT infer external authorization from any of the following, each of which is explicitly insufficient:

- Roboflow being the D-02 candidate;
- the HUMAN PROJECT OWNER currently using Roboflow;
- previous discussion;
- the D-02-C candidate declaration (D-02-C @ 234, 238);
- Section 8.6 boundary acceptance (D-02-C @ 261);
- the existence of a Roboflow account;
- the existence of an API key;
- prior use of Roboflow;
- any wording such as "go ahead", "try it", "you can use Roboflow".

**Candidate status ≠ external-access authorization. Tool-selection authority ≠ external-access authorization. Section 8.6 acceptance ≠ external-access authorization. Account existence ≠ authorization.**

### No Credential Search Performed

Per the credential boundary, this task did NOT search the filesystem for credentials, did NOT print credentials, and did NOT write credentials into ACTIVE_CONTEXT.md, source code, configuration files, logs, reports, or git history. No credential was discovered, exposed, or recorded.

### Consequence

- **D-02-D3 is NOT re-performed.** STOP.
- **No external Roboflow test was performed by this task.**
- D-02 remains OPEN / UNDECIDED.
- Roboflow remains candidate only — NOT selected, NOT authorized as the project annotation tool.
- All 15 unresolved capability questions from D-02-D2 remain unresolved.
- All 14 project fields remain NOT TESTED.

### D-02-D4 Does NOT

authorize any external Roboflow action; select Roboflow; recommend Roboflow; score or rank Roboflow; resolve D-02; resolve O2–O12; resolve D-01, D-03, D-04, D-05, or D-06; modify the protocol; modify schemas; modify production code or configuration; access production datasets; or upload any data. Recording an authorization boundary does NOT itself authorize the boundary's content.

## D-02 Human-Verifiable Roboflow Gap Checklist (D-02-E1)

STATUS: RECORDED (2026-08-29). Human-verifiable checklist only. No external action.
No external Roboflow access was performed. No credentials were accessed.
No inference of undocumented Roboflow behavior was made.

### Checklist items

1. Source filename / frame identity
   A. HUMAN CHECK: upload one image in the current Roboflow workflow and inspect the project view, the dataset view, and the export for the stored filename.
   B. EXPECTED OBSERVATION: if the capability exists, the filename appears unchanged (for example SYNTH_FRAME_0005.jpg is recoverable after export).
   C. PROJECT RELEVANCE: project field frame_id (protocol line 31); D-02 selection criterion 2.
   D. EVIDENCE STATUS: DIRECTLY OBSERVABLE
   E. LIMITATION: insufficient to resolve D-02; one filename is not a sampled-frame identity guarantee.

2. Sampling identity
   A. HUMAN CHECK: attach a project-specific sample reference such as S_0005 to the image, either as a native field or as custom metadata, then export and inspect.
   B. EXPECTED OBSERVATION: the value S_0005 is present and unchanged in the export.
   C. PROJECT RELEVANCE: Sampling Manifest sample_id; criterion 2.
   D. EVIDENCE STATUS: PARTIALLY OBSERVABLE
   E. LIMITATION: does not prove the workflow enforces sampled-frame-only identity.

3. Bounding-box coordinate representation
   A. HUMAN CHECK: create one bounding box on the image, export the dataset, and inspect the exported coordinate values and convention.
   B. EXPECTED OBSERVATION: pixel coordinates are exposed; the convention is identified in the export.
   C. PROJECT RELEVANCE: project bbox contract 1020x500 integer [x1,y1,x2,y2]; criterion 3.
   D. EVIDENCE STATUS: PARTIALLY OBSERVABLE
   E. LIMITATION: a single bbox does not prove the full coordinate contract holds for the whole dataset.

4. Manual global identity
   A. HUMAN CHECK: enter a value such as GT_999 into the annotation interface for the object, then export and inspect where and whether it is stored.
   B. EXPECTED OBSERVATION: the value GT_999 is stored and preserved after export.
   C. PROJECT RELEVANCE: global_id policy (protocol Section 5); criterion 4.
   D. EVIDENCE STATUS: PARTIALLY OBSERVABLE
   E. LIMITATION: any Roboflow internal ID is NOT equivalent to GT_999; this observation is about the human-entered value only.

5. Model-assisted labeling separation
   A. HUMAN CHECK: inspect the annotation interface and export for a field or label that distinguishes model-generated labels from human-authored or human-confirmed annotations.
   B. EXPECTED OBSERVATION: an origin indicator (model vs human) is visible and preserved after export.
   C. PROJECT RELEVANCE: criterion 5; protocol rule that model output must not be authoritative Ground Truth.
   D. EVIDENCE STATUS: NOT OBSERVABLE
   E. LIMITATION: official documentation does not mention model-vs-human origin; this item requires human inspection of the current interface.

6. Sampled-frame-only restriction
   A. HUMAN CHECK: check whether the workflow prevents annotation of frames outside the sampled set, and whether that prevention is enforced by the tool or by an external rule.
   B. EXPECTED OBSERVATION: either the tool enforces it, or the workflow relies on an external documented rule.
   C. PROJECT RELEVANCE: Sampling Protocol; criterion 6.
   D. EVIDENCE STATUS: NOT OBSERVABLE
   E. LIMITATION: even if the tool does not enforce it, an external rule may still satisfy the criterion.

7. Split handling
   A. HUMAN CHECK: assign the image to train, validation, or test, export the dataset, and inspect whether the split assignment is preserved.
   B. EXPECTED OBSERVATION: the exported split is present and identifiable.
   C. PROJECT RELEVANCE: protocol Section 7.6 split; criterion 10 Layer 1/2 compatibility.
   D. EVIDENCE STATUS: PARTIALLY OBSERVABLE
   E. LIMITATION: does not prove the project can determine the authoritative split.

8. Custom metadata
   A. HUMAN CHECK: attach custom metadata to the image, export, and inspect whether it is retrievable and whether project identifiers keep their meaning.
   B. EXPECTED OBSERVATION: the custom metadata is present in the export with unchanged meaning.
   C. PROJECT RELEVANCE: criteria 2, 4, 9.
   D. EVIDENCE STATUS: PARTIALLY OBSERVABLE
   E. LIMITATION: retrieval depends on the export format chosen.

9. Annotation history / human correction
   A. HUMAN CHECK: inspect the annotation history for an object that was corrected, and determine whether the history records origin or only modification history.
   B. EXPECTED OBSERVATION: the history shows that a human corrected the annotation, and whether it identifies origin.
   C. PROJECT RELEVANCE: criterion 5; criterion 11 derived-field integrity.
   D. EVIDENCE STATUS: NOT OBSERVABLE
   E. LIMITATION: official documentation mentions Annotation History but not model-vs-human origin.

10. Export field mapping
   A. HUMAN CHECK: export the dataset and map each exported field to bbox, class, filename, metadata, and identifiers.
   B. EXPECTED OBSERVATION: the mapping is identified for each field.
   C. PROJECT RELEVANCE: criteria 9, 10, 11.
   D. EVIDENCE STATUS: UNKNOWN
   E. LIMITATION: any field whose mapping the owner cannot verify must be recorded as UNKNOWN; this does not invent a mapping.

### Evidence status summary

| Item | Status |
|---|---|
| 1 Source filename / frame identity | DIRECTLY OBSERVABLE |
| 2 Sampling identity | PARTIALLY OBSERVABLE |
| 3 Bounding-box coordinate representation | PARTIALLY OBSERVABLE |
| 4 Manual global identity | PARTIALLY OBSERVABLE |
| 5 Model-assisted labeling separation | NOT OBSERVABLE |
| 6 Sampled-frame-only restriction | NOT OBSERVABLE |
| 7 Split handling | PARTIALLY OBSERVABLE |
| 8 Custom metadata | PARTIALLY OBSERVABLE |
| 9 Annotation history / human correction | NOT OBSERVABLE |
| 10 Export field mapping | UNKNOWN |

**Coverage:** 10 of 15 unresolved capability questions from D-02-D2 are addressed. 5 remain outside this checklist.

**No item in this checklist resolves D-02.** Each item is evidence about the current Roboflow workflow only. No item establishes a protocol requirement, a permanent Roboflow capability guarantee, a tool-selection criterion, or a D-02 decision.

**No external action was performed.** No Roboflow access, no workspace, no project, no upload, no export, no API key, no credential search.

**D-02 remains OPEN / UNDECIDED.** Roboflow remains candidate only. No tool selected, authorized, recommended, scored, or ranked.

## D-02-E4 Human Observation / Project Evidence Reconciliation

STATUS: RECONCILED
PERSON_SOURCE: HUMAN_CONFIRMED_VIDEO_3
PERSON_PERFORMANCE_VALIDATED: NO
SOURCE_VIDEO_TRACEABILITY: UNKNOWN

### D-02-E4-R2 Project Artifact Inventory

STATUS: RECORDED (2026-08-29). Project-side artifact existence audit only.
No repository-wide scan was performed. Only the 10 named artifacts were
inspected. Existence is recorded as evidence of existence only; nothing below
infers training quality, Roboflow provenance, dataset provenance, annotation
provenance, model performance, or current/latest status.

1. **frame.py** — EXISTS / FILE (625 bytes).
2. **extract_frames.py** — EXISTS / FILE (792 bytes).
3. **train.py** — EXISTS / FILE (840 bytes).
4. **dataset/** — EXISTS / DIRECTORY (contains `images/` subdir).
5. **runs/detect/train-10/** — EXISTS / DIRECTORY (contains BoxF1_curve.png, BoxPR_curve.png, BoxP_curve.png, BoxR_curve.png, args.yaml, confusion_matrix.png, confusion_matrix_normalized.png, labels.jpg, results.csv, results.png, train_batch0.jpg, train_batch1.jpg, train_batch2.jpg, val_batch0_labels.jpg, val_batch0_pred.jpg, val_batch1_labels.jpg, val_batch1_pred.jpg, val_batch2_labels.jpg, val_batch2_pred.jpg, weights/).
6. **runs/detect/train-13/** — EXISTS / DIRECTORY (contains args.yaml, labels.jpg, results.csv, train_batch0.jpg, train_batch1.jpg, train_batch2.jpg, weights/).
7. **runs/detect/train-16/** — EXISTS / DIRECTORY (contains BoxF1_curve.png, BoxPR_curve.png, BoxP_curve.png, BoxR_curve.png, args.yaml, confusion_matrix.png, confusion_matrix_normalized.png, labels.jpg, results.csv, results.png, train_batch0.jpg, train_batch1.jpg, train_batch2.jpg, val_batch0_labels.jpg, val_batch0_pred.jpg, val_batch1_labels.jpg, val_batch1_pred.jpg, val_batch2_labels.jpg, val_batch2_pred.jpg, weights/).
   - The directory named `train-16` exists. This is evidence of directory existence only. It does NOT establish that any Roboflow run labeled "detect train 16" exists, was performed, or corresponds to this directory.
8. **My-First-Project-1/** — EXISTS / DIRECTORY (contains README.dataset.txt, README.roboflow.txt, data.yaml, train/, val/).
9. **My-First-Project-3/** — EXISTS / DIRECTORY (contains README.dataset.txt, README.roboflow.txt, data.yaml, test/, train/, valid/).
10. **My-First-Project-4/** — EXISTS / DIRECTORY (contains README.dataset.txt, README.roboflow.txt, data.yaml, test/, train/, valid/).

All 10 named artifacts were found present in the working tree.

## Video 3 / Video 4 Dataset Roles

Recorded from human-verified evidence (minimal video content check). This section formalizes roles only; it implements no decision about training usage.

**Video 3** (`public/3.mp4`) — PRIMARY annotation/evaluation source.
- 621 decoded physical frames (frame_id domain 0–620), 15.0 FPS, 1280×720, duration convention 41.4 s, HEVC/H.265
- Daytime road/traffic scene; multiple vehicles present; cars clearly present; junction/lane convergence visible
- The established Decision 1 domain (temporal split, baseline sampling) applies to Video 3 ONLY.

**Video 4** (`public/4.mp4`) — CANDIDATE supplementary detection/classification training source.
- 276 decoded physical frames, 29.97 FPS, 3840×2160, duration 9.209 s, H.264/AVC
- Daytime road/traffic scene; multiple vehicles present; cars clearly present; junction geometry not confirmed from the minimal sample

**Technical differences:**

| Property | Video 3 | Video 4 |
|---|---|---|
| Physical frames | 621 | 276 |
| FPS | 15.0 | 29.97 |
| Resolution | 1280×720 | 3840×2160 |
| Codec | HEVC/H.265 | H.264/AVC |

**Cross-video invariants:**
1. Video 3 and Video 4 are NOT the same physical scene (based on inspected samples).
2. Both are within the general daytime vehicular-traffic domain.
3. Raw frame_id values MUST NOT be treated as a cross-video temporal key.
4. Video 4 MUST NOT be merged into the Video-3 evaluation partition merely because both contain traffic.
5. Video 4 is NOT part of the Video-3 annotation/evaluation dataset at this stage.
6. No decision has been made about using Video 4 for final training yet.
7. No Decision 3 implementation follows from this record.

## Decision 3 — Approved Approach Geometry Layer (Video 3)

**Human approval date:** 2026-08-26 (following Task 10.4I temporal validation of the candidate geometry against frames 0–620 of Video 3).

**Status:**
- APPROACH STRUCTURE: HUMAN CONFIRMED
- APPROACH A GEOMETRY: HUMAN APPROVED — CANDIDATE COORDINATES
- APPROACH B GEOMETRY: HUMAN APPROVED — CANDIDATE COORDINATES
- JUNCTION / TRANSITION GEOMETRY: HUMAN APPROVED — CANDIDATE COORDINATES
- JUNCTION PRECEDENCE: HUMAN APPROVED

**Approved coordinates (Video 3 native resolution 1280×720; origin top-left; x = 0…1279; y = 0…719):**

Approach A:
- A1 = (0,365)
- A2 = (300,365)
- A3 = (1279,420)
- A4 = (1279,719)
- A5 = (650,719)
- A6 = (0,719)

Approach B:
- B1 = (390,175)
- B2 = (520,185)
- B3 = (850,325)
- B4 = (720,365)

Junction / Transition Zone:
- J1 = (450,405)
- J2 = (720,350)
- J3 = (950,455)
- J4 = (1030,405)

**Junction precedence rule:** Where the Junction region overlaps the Approach A region, the effective Approach A region is:

Effective Approach A = Candidate Approach A − Junction Zone

The approved candidate coordinates are NOT rewritten to remove the Junction; precedence is semantic geometry behavior only.

**Scope and limitations of this approval:**
1. These are project-defined spatial regions based on reviewed Video 3 frame geometry. They are NOT ground truth, measured physical road boundaries, universally correct boundaries, lane boundaries, or traffic-direction boundaries.
2. The existing Counting ROI is UNCHANGED. The Approach A/B/Junction geometry is a separate Decision 3 spatial layer; it must not be merged into or replace the Counting ROI.
3. Traffic density, vehicle-density metric, traffic imbalance metric, queue length, waiting time, stopped-vehicle criterion, speed, traffic direction, lane structure, signal state/phase, green duration, phase allocation, controller logic, optimization objective, and real-time control remain UNDEFINED by this approval.
4. Decision 3 implementation has NOT started. Only the spatial foundation for future traffic-state analysis has been approved.

## Decision 3 — Coordinate-Space Mapping Ratification (Decision A2 / B1 / C2)

**Human ratification date:** 2026-08-26

**Decision A — Transformation basis: A2 — dimension-ratio mapping.**

The documented full-frame transformation from native Video 3 resolution to the pipeline / Ground Truth coordinate space is:

```text
x_gt = x_native × 1020 / 1280
y_gt = y_native × 500 / 720
```

- Native resolution: 1280 × 720 (x = 0…1279, y = 0…719)
- GT / pipeline resolution: 1020 × 500

This dimension-ratio mapping is ratified. It is NOT replaced by the max-index mapping (1019/1279, 499/719).

**Decision B — Evaluation space: B1 — map geometry into GT space.**

The canonical human-approved Decision 3 geometry remains stored in its original native Video 3 coordinate system (1280 × 720). For membership evaluation only, the approved geometry is transformed into the 1020×500 GT space:

```text
Canonical native geometry
        ↓
dimension-ratio transformation
        ↓
GT-space geometry
        ↓
membership evaluation against GT observations
```

The canonical native coordinates are NOT transformed and overwritten. The 14 approved vertices in this file are NOT rewritten. Ground Truth observations are NOT transformed into native space.

**Decision C — Border behavior: C2 — continuous mapping.**

The mathematical transformation remains continuous:

```text
x_gt = x_native × 1020 / 1280
y_gt = y_native × 500 / 720
```

Transformed geometry coordinates are NOT clamped merely because the mathematical result can slightly exceed the maximum integer pixel index (e.g., A4 native = (1279,719) transforms to x ≈ 1019.2, y ≈ 499.3). These remain continuous geometry coordinates.

No integer rounding rule has been ratified. No clamping rule has been ratified. If a future schema or storage layer requires integer coordinates, that is a SEPARATE representation/serialization question and must NOT be silently introduced into this ratification.

**Semantic invariants preserved:**
1. The 14 native coordinates remain canonical (A1–A6, B1–B4, J1–J4 unchanged above).
2. Junction precedence remains: Effective Approach A = Candidate Approach A − Junction Zone.
3. Existing Counting ROI remains unchanged.
4. Decision 3 geometry remains a separate spatial layer.
5. No lane definitions, traffic-direction definitions, traffic-density formula, queue definition, waiting-time definition, or signal-control model are introduced.
6. Decision 3 geometry + classification implementation is now IMPLEMENTED AND VALIDATED; it remains SPATIAL CLASSIFICATION ONLY with NO DOWNSTREAM CONSUMER.

## Decision 3 — Coordinate-Space Implementation Contract

**Status:** IMPLEMENTATION CONTRACT FINALIZED; IMPLEMENTATION COMPLETE AND VALIDATED.

This contract converts the human-ratified coordinate-space decisions (A2 / B1 / C2) into a precise implementation specification. It does not reopen the mapping decision, does not re-audit the native geometry, and does not implement membership evaluation.

IMPLEMENTED (runtime code exists and is validated):
- runtime observation-point calculation (bbox geometric center, `cx = (x1+x2)/2`, `cy = (y1+y2)/2`) in `main.py:decision3_observation_point()`
- inverse A2 dimension-ratio mapping to native 1280×720 (`x_native = cx × 1280 / 1020`, `y_native = cy × 720 / 500`)
- canonical polygon classification via `classify_decision3()` in `decision3_geometry.py`
- JUNCTION > APPROACH_A > APPROACH_B > NONE precedence
- per-frame classification only; `decision3_region` is computed and currently discarded
- test suite: 15/15 tests pass

NOT IMPLEMENTED / NOT CONNECTED: downstream semantic consumers, density, queue, waiting time, traffic direction, signal/control, Ground Truth integration, sampling integration, and persistence/output integration. Decision 3 remains SPATIAL CLASSIFICATION ONLY with NO DOWNSTREAM CONSUMER.

### 1. Canonical geometry

The 14 approved Decision 3 vertices remain canonical and immutable in the native Video 3 coordinate system:

- Resolution: 1280 × 720 (x = 0…1279, y = 0…719)
- Origin: top-left

These native coordinates are stored as-is and are NEVER rewritten, rounded, clamped, or replaced by transformed values.

### 2. Transformation

Decision 3 uses the ratified dimension-ratio mapping:

```text
x_gt = x_native × 1020 / 1280
y_gt = y_native × 500 / 720
```

This is a full-frame linear scaling from native 1280×720 to GT 1020×500. It is applied to the canonical vertices at evaluation time only.

### 3. Evaluation

Membership evaluation is performed in the GT 1020×500 coordinate space. The evaluation pipeline is conceptually:

```text
Load canonical native geometry
        ↓
transform vertices via dimension-ratio mapping
        ↓
preserve transformed vertices as continuous floating-point values
        ↓
evaluate GT observation geometry (1020×500) against the transformed polygon
```

### 4. Numeric representation

Mapped polygon vertices remain continuous floating-point values. They are NOT coerced to integer pixel indices.

### 5. Rounding

**NO rounding is applied during geometry transformation.**

Decision 3 explicitly ratified continuous mapping (C2). Polygon geometry does not become integer-valued merely because GT observations use integer pixel coordinates. Rounding vertices would introduce unnecessary geometric distortion. Point-in-polygon membership evaluates integer GT observation points against floating-point polygon vertices directly.

### 6. Clamping

**NO clamping is applied to transformed polygon vertices.**

The dimension-ratio transformation is continuous. Transformed vertices may mathematically exceed the maximum integer GT pixel index (1019 / 499) as a consequence of the mapping, e.g.:

- A3/A4 native x = 1279 → x_gt = 1019.203125
- A4/A5/A6 native y = 719 → y_gt = 499.305555…

These remain continuous geometry coordinates. The values 1019.203125 and 499.305555… are NOT silently replaced by 1019 and 499. Such clamping is unnecessary for membership evaluation against valid GT observation points and would alter the approved geometry.

### 7. Observation coordinates

GT observations remain in their existing 1020×500 integer pixel coordinate representation. Valid stored observation indices are x = 0…1019, y = 0…499.

### 8. Pixel-index validity vs. continuous polygon-coordinate validity

These are distinct concepts and MUST NOT be conflated:

- **Pixel-index validity** applies to GT observations: integer coordinates, valid range 0…1019 / 0…499.
- **Continuous polygon-coordinate validity** applies to Decision 3 mapped geometry: floating-point values that may lie slightly beyond the maximum integer sample index as a mathematical consequence of the dimension-ratio transformation.

The implementation MUST NOT modify the GT schema merely because transformed polygon vertices are fractional. Likewise, the approved native coordinates MUST NOT be altered to make transformed coordinates land on integer GT indices.

### 9. Verified transformed coordinates (all 14 vertices)

Computed with x_gt = x_native × 1020 / 1280 and y_gt = y_native × 500 / 720. Native coordinates are unchanged; these are recorded for implementation verification only.

Approach A:
- A1 = (0, 365) → (0.0, 253.472222…)
- A2 = (300, 365) → (238.125, 253.472222…)
- A3 = (1279, 420) → (1019.203125, 291.666666…)
- A4 = (1279, 719) → (1019.203125, 499.305555…)
- A5 = (650, 719) → (517.96875, 499.305555…)
- A6 = (0, 719) → (0.0, 499.305555…)

Approach B:
- B1 = (390, 175) → (310.78125, 121.527777…)
- B2 = (520, 185) → (414.375, 128.472222…)
- B3 = (850, 325) → (677.34375, 225.694444…)
- B4 = (720, 365) → (573.75, 253.472222…)

Junction / Transition Zone:
- J1 = (450, 405) → (358.59375, 281.25)
- J2 = (720, 350) → (573.75, 243.055555…)
- J3 = (950, 455) → (757.03125, 315.972222…)
- J4 = (1030, 405) → (820.78125, 281.25)

### 10. ROI

The Counting ROI remains unchanged and independent. It is a separate spatial layer and MUST NOT be replaced, merged with, or redefined by Decision 3 geometry.

### 11. Scope

Decision 3 remains a geometry/mapping layer only. This contract introduces NO:
- lane boundaries
- traffic directions
- density formula
- queue definition
- waiting-time definition
- signal-control logic
- camera calibration
- physical-world coordinates
- homography
- perspective correction

### 12. Implementation status

Decision 3 geometry + classification implementation is IMPLEMENTED AND VALIDATED. Runtime code now exists: `main.py:decision3_observation_point()` computes the bbox geometric center, applies the inverse A2 mapping, and calls `classify_decision3()`; `decision3_geometry.py` holds the canonical polygons and Junction precedence; and 15/15 tests pass.

NOT IMPLEMENTED / NOT CONNECTED: downstream semantic consumers, density, queue, waiting time, traffic direction, signal/control, Ground Truth integration, sampling integration, and persistence/output integration. Decision 3 remains SPATIAL CLASSIFICATION ONLY with NO DOWNSTREAM CONSUMER.

## Decision 3 — Observation-Point Semantics Ratification

**Human ratification date:** 2026-08-26 (following Task 10.4O observation-point semantics audit, which found the current implementation uses an inherited bottom-center point that is not documented anywhere in the project).

### Ratified observation point

**Decision 3 observation point = bbox geometric center.**

```text
cx = (x1 + x2) / 2
cy = (y1 + y2) / 2

Decision 3 observation point = (cx, cy)
```

This is the Tracking GT geometric center already defined by the project (`tracking_ground_truth.schema.json` — `center` = `[(x1+x2)/2, (y1+y2)/2]`, "Used for trajectory and ROI crossing").

### Semantic separation from Counting ROI

Decision 3 and the Counting ROI use **different** observation-point semantics. They must remain independent.

| | Decision 3 | Counting ROI |
|---|---|---|
| Observation point | bbox geometric center `(cx, cy)` | bbox bottom-center `(cx, y2)` |
| Purpose | spatial classification into Approach A / Approach B / Junction / NONE | existing Counting ROI / crossing semantics |
| Coordinate recovery/mapping | exactly as already ratified (native 1280×720 ↔ GT 1020×500) | unchanged |
| Must not be described as | `roi_point` | — |

Counting ROI behavior remains unchanged.

### Rationale (recorded, not expanded into new traffic semantics)

1. Tracking GT already defines the bbox geometric center.
2. Decision 3 is a spatial-region classification layer, not a Counting ROI crossing layer.
3. Using the geometric center avoids inheriting Counting ROI semantics by implementation accident.
4. Using the geometric center reduces the systematic downward displacement caused by the bottom-center point.
5. This avoids unnecessarily increasing Junction membership near the A/Junction overlap.
6. This choice does NOT redefine geometry, mapping, precedence, density, queue, waiting time, direction, signal control, or any other downstream semantic.

### Hard invariants (unchanged)

- Canonical native coordinates (A1–A6, B1–B4, J1–J4) remain unchanged.
- Mapping remains A2: `x_gt = x_native × 1020 / 1280`, `y_gt = y_native × 500 / 720`.
- Evaluation space remains B1: GT 1020×500.
- Border behavior remains C2: continuous.
- Rounding remains NOT APPLIED.
- Clamping remains NOT APPLIED.
- Junction precedence remains: `JUNCTION > APPROACH_A > APPROACH_B > NONE`.
- Counting ROI remains unchanged and separate.
- Decision 3 remains geometry + classification only.
- No density, queue, waiting-time, traffic-direction, or signal/control semantics are introduced.

### Implementation status

- **OBSERVATION_POINT_DECISION:** RATIFIED — BBOX GEOMETRIC CENTER.
- **CURRENT_IMPLEMENTATION:** IMPLEMENTED. `main.py:decision3_observation_point()` computes the bbox geometric center `(cx, cy)` — `cx = (x1 + x2) / 2`, `cy = (y1 + y2) / 2` — in GT 1020×500 space and recovers the native 1280×720 coordinate via the inverse A2 mapping before calling `classify_decision3()`.
- **IMPLEMENTATION_ALIGNMENT:** COMPLETE / VALIDATED. The Decision 3 observation point is the bbox geometric center; the Counting ROI observation point remains the bbox bottom-center `(cx, y2)`. Decision 3 and the Counting ROI remain independent. The Counting ROI is UNCHANGED — nothing in this ratification altered it.
- Decision 3 remains SPATIAL CLASSIFICATION ONLY with NO DOWNSTREAM CONSUMER. No density, queue, waiting-time, traffic-direction, or signal/control semantics are introduced.

### Observation-Point Input Representation Clarification (appended, append-only)

Recorded to prevent a future reader from conflating two separate concerns: the integer representation of the detection bbox with the rounding/clamping behavior of the Decision 3 geometry transformation.

- Detection bbox values entering the Decision 3 observation-point helper (`decision3_observation_point()` in `main.py`) are the existing integer GT pixel-coordinate representation (1020×500). This integer representation is the existing input convention and is intentional and contract-compliant; it is NOT introduced by the helper.
- Decision 3 observation point = bbox geometric center: `cx = (x1 + x2) / 2`, `cy = (y1 + y2) / 2`, computed in GT 1020×500 space, then recovered to native 1280×720 via the inverse A2 mapping (`x_native = cx × 1280 / 1020`, `y_native = cy × 720 / 500`).
- Counting ROI observation point = bbox bottom-center `(cx, y2)`, independently maintained and unchanged.
- No rounding and no clamping is applied to the Decision 3 geometry transformation or polygon evaluation path. The no-rounding/no-clamping rule applies to the geometry mapping and polygon evaluation, not to the integer representation of the input bbox.
- The distinction between bbox integer representation and geometry transformation rounding must not be conflated. Neither implies a change to the A2 mapping, B1 evaluation space, C2 continuous geometry, canonical A1–A6 / B1–B4 / J1–J4 coordinates, junction precedence, or Counting ROI semantics.
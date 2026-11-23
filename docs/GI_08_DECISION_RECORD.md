# GI-08 — GLOBAL IDENTITY EVALUATION DECISION RECORD

**Status:** ALL HUMAN DECISIONS CLOSED

---

## ALREADY ESTABLISHED DECISIONS

These decisions are protocol-constrained and do not require Human Project Owner input:

| Decision | Status | Value |
|----------|--------|-------|
| D1 | ALREADY_ESTABLISHED | Evaluation IoU threshold = 0.50 |
| D3 | DATA_CONSTRAINT | No runtime visibility field available |
| D4 | DATA_CONSTRAINT | No runtime occlusion field available |
| D7 | ALREADY_ESTABLISHED | Timestamp-based runtime-to-GT temporal alignment; runtime frame N corresponds to GT frame N-1 where timestamps establish correspondence |

---

## HUMAN DECISIONS CLOSED

The following four decisions have been explicitly approved by the Human Project Owner:

---

### D2 — AMBIGUOUS RUNTIME-TO-GT MATCHING

**Status:** CLOSED — HUMAN PROJECT OWNER APPROVED

**Selected Option: C**

Use Hungarian one-to-one assignment within each frame for runtime-observation to GT-observation matching.

**D2_SELECTED:** C

---

### D5 — CLASS REPORTING

**Status:** CLOSED — HUMAN PROJECT OWNER APPROVED

**Selected Option: B**

Report both aggregate Global Identity results and per-class results for:
* car
* motorcycle
* bus
* truck

**D5_SELECTED:** B

---

### D6 — MINIMUM OBSERVATION COUNT

**Status:** CLOSED — HUMAN PROJECT OWNER APPROVED

**Selected Option: A**

Minimum 1 runtime observation.

All runtime global_ids are eligible for evaluation, including identities with only one observation. Do not exclude short-lived global_ids based on an invented threshold.

**D6_SELECTED:** A

---

### D8 — ID SWITCH ACROSS DETECTION GAPS

**Status:** CLOSED — HUMAN PROJECT OWNER APPROVED

**Selected Option: C**

Use GT-validated continuity.

An identity change across a runtime detection gap is counted as a Global Identity ID switch only when the corresponding GT identity remains continuously valid/visible across that interval.

A detection/tracking gap alone must NOT automatically be classified as a Global Identity ID switch.

**D8_SELECTED:** C

---

## IMPLEMENTATION STATUS

| Item | Status |
|------|--------|
| Implementation | NOT_STARTED |
| Source Changes | NONE |
| Test Changes | NONE |
| Evaluator Created | NO |
| ALL_HUMAN_DECISIONS_CLOSED | YES |

---

*This document exists only to record Human Project Owner decisions. It does not implement any evaluation logic.*

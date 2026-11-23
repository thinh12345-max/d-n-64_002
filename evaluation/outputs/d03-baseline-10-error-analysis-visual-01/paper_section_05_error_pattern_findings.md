# 5. Error Pattern Findings

This section presents the observed error categories and their support states. All findings in this section are visual evidence (evidence level LEVEL_C), except where a different evidence level is stated. Visual findings are observations made in the 12 inspected cases (VC-01 through VC-12) and must not be described as what the dataset as a whole contains unless independently supported by full-subset numerical evidence. No dataset-wide prevalence of any error category is claimed.

EP-01 — SMALL_OBJECT (evidence level LEVEL_C, support status PARTIALLY_SUPPORTED)

Patterns associated with small objects were observed in all 12 inspected cases: VC-01, VC-02, VC-03, VC-04, VC-05, VC-06, VC-07, VC-08, VC-09, VC-10, VC-11, VC-12. Recorded as a contributing scene-level difficulty, not a proven cause. The AP@0.5 versus AP@0.5:0.95 gap is consistent with localization weakness but does not prove object size is the cause of any specific prediction.

EP-02 — FALSE_POSITIVE_BACKGROUND (evidence level LEVEL_C, support status PARTIALLY_SUPPORTED)

Background false positives were observed in VC-01, VC-02, VC-03, VC-11, and VC-12. Low precision confirms many false positives at the evaluated operating point but cannot establish that they are background artifacts. The label rests on the annotation set as well as the image.

EP-03 — LOCALIZATION_ERROR (evidence level LEVEL_C, support status PARTIALLY_SUPPORTED)

Localization difficulty was observed in VC-02, VC-04, VC-05, and VC-06. The AP gap is consistent with localization sensitivity but does not prove localization is the cause of the specific inspected cases or the sole weakness. The IoU shortfall could also reflect small object size.

EP-04 — FALSE_NEGATIVE (evidence level LEVEL_C, support status PARTIALLY_SUPPORTED)

False negatives were observed in VC-04, VC-05, and VC-06. High aggregate recall with residual FN counts is consistent with missed detections but does not prove the three inspected truck cases are representative of the full FN population.

EP-05 — DUPLICATE_DETECTION (evidence level LEVEL_C, support status NOT_DIRECTLY_SUPPORTED)

Duplicate detections were observed in VC-07 and VC-08. Aggregate motorcycle FP counts are consistent with repeated detections in dense regions but cannot distinguish duplicates from background false positives. The duplicate classification is a consequence of greedy one-to-one matching, not of box quality. Duplicate detections recorded in the visual cases are an artefact of the greedy one-to-one matching rule and are not a measured property of the detector.

EP-06 — LOW_CONFIDENCE (evidence level LEVEL_C, support status NOT_DIRECTLY_SUPPORTED)

Low-confidence detections were observed in VC-09 and VC-10. Aggregate precision does not measure per-prediction confidence calibration. No confidence distribution field exists in the baseline summary, so per-prediction confidence cannot be measured or compared.

EP-07 — CROWDING (evidence level LEVEL_C, support status NOT_DIRECTLY_SUPPORTED)

Crowding was observed in VC-12. No numerical field measures object density or crowding. The high motorcycle FP count is consistent with difficulty in dense regions but does not establish crowding as the cause of the single inspected case.

EP-08 — BORDERLINE_IOU_MATCH (evidence level LEVEL_B, support status SUPPORTED)

Borderline IoU behaviour relative to the 0.50 matching threshold was observed in VC-01 (IoU 0.4718) and VC-03 (IoU 0.4582). Supported by the fixed 0.50 IoU matching threshold. Limited to the threshold dependence of the matching rule, not to detector quality beyond that threshold.

Support status boundary: PARTIALLY_SUPPORTED categories remain PARTIALLY_SUPPORTED and NOT_DIRECTLY_SUPPORTED categories remain NOT_DIRECTLY_SUPPORTED. No category was upgraded to SUPPORTED. Causal mechanisms cannot be established where the evidence is insufficient.
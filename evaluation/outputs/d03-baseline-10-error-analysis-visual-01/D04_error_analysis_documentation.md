# 1. Study Context

This section frames the documentation stage by stating what the present error analysis is and is not. It is a documentation of the existing D-03 baseline evaluation and visual error-analysis evidence. It is not a new experiment, and it introduces no new evidence, no new interpretations, no causal claims, no recommendations, and no hypotheses.

The analysis identified as d03-baseline-10-error-analysis-visual-01 is an extraction-only distillation of paper-ready findings from the frozen D-03 baseline evaluation and the associated visual error analysis. Its stated scope is extraction only: no new evidence was created, no inference was run, no training was performed, the baseline evaluation was not rerun, and no image pixels were inspected.

Three evidence levels are in use and are not interchangeable:

- LEVEL_A: Full-subset numerical metrics over the complete evaluated valid and test subsets.
- LEVEL_B: Machine matching evidence (true positives, false positives, false negatives) for the 12 selected images.
- LEVEL_C: Direct visual inspection observations for the same 12 cases.

A statement supported only by Level C must not be presented as supported by Level A. Numerical evidence and visual evidence are therefore distinguished throughout this document: numerical evidence concerns the full evaluated subsets, while visual evidence is confined to the 12 inspected cases and does not establish dataset-wide prevalence of any observation.

The person class is a documented limitation of the evaluated subsets. The person class has no ground truth in the evaluated validation or test subsets (status no_ground_truth in both splits). No person precision, recall, average precision, false-positive, or false-negative conclusion may be inferred, and the no_ground_truth status must not be reinterpreted as poor person-class performance.

Model architecture, training procedure, hardware, and hyperparameters are not established by the selected source artifacts and are therefore not reported here.

Every finding documented in this work traces to named source artifacts. The authoritative sources are the full D-03 report, the integrated evidence relationships, the interpretation constraints, and the full valid/test numerical baseline. The supporting sources are the 12-image machine matching evidence, the 12-case visual inspection records, the aggregated visual error categories, the visual-to-numerical support mapping, and the integrity audit. All numerical values are copied verbatim from the source artifacts; no value was computed, derived, or inferred, and no source artifact was modified by this extraction.# 2. Evaluation Scope

This section defines the evaluated splits, their sample sizes, and the deterministic 12-case visual error-analysis sample.

Two subsets were evaluated, and the distinction between them is preserved throughout this document:

- The validation subset contains 43 images with 3,337 ground-truth objects and 12,900 predictions.
- The test subset contains 21 images with 1,607 ground-truth objects and 6,300 predictions.

Full-subset numerical metrics were computed over both subsets. These metrics constitute numerical evidence (evidence level LEVEL_A). They concern the complete evaluated subsets and are distinct from the visual evidence described below.

The visual error-analysis sample consists of 12 inspected cases, designated VC-01 through VC-12. Their split composition is: one case (VC-09) originates from the validation split and eleven cases originate from the test split. The 12 cases constitute visual evidence (evidence level LEVEL_C) and are confined to those cases; they do not establish what the dataset as a whole contains.

The 12 selected images were matched using a class-aware, greedy, confidence-ranked, one-to-one matching procedure with an IoU threshold of 0.50 and no non-maximum suppression at evaluation time. Aggregate matching totals for the 12 selected images are 781 true positives, 2,819 false positives, and 182 false negatives. Duplicate detections recorded in the visual cases are an artefact of the greedy one-to-one matching rule, not a measured property of the detector.

The 12-case sample is a deterministic error-analysis sample selected from matching evidence. It is not a statistically representative random sample of the dataset, and no statistical significance may be inferred from it. No generalization failure can be concluded from individual case differences.

The person class is a documented limitation of the evaluated scope. The person class has no ground truth in either the validation or the test subset (status no_ground_truth in both splits). No person precision, recall, average precision, false-positive, or false-negative conclusion may be inferred, and the no_ground_truth status must not be reinterpreted as poor person-class performance.# 3. Numerical Baseline Findings

This section presents the full-subset numerical metrics at the evaluated operating point. All findings in this section are numerical evidence (evidence level LEVEL_A), computed over the complete evaluated valid and test subsets. They are distinct from the visual evidence confined to the 12 inspected cases.

At the evaluated operating point, recall is substantially higher than precision in both evaluated splits:

- Valid: recall 0.862152, precision 0.223023.
- Test: recall 0.873055, precision 0.222698.

False positives are numerous relative to true positives in both evaluated splits:

- Valid: total true positives 2877, total false positives 10023.
- Test: total true positives 1403, total false positives 4897.

False negatives occur across the evaluated classes in both splits:

- Valid: total false negatives 460.
- Test: total false negatives 204.

Valid and test aggregate performance are close on all four overall metrics:

- Valid: mAP@0.5 0.680575, mAP@0.5:0.95 0.319892, precision 0.223023, recall 0.862152.
- Test: mAP@0.5 0.676974, mAP@0.5:0.95 0.319613, precision 0.222698, recall 0.873055.
- Valid minus test differences: mAP@0.5 0.003601, mAP@0.5:0.95 0.000279, precision 0.000325, recall -0.010903.

The valid/test difference cannot be established as statistically significant. No statistical significance test was performed, and the differences are small in absolute terms. No generalization failure can be concluded from these differences.

The gap between average precision at IoU 0.50 and average precision over IoU 0.50-0.95 is substantial for every evaluated class in both splits:

- Bus: AP@0.5 0.857143 (valid) / 0.800000 (test); AP@0.5:0.95 0.397619 (valid) / 0.39 (test).
- Car: AP@0.5 0.895222 (valid) / 0.894281 (test); AP@0.5:0.95 0.432775 (valid) / 0.422704 (test).
- Motorcycle: AP@0.5 0.846828 (valid) / 0.865591 (test); AP@0.5:0.95 0.399742 (valid) / 0.391613 (test).
- Truck: AP@0.5 0.803681 (valid) / 0.825000 (test); AP@0.5:0.95 0.369325 (valid) / 0.39375 (test).

This gap is partially consistent with localization weakness, but the numerical evidence cannot establish that localization is the sole or primary weakness, nor that it applies to any specific inspected case.

The evaluated validation subset contains 43 images with 3337 ground-truth objects and 12900 predictions. The evaluated test subset contains 21 images with 1607 ground-truth objects and 6300 predictions.

The person class is a documented limitation of the evaluated scope. The person class has no ground truth in either the validation or the test subset (status no_ground_truth in both splits). No person precision, recall, average precision, false-positive, or false-negative conclusion may be inferred, and the no_ground_truth status must not be reinterpreted as poor person-class performance.

Model architecture, training procedure, hardware, and hyperparameters are not established by the source artifacts and are therefore not reported.# 4. Per-Class Findings

This section presents per-class results across the evaluated classes. All per-class numerical findings in this section are numerical evidence (evidence level LEVEL_A), computed over the complete evaluated valid and test subsets. They are distinct from the visual case distribution, which is visual evidence (evidence level LEVEL_C) and is confined to the 12 inspected cases.

Bus

- Validation: ground truth 42, predictions 227, true positives 36, false positives 191, false negatives 6, precision 0.15859, recall 0.857143, AP@0.5 0.857143, AP@0.5:0.95 0.397619.
- Test: ground truth 20, predictions 112, true positives 16, false positives 96, false negatives 4, precision 0.142857, recall 0.8, AP@0.5 0.8, AP@0.5:0.95 0.39.

Car

- Validation: ground truth 1193, predictions 5616, true positives 1068, false positives 4548, false negatives 125, precision 0.190171, recall 0.895222, AP@0.5 0.895222, AP@0.5:0.95 0.432775.
- Test: ground truth 577, predictions 2713, true positives 516, false positives 2197, false negatives 61, precision 0.190195, recall 0.894281, AP@0.5 0.894281, AP@0.5:0.95 0.422704.

Motorcycle

- Validation: ground truth 1939, predictions 6342, true positives 1642, false positives 4700, false negatives 297, precision 0.258909, recall 0.846828, AP@0.5 0.846828, AP@0.5:0.95 0.399742.
- Test: ground truth 930, predictions 3096, true positives 805, false positives 2291, false negatives 125, precision 0.260013, recall 0.865591, AP@0.5 0.865591, AP@0.5:0.95 0.391613.

Truck

- Validation: ground truth 163, predictions 715, true positives 131, false positives 584, false negatives 32, precision 0.183217, recall 0.803681, AP@0.5 0.803681, AP@0.5:0.95 0.369325.
- Test: ground truth 80, predictions 379, true positives 66, false positives 313, false negatives 14, precision 0.174142, recall 0.825, AP@0.5 0.825, AP@0.5:0.95 0.39375.

Visual case distribution by class within the 12 inspected cases only (evidence level LEVEL_C): bus 3 (VC-01, VC-02, VC-03); truck 4 (VC-04, VC-05, VC-06, VC-10); motorcycle 4 (VC-07, VC-08, VC-09, VC-12); car 1 (VC-11). This distribution is limited to the 12 inspected cases and is not representative of the full dataset. It must not be described as what the dataset as a whole contains.

The person class is a documented limitation of the evaluated scope. The person class has no ground truth in either the validation or the test subset (status no_ground_truth in both splits). No person precision, recall, average precision, false-positive, or false-negative conclusion may be inferred, and the no_ground_truth status must not be reinterpreted as poor person-class performance.

Model architecture, training procedure, hardware, and hyperparameters are not established by the source artifacts and are therefore not reported.# 5. Error Pattern Findings

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

Support status boundary: PARTIALLY_SUPPORTED categories remain PARTIALLY_SUPPORTED and NOT_DIRECTLY_SUPPORTED categories remain NOT_DIRECTLY_SUPPORTED. No category was upgraded to SUPPORTED. Causal mechanisms cannot be established where the evidence is insufficient.# 6. Visual Evidence

This section presents the visual inspection records and their evidence-level constraints. All findings in this section are visual evidence (evidence level LEVEL_C). They are distinct from the full-subset numerical evidence (evidence level LEVEL_A) described in Section 3.

VE-01

Single-image visual inspection records exist for 12 cases (VC-01 through VC-12); one from the validation split (VC-09) and eleven from the test split.

VE-02

No new visual observations were created during evidence integration; the categories are those already recorded in the source artifacts.

VE-03

The BORDERLINE_IOU_MATCH category is the only visual category with full support (SUPPORTED); all other categories are PARTIALLY_SUPPORTED or NOT_DIRECTLY_SUPPORTED.

VE-04

The 12-case sample is a deterministic error-analysis sample selected from matching evidence, not a statistically representative random sample of the dataset.

VE-05

Visual findings are observations made in the inspected cases and must not be described as what the dataset as a whole contains unless independently supported by full-subset numerical evidence.

The visual evidence consists of 12 inspected cases. Their split composition is exactly: one case from the validation split (VC-09) and eleven cases from the test split. No dataset-wide prevalence of any visual error category is claimed.

The 12-case sample is deterministic and is an error-analysis sample, not a statistically representative random sample of the dataset. Visual findings apply to the inspected cases only unless independently supported by full-subset numerical evidence.

Support-status boundary: BORDERLINE_IOU_MATCH is the only category with full SUPPORT. All other categories remain PARTIALLY_SUPPORTED or NOT_DIRECTLY_SUPPORTED. No category was upgraded to SUPPORTED.

Model architecture, training procedure, hardware, and hyperparameters are not established by the source artifacts and are therefore not reported.# 7. Evidence Strength and Support Boundaries

This section classifies each observed error category according to the strength of the evidence supporting it and states the boundary that governs how each classification may be described. The classification is derived from the integrated evidence layers and is reported here without modification. No category was upgraded from its validated assignment.

## 7.1 Supported

### BORDERLINE_IOU_MATCH

Status: SUPPORTED.

This category is supported by the fixed 0.50 IoU matching threshold used in the evaluation. Borderline behaviour relative to that threshold was observed in VC-01 (IoU 0.4718) and VC-03 (IoU 0.4582). The support for this category rests on the threshold dependence of the matching rule, not on any property of the detector beyond that threshold. The finding is therefore a statement about the matching procedure, and it should not be interpreted as evidence of detector quality at other IoU values.

## 7.2 Partially Supported

The following categories are PARTIALLY_SUPPORTED. In each case the observed pattern is consistent with the category label, but the available evidence does not establish that the category describes the cause of any specific prediction, nor that it applies beyond the inspected cases.

- SMALL_OBJECT
- FALSE_POSITIVE_BACKGROUND
- LOCALIZATION_ERROR
- FALSE_NEGATIVE

For these categories the support boundary is defined by the evidence levels involved. The observations rest on the 12 inspected cases (LEVEL C), and in some cases are consistent with full-subset numerical aggregates (LEVEL A). Consistency with an aggregate metric, such as the gap between average precision at IoU 0.50 and average precision over IoU 0.50-0.95, does not constitute proof of the mechanism behind any individual prediction. A PARTIALLY_SUPPORTED category may therefore be described as a pattern that is consistent with the evidence, but it must not be described as a confirmed cause, a confirmed detector weakness, or a property established for the dataset as a whole.

## 7.3 Not Directly Supported

The following categories are NOT_DIRECTLY_SUPPORTED. The observations recorded for them do not have an independent evidential basis in the available data, and the category labels must not be reinterpreted as confirmed mechanisms.

- DUPLICATE_DETECTION
- LOW_CONFIDENCE
- CROWDING

For DUPLICATE_DETECTION, the recorded duplicates are a consequence of the greedy one-to-one matching rule, not a measured property of the detector. For LOW_CONFIDENCE, no confidence distribution field exists in the baseline summary, so per-prediction confidence cannot be measured. For CROWDING, no numerical field measures object density, and the single inspected case does not support a general claim.

## 7.4 The No-Upgrade Rule

The support classification of every category is fixed by the validated evidence and is not revised on the basis of this documentation. PARTIALLY_SUPPORTED remains PARTIALLY_SUPPORTED, and NOT_DIRECTLY_SUPPORTED remains NOT_DIRECTLY_SUPPORTED. No category was upgraded to SUPPORTED. The only category assigned SUPPORTED is BORDERLINE_IOU_MATCH, on the basis of the fixed 0.50 IoU matching threshold.

## 7.5 Evidence Support and Causal Explanation

This section distinguishes evidence support from causal explanation. Evidence support describes whether the available data are sufficient to sustain a category label under the evaluation protocol. Causal explanation describes the mechanism that produced an observation. The two are not equivalent: a category may be supported as an observed pattern while the causal mechanism remains unestablished. No causal claim is made in this section, and none of the categories above is asserted to be the cause of any prediction outcome.# 8. Scientific Limitations

This section states the boundaries that constrain how the findings of this error analysis may be described. Each limitation is reported as validated in the source evidence. No limitation has been weakened, removed, merged, or upgraded, and no new limitation has been introduced.

## 8.1 Limited Visual Sample Size (SL-01)

Only 12 visual cases were inspected, of which one originates from the validation split (VC-09) and eleven from the test split. The sample was selected deterministically from matching evidence and is an error-analysis sample, not a statistically representative random sample of the dataset. Conclusions drawn from the visual inspection are therefore bounded by this sample.

## 8.2 Visual Findings Are Case-Bound (SL-02)

Visual findings are observations made in the inspected cases. They must not be described as what the dataset as a whole contains unless independently supported by full-subset numerical evidence.

## 8.3 No Dataset-Wide Prevalence (SL-03)

Visual evidence does not establish the dataset-wide prevalence of any error category. The observations apply to the inspected cases and cannot be extrapolated to the full evaluated subsets without separate numerical support.

## 8.4 Person-Class Evaluation Limitation (SL-04)

The person class has no ground truth in the evaluated validation and test subsets (status no_ground_truth in both splits). No person precision, recall, average precision, false-positive, or false-negative conclusion may be inferred. The no_ground_truth status must not be reinterpreted as poor person-class performance; person-class performance cannot be established from the available evidence.

## 8.5 Absence of Confidence Information (SL-05)

No confidence distribution field exists in the baseline summary. Per-prediction confidence therefore cannot be measured or compared, and no statement about confidence calibration may be made.

## 8.6 Uncertainty of Causal Attribution (SL-06)

Causal mechanisms cannot be established where the evidence is insufficient. Aggregate precision, recall, and average precision measure detection quality at the evaluated operating point and cannot by themselves establish the mechanism behind any specific false positive or false negative.

## 8.7 Duplicate Detections Are a Matching Artefact (SL-07)

Duplicate detections recorded in the visual cases are an artefact of the greedy one-to-one matching rule, not a measured property of the detector. They must not be interpreted as evidence of detector behaviour.

## 8.8 Statistical Significance Not Established (SL-08)

The difference between the validation and test aggregate results cannot be established as statistically significant. No statistical test was performed, and the difference is small in absolute terms.

## 8.9 No Generalization Failure Conclusion (SL-09)

No generalization failure can be concluded from individual case differences. The inspected cases do not support a claim that the detector fails to generalize.

## 8.10 Model Information Not Established (SL-10)

Model architecture, training procedure, hardware, and hyperparameters are not established by the selected source artifacts. They are therefore not reported in this documentation.# 9. Traceability and Source Artifacts

This section documents the provenance of every finding used in this error analysis. The source artifacts are divided into authoritative sources, which carry the primary evidence and interpretation constraints, and supporting sources, which carry the underlying evidence records and audit information. No source artifact other than those listed below was used, and no artifact outside this set is referenced.

## 9.1 Authoritative Sources

The following artifacts are the authoritative sources for this documentation.

- evaluation/outputs/d03-baseline-10-error-analysis-visual-01/research_report.md — Full D-03 report; narrative synthesis of the evidence layers.
- evaluation/outputs/d03-baseline-10-error-analysis-visual-01/evidence_integration.json — Integrated evidence relationships, support states, machine error evidence, and visual evidence aggregation (LEVEL B and LEVEL C authoritative).
- evaluation/outputs/d03-baseline-10-error-analysis-visual-01/scientific_boundary.json — Authoritative interpretation constraints, evidence-level boundary, causal-language boundary, person-class boundary, and sample-scope boundary.
- evaluation/outputs/d03-baseline-10-error-analysis-visual-01/numerical_baseline_extract.json — Authoritative full valid/test numerical baseline (LEVEL A).

## 9.2 Supporting Sources

The following artifacts are the supporting sources for this documentation.

- evaluation/outputs/d03-baseline-10-error-analysis-visual-01/matching.json — Authoritative 12-image TP/FP/FN machine matching evidence (LEVEL B).
- evaluation/outputs/d03-baseline-10-error-analysis-visual-01/visual_inspection.json — Authoritative 12-case visual inspection records (LEVEL C).
- evaluation/outputs/d03-baseline-10-error-analysis-visual-01/visual_error_summary.json — Aggregated visual error categories and uncertainty summary.
- evaluation/outputs/d03-baseline-10-error-analysis-visual-01/evidence_mapping.json — Visual-to-numerical support status for each category.
- evaluation/outputs/d03-baseline-10-error-analysis-visual-01/final_integrity_validation.json — Integrity audit confirming artifact existence and that no protected file was modified.

## 9.3 Evidence Roles

Each artifact has the evidence role stated in the source record. In particular:

- numerical_baseline_extract.json provides the LEVEL A numerical baseline over the complete evaluated valid/test subsets.
- evidence_integration.json provides the LEVEL B and LEVEL C integrated evidence relationships, support states, and visual evidence aggregation.
- scientific_boundary.json provides the interpretation and scientific boundaries, including the evidence-level, causal-language, person-class, and sample-scope constraints.
- research_report.md provides the full D-03 narrative report.
- matching.json provides the LEVEL B machine matching evidence for the 12 selected images.
- visual_inspection.json provides the LEVEL C visual inspection records for the same 12 cases.
- visual_error_summary.json provides the aggregated visual error categories and uncertainty summary.
- evidence_mapping.json provides the visual-to-numerical support status for each category.
- final_integrity_validation.json provides the artifact integrity audit.

## 9.4 Extraction Note

All numerical values in this documentation are copied verbatim from numerical_baseline_extract.json and evidence_integration.json. No value was computed, derived, or inferred. No source artifact was modified by this extraction.# 10. Conclusion Boundary

This section states what the evidence permits this documentation to conclude and explicitly excludes what it does not. Every statement below is drawn from the validated findings in paper_ready_findings.json. No new evidence was introduced, no new metric was computed, and no claim is made beyond the support state recorded for each finding.

## 10.1 LEVEL_A Numerical Findings

The following conclusions rest on full-subset numerical metrics over the complete evaluated valid/test subsets (LEVEL_A) and may be stated for the evaluated splits as a whole.

- At the evaluated operating point, recall is substantially higher than precision in both evaluated splits: valid recall 0.862152 versus precision 0.223023; test recall 0.873055 versus precision 0.222698.
- False positives are numerous relative to true positives in both evaluated splits: valid 2877 true positives and 10023 false positives; test 1403 true positives and 4897 false positives.
- False negatives occur across the evaluated classes in both splits: valid 460; test 204.
- Valid and test aggregate performance are close on all four overall metrics (map_0.5, map_0.5_0.95, precision, recall), with small absolute differences between the splits.
- For every evaluated class in both splits, the gap between average precision at IoU 0.50 and average precision over IoU 0.50-0.95 is substantial.

These statements describe observed numerical values at the evaluated operating point. They do not establish why those values arise, and they do not extend beyond the evaluated valid/test subsets.

## 10.2 LEVEL_B Matching Evidence

The following conclusions rest on machine matching evidence (TP/FP/FN) for the 12 selected images (LEVEL_B).

- The 12 selected images were matched using a class-aware, greedy, confidence-ranked, one-to-one matching procedure with an IoU threshold of 0.50 and no non-maximum suppression at evaluation time.
- Aggregate matching totals for the 12 selected images are 781 true positives, 2819 false positives, and 182 false negatives.
- The BORDERLINE_IOU_MATCH category is the only error category with full support (SUPPORTED). Borderline IoU behaviour relative to the 0.50 matching threshold was observed in VC-01 (IoU 0.4718) and VC-03 (IoU 0.4582). This support rests on the fixed 0.50 IoU matching threshold and is limited to the threshold dependence of the matching rule.
- Duplicate detections recorded in the visual cases are an artefact of the greedy one-to-one matching rule, not a measured property of the detector.

## 10.3 LEVEL_C Visual Observations

The following conclusions rest on direct visual inspection observations for the 12 inspected cases (LEVEL_C).

- Visual inspection records exist for 12 cases (VC-01 through VC-12), of which one case (VC-09) originates from the validation split and eleven from the test split.
- No new visual observations were created during evidence integration; the categories are those already recorded in the source artifacts.
- Patterns associated with small objects, background false positives, localization difficulty, and false negatives were observed in the inspected cases, with the case counts recorded in the findings.

Visual observations are limited to the deterministic 12-case error-analysis sample. This sample was selected from matching evidence and is not a statistically representative random sample of the dataset. Visual findings are observations made in the inspected cases and must not be described as what the dataset as a whole contains unless independently supported by full-subset numerical evidence. Visual evidence does not establish dataset-wide prevalence of any error category.

## 10.4 Boundaries That Exclude Unsupported Conclusions

The evidence does not support the following, and no such conclusion is asserted here.

Person-class boundary. The person class has no ground truth in the evaluated validation and test subsets (status no_ground_truth in both). No person precision, recall, average precision, false-positive, or false-negative conclusion may be inferred, and the no_ground_truth status must not be reinterpreted as poor person-class performance. No person-class performance conclusion can be inferred.

Support boundary. BORDERLINE_IOU_MATCH is SUPPORTED. SMALL_OBJECT, FALSE_POSITIVE_BACKGROUND, LOCALIZATION_ERROR, and FALSE_NEGATIVE are PARTIALLY_SUPPORTED. DUPLICATE_DETECTION, LOW_CONFIDENCE, and CROWDING are NOT_DIRECTLY_SUPPORTED. No category was upgraded to SUPPORTED.

Causal boundary. The evidence does not establish causal mechanisms for individual errors. Recorded patterns are described as contributing scene-level difficulties, not as proven causes. Aggregate precision, recall, and average precision measure detection quality at the evaluated operating point and cannot by themselves establish the mechanism behind any specific false positive or false negative.

Statistical boundary. No statistical significance conclusion was established for validation/test differences. No statistical test was performed, and the observed differences are small in absolute terms.

Generalization boundary. Individual case differences do not establish generalization failure. No generalization failure is concluded from the observed case-level variation.

Confidence boundary. Prediction-level confidence distributions cannot be measured from the available baseline summary. No confidence distribution field exists in the baseline summary, so per-prediction confidence cannot be measured or compared.

Scope boundary. Model architecture, training procedure, hardware configuration, and hyperparameter setting are not established by the selected source artifacts and are therefore not reported. This documentation does not claim that the analysis proves any particular model architecture, training procedure, hardware configuration, or hyperparameter setting, and it introduces no recommendations for model improvement.
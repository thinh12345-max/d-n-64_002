# 10. Conclusion Boundary

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
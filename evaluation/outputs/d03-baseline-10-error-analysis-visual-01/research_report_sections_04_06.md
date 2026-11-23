# D-03 Baseline Evaluation and Visual Error Analysis — Report Sections 4-6

## 4. Baseline quantitative results

The baseline results are recorded for the full evaluated validation subset (43 images) and test subset (21 images) and are reproduced here from the numerical baseline artifact [Source: evidence_integration.json].

Validation overall: mAP@0.5 = 0.680575; mAP@0.5:0.95 = 0.319892; precision = 0.223023; recall = 0.862152. The subset contains 3337 ground-truth objects and 12900 predictions, with 2877 true positives, 10023 false positives, and 460 false negatives [Source: evidence_integration.json].

Test overall: mAP@0.5 = 0.676974; mAP@0.5:0.95 = 0.319613; precision = 0.222698; recall = 0.873055. The subset contains 1607 ground-truth objects and 6300 predictions, with 1403 true positives, 4897 false positives, and 204 false negatives [Source: evidence_integration.json].

Per-class average precision at IoU 0.50 for validation and test respectively: bus 0.857143 / 0.800000; car 0.895222 / 0.894281; motorcycle 0.846828 / 0.865591; truck 0.803681 / 0.825000. The person class has no ground truth in either split, so no person average precision is defined [Source: evidence_integration.json].

Valid-minus-test differences are: mAP@0.5 +0.003601; mAP@0.5:0.95 +0.000279; precision +0.000325; recall -0.010903 [Source: evidence_integration.json]. No further statistics have been computed, and no claim is made that any of these differences is statistically significant [Source: scientific_boundary.json].

## 5. Visual error-analysis findings

Twelve visual cases (VC-01 through VC-12) were inspected, one from the validation split (VC-09) and eleven from the test split [Source: evidence_integration.json]. The following categories were recorded in the inspected cases, together with their evidence support state [Source: evidence_integration.json]:

- SMALL_OBJECT: observed in all 12 cases; PARTIALLY_SUPPORTED.
- FALSE_POSITIVE_BACKGROUND: observed in VC-01, VC-02, VC-03, VC-11, VC-12; PARTIALLY_SUPPORTED.
- LOCALIZATION_ERROR: observed in VC-02, VC-04, VC-05, VC-06; PARTIALLY_SUPPORTED.
- FALSE_NEGATIVE: observed in VC-04, VC-05, VC-06; PARTIALLY_SUPPORTED.
- DUPLICATE_DETECTION: observed in VC-07, VC-08; NOT_DIRECTLY_SUPPORTED.
- LOW_CONFIDENCE: observed in VC-09, VC-10; NOT_DIRECTLY_SUPPORTED.
- CROWDING: observed in VC-12; NOT_DIRECTLY_SUPPORTED.
- BORDERLINE_IOU_MATCH: observed in VC-01 (IoU 0.4718) and VC-03 (IoU 0.4582); SUPPORTED.

The only category with full support is BORDERLINE_IOU_MATCH, whose status rests on the fixed 0.50 IoU matching threshold [Source: scientific_boundary.json]. The machine matching evidence for the 12 selected images gives aggregate totals of 781 true positives, 2819 false positives, and 182 false negatives [Source: evidence_integration.json].

These findings are observations made in the inspected cases. They are not statements about what the dataset as a whole contains, and the 12-case sample is a deterministic error-analysis sample, not a statistically representative random sample [Source: scientific_boundary.json].

## 6. Integrated evidence interpretation

The evidence supports a limited set of observations. Recall is substantially higher than precision at the evaluated operating point in both splits, and false positives are numerous relative to true positives [Source: scientific_boundary.json]. False negatives occur across the evaluated classes, and valid and test aggregate performance are close [Source: scientific_boundary.json]. The gap between average precision at IoU 0.50 and average precision over IoU 0.50-0.95 is substantial for every evaluated class in both splits [Source: scientific_boundary.json].

The large AP@0.5 versus AP@0.5:0.95 gap is partially consistent with localization weakness, but the numerical evidence cannot establish that localization is the sole or primary weakness, nor that it applies to any specific inspected case [Source: scientific_boundary.json]. The low aggregate precision is partially consistent with the presence of many false positives, but the mechanism behind any specific false positive cannot be established, including whether any are background artefacts or duplicate detections [Source: scientific_boundary.json]. The residual false-negative counts are partially consistent with missed detections, but the representativeness of the inspected truck cases cannot be established [Source: scientific_boundary.json].

The following cannot be established from the current evidence: that all false positives are duplicate detections; that low precision is caused by duplicate detections; that every localization error is caused by small objects; that the AP gap proves localization is the sole weakness; that low confidence is the cause of false positives; that crowding is the cause of the observed errors; or that the visual findings from 12 cases represent the entire dataset statistically [Source: scientific_boundary.json]. Person-class performance cannot be established, because the person class has no ground truth in the evaluated validation and test subsets [Source: scientific_boundary.json].
# 7. Evidence Strength and Support Boundaries

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

This section distinguishes evidence support from causal explanation. Evidence support describes whether the available data are sufficient to sustain a category label under the evaluation protocol. Causal explanation describes the mechanism that produced an observation. The two are not equivalent: a category may be supported as an observed pattern while the causal mechanism remains unestablished. No causal claim is made in this section, and none of the categories above is asserted to be the cause of any prediction outcome.
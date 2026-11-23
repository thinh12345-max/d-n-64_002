# 8. Scientific Limitations

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

Model architecture, training procedure, hardware, and hyperparameters are not established by the selected source artifacts. They are therefore not reported in this documentation.
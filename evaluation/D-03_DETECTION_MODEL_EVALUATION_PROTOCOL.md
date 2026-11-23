# D-03 Detection Model Evaluation Protocol

## 1. Purpose and Scope

This protocol defines the mandatory evaluation procedure for the D-03
detection model. It governs how a trained detector is measured, how
results are recorded, and how the evaluation dataset is protected from
contamination.

Scope:
- Current D-03 baseline evaluation of the trained detector.
- Definition of class semantics, metrics, thresholds, and reproducibility.
- Future generalization evaluation of Video 1 and Video 2 as a separate
  stage.

Out of scope:
- Training procedure and hyperparameter selection.
- Dataset construction, annotation, or repair.
- Video 1 / Video 2 integration into the baseline.

## 2. Evaluation Dataset Boundaries

The D-03 evaluation is performed on the derived detection dataset
`My-First-Project-4-detection`, which is a separate derived detection
dataset produced from the canonical source dataset
`My-First-Project-4`.

The canonical source dataset `My-First-Project-4` must remain untouched.
It is the canonical source dataset and is never modified by evaluation.

The derived detection dataset splits:

| Split    | Images | Annotation lines | Person (class 3) instances |
|----------|--------|------------------|---------------------------|
| train    | 2309   | 47681            | 546                       |
| valid    | 43     | 3337             | 0                         |
| test     | 21     | 1607             | 0                         |
| TOTAL    | 2373   | 52625            | 546                       |

All 52625 annotation lines are 5-field YOLO detection format
(`class x_center y_center width height`, normalized to image dimensions).

Person-class distribution note:
- Person instances (546) exist only in the train split.
- valid person instances = 0.
- test person instances = 0.

This is an established fact of the current dataset. The evaluation
protocol must report it as-is and must not silently repair or re-balance
it.

## 3. Relationship Between Training Dataset and Evaluation Dataset

The training dataset and the evaluation dataset are distinct splits of
the derived detection dataset:

- Training dataset: `train/` (2309 images, 47681 annotation lines).
- Evaluation dataset: `valid/` (43 images) and `test/` (21 images).

The evaluation dataset is held-out. It is never used during training and
is never written to by the training process. Evaluation metrics are
computed only on `valid/` and `test/`.

No image or annotation may appear in more than one split. The splits are
fixed and must not be reshuffled as part of evaluation.

## 4. Class Definitions

The detection model uses exactly 5 classes, as defined in
`My-First-Project-4-detection/data.yaml`:

| Class ID | Class     |
|----------|-----------|
| 0        | bus       |
| 1        | car       |
| 2        | motorcycle|
| 3        | person    |
| 4        | truck     |

Class IDs are zero-indexed and contiguous. Any prediction whose class
ID is outside 0-4 is invalid and must be discarded before metric
computation.

## 5. Detection Metrics

The following metrics are computed per class and aggregated.

### Precision

Precision is the ratio of correct predictions to all predicted
positive detections, at a given IoU and confidence threshold:

    precision = TP / (TP + FP)

### Recall

Recall is the ratio of correct predictions to all ground-truth instances,
at a given IoU and confidence threshold:

    recall = TP / (TP + FN)

A prediction is a true positive (TP) when it matches a ground-truth
instance of the same class with IoU at or above the evaluation IoU
threshold. A prediction with no matching ground truth is a false
positive (FP). An unmatched ground-truth instance is a false negative
(FN).

### mAP@0.5

Mean Average Precision at IoU threshold 0.5. For each class, precision is
computed as a function of recall (precision-recall curve), and the
average precision (AP) is the area under that curve. mAP@0.5 is the
mean of AP across all 5 classes, computed at a single IoU threshold of
0.5.

### mAP@0.5:0.95

Mean Average Precision averaged over IoU thresholds from 0.5 to 0.95 in
steps of 0.05 (eleven thresholds: 0.50, 0.55, ..., 0.95). For each class,
AP is computed at each threshold and averaged; mAP@0.5:0.95 is the
mean of those per-class averages across all 5 classes.

## 6. Per-Class Evaluation

Metrics are computed separately for each of the 5 classes:
bus, car, motorcycle, person, truck.

Per-class AP, precision, and recall are reported individually. No class
metrics are averaged into the overall score without the per-class values
being reported alongside.

## 7. Overall Evaluation

Overall evaluation is the mean of per-class metrics across all 5
classes. It is reported together with the per-class breakdown. An
overall score without the per-class breakdown is not a valid result.

## 8. Person-Class Evaluation Requirements

The person class (class 3) is a designated evaluation target and is
reported separately from the vehicle classes.

Current established facts:
- Person instances exist only in the train split (546 instances).
- valid person instances = 0.
- test person instances = 0.

Consequences for evaluation:
- Per-class person AP on `valid/` and `test/` is undefined because there
  are no ground-truth person instances in those splits. This must be
  reported as "no ground truth" and must not be reported as a perfect
  score, a zero score, or silently omitted.
- Person-class behavior on the training split is for diagnostic
  inspection only and is not part of the held-out evaluation score.
- Any future person evaluation requires a split with non-zero person
  ground truth and must be defined as a separate evaluation stage.

## 9. IoU Threshold Semantics

Intersection over Union (IoU) is computed between a predicted bounding
box and a ground-truth bounding box of the same class:

    IoU = area(intersection) / area(union)

Boxes are compared in normalized image coordinates. A prediction is a
candidate true positive only when IoU >= the evaluation IoU threshold.

mAP@0.5 uses a single IoU threshold of 0.5. mAP@0.5:0.95 uses eleven
thresholds from 0.50 to 0.95 in steps of 0.05.

One ground-truth instance may match at most one prediction. Matching is
greedy, ordered by descending prediction confidence.

## 10. Confidence Threshold Handling

Predictions are ranked by confidence score in descending order before
matching. Predictions below the minimum confidence threshold are
discarded and do not contribute to TP or FP.

For precision-recall curve computation, all predictions above the
minimum confidence threshold are used; the threshold is swept to build
the curve.

The minimum confidence threshold used for reporting must be recorded in
the result record.

## 11. NMS Considerations

Non-Maximum Suppression (NMS) is applied to raw model output before
metric computation. Duplicate detections of the same instance are
suppressed; only the highest-confidence detection per suppressed group
is retained.

NMS IoU threshold and confidence threshold used for suppression must be
recorded in the result record. Different NMS settings change results;
they must not be silently altered between evaluation runs.

## 12. Evaluation Reproducibility

Every evaluation run must be reproducible. The result record must
include:
- Model identifier and checkpoint path or hash.
- Dataset identifier and split paths.
- Evaluation code version and library versions (including the
  ultralytics / YOLO evaluation implementation version).
- IoU thresholds used.
- Confidence threshold used.
- NMS settings used.
- Software environment: Python version and key dependency versions.

A run that omits these fields is not a valid baseline result and must
be re-run or marked invalid.

## 13. Model/Checkpoint Identification

The detector under evaluation is identified by:
- Model identifier (e.g., trained checkpoint path).
- Checkpoint file hash or modification timestamp.
- Training run identifier from the D-03 baseline training stage.

The same checkpoint must be used for all reported metrics in a single
result record. Different checkpoints must not be mixed in one record.

## 14. Dataset Identification

The evaluation dataset is identified by:
- Dataset name: `My-First-Project-4-detection`.
- Source dataset: `My-First-Project-4` (canonical, untouched).
- Split paths: `train/`, `valid/`, `test/`.
- Annotation line count and per-split image counts.

The dataset version is fixed for the baseline. Any change to the
dataset requires a new dataset identifier and a new evaluation record.
## 15. No-Data-Modification Rule

Evaluation must not modify any dataset.

Prohibited:
- Editing, repairing, re-balancing, or resampling any annotation file.
- Moving, deleting, or renaming images or labels.
- Regenerating or re-exporting annotations.
- Changing the train/valid/test split.

The 41 boundary-overflow annotations are pre-existing source/export
precision artifacts. They must be left untouched and reported as-is.
They must not be silently repaired, filtered, or corrected during
evaluation.

Evaluation reads the dataset. It writes only evaluation results.

## 16. Leakage/Isolation Requirements

The evaluation dataset must be isolated from training:

- The evaluation splits (`valid/`, `test/`) must never be read or
  written by the training process.
- No evaluation result may be used to select, tune, or modify the model.
- Evaluation must not feed back into training data or training
  decisions.
- The canonical source dataset `My-First-Project-4` must remain
  untouched and must not be used directly for evaluation.

A single evaluation run must use one checkpoint and one fixed dataset
version. Mixing checkpoints or dataset versions in one run invalidates
the result.

## 17. Baseline Evaluation Procedure

The D-03 baseline evaluation procedure:

1. Identify the trained checkpoint produced by the D-03 baseline
   training stage. Do not start or restart training as part of this
   procedure.
2. Load the checkpoint and the fixed evaluation dataset
   `My-First-Project-4-detection`, splits `valid/` and `test/`.
3. Run inference on every image in `valid/` and `test/`.
4. Apply NMS with the recorded settings.
5. Compute per-class and overall precision, recall, mAP@0.5, and
   mAP@0.5:0.95.
6. Report per-class metrics for all 5 classes.
7. Report the person-class status separately, noting that person
   ground truth is 0 in `valid/` and `test/`.
8. Record all reproducibility fields.
9. Do not modify any dataset file at any step.

The baseline evaluation covers `valid/` and `test/` only. The training
split is excluded from the baseline score.

## 18. Future Video 1/Video 2 Evaluation Boundary

Video 1 and Video 2 are not part of the current training/evaluation
dataset and must remain outside the current baseline evaluation.

They may be evaluated later as a separate generalization evaluation
stage. When that stage runs:

- Video 1/Video 2 data is treated as external/generalization data.
- Its results must not overwrite or contaminate the baseline test
  results.
- It must be recorded as a distinct result record with its own dataset
  identifier.
- The baseline evaluation record must remain unchanged.

The baseline and the Video 1/Video 2 evaluation are separate stages and
must never be mixed into a single score.

## 19. Result Recording Requirements

Every evaluation result must be recorded with:

- Baseline or generalization stage label.
- Model identifier and checkpoint path/hash.
- Dataset identifier and split paths and image counts.
- Per-class precision, recall, AP@0.5, AP@0.5:0.95 for all 5 classes.
- Overall mAP@0.5 and mAP@0.5:0.95.
- Person-class status, including the fact that person ground truth is 0
  in `valid/` and `test/`.
- IoU threshold(s), confidence threshold, NMS settings.
- Software environment and library versions.
- Timestamp and run identifier.
- The 41 boundary-overflow annotations reported as-is.

A result missing these fields is incomplete and must be treated as
invalid.

## 20. Failure/Invalid-Result Handling

An evaluation run is invalid and must not be reported as a baseline
result when any of the following occur:

- The dataset was modified during evaluation.
- The wrong checkpoint or a mixed set of checkpoints was used.
- The evaluation splits differ from the fixed `valid/` and `test/`.
- Video 1/Video 2 data was included in the baseline score.
- Required reproducibility or result fields are missing.
- Metrics were computed without the per-class breakdown.
- The person-class status was reported as a numeric score instead of
  "no ground truth".

Invalid results must be flagged, not silently accepted. The run must be
re-executed under the corrected conditions, or recorded explicitly as
invalid with the reason documented.

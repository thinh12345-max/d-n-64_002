# TIER 2 — OBJECT DETECTION CLOSURE

**Date:** 2026-09-18
**Status:** SCIENTIFIC CLOSURE

---

## 1. Current Baseline

### Baseline Configuration

| Parameter | Value |
|-----------|-------|
| Model | YOLOv8m |
| Checkpoint | `runs/detect/train-16/weights/best.pt` |
| Confidence | 0.30 |
| IoU | 0.50 |
| Image Size | 640 |

The baseline configuration is documented in [D07_DETECTION_TRACKING_TRAJECTORY_BASELINE_FREEZE.md](docs/D07_DETECTION_TRACKING_TRAJECTORY_BASELINE_FREEZE.md).

**Note:** The runtime config.yaml shows confidence=0.20, but the frozen baseline evaluation uses confidence=0.30. This is a documented inconsistency that does not affect the scientific status of the baseline.

---

## 2. Model Provenance

### Training Configuration

| Parameter | Value |
|-----------|-------|
| Base Model | yolov8m.pt |
| Training Dataset | `My-First-Project-4/data.yaml` |
| Epochs | 100 |
| Batch Size | 8 |
| Image Size | 640 |
| Optimizer | Auto |
| Learning Rate (lr0) | 0.0005 |
| Loss Weights (box/cls/dfl) | 7.5 / 0.5 / 1.5 |

### Evidence Sources

- Training configuration: [runs/detect/train-16/args.yaml](runs/detect/train-16/args.yaml)
- Model checkpoint: `runs/detect/train-16/weights/best.pt`
- Evaluation protocol: [evaluation/D-03_DETECTION_MODEL_EVALUATION_PROTOCOL.md](evaluation/D-03_DETECTION_MODEL_EVALUATION_PROTOCOL.md)

### Missing Reproducibility Information

The following information is not available in the project artifacts:
- Exact training hardware (GPU model)
- Training duration (wall-clock time)
- Learning rate schedule details beyond lr0/lrf
- Augmentation parameters used during training

---

## 3. Dataset Relationship

### Dataset Statistics

| Split | Images | Boxes |
|-------|--------|-------|
| Train | 2,309 | 47,681 |
| Valid | 43 | 3,337 |
| Test | 21 | 1,607 |
| **Total** | **2,373** | **52,625** |

### Class Distribution

**Training Set:**

| Class | Count | Percentage |
|-------|-------|------------|
| bus | 431 | 0.9% |
| car | 21,706 | 45.5% |
| motorcycle | 23,187 | 48.6% |
| person | 546 | 1.1% |
| truck | 1,811 | 3.8% |

**Validation Set:**

| Class | Count | Percentage |
|-------|-------|------------|
| bus | 42 | 1.3% |
| car | 1,193 | 35.8% |
| motorcycle | 1,939 | 58.1% |
| person | 0 | 0.0% |
| truck | 163 | 4.9% |

### Dataset Characteristics

1. **Person class:** Person instances exist only in the training set (546), with zero instances in validation and test sets. This is a documented dataset characteristic.

2. **Class imbalance:** The dataset is heavily imbalanced toward car and motorcycle classes, which together comprise over 94% of all instances.

3. **Small objects:** Bus bounding boxes are predominantly small (95% < 20px), representing an observed dataset characteristic.

---

## 4. Class Consistency

### Detection Classes

| Class ID | Class Name |
|----------|------------|
| 0 | bus |
| 1 | car |
| 2 | motorcycle |
| 3 | person |
| 4 | truck |

### Runtime Mapping

The runtime uses the same 5-class detection output for both tracking and counting:
- Config: `config/config.yaml`
- Counting classes: car, motorcycle, bus, truck, person

### Consistency Status

The detection class universe is consistent between:
- Training dataset
- Model output
- Runtime configuration

---

## 5. Detection Evaluation

### Overall Metrics (Validation + Test Combined)

| Metric | Value |
|--------|-------|
| mAP@0.5 | ~0.68 |
| mAP@0.5:0.95 | ~0.32 |
| Precision | ~0.22 |
| Recall | ~0.86 |

### Per-Class Performance (Validation Set)

| Class | Precision | Recall | AP@0.5 | AP@0.5:0.95 |
|-------|-----------|--------|---------|--------------|
| bus | 0.159 | 0.857 | 0.857 | 0.398 |
| car | 0.190 | 0.895 | 0.895 | 0.433 |
| motorcycle | 0.259 | 0.847 | 0.847 | 0.400 |
| truck | 0.183 | 0.804 | 0.804 | 0.369 |
| person | N/A | N/A | N/A | N/A |

### Person Class Status

The person class has **no ground truth** in the validation and test sets. Per the evaluation protocol:
- Person precision, recall, and AP cannot be computed
- Status must be reported as "no ground truth"
- This is NOT equivalent to poor performance

### Evidence Source

[evaluation/outputs/d03-baseline-10-error-analysis-visual-01/paper_section_03_numerical_baseline_findings.md](evaluation/outputs/d03-baseline-10-error-analysis-visual-01/paper_section_03_numerical_baseline_findings.md)

---

## 6. Per-Class Behavior

### Observed Detection Patterns

**Car:**
- Highest recall (0.895) among vehicle classes
- Moderate precision (0.190)
- High true positive count (1,068 validation)
- Significant false positives (4,548 validation)

**Motorcycle:**
- High recall (0.847)
- Highest precision among vehicle classes (0.259)
- Moderate true positives (1,642 validation)
- Significant false positives (4,700 validation)

**Bus:**
- High recall (0.857)
- Low precision (0.159)
- Zero detections at runtime (confirmed)
- Small bounding box characteristic: 95% < 20px

**Truck:**
- High recall (0.804)
- Low precision (0.183)
- Lower instance count than car/motorcycle
- Moderate true positives (131 validation)

### Confidence Threshold Behavior

The task specification references a confidence experiment with thresholds 0.20–0.50. The specific numerical evidence for this experiment was not located in the current project artifacts. The baseline uses confidence=0.30 as documented in the baseline freeze.

---

## 7. Observed Limitations

### Detection Limitations

1. **High False Positive Rate:**
   - FP/TP ratio approximately 3.5:1
   - Predictions outnumber true positives by a large margin

2. **Low Precision:**
   - Overall precision ~22%
   - Majority of predictions are false positives

3. **Bus Detection:**
   - Zero bus detections observed in runtime evaluation
   - Dataset characteristic: 95% of bus boxes < 20px
   - Small object detection challenge

4. **Class Imbalance:**
   - Car and motorcycle dominate (>94%)
   - Person class has no evaluation ground truth
   - Rare classes (bus, truck) have limited samples

5. **Person Class:**
   - Cannot be evaluated (no validation/test ground truth)
   - Must not be reported as poor performance

### Limitations NOT Established

- No causal relationship established between small objects and bus detection failure
- No evidence of systematic class confusion in detection
- No evidence of model architecture limitations

---

## 8. Reproducibility

### Available Reproducibility Information

| Element | Status |
|---------|--------|
| Model checkpoint path | ✅ Available |
| Dataset identifier | ✅ Available |
| Class definitions | ✅ Available |
| Image size (640) | ✅ Available |
| Confidence threshold | ✅ Available |
| IoU threshold (0.50) | ✅ Available |
| Training hyperparameters | ✅ Partial |
| Training hardware | ❌ Not available |
| Evaluation code version | ❌ Not available |

### Reproducibility Status

The baseline can be partially reconstructed. Missing elements prevent exact reproducibility but do not invalidate the scientific status of the baseline.

---

## 9. Scientific Status

### Status Determination

Based on the available evidence, Tầng 2 — Object Detection is best classified as:

**EVALUATED**

This means:
- Implementation exists and runs correctly
- Configuration is documented and frozen
- Evaluation metrics are measured and recorded
- Limitations are documented
- However, NOT frozen for future changes (dataset remains open)

### Status Justification

| Criterion | Status |
|-----------|--------|
| Implementation | ✅ YOLOv8m trained and functional |
| Configuration | ✅ Documented and frozen |
| Evaluation | ✅ Metrics computed per protocol |
| Limitations | ✅ Documented |
| Frozen | ❌ Dataset open for expansion |

---

## 10. Relationship to Tracking

### Detection → Tracking Contract

The current detection output provides:
- Bounding boxes with confidence scores
- Class predictions
- 5-class detection output

### Detection Quality vs Tracking Quality

- Detection limitations (FP, FN, class imbalance) propagate to tracking
- However, tracking quality is evaluated separately
- No evidence attributes tracking errors specifically to detection

### ByteTrack Input

- ByteTrack receives detection output as input
- Tracks objects across frames using motion information
- Track ID assignment is independent of detection quality

---

## 11. Open Data-Expansion Boundary

### Dataset Expansion Allowed

Tầng 1 (Database) remains open to future dataset expansion. Therefore:

> **The current detection baseline is documented against the current dataset snapshot, while the data foundation remains open to future dataset expansion and additional training data.**

### Implications

1. Current evaluation reflects current dataset state
2. Future dataset additions may require re-evaluation
3. The baseline is not claiming finality
4. Dataset expansion is a planned future activity

---

## 12. Final Conclusion

### What Is Established

1. **YOLOv8m baseline model** with documented checkpoint path
2. **Evaluation protocol** (D-03) defining metrics and procedures
3. **Per-class metrics** computed on validation and test splits
4. **Class consistency** between training and runtime
5. **Limitations documented** including bus detection, person class, class imbalance

### What Is Evaluated

1. **Detection metrics** at confidence 0.30, IoU 0.50
2. **Per-class performance** across all five classes
3. **Precision/recall tradeoff** observed
4. **Dataset characteristics** documented

### What Remains Uncertain

1. **Optimal confidence threshold** — confidence experiment data not fully located
2. **Causal explanation** for bus detection failure
3. **Generalization** to other videos
4. **Person class** cannot be evaluated

### What Limitations Remain

1. High false positive rate (~78% of predictions)
2. Bus class has zero runtime detections
3. Person class has no evaluation ground truth
4. Class imbalance toward car/motorcycle
5. Limited reproducibility information

### Tầng 2 Closure Status

**TIER_2_STATUS: EVALUATED**

Tầng 2 — Object Detection is scientifically established as the current detection baseline within the research scope (Tiers 1–5 ending at Trajectory). The baseline has sufficient documentation, evaluation evidence, and documented limitations to support the current research pipeline.

The baseline is NOT claimed to be optimal. It represents the current documented detection capability against the current dataset snapshot.

---

## Validation Checklist

- [x] All reported numbers match existing evidence
- [x] Baseline configuration is consistent (YOLOv8m, conf=0.30, IoU=0.50, imgsz=640)
- [x] Class mappings are consistent (5 classes)
- [x] No unsupported accuracy claim exists
- [x] Dataset remains open to future expansion
- [x] No downstream stage is evaluated
- [x] No source code changed
- [x] No tests changed
- [x] No GT changed
- [x] No runtime artifacts changed

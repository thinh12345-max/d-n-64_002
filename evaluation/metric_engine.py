"""D-03 detection metric engine.

Deterministic per-class precision, recall, mAP@0.50 and mAP@0.50:0.95
implementation used by evaluation/d03_evaluate.py.

Matching follows the D-03 Evaluation Protocol (sections 5, 9, 10, 11):
  * Predictions are ranked by descending confidence.
  * A prediction matches the unmatched ground-truth box of the same class
    with the highest IoU, when IoU >= the evaluation threshold.
  * Each ground-truth box is matched at most once.
  * Unmatched predictions are false positives; unmatched ground truth is
    false negatives.
  * Classes never match across class boundaries.
  * NMS is applied upstream by the model/post-processing call; this module
    performs metric matching only and never applies a second NMS.
"""


def box_iou_xyxy(a, b):
    """Intersection-over-Union for two [x1, y1, x2, y2] boxes."""
    ax1, ay1, ax2, ay2 = a
    bx1, by1, bx2, by2 = b
    ix1 = max(ax1, bx1)
    iy1 = max(ay1, by1)
    ix2 = min(ax2, bx2)
    iy2 = min(ay2, by2)
    iw = ix2 - ix1
    ih = iy2 - iy1
    if iw <= 0.0 or ih <= 0.0:
        return 0.0
    inter = iw * ih
    area_a = max(0.0, ax2 - ax1) * max(0.0, ay2 - ay1)
    area_b = max(0.0, bx2 - bx1) * max(0.0, by2 - by1)
    union = area_a + area_b - inter
    if union <= 0.0:
        return 0.0
    return inter / union


def match_one_class(predictions, ground_truths, iou_threshold):
    """Greedy confidence-ranked matching for one class in one image.

    predictions: list of (conf, xyxy) already sorted descending by conf.
    ground_truths: list of xyxy boxes.

    Returns (true_positives, false_positives, false_negatives).
    """
    tp = 0
    fp = 0
    matched_gt = [False] * len(ground_truths)
    for _conf, pred_box in predictions:
        best_idx = -1
        best_iou = iou_threshold
        for idx, gt_box in enumerate(ground_truths):
            if matched_gt[idx]:
                continue
            iou = box_iou_xyxy(pred_box, gt_box)
            # Protocol section 9: a prediction is a candidate true positive when
            # IoU >= the evaluation threshold, so the boundary value itself is
            # included. `>=` also preserves "highest IoU wins" selection.
            if iou >= best_iou:
                best_iou = iou
                best_idx = idx
        if best_idx >= 0:
            matched_gt[best_idx] = True
            tp += 1
        else:
            fp += 1
    fn = sum(1 for m in matched_gt if not m)
    return tp, fp, fn


def compute_ap_from_pr(precision_points, recall_points):
    """Deterministic average-precision integration over a precision-recall curve.

    Uses all-point interpolation: at each recall level the precision is the
    maximum precision observed at recall >= that level. AP is the integral
    approximated over the sorted unique recall breakpoints. The result does
    not depend on set/dict iteration order.
    """
    pairs = sorted(zip(recall_points, precision_points), key=lambda x: x[0])
    if not pairs:
        return 0.0
    recalls = [r for r, _ in pairs]
    precisions = [p for _, p in pairs]
    max_p = 0.0
    for i in range(len(precisions) - 1, -1, -1):
        if precisions[i] > max_p:
            max_p = precisions[i]
        precisions[i] = max_p
    # Anchor the integral at recall 0.0: every recall level is interpolated by
    # the maximum precision observed at recall >= that level, so the precision
    # at recall 0.0 (the highest precision in the curve) contributes area from
    # the start. Starting at recalls[0] silently dropped that area and returned
    # 0.0 for any curve whose first recall point was not 0.0.
    ap = precisions[0] * (recalls[0] - 0.0)
    prev_r = recalls[0]
    for i in range(1, len(recalls)):
        ap += precisions[i] * (recalls[i] - prev_r)
        prev_r = recalls[i]
    return ap


def compute_pr_ap(predictions, ground_truths, iou_threshold):
    """AP at a single IoU threshold from the precision-recall curve."""
    if not predictions or not ground_truths:
        return 0.0
    tp = 0
    matched_gt = [False] * len(ground_truths)
    recall_points = []
    precision_points = []
    for _conf, pred_box in predictions:
        best_idx = -1
        best_iou = iou_threshold
        for idx, gt_box in enumerate(ground_truths):
            if matched_gt[idx]:
                continue
            iou = box_iou_xyxy(pred_box, gt_box)
            if iou > best_iou:
                best_iou = iou
                best_idx = idx
        if best_idx >= 0:
            matched_gt[best_idx] = True
            tp += 1
        denom_p = tp + (0 if best_idx >= 0 else 1)
        denom_r = len(ground_truths)
        precision_points.append(tp / float(denom_p) if denom_p > 0 else 0.0)
        recall_points.append(tp / float(denom_r) if denom_r > 0 else 0.0)
    return compute_ap_from_pr(precision_points, recall_points)


def compute_class_metrics(predictions, ground_truths, iou_threshold):
    """Precision, recall and AP@iou for a single class.

    predictions: list of (conf, xyxy) already sorted descending by conf.
    ground_truths: list of xyxy boxes.

    Returns (precision, recall, ap, tp, fp, fn).
    """
    tp, fp, fn = match_one_class(predictions, ground_truths, iou_threshold)
    precision = tp / float(tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / float(tp + fn) if (tp + fn) > 0 else 0.0
    ap = compute_pr_ap(predictions, ground_truths, iou_threshold)
    return precision, recall, ap, tp, fp, fn
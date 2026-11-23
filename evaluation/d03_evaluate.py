import argparse
import hashlib
import json
import os
import platform
import sys
from datetime import datetime, timezone

PROTOCOL_NAME = "D-03 Detection Model Evaluation Protocol"
PROTOCOL_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "D-03_DETECTION_MODEL_EVALUATION_PROTOCOL.md"
)
DATASET_NAME = "My-First-Project-4-detection"
CANONICAL_NAME = "My-First-Project-4"
DEFAULT_DATASET_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), DATASET_NAME
)
DEFAULT_DATA_YAML = os.path.join(DEFAULT_DATASET_DIR, "data.yaml")
DEFAULT_OUTPUT_ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")

CLASS_ORDER = [0, 1, 2, 3, 4]
CLASS_NAMES = {0: "bus", 1: "car", 2: "motorcycle", 3: "person", 4: "truck"}
PERSON_CLASS_ID = 3
VALID_SPLITS = ("valid", "test")
ALL_SPLITS = ("train", "valid", "test")
DEFAULT_CONF = 0.001
DEFAULT_EVAL_IOU = 0.5
DEFAULT_NMS_IOU = 0.7
DEFAULT_IMGSZ = 640

# IoU thresholds used by the metric engine (protocol sections 5, 9, 11).
# Protocol section 11 lists the thresholds explicitly as 0.50, 0.55, ..., 0.95
# (ten values, step 0.05). `range(10)` yields exactly that; `range(11)` would
# append 1.00, which is outside the protocol range and shifted every
# mAP@0.5:0.95 value.
EVAL_IOU_THRESHOLDS = [0.50 + 0.05 * i for i in range(10)]  # 0.50..0.95 step 0.05

# Expected number of class count (protocol section 4).
EXPECTED_NC = 5

# Boundary-overflow semantics (protocol section 15).
# The 41 boundary-overflow annotations are pre-existing source/export precision
# artifacts: tiny floating-point excursions around the [0,1] box boundary. They
# are NOT material out-of-domain coordinates and must be reported as-is, never
# repaired, clamped, or discarded. The protocol tolerance is 5e-7 (relative),
# derived from the established dataset fact that every known boundary-overflow
# annotation has a box-edge excursion of ~5e-7. Coordinates exceeding this
# tolerance are material out-of-domain and remain fatal.
BOUNDARY_OVERFLOW_TOLERANCE = 5e-7
BOUNDARY_OVERFLOW_REL_TOL = 1e-6


# D-03 detection metric engine (deterministic per-class precision, recall,
# mAP@0.50 and mAP@0.50:0.95). Lives in evaluation/metric_engine.py and is
# imported lazily so that static validation never requires inference libraries.
def _load_metric_engine():
    import importlib.util
    here = os.path.dirname(os.path.abspath(__file__))
    engine_path = os.path.join(here, "metric_engine.py")
    spec = importlib.util.spec_from_file_location("d03_metric_engine", engine_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def file_sha256(path, chunk=1024 * 1024):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(chunk), b""):
            h.update(block)
    return h.hexdigest()


def load_data_yaml(path):
    try:
        import yaml
    except ImportError:
        sys.stderr.write("ERROR: PyYAML is required to read data.yaml\n")
        sys.exit(2)
    if not os.path.isfile(path):
        sys.stderr.write("ERROR: data.yaml not found: %s\n" % path)
        sys.exit(2)
    with open(path, "r") as f:
        cfg = yaml.safe_load(f) or {}
    return cfg


def validate_class_mapping(cfg):
    # Protocol section 4: the detector uses exactly 5 classes. nc is an explicit
    # field and must never be inferred from 'names'.
    nc = cfg.get("nc")
    if not isinstance(nc, int) or isinstance(nc, bool):
        sys.stderr.write(
            "ERROR: data.yaml 'nc' must be an integer 5, got: %r\n" % (nc,)
        )
        sys.exit(2)
    if nc != EXPECTED_NC:
        sys.stderr.write(
            "ERROR: data.yaml 'nc' must be %d, got %d\n" % (EXPECTED_NC, nc)
        )
        sys.exit(2)

    names = cfg.get("names")
    if not isinstance(names, dict):
        sys.stderr.write("ERROR: data.yaml 'names' must be a mapping\n")
        sys.exit(2)
    for cid in CLASS_ORDER:
        if cid not in names:
            sys.stderr.write("ERROR: missing class id %d in data.yaml names\n" % cid)
            sys.exit(2)
        if str(names[cid]).strip().lower() != CLASS_NAMES[cid]:
            sys.stderr.write(
                "ERROR: class %d name mismatch: expected '%s', got '%s'\n"
                % (cid, CLASS_NAMES[cid], names[cid])
            )
            sys.exit(2)
    for cid in names:
        if cid not in CLASS_ORDER:
            sys.stderr.write("ERROR: unexpected class id %d in data.yaml names\n" % cid)
            sys.exit(2)
    return True


def list_split_files(split_dir):
    if not os.path.isdir(split_dir):
        return None
    files = []
    for name in sorted(os.listdir(split_dir)):
        low = name.lower()
        if low.endswith((".jpg", ".jpeg", ".png", ".bmp", ".webp", ".tif", ".tiff")):
            files.append(name)
    return files


def resolve_split(dataset_dir, split):
    if split not in ALL_SPLITS:
        sys.stderr.write("ERROR: unknown split '%s' (expected one of %s)\n" % (split, ALL_SPLITS))
        sys.exit(2)
    images_dir = os.path.join(dataset_dir, split, "images")
    labels_dir = os.path.join(dataset_dir, split, "labels")
    if not os.path.isdir(images_dir):
        sys.stderr.write("ERROR: missing split images directory: %s\n" % images_dir)
        sys.exit(2)
    if not os.path.isdir(labels_dir):
        sys.stderr.write("ERROR: missing split labels directory: %s\n" % labels_dir)
        sys.exit(2)
    return images_dir, labels_dir


def check_image_label_pairs(images_dir, labels_dir):
    images = list_split_files(images_dir)
    if images is None:
        sys.stderr.write("ERROR: no images found in %s\n" % images_dir)
        sys.exit(2)
    problems = []
    for img in images:
        stem = os.path.splitext(img)[0]
        label = os.path.join(labels_dir, stem + ".txt")
        if not os.path.isfile(label):
            problems.append("missing label for image: %s" % img)
    if problems:
        for p in problems[:20]:
            sys.stderr.write("ERROR: %s\n" % p)
        if len(problems) > 20:
            sys.stderr.write("ERROR: ... and %d more pairing problems\n" % (len(problems) - 20))
        sys.exit(2)
    return images


def box_edge_excursion(cx, cy, w, h):
    """Max excursion of a box edge beyond the [0,1] normalized domain.

    Returns 0.0 when the box is fully inside the domain. A positive value means
    at least one edge exceeds the boundary; the magnitude is the largest such
    excursion (left/top use the deficit below 0, right/bottom the excess above 1).
    """
    left = cx - w / 2.0
    right = cx + w / 2.0
    top = cy - h / 2.0
    bottom = cy + h / 2.0
    excursion = 0.0
    if left < 0.0:
        excursion = max(excursion, -left)
    if right > 1.0:
        excursion = max(excursion, right - 1.0)
    if top < 0.0:
        excursion = max(excursion, -top)
    if bottom > 1.0:
        excursion = max(excursion, bottom - 1.0)
    return excursion


def is_boundary_overflow(excursion):
    """Protocol section 15 tolerance: a known boundary-overflow annotation has a
    box-edge excursion of ~5e-7. Anything larger is material out-of-domain."""
    return 0.0 < excursion <= BOUNDARY_OVERFLOW_TOLERANCE * (1.0 + BOUNDARY_OVERFLOW_REL_TOL)


def parse_label_line(line, line_no, path):
    parts = line.split()
    if len(parts) != 5:
        return ("bad_fields", line_no, path, "expected 5 fields, got %d" % len(parts))
    try:
        cid = int(float(parts[0]))
        cx, cy, w, h = (float(x) for x in parts[1:])
    except ValueError:
        return ("bad_fields", line_no, path, "non-numeric field")
    if cid not in CLASS_ORDER:
        return ("bad_class", line_no, path, "class id %d out of range 0-4" % cid)
    excursion = box_edge_excursion(cx, cy, w, h)
    if excursion > 0.0:
        if is_boundary_overflow(excursion):
            return ("boundary_overflow", line_no, path,
                    "box edge excursion %.3e within protocol tolerance" % excursion)
        return ("material_out_of_domain", line_no, path,
                "box edge excursion %.3e exceeds protocol tolerance" % excursion)
    return None


def validate_labels(labels_dir, images):
    issues = []
    total_lines = 0
    per_class = {c: 0 for c in CLASS_ORDER}
    boundary_overflow = 0
    boundary_overflow_per_class = {c: 0 for c in CLASS_ORDER}
    for img in images:
        stem = os.path.splitext(img)[0]
        path = os.path.join(labels_dir, stem + ".txt")
        if not os.path.isfile(path):
            continue
        with open(path, "r") as f:
            for line_no, raw in enumerate(f, start=1):
                line = raw.strip()
                if not line:
                    continue
                total_lines += 1
                prob = parse_label_line(line, line_no, path)
                if prob is not None:
                    kind, _lno, _p, msg = prob
                    if kind == "boundary_overflow":
                        # Protocol section 15: preserved and reported as-is, never
                        # repaired, clamped, discarded, or counted as malformed.
                        cid = int(float(line.split()[0]))
                        boundary_overflow += 1
                        boundary_overflow_per_class[cid] += 1
                        per_class[cid] += 1
                        continue
                    issues.append(prob)
                    continue
                cid = int(float(line.split()[0]))
                per_class[cid] += 1
    if issues:
        kinds = {}
        for kind, *_ in issues:
            kinds[kind] = kinds.get(kind, 0) + 1
        sys.stderr.write("ERROR: %d malformed annotation line(s): %s\n" % (len(issues), kinds))
        for kind, line_no, path, msg in issues[:10]:
            sys.stderr.write("  - %s:%d (%s)\n" % (path, line_no, msg))
        sys.exit(2)
    return total_lines, per_class, boundary_overflow, boundary_overflow_per_class


def build_parser():
    parser = argparse.ArgumentParser(
        prog="d03_evaluate",
        description=(
            "D-03 Detection Model Evaluation. Evaluates a trained detector "
            "against a fixed held-out split of My-First-Project-4-detection."
        ),
    )
    parser.add_argument("--weights", required=False, default=None,
                        help="Path to model checkpoint (.pt). Required to run evaluation.")
    parser.add_argument("--data", default=DEFAULT_DATA_YAML,
                        help="Path to dataset data.yaml (default: %(default)s)")
    parser.add_argument("--dataset-dir", default=DEFAULT_DATASET_DIR,
                        help="Path to derived detection dataset directory (default: %(default)s)")
    parser.add_argument("--split", default="valid", choices=list(ALL_SPLITS),
                        help="Evaluation split (default: %(default)s)")
    parser.add_argument("--splits", default=None,
                        help="Comma-separated splits to evaluate, e.g. valid,test")
    parser.add_argument("--conf", type=float, default=DEFAULT_CONF,
                        help="Confidence threshold for predictions (default: %(default)s)")
    parser.add_argument("--eval-iou", type=float, default=DEFAULT_EVAL_IOU,
                        help="Evaluation IoU threshold for mAP@0.5 matching "
                             "(default: %(default)s)")
    parser.add_argument("--imgsz", type=int, default=DEFAULT_IMGSZ,
                        help="Inference image size (default: %(default)s)")
    parser.add_argument("--device", default="cpu",
                        help="Inference device, e.g. cpu, 0, cuda:0 (default: %(default)s)")
    parser.add_argument("--nms-iou", type=float, default=DEFAULT_NMS_IOU,
                        help="NMS IoU threshold applied to raw model output before "
                             "metric computation (default: %(default)s)")
    parser.add_argument("--max-det", type=int, default=300,
                        help="Max detections per image (default: %(default)s)")
    parser.add_argument("--output-dir", default=None,
                        help="Directory for evaluation results (default: evaluation/outputs/<run>)")
    parser.add_argument("--run-id", default=None,
                        help="Explicit run identifier for output naming")
    parser.add_argument("--stage", default="baseline",
                        choices=("baseline", "generalization"),
                        help="Evaluation stage label (default: %(default)s)")
    parser.add_argument("--no-infer", action="store_true",
                        help="Validate configuration and dataset only; do not run inference")
    parser.add_argument("--dry-run", action="store_true",
                        help="Alias for --no-infer")
    return parser


def resolve_output_dir(args):
    if args.output_dir:
        out = args.output_dir
    else:
        ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        rid = args.run_id or ("%s_%s" % (args.stage, ts))
        out = os.path.join(DEFAULT_OUTPUT_ROOT, rid)
    return os.path.abspath(out)


def build_repro_metadata(args, cfg, split, image_count, label_lines, per_class,
                         boundary_overflow, boundary_overflow_per_class=None):
    meta = {
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "stage": args.stage,
        "protocol": {
            "name": PROTOCOL_NAME,
            "path": PROTOCOL_PATH,
            "exists": os.path.isfile(PROTOCOL_PATH),
        },
        "model": {
            "weights_path": os.path.abspath(args.weights) if args.weights else None,
            "weights_sha256": file_sha256(args.weights) if args.weights and os.path.isfile(args.weights) else None,
        },
        "dataset": {
            "name": DATASET_NAME,
            "canonical_source": CANONICAL_NAME,
            "dataset_dir": os.path.abspath(args.dataset_dir),
            "data_yaml": os.path.abspath(args.data),
            "nc": cfg.get("nc"),
            "names": {int(k): str(v) for k, v in cfg.get("names", {}).items()},
            "split": split,
            "image_count": image_count,
            "label_line_count": label_lines,
            "per_class_gt": {CLASS_NAMES[c]: per_class[c] for c in CLASS_ORDER},
            "boundary_overflow_annotations": boundary_overflow,
            "boundary_overflow_per_class": (
                {CLASS_NAMES[c]: boundary_overflow_per_class[c] for c in CLASS_ORDER}
                if boundary_overflow_per_class else None
            ),
            "boundary_overflow_tolerance": BOUNDARY_OVERFLOW_TOLERANCE,
        },
        "inference": {
            "conf": args.conf,
            "eval_iou": args.eval_iou,
            "imgsz": args.imgsz,
            "device": args.device,
            "nms_iou": args.nms_iou,
            "max_det": args.max_det,
            "nms_note": (
                "model.predict(iou=...) applies ultralytics NMS to raw output before "
                "metric computation. It is the NMS IoU, not the evaluation matching "
                "threshold. Evaluation matching uses eval_iou and the metric engine."
            ),
        },
        "environment": {
            "python": platform.python_version(),
            "platform": platform.platform(),
        },
    }
    try:
        import ultralytics
        meta["environment"]["ultralytics"] = getattr(ultralytics, "__version__", None)
    except Exception:
        meta["environment"]["ultralytics"] = None
    try:
        import torch
        meta["environment"]["torch"] = getattr(torch, "__version__", None)
    except Exception:
        meta["environment"]["torch"] = None
    meta["evaluator"] = {
        "script": os.path.basename(__file__),
        "script_path": os.path.abspath(__file__),
    }
    return meta


def write_outputs(out_dir, base_name, meta, summary):
    os.makedirs(out_dir, exist_ok=True)
    meta_path = os.path.join(out_dir, base_name + ".meta.json")
    sum_path = os.path.join(out_dir, base_name + ".summary.json")
    with open(meta_path, "w") as f:
        json.dump(meta, f, indent=2, sort_keys=True)
    with open(sum_path, "w") as f:
        json.dump(summary, f, indent=2, sort_keys=True)
    return meta_path, sum_path


def run_inference(args, model, images_dir, images):
    results = {}
    for img in images:
        path = os.path.join(images_dir, img)
        try:
            # `iou` here is ultralytics' NMS IoU (post-processing), NOT the evaluation
            # matching threshold. Evaluation IoU is consumed separately by the metric
            # engine. See --nms-iou and --eval-iou.
            pred = model.predict(
                source=path,
                conf=args.conf,
                iou=args.nms_iou,
                imgsz=args.imgsz,
                device=args.device,
                verbose=False,
            )[0]
        except Exception as exc:  # pragma: no cover - defensive
            sys.stderr.write("ERROR: inference failed on %s: %s\n" % (img, exc))
            return None
        # Ground truth is read from label files as normalized [0,1] coordinates and
        # converted to xyxy in [0,1]. ultralytics reports b.xyxy in ORIGINAL image
        # pixels, so every prediction must be normalized to the same [0,1] frame
        # before metric matching. Leaving predictions in pixels made IoU between a
        # prediction and any ground-truth box structurally impossible (IoU 0) and
        # turned every prediction into a false positive.
        orig_shape = getattr(pred, "orig_shape", None)
        img_h = float(orig_shape[0]) if orig_shape else 1.0
        img_w = float(orig_shape[1]) if orig_shape else 1.0
        boxes = []
        if pred.boxes is not None:
            for b in pred.boxes:
                cls = int(b.cls.item()) if hasattr(b.cls, "item") else int(b.cls)
                conf = float(b.conf.item()) if hasattr(b.conf, "item") else float(b.conf)
                xyxy = b.xyxy[0].tolist() if hasattr(b.xyxy, "__getitem__") else list(b.xyxy)
                if img_w > 0.0 and img_h > 0.0:
                    xyxy = [xyxy[0] / img_w, xyxy[1] / img_h,
                            xyxy[2] / img_w, xyxy[3] / img_h]
                boxes.append({"class_id": cls, "class_name": CLASS_NAMES.get(cls, "unknown"),
                              "conf": conf, "xyxy": xyxy})
        results[img] = boxes
    return results


def summarize_metrics(meta, predictions_by_image, labels_dir, images):
    """Compute per-class precision, recall, mAP@0.50 and mAP@0.50:0.95.

    Ground truth is read from the on-disk label files (labels_dir / images) so
    that the metric engine always sees the same instances the protocol counts,
    including the preserved boundary-overflow annotations. Predictions come
    from the inference stage and have already had NMS applied by the model
    post-processing call; this function performs metric matching only and never
    applies a second NMS.
    """
    engine = _load_metric_engine()

    eval_iou = float(meta["inference"].get("eval_iou", 0.5))
    iou_thresholds = list(EVAL_IOU_THRESHOLDS)

    # Ground truth: canonical class order, deterministic image order.
    gt_by_class = {c: [] for c in CLASS_ORDER}
    gt_count_by_class = {c: 0 for c in CLASS_ORDER}
    for img in images:
        stem = os.path.splitext(img)[0]
        label_path = os.path.join(labels_dir, stem + ".txt")
        if not os.path.isfile(label_path):
            continue
        with open(label_path, "r") as f:
            for raw in f:
                line = raw.strip()
                if not line:
                    continue
                parts = line.split()
                if len(parts) != 5:
                    continue
                cid = int(float(parts[0]))
                if cid not in CLASS_ORDER:
                    continue
                cx, cy, w, h = (float(x) for x in parts[1:])
                x1 = cx - w / 2.0
                y1 = cy - h / 2.0
                x2 = cx + w / 2.0
                y2 = cy + h / 2.0
                gt_by_class[cid].append((img, (x1, y1, x2, y2)))
                gt_count_by_class[cid] += 1

    # Predictions: deterministic ordering (conf desc, image, stable index).
    pred_by_class = {c: [] for c in CLASS_ORDER}
    pred_count_by_class = {c: 0 for c in CLASS_ORDER}
    for img in sorted(predictions_by_image.keys()):
        boxes = predictions_by_image[img]
        for idx, b in enumerate(boxes):
            cid = b.get("class_id")
            if cid not in CLASS_ORDER:
                continue
            conf = float(b.get("conf", 0.0))
            xyxy = b.get("xyxy")
            if not xyxy or len(xyxy) != 4:
                continue
            pred_by_class[cid].append((conf, img, idx, tuple(float(v) for v in xyxy)))
            pred_count_by_class[cid] += 1

    def sort_preds(items):
        return sorted(items, key=lambda t: (-t[0], t[1], t[2]))

    per_class = {}
    for c in CLASS_ORDER:
        preds = sort_preds(pred_by_class[c])
        pred_boxes = [(conf, box) for conf, _img, _idx, box in preds]
        gt_boxes = [box for _img, box in gt_by_class[c]]
        precision, recall, ap05, tp, fp, fn = engine.compute_class_metrics(
            pred_boxes, gt_boxes, eval_iou)
        ap50_95_vals = []
        for thr in iou_thresholds:
            # compute_class_metrics returns (precision, recall, ap, tp, fp, fn);
            # index [2] selects the AP alone.
            ap = engine.compute_class_metrics(pred_boxes, gt_boxes, thr)[2]
            ap50_95_vals.append(ap)
        ap50_95 = sum(ap50_95_vals) / float(len(ap50_95_vals)) if ap50_95_vals else 0.0
        per_class[c] = {
            "precision": round(precision, 6),
            "recall": round(recall, 6),
            "ap05": round(ap05, 6),
            "ap50_95": round(ap50_95, 6),
            "tp": tp,
            "fp": fp,
            "fn": fn,
            "gt": gt_count_by_class[c],
            "predictions": pred_count_by_class[c],
        }

    total_tp = sum(per_class[c]["tp"] for c in CLASS_ORDER)
    total_fp = sum(per_class[c]["fp"] for c in CLASS_ORDER)
    total_fn = sum(per_class[c]["fn"] for c in CLASS_ORDER)
    overall_precision = total_tp / float(total_tp + total_fp) if (total_tp + total_fp) > 0 else 0.0
    overall_recall = total_tp / float(total_tp + total_fn) if (total_tp + total_fn) > 0 else 0.0
    map_05 = sum(per_class[c]["ap05"] for c in CLASS_ORDER) / float(len(CLASS_ORDER))
    map_05_95 = sum(per_class[c]["ap50_95"] for c in CLASS_ORDER) / float(len(CLASS_ORDER))

    person = per_class[PERSON_CLASS_ID]
    summary = {
        "stage": meta["stage"],
        "split": meta["dataset"]["split"],
        "image_count": meta["dataset"]["image_count"],
        "model_weights": meta["model"]["weights_path"],
        "eval_iou": eval_iou,
        "iou_thresholds_ap50_95": [round(t, 2) for t in iou_thresholds],
        "overall": {
            "precision": round(overall_precision, 6),
            "recall": round(overall_recall, 6),
            "map_0.5": round(map_05, 6),
            "map_0.5_0.95": round(map_05_95, 6),
        },
        "per_class": {CLASS_NAMES[c]: per_class[c] for c in CLASS_ORDER},
        "person": {
            "class_id": PERSON_CLASS_ID,
            "class_name": CLASS_NAMES[PERSON_CLASS_ID],
            "gt_instances": person["gt"],
            "predictions": person["predictions"],
            "precision": person["precision"],
            "recall": person["recall"],
            "ap05": person["ap05"],
            "ap50_95": person["ap50_95"],
            "tp": person["tp"],
            "fp": person["fp"],
            "fn": person["fn"],
            "status": "no_ground_truth" if person["gt"] == 0 else "evaluated",
        },
        "person_note": (
            "Person ground truth is 0 in this split. Per-class person AP is undefined "
            "and is reported as 'no_ground_truth', not as a numeric score."
        ),
        "person_boundary_overflow": (
            (meta["dataset"].get("boundary_overflow_per_class") or {}).get(CLASS_NAMES[PERSON_CLASS_ID], 0)
        ),
        "boundary_overflow_annotations": meta["dataset"]["boundary_overflow_annotations"],
        "boundary_overflow_per_class": meta["dataset"].get("boundary_overflow_per_class"),
        "boundary_overflow_note": (
            "Boundary-overflow annotations are pre-existing source/export precision "
            "artifacts. They are reported as-is and are not repaired."
        ),
    }
    return summary


def run(args):
    cfg = load_data_yaml(args.data)
    validate_class_mapping(cfg)

    splits = args.splits.split(",") if args.splits else [args.split]
    splits = [s.strip() for s in splits if s.strip()]
    if not splits:
        sys.stderr.write("ERROR: no evaluation splits selected\n")
        return 2

    run_outputs = []
    for split in splits:
        images_dir, labels_dir = resolve_split(args.dataset_dir, split)
        images = check_image_label_pairs(images_dir, labels_dir)
        label_lines, per_class, boundary_overflow, boundary_overflow_per_class = (
            validate_labels(labels_dir, images)
        )

        if not args.no_infer:
            if not args.weights:
                sys.stderr.write("ERROR: --weights is required to run evaluation (got: %s)\n"
                                 % args.weights)
                return 2
            if not os.path.isfile(args.weights):
                sys.stderr.write("ERROR: checkpoint not found: %s\n" % args.weights)
                return 2

        out_dir = resolve_output_dir(args)
        base = "split_%s" % split
        meta = build_repro_metadata(args, cfg, split, len(images), label_lines,
                                    per_class, boundary_overflow, boundary_overflow_per_class)

        if args.no_infer or args.dry_run:
            summary = summarize_metrics(meta, {}, labels_dir, images)
            meta_path, sum_path = write_outputs(out_dir, base, meta, summary)
            run_outputs.append({"split": split, "mode": "config_only",
                                "meta_path": meta_path, "summary_path": sum_path})
            continue

        try:
            from ultralytics import YOLO
        except Exception as exc:
            sys.stderr.write("ERROR: ultralytics is required for inference: %s\n" % exc)
            return 2
        model = YOLO(args.weights)
        preds = run_inference(args, model, images_dir, images)
        if preds is None:
            return 2
        summary = summarize_metrics(meta, preds, labels_dir, images)
        meta_path, sum_path = write_outputs(out_dir, base, meta, summary)
        run_outputs.append({"split": split, "mode": "inference",
                            "meta_path": meta_path, "summary_path": sum_path})

    final = {
        "evaluator": os.path.basename(__file__),
        "protocol": PROTOCOL_NAME,
        "stage": args.stage,
        "splits": splits,
        "outputs": run_outputs,
    }
    out_dir = os.path.dirname(run_outputs[0]["meta_path"]) if run_outputs else resolve_output_dir(args)
    os.makedirs(out_dir, exist_ok=True)
    with open(os.path.join(out_dir, "run.json"), "w") as f:
        json.dump(final, f, indent=2, sort_keys=True)
    print("D-03 evaluation completed. Splits: %s" % ", ".join(splits))
    print("Output dir: %s" % out_dir)
    return 0


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    if args.dry_run:
        args.no_infer = True
    return run(args)


if __name__ == "__main__":
    sys.exit(main())

"""Canonical read-only dataset validator for My-First-Project-4.

Validates the YOLO-format detection dataset at My-First-Project-4
exhaustively for all cheap structural and label checks. It is a DIAGNOSTIC
system only: it never modifies, moves, deletes, renames, repairs, or clamps
any dataset file.

Exit codes
----------
0  PASS
1  WARN
2  FAIL
3  NOT_VERIFIED / validator execution problem

A dataset validation failure is distinct from a validator execution
failure. A malformed label is a DATASET FAIL; a Python exception that
prevents validation is a VALIDATOR EXECUTION ERROR.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import yaml
except ImportError:  # pragma: no cover - dependency guard
    yaml = None  # type: ignore[assignment]

try:
    from PIL import Image as _PILImage
except ImportError:  # pragma: no cover - dependency guard
    _PILImage = None  # type: ignore[assignment]


EXIT_PASS = 0
EXIT_WARN = 1
EXIT_FAIL = 2
EXIT_NOT_VERIFIED = 3

EXPECTED_CLASS_NAMES = ("bus", "car", "motorcycle", "person", "truck")
EXPECTED_NC = len(EXPECTED_CLASS_NAMES)
EXPECTED_CLASS_IDS = tuple(range(EXPECTED_NC))

IMAGE_EXTENSIONS = (".jpg", ".jpeg", ".png", ".bmp", ".webp")
LABEL_EXTENSION = ".txt"

SPLIT_NAMES = ("train", "valid", "test")

ISOLATION_TARGETS = (
    "evaluation/person_eval",
    "evaluation/video12_screening",
    "evaluation/video12_annotation_candidates",
    "runs/detect/train-16",
)

EMPTY_LABEL_POLICY = "NOT_DEFINED"
DATASET_ROOT = Path("My-First-Project-4")


@dataclass
class CheckResult:
    check_id: str
    category: str
    status: str
    severity: str
    message: str
    split: Optional[str] = None
    file: Optional[str] = None
    line: Optional[int] = None
    observed: Any = None
    expected: Any = None

    def as_dict(self):
        d = {
            "check_id": self.check_id,
            "category": self.category,
            "status": self.status,
            "severity": self.severity,
            "message": self.message,
        }
        for key in ("split", "file", "line", "observed", "expected"):
            value = getattr(self, key)
            if value is not None:
                d[key] = value
        return d


@dataclass
class DatasetValidationReport:
    dataset_root: str
    overall_status: str = "NOT_VERIFIED"
    checks: List[CheckResult] = field(default_factory=list)
    person_stats: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    empty_label_stats: Dict[str, List[str]] = field(default_factory=dict)
    roboflow_metadata: bool = False
    isolation_status: Dict[str, bool] = field(default_factory=dict)
    image_count: int = 0
    label_count: int = 0
    per_split_image_counts: Dict[str, int] = field(default_factory=dict)
    per_split_label_counts: Dict[str, int] = field(default_factory=dict)

    def add(self, check):
        self.checks.append(check)

    def errors(self):
        return [c for c in self.checks if c.status == "FAIL" and c.severity == "ERROR"]

    def warnings(self):
        return [c for c in self.checks if c.status == "WARN"]

    def infos(self):
        return [c for c in self.checks if c.severity == "INFO"]

    def compute_overall(self):
        if any(c.status == "NOT_VERIFIED" for c in self.checks):
            self.overall_status = "NOT_VERIFIED"
        elif self.errors():
            self.overall_status = "FAIL"
        elif self.warnings():
            self.overall_status = "WARN"
        else:
            self.overall_status = "PASS"
        return self.overall_status

    def exit_code(self):
        return {"PASS": 0, "WARN": 1, "FAIL": 2, "NOT_VERIFIED": 3}[self.overall_status]


def _repo_root():
    here = Path(__file__).resolve()
    for parent in (here.parent, here.parent.parent, here.parent.parent.parent):
        if (parent / DATASET_ROOT.name).is_dir():
            return parent
    return Path.cwd()


def _safe_resolve(path, base):
    try:
        return (base / path).resolve()
    except OSError:
        return (base / path)


def _list_files(directory):
    if not directory.is_dir():
        return []
    try:
        return sorted(p for p in directory.iterdir() if p.is_file())
    except OSError:
        return []


def _is_image(name):
    return name.lower().endswith(IMAGE_EXTENSIONS)


def _is_label(name):
    return name.lower().endswith(LABEL_EXTENSION)


def _read_label_lines(path):
    """Yield (line_no, raw_line) for every non-empty line in a label file."""
    try:
        with open(path, "r", encoding="utf-8") as fh:
            for idx, line in enumerate(fh, start=1):
                stripped = line.strip()
                if stripped:
                    yield idx, stripped
    except OSError:
        return


class DatasetValidator:
    """Read-only canonical dataset validator for My-First-Project-4.

    Diagnostic system only. Never modifies, moves, deletes, renames,
    repairs, or clamps any dataset file.
    """

    def __init__(self, dataset_root=None):
        self.dataset_root = Path(dataset_root) if dataset_root else None
        self.report = DatasetValidationReport(dataset_root=str(self.dataset_root or ""))

    def run(self, dataset_root=None):
        if dataset_root is not None:
            self.dataset_root = Path(dataset_root)
        if self.dataset_root is None:
            self.dataset_root = _repo_root() / DATASET_ROOT
        self.report.dataset_root = str(self.dataset_root)
        try:
            self._c0_configuration()
            self._f0_file_structure()
            self._p0_pairing()
            self._s0_label_syntax()
            self._e0_label_semantics()
            self._f0_split_integrity()
            self._v0_image_validity()
            self._empty_label_report()
            self._roboflow_metadata()
            self._isolation_checks()
        except Exception as exc:
            self.report.add(CheckResult(
                check_id="V00_EXECUTION", category="EXECUTION",
                status="NOT_VERIFIED", severity="ERROR",
                message="Validator execution failed: %s: %s" % (type(exc).__name__, exc),
            ))
        self.report.compute_overall()
        return self.report

    # -- CATEGORY 1: configuration -----------------------------------------

    def _c0_configuration(self):
        root = self.dataset_root
        yaml_path = root / "data.yaml"
        if not yaml_path.is_file():
            self.report.add(CheckResult(
                check_id="C01", category="CONFIGURATION", status="FAIL",
                severity="ERROR", message="data.yaml does not exist.",
                observed=str(yaml_path), expected="existing data.yaml",
            ))
            return
        self.report.add(CheckResult(
            check_id="C01", category="CONFIGURATION", status="PASS",
            severity="INFO", message="data.yaml exists.", observed=str(yaml_path),
        ))
        if yaml is None:
            self.report.add(CheckResult(
                check_id="C02", category="CONFIGURATION", status="NOT_VERIFIED",
                severity="ERROR",
                message="PyYAML is not available; cannot parse data.yaml.",
            ))
            return
        try:
            with open(yaml_path, "r", encoding="utf-8") as fh:
                config = yaml.safe_load(fh) or {}
        except Exception as exc:
            self.report.add(CheckResult(
                check_id="C02", category="CONFIGURATION", status="FAIL",
                severity="ERROR",
                message="data.yaml is malformed: %s: %s" % (type(exc).__name__, exc),
            ))
            return
        if not isinstance(config, dict):
            self.report.add(CheckResult(
                check_id="C02", category="CONFIGURATION", status="FAIL",
                severity="ERROR", message="data.yaml root is not a mapping.",
                observed=type(config).__name__, expected="mapping",
            ))
            return
        nc = config.get("nc")
        if nc == EXPECTED_NC:
            self.report.add(CheckResult(
                check_id="C02", category="CONFIGURATION", status="PASS",
                severity="INFO", message="nc == %d." % EXPECTED_NC,
                observed=nc, expected=EXPECTED_NC,
            ))
        else:
            self.report.add(CheckResult(
                check_id="C02", category="CONFIGURATION", status="FAIL",
                severity="ERROR", message="nc is not %d." % EXPECTED_NC,
                observed=nc, expected=EXPECTED_NC,
            ))
        names = config.get("names")
        if not isinstance(names, list) or len(names) != EXPECTED_NC:
            self.report.add(CheckResult(
                check_id="C03", category="CONFIGURATION", status="FAIL",
                severity="ERROR",
                message="names is not a list of exactly %d strings." % EXPECTED_NC,
                observed=names, expected="list of %d strings" % EXPECTED_NC,
            ))
        else:
            self.report.add(CheckResult(
                check_id="C03", category="CONFIGURATION", status="PASS",
                severity="INFO",
                message="names contains exactly %d entries." % EXPECTED_NC,
                observed=len(names), expected=EXPECTED_NC,
            ))
            for idx, expected_name in enumerate(EXPECTED_CLASS_NAMES):
                cid = "C0%d" % (3 + idx)
                actual = names[idx] if idx < len(names) else None
                if actual == expected_name:
                    self.report.add(CheckResult(
                        check_id=cid, category="CONFIGURATION", status="PASS",
                        severity="INFO",
                        message="names[%d] == %r." % (idx, expected_name),
                        observed=actual, expected=expected_name,
                    ))
                else:
                    self.report.add(CheckResult(
                        check_id=cid, category="CONFIGURATION", status="FAIL",
                        severity="ERROR",
                        message="names[%d] is not %r." % (idx, expected_name),
                        observed=actual, expected=expected_name,
                    ))
        for offset, key in enumerate(("train", "valid", "test")):
            cid = "C0%d" % (9 + offset)
            raw = config.get(key)
            if raw is None:
                self.report.add(CheckResult(
                    check_id=cid, category="CONFIGURATION", status="FAIL",
                    severity="ERROR",
                    message="%s path is missing from data.yaml." % key,
                    observed=raw, expected="existing directory",
                ))
                continue
            resolved = _safe_resolve(Path(str(raw)), root)
            if resolved.is_dir():
                self.report.add(CheckResult(
                    check_id=cid, category="CONFIGURATION", status="PASS",
                    severity="INFO",
                    message="%s path resolves to an existing directory." % key,
                    observed=str(resolved),
                ))
            else:
                self.report.add(CheckResult(
                    check_id=cid, category="CONFIGURATION", status="FAIL",
                    severity="ERROR",
                    message="%s path does not resolve to an existing directory." % key,
                    observed=str(raw), expected="existing directory",
                ))

    # -- CATEGORY 2: file structure -----------------------------------------

    def _f0_file_structure(self):
        root = self.dataset_root
        for offset, split in enumerate(SPLIT_NAMES):
            base_num = 1 + offset * 3
            split_dir = root / split
            images_dir = split_dir / "images"
            labels_dir = split_dir / "labels"
            for cid, target, expected in (
                ("F0%d" % base_num, split_dir, "existing %s directory" % split),
                ("F0%d" % (base_num + 1), images_dir,
                 "existing %s/images directory" % split),
                ("F0%d" % (base_num + 2), labels_dir,
                 "existing %s/labels directory" % split),
            ):
                if target.is_dir():
                    self.report.add(CheckResult(
                        check_id=cid, category="FILE_STRUCTURE", status="PASS",
                        severity="INFO",
                        message="%s exists." % target.relative_to(root),
                        observed=str(target.relative_to(root)),
                    ))
                else:
                    self.report.add(CheckResult(
                        check_id=cid, category="FILE_STRUCTURE", status="FAIL",
                        severity="ERROR",
                        message="%s does not exist." % target.relative_to(root),
                        observed=str(target.relative_to(root)), expected=expected,
                    ))

    # -- CATEGORY 3: image/label pairing ------------------------------------

    def _p0_pairing(self):
        root = self.dataset_root
        for split in SPLIT_NAMES:
            images_dir = root / split / "images"
            labels_dir = root / split / "labels"
            image_files = _list_files(images_dir)
            label_files = _list_files(labels_dir)
            image_stems = {p.stem: p for p in image_files if _is_image(p.name)}
            label_stems = {p.stem: p for p in label_files if _is_label(p.name)}
            unexpected_images = [p.name for p in image_files if not _is_image(p.name)]
            unexpected_labels = [p.name for p in label_files if not _is_label(p.name)]
            missing_labels = sorted(s for s in image_stems if s not in label_stems)
            orphan_labels = sorted(s for s in label_stems if s not in image_stems)
            dup_image_stems = sorted(
                s for s, p in image_stems.items()
                if sum(1 for q in image_files if q.stem == s) > 1
            )
            dup_label_stems = sorted(
                s for s, p in label_stems.items()
                if sum(1 for q in label_files if q.stem == s) > 1
            )
            self.report.per_split_image_counts[split] = len(image_stems)
            self.report.per_split_label_counts[split] = len(label_stems)
            self.report.image_count += len(image_stems)
            self.report.label_count += len(label_stems)

            if not missing_labels and not orphan_labels and not dup_image_stems and not dup_label_stems:
                self.report.add(CheckResult(
                    check_id="P01", category="PAIRING", status="PASS",
                    severity="INFO",
                    message="%s: every image has exactly one matching label stem "
                            "and vice versa." % split,
                    observed="%d images, %d labels" % (len(image_stems), len(label_stems)),
                ))
            else:
                self.report.add(CheckResult(
                    check_id="P01", category="PAIRING", status="FAIL",
                    severity="ERROR",
                    message="%s: image/label pairing is incomplete." % split,
                    observed="missing=%d orphan=%d dup_image=%d dup_label=%d"
                    % (len(missing_labels), len(orphan_labels),
                       len(dup_image_stems), len(dup_label_stems)),
                ))
                for stem in missing_labels:
                    self.report.add(CheckResult(
                        check_id="P02", category="PAIRING", status="FAIL",
                        severity="ERROR",
                        message="missing label for image stem %r." % stem,
                        split=split, file=stem, observed=stem, expected="label file",
                    ))
                for stem in orphan_labels:
                    self.report.add(CheckResult(
                        check_id="P03", category="PAIRING", status="FAIL",
                        severity="ERROR",
                        message="orphan label with no matching image stem %r." % stem,
                        split=split, file=stem, observed=stem, expected="image file",
                    ))
                for stem in dup_image_stems:
                    self.report.add(CheckResult(
                        check_id="P04", category="PAIRING", status="FAIL",
                        severity="ERROR",
                        message="duplicate image stem %r." % stem,
                        split=split, file=stem, observed=stem, expected="unique stem",
                    ))
                for stem in dup_label_stems:
                    self.report.add(CheckResult(
                        check_id="P05", category="PAIRING", status="FAIL",
                        severity="ERROR",
                        message="duplicate label stem %r." % stem,
                        split=split, file=stem, observed=stem, expected="unique stem",
                    ))
            for name in unexpected_images:
                self.report.add(CheckResult(
                    check_id="P06", category="PAIRING", status="WARN",
                    severity="WARNING",
                    message="unexpected non-image file in %s/images: %r." % (split, name),
                    split=split, file=name, observed=name,
                    expected="recognized image extension",
                ))
            for name in unexpected_labels:
                self.report.add(CheckResult(
                    check_id="P07", category="PAIRING", status="WARN",
                    severity="WARNING",
                    message="unexpected non-label file in %s/labels: %r." % (split, name),
                    split=split, file=name, observed=name,
                    expected=LABEL_EXTENSION,
                ))

    # -- CATEGORY 4: label syntax -------------------------------------------

    def _s0_label_syntax(self):
        root = self.dataset_root
        syntax_failures = 0
        for split in SPLIT_NAMES:
            labels_dir = root / split / "labels"
            label_files = _list_files(labels_dir)
            label_files = [p for p in label_files if _is_label(p.name)]
            for path in sorted(label_files, key=lambda p: p.name):
                rel = path.relative_to(root)
                empty = True
                for lineno, raw in _read_label_lines(path):
                    empty = False
                    fields = raw.split()
                    if len(fields) != 5:
                        syntax_failures += 1
                        self.report.add(CheckResult(
                            check_id="S01", category="LABEL_SYNTAX", status="FAIL",
                            severity="ERROR",
                            message="annotation line does not have 5 fields.",
                            split=split, file=str(rel), line=lineno,
                            observed="field_count=%d" % len(fields),
                            expected="field_count=5",
                        ))
                        continue
                    class_field = fields[0]
                    coord_fields = fields[1:5]
                    if not _is_int(class_field):
                        syntax_failures += 1
                        self.report.add(CheckResult(
                            check_id="S02", category="LABEL_SYNTAX", status="FAIL",
                            severity="ERROR",
                            message="class id is not an integer.",
                            split=split, file=str(rel), line=lineno,
                            observed="class_id=%r" % class_field,
                            expected="integer class id",
                        ))
                    for coord in coord_fields:
                        if not _is_float(coord):
                            syntax_failures += 1
                            self.report.add(CheckResult(
                                check_id="S03", category="LABEL_SYNTAX", status="FAIL",
                                severity="ERROR",
                                message="coordinate is not a floating-point number.",
                                split=split, file=str(rel), line=lineno,
                                observed="coord=%r" % coord,
                                expected="floating-point number",
                            ))
                if empty:
                    self.report.empty_label_stats.setdefault(split, []).append(str(rel))
        if syntax_failures == 0:
            self.report.add(CheckResult(
                check_id="S04", category="LABEL_SYNTAX", status="PASS",
                severity="INFO",
                message="all non-empty annotation lines have exactly five "
                        "whitespace-separated fields.",
                observed="syntax_failures=0",
            ))
        else:
            self.report.add(CheckResult(
                check_id="S05", category="LABEL_SYNTAX", status="FAIL",
                severity="ERROR",
                message="label syntax errors found.",
                observed="syntax_failures=%d" % syntax_failures,
                expected="syntax_failures=0",
            ))

    # -- CATEGORY 5: label semantics ----------------------------------------

    def _e0_label_semantics(self):
        root = self.dataset_root
        semantic_failures = 0
        person_stats = {s: {"files": 0, "instances": 0, "widths": [],
                            "heights": [], "areas": []} for s in SPLIT_NAMES}
        for split in SPLIT_NAMES:
            labels_dir = root / split / "labels"
            label_files = [p for p in _list_files(labels_dir) if _is_label(p.name)]
            for path in sorted(label_files, key=lambda p: p.name):
                rel = path.relative_to(root)
                for lineno, raw in _read_label_lines(path):
                    fields = raw.split()
                    if len(fields) != 5:
                        continue
                    class_field = fields[0]
                    try:
                        class_id = int(class_field)
                    except ValueError:
                        semantic_failures += 1
                        self.report.add(CheckResult(
                            check_id="E01", category="LABEL_SEMANTICS",
                            status="FAIL", severity="ERROR",
                            message="class id is not an integer.",
                            split=split, file=str(rel), line=lineno,
                            observed="class_id=%r" % class_field,
                            expected="integer class id",
                        ))
                        continue
                    if class_id not in EXPECTED_CLASS_IDS:
                        semantic_failures += 1
                        self.report.add(CheckResult(
                            check_id="E02", category="LABEL_SEMANTICS",
                            status="FAIL", severity="ERROR",
                            message="class id %d is not one of %s."
                            % (class_id, list(EXPECTED_CLASS_IDS)),
                            split=split, file=str(rel), line=lineno,
                            observed=class_id, expected=list(EXPECTED_CLASS_IDS),
                        ))
                        continue
                    try:
                        cx = float(fields[1])
                        cy = float(fields[2])
                        w = float(fields[3])
                        h = float(fields[4])
                    except ValueError:
                        semantic_failures += 1
                        self.report.add(CheckResult(
                            check_id="E03", category="LABEL_SEMANTICS",
                            status="FAIL", severity="ERROR",
                            message="coordinate is not a floating-point number.",
                            split=split, file=str(rel), line=lineno,
                            observed="coords=%r" % (fields[1:5],),
                            expected="four floating-point numbers",
                        ))
                        continue
                    for cid, name, value in (
                        ("E04", "cx", cx), ("E05", "cy", cy),
                        ("E06", "w", w), ("E07", "h", h),
                    ):
                        if not (0.0 <= value <= 1.0):
                            semantic_failures += 1
                            self.report.add(CheckResult(
                                check_id=cid, category="LABEL_SEMANTICS",
                                status="FAIL", severity="ERROR",
                                message="%s is outside [0, 1]." % name,
                                split=split, file=str(rel), line=lineno,
                                observed="%s=%r" % (name, value),
                                expected="0.0 <= %s <= 1.0" % name,
                            ))
                    if w <= 0.0:
                        semantic_failures += 1
                        self.report.add(CheckResult(
                            check_id="E08", category="LABEL_SEMANTICS",
                            status="FAIL", severity="ERROR",
                            message="width must be greater than 0.",
                            split=split, file=str(rel), line=lineno,
                            observed="w=%r" % w, expected="w > 0",
                        ))
                    if h <= 0.0:
                        semantic_failures += 1
                        self.report.add(CheckResult(
                            check_id="E09", category="LABEL_SEMANTICS",
                            status="FAIL", severity="ERROR",
                            message="height must be greater than 0.",
                            split=split, file=str(rel), line=lineno,
                            observed="h=%r" % h, expected="h > 0",
                        ))
                    if cx - w / 2.0 < 0.0:
                        semantic_failures += 1
                        self.report.add(CheckResult(
                            check_id="E10", category="LABEL_SEMANTICS",
                            status="FAIL", severity="ERROR",
                            message="bounding box left edge is outside the image.",
                            split=split, file=str(rel), line=lineno,
                            observed="cx-w/2=%r" % (cx - w / 2.0),
                            expected="cx - w/2 >= 0",
                        ))
                    if cx + w / 2.0 > 1.0:
                        semantic_failures += 1
                        self.report.add(CheckResult(
                            check_id="E11", category="LABEL_SEMANTICS",
                            status="FAIL", severity="ERROR",
                            message="bounding box right edge is outside the image.",
                            split=split, file=str(rel), line=lineno,
                            observed="cx+w/2=%r" % (cx + w / 2.0),
                            expected="cx + w/2 <= 1",
                        ))
                    if cy - h / 2.0 < 0.0:
                        semantic_failures += 1
                        self.report.add(CheckResult(
                            check_id="E10", category="LABEL_SEMANTICS",
                            status="FAIL", severity="ERROR",
                            message="bounding box top edge is outside the image.",
                            split=split, file=str(rel), line=lineno,
                            observed="cy-h/2=%r" % (cy - h / 2.0),
                            expected="cy - h/2 >= 0",
                        ))
                    if cy + h / 2.0 > 1.0:
                        semantic_failures += 1
                        self.report.add(CheckResult(
                            check_id="E11", category="LABEL_SEMANTICS",
                            status="FAIL", severity="ERROR",
                            message="bounding box bottom edge is outside the image.",
                            split=split, file=str(rel), line=lineno,
                            observed="cy+h/2=%r" % (cy + h / 2.0),
                            expected="cy + h/2 <= 1",
                        ))
                    if class_id == 3:
                        stats = person_stats[split]
                        stats["instances"] += 1
                        stats["widths"].append(w)
                        stats["heights"].append(h)
                        stats["areas"].append(w * h)
        if semantic_failures == 0:
            self.report.add(CheckResult(
                check_id="E00", category="LABEL_SEMANTICS", status="PASS",
                severity="INFO",
                message="all annotations are semantically valid.",
                observed="semantic_failures=0",
            ))
        else:
            self.report.add(CheckResult(
                check_id="E00", category="LABEL_SEMANTICS", status="FAIL",
                severity="ERROR",
                message="label semantic errors found.",
                observed="semantic_failures=%d" % semantic_failures,
                expected="semantic_failures=0",
            ))
        self.report.person_stats = self._summarize_person_stats(person_stats)
        self._person_statistics()

    def _person_statistics(self):
        """Diagnostic class-3 bbox statistics.

        Reported for every non-empty label line whose first field is the
        class id 3 and which carries at least four coordinate fields. The
        bounding box is read from the first four coordinate fields; any
        trailing tracking data is ignored. These are diagnostic statistics
        only and are not claims about detection quality.
        """
        root = self.dataset_root
        raw = {s: {"files": 0, "instances": 0, "widths": [],
                    "heights": [], "areas": []} for s in SPLIT_NAMES}
        for split in SPLIT_NAMES:
            labels_dir = root / split / "labels"
            label_files = [p for p in _list_files(labels_dir) if _is_label(p.name)]
            for path in sorted(label_files, key=lambda p: p.name):
                seen = set()
                for lineno, raw_line in _read_label_lines(path):
                    fields = raw_line.split()
                    if len(fields) < 5:
                        continue
                    if fields[0] != "3":
                        continue
                    try:
                        cx = float(fields[1])
                        cy = float(fields[2])
                        w = float(fields[3])
                        h = float(fields[4])
                    except ValueError:
                        continue
                    stats = raw[split]
                    stats["instances"] += 1
                    stats["widths"].append(w)
                    stats["heights"].append(h)
                    stats["areas"].append(w * h)
                    seen.add(path)
                raw[split]["files"] += len(seen)
        self.report.person_stats = self._summarize_person_stats(raw)

    @staticmethod
    def _summarize_person_stats(raw):
        result = {}
        for split, stats in raw.items():
            widths = stats["widths"]
            heights = stats["heights"]
            areas = stats["areas"]
            result[split] = {
                "files_with_class_3": stats["files"],
                "instances": stats["instances"],
                "min_width": min(widths) if widths else None,
                "max_width": max(widths) if widths else None,
                "mean_width": (sum(widths) / len(widths)) if widths else None,
                "min_height": min(heights) if heights else None,
                "max_height": max(heights) if heights else None,
                "mean_height": (sum(heights) / len(heights)) if heights else None,
                "min_area": min(areas) if areas else None,
                "max_area": max(areas) if areas else None,
                "mean_area": (sum(areas) / len(areas)) if areas else None,
            }
        return result

    # -- CATEGORY 6: split integrity ----------------------------------------

    def _f0_split_integrity(self):
        root = self.dataset_root
        stem_to_splits = {}
        for split in SPLIT_NAMES:
            images_dir = root / split / "images"
            for path in _list_files(images_dir):
                if _is_image(path.name):
                    stem_to_splits.setdefault(path.stem, []).append(split)
        conflicts = sorted(
            (stem, splits) for stem, splits in stem_to_splits.items()
            if len(set(splits)) > 1
        )
        if not conflicts:
            self.report.add(CheckResult(
                check_id="F01_SPLIT", category="SPLIT_INTEGRITY", status="PASS",
                severity="INFO",
                message="no stem appears in more than one split.",
                observed="conflicting_stems=0",
            ))
        else:
            self.report.add(CheckResult(
                check_id="F01_SPLIT", category="SPLIT_INTEGRITY", status="FAIL",
                severity="ERROR",
                message="stems appear in more than one split.",
                observed="conflicting_stems=%d" % len(conflicts),
                expected="conflicting_stems=0",
            ))
            for stem, splits in conflicts:
                self.report.add(CheckResult(
                    check_id="F02_SPLIT", category="SPLIT_INTEGRITY", status="FAIL",
                    severity="ERROR",
                    message="stem %r appears in splits %s." % (stem, sorted(splits)),
                    file=stem, observed=sorted(splits), expected="single split",
                ))

    # -- CATEGORY 7: image validity -----------------------------------------

    def _v0_image_validity(self):
        root = self.dataset_root
        decode_failures = 0
        decoded_count = 0
        for split in SPLIT_NAMES:
            images_dir = root / split / "images"
            image_files = [p for p in _list_files(images_dir) if _is_image(p.name)]
            for path in sorted(image_files, key=lambda p: p.name):
                rel = path.relative_to(root)
                size = None
                try:
                    size = path.stat().st_size
                except OSError:
                    pass
                if size is None or size <= 0:
                    decode_failures += 1
                    self.report.add(CheckResult(
                        check_id="V01", category="IMAGE_VALIDITY", status="FAIL",
                        severity="ERROR",
                        message="image file size is not greater than 0.",
                        split=split, file=str(rel), observed=size,
                        expected="file_size > 0",
                    ))
                    continue
                if _PILImage is None:
                    self.report.add(CheckResult(
                        check_id="V02", category="IMAGE_VALIDITY",
                        status="NOT_VERIFIED", severity="WARNING",
                        message="Pillow is not available; image decode not verified.",
                        split=split, file=str(rel),
                    ))
                    continue
                try:
                    with open(path, "rb") as fh:
                        img = _PILImage.open(fh)
                        img.load()
                        width, height = img.size
                        data = img.tobytes()
                    decoded_count += 1
                except Exception as exc:
                    decode_failures += 1
                    self.report.add(CheckResult(
                        check_id="V02", category="IMAGE_VALIDITY", status="FAIL",
                        severity="ERROR",
                        message="image could not be decoded: %s: %s"
                        % (type(exc).__name__, exc),
                        split=split, file=str(rel),
                        observed="decode_error", expected="decodable image",
                    ))
                    continue
                if width <= 0:
                    decode_failures += 1
                    self.report.add(CheckResult(
                        check_id="V03", category="IMAGE_VALIDITY", status="FAIL",
                        severity="ERROR",
                        message="decoded width is not greater than 0.",
                        split=split, file=str(rel), observed=width,
                        expected="width > 0",
                    ))
                if height <= 0:
                    decode_failures += 1
                    self.report.add(CheckResult(
                        check_id="V04", category="IMAGE_VALIDITY", status="FAIL",
                        severity="ERROR",
                        message="decoded height is not greater than 0.",
                        split=split, file=str(rel), observed=height,
                        expected="height > 0",
                    ))
                if not data:
                    decode_failures += 1
                    self.report.add(CheckResult(
                        check_id="V05", category="IMAGE_VALIDITY", status="FAIL",
                        severity="ERROR",
                        message="decoded image data is empty.",
                        split=split, file=str(rel),
                        observed="data_len=0", expected="non-empty image data",
                    ))
        if decode_failures == 0:
            self.report.add(CheckResult(
                check_id="V00", category="IMAGE_VALIDITY", status="PASS",
                severity="INFO",
                message="all images passed size, decode, dimension, and "
                        "non-empty-data checks.",
                observed="decoded=%d failures=0" % decoded_count,
            ))
        else:
            self.report.add(CheckResult(
                check_id="V00", category="IMAGE_VALIDITY", status="FAIL",
                severity="ERROR",
                message="image validity checks failed.",
                observed="failures=%d decoded=%d" % (decode_failures, decoded_count),
                expected="failures=0",
            ))

    # -- CATEGORY 9: empty label files --------------------------------------

    def _empty_label_report(self):
        total_empty = 0
        for split in SPLIT_NAMES:
            files = sorted(self.report.empty_label_stats.get(split, []))
            total_empty += len(files)
            for rel in files:
                self.report.add(CheckResult(
                    check_id="EMPTY01", category="EMPTY_LABEL", status="WARN",
                    severity="WARNING",
                    message="empty label file (no annotations).",
                    split=split, file=rel, observed="annotation_count=0",
                    expected="EMPTY_LABEL_POLICY=%s" % EMPTY_LABEL_POLICY,
                ))
        if total_empty == 0:
            self.report.add(CheckResult(
                check_id="EMPTY00", category="EMPTY_LABEL", status="PASS",
                severity="INFO",
                message="no empty label files found.",
                observed="empty_label_count=0",
            ))
        else:
            self.report.add(CheckResult(
                check_id="EMPTY00", category="EMPTY_LABEL", status="WARN",
                severity="WARNING",
                message="empty label files detected.",
                observed="empty_label_count=%d" % total_empty,
                expected="EMPTY_LABEL_POLICY=%s" % EMPTY_LABEL_POLICY,
            ))

    # -- CATEGORY 10: roboflow metadata -------------------------------------

    def _roboflow_metadata(self):
        root = self.dataset_root
        yaml_path = root / "data.yaml"
        if not yaml_path.is_file() or yaml is None:
            self.report.roboflow_metadata = False
            self.report.add(CheckResult(
                check_id="ROBO00", category="ROBOfLOW_METADATA", status="NOT_VERIFIED",
                severity="WARNING",
                message="data.yaml unavailable; Roboflow metadata presence not verified.",
            ))
            return
        try:
            with open(yaml_path, "r", encoding="utf-8") as fh:
                config = yaml.safe_load(fh) or {}
        except Exception:
            self.report.roboflow_metadata = False
            self.report.add(CheckResult(
                check_id="ROBO00", category="ROBOfLOW_METADATA", status="NOT_VERIFIED",
                severity="WARNING",
                message="data.yaml unreadable; Roboflow metadata presence not verified.",
            ))
            return
        present = isinstance(config, dict) and isinstance(config.get("roboflow"), dict)
        self.report.roboflow_metadata = present
        self.report.add(CheckResult(
            check_id="ROBO00", category="ROBOfLOW_METADATA",
            status="PASS" if present else "WARN",
            severity="INFO",
            message="Roboflow metadata block present." if present
                    else "no Roboflow metadata block found in data.yaml.",
            observed=present, expected="informational only",
        ))

    # -- CATEGORY 11: isolation checks --------------------------------------

    def _isolation_checks(self):
        root = self.dataset_root
        for target in ISOLATION_TARGETS:
            resolved = _safe_resolve(Path(target), _repo_root())
            inside = False
            try:
                resolved.relative_to(root)
                inside = True
            except ValueError:
                inside = False
            self.report.isolation_status[target] = not inside
            if inside:
                self.report.add(CheckResult(
                    check_id="ISOL01", category="ISOLATION", status="FAIL",
                    severity="ERROR",
                    message="canonical dataset path resolves into %s." % target,
                    observed=str(resolved), expected="outside canonical dataset",
                ))
            else:
                self.report.add(CheckResult(
                    check_id="ISOL01", category="ISOLATION", status="PASS",
                    severity="INFO",
                    message="canonical dataset does not resolve into %s." % target,
                    observed=str(resolved),
                ))


# ---------------------------------------------------------------------------
# Module-level helpers (referenced by the validator methods above)
# ---------------------------------------------------------------------------

def _is_int(value):
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    if isinstance(value, str):
        try:
            int(value)
            return True
        except ValueError:
            return False
    return False


def _is_float(value):
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        try:
            float(value)
            return True
        except ValueError:
            return False
    return False


# ---------------------------------------------------------------------------
# Report rendering
# ---------------------------------------------------------------------------

def _fmt(value):
    if isinstance(value, float):
        return "%.6g" % value
    return str(value)


def render_report(report):
    lines = []
    lines.append("=" * 72)
    lines.append("MY-FIRST-PROJECT-4 DATASET VALIDATOR REPORT")
    lines.append("=" * 72)
    lines.append("Dataset root: %s" % report.dataset_root)
    lines.append("Overall status: %s" % report.overall_status)
    lines.append("")

    lines.append("1. CONFIGURATION SUMMARY")
    for cid in ("C01", "C02", "C03", "C04", "C05", "C06", "C07", "C08", "C09", "C10", "C11"):
        for c in report.checks:
            if c.check_id == cid and c.category == "CONFIGURATION":
                lines.append("  [%-5s] %s" % (c.status, c.message))
                break
    lines.append("")

    lines.append("2. FILE STRUCTURE SUMMARY")
    for cid in ("F01", "F02", "F03", "F04", "F05", "F06", "F07", "F08", "F09"):
        for c in report.checks:
            if c.check_id == cid and c.category == "FILE_STRUCTURE":
                lines.append("  [%-5s] %s" % (c.status, c.message))
                break
    lines.append("")

    lines.append("3. IMAGE/LABEL PAIRING SUMMARY")
    for c in report.checks:
        if c.category == "PAIRING" and c.check_id in ("P01", "P02", "P03", "P04", "P05", "P06", "P07"):
            if c.check_id == "P01":
                lines.append("  [%-5s] %s" % (c.status, c.message))
    lines.append("  per-split image counts: %s" % report.per_split_image_counts)
    lines.append("  per-split label counts: %s" % report.per_split_label_counts)
    lines.append("")

    lines.append("4. LABEL SYNTAX SUMMARY")
    for c in report.checks:
        if c.category == "LABEL_SYNTAX" and c.check_id in ("S04", "S05"):
            lines.append("  [%-5s] %s" % (c.status, c.message))
    lines.append("")

    lines.append("5. LABEL SEMANTICS SUMMARY")
    for c in report.checks:
        if c.category == "LABEL_SEMANTICS" and c.check_id == "E00":
            lines.append("  [%-5s] %s" % (c.status, c.message))
    lines.append("")

    lines.append("6. SPLIT INTEGRITY SUMMARY")
    for c in report.checks:
        if c.category == "SPLIT_INTEGRITY" and c.check_id in ("F01_SPLIT", "F02_SPLIT"):
            if c.check_id == "F01_SPLIT":
                lines.append("  [%-5s] %s" % (c.status, c.message))
    lines.append("")

    lines.append("7. IMAGE VALIDITY SUMMARY")
    for c in report.checks:
        if c.category == "IMAGE_VALIDITY" and c.check_id in ("V00", "V01", "V02", "V03", "V04", "V05"):
            if c.check_id == "V00":
                lines.append("  [%-5s] %s" % (c.status, c.message))
    lines.append("")

    lines.append("8. PERSON STATISTICS (diagnostic only)")
    for split in SPLIT_NAMES:
        stats = report.person_stats.get(split, {})
        lines.append("  %s:" % split)
        lines.append("    files_with_class_3: %s" % stats.get("files_with_class_3"))
        lines.append("    instances: %s" % stats.get("instances"))
        lines.append("    min_width: %s  max_width: %s  mean_width: %s"
                     % (_fmt(stats.get("min_width")), _fmt(stats.get("max_width")),
                        _fmt(stats.get("mean_width"))))
        lines.append("    min_height: %s  max_height: %s  mean_height: %s"
                     % (_fmt(stats.get("min_height")), _fmt(stats.get("max_height")),
                        _fmt(stats.get("mean_height"))))
        lines.append("    min_area: %s  max_area: %s  mean_area: %s"
                     % (_fmt(stats.get("min_area")), _fmt(stats.get("max_area")),
                        _fmt(stats.get("mean_area"))))
    lines.append("")

    lines.append("9. EMPTY LABEL STATISTICS")
    lines.append("  EMPTY_LABEL_POLICY: %s" % EMPTY_LABEL_POLICY)
    for split in SPLIT_NAMES:
        files = sorted(report.empty_label_stats.get(split, []))
        lines.append("  %s empty labels: %d" % (split, len(files)))
        for rel in files:
            lines.append("    - %s" % rel)
    lines.append("")

    lines.append("10. ROBOfLOW METADATA STATUS")
    lines.append("  present: %s" % report.roboflow_metadata)
    for c in report.checks:
        if c.category == "ROBOfLOW_METADATA" and c.check_id == "ROBO00":
            lines.append("  [%-5s] %s" % (c.status, c.message))
            break
    lines.append("")

    lines.append("11. ISOLATION STATUS")
    for target, ok in report.isolation_status.items():
        lines.append("  %s: %s" % (target, "outside canonical dataset" if ok else "INSIDE"))
    lines.append("")

    lines.append("12. DETAILED FAILURES")
    failures = sorted(report.errors(), key=lambda c: (c.category, c.check_id, c.file or ""))
    if not failures:
        lines.append("  none")
    for c in failures:
        lines.append("  [%s] %s %s" % (c.check_id, c.category, c.message))
        if c.file:
            lines.append("    file=%s" % c.file)
        if c.line is not None:
            lines.append("    line=%s" % c.line)
        if c.observed is not None:
            lines.append("    observed=%s" % _fmt(c.observed))
        if c.expected is not None:
            lines.append("    expected=%s" % _fmt(c.expected))
    lines.append("")

    lines.append("13. WARNINGS")
    warns = sorted(report.warnings(), key=lambda c: (c.category, c.check_id, c.file or ""))
    if not warns:
        lines.append("  none")
    for c in warns:
        lines.append("  [%s] %s %s" % (c.check_id, c.category, c.message))
        if c.file:
            lines.append("    file=%s" % c.file)
    lines.append("")

    lines.append("14. INFORMATIONAL STATISTICS")
    infos = sorted(report.infos(), key=lambda c: (c.category, c.check_id))
    for c in infos:
        lines.append("  [%s] %s %s" % (c.check_id, c.category, c.message))
    lines.append("")
    lines.append("=" * 72)
    lines.append("ERROR_COUNT=%d  WARNING_COUNT=%d  INFO_COUNT=%d"
                 % (len(report.errors()), len(report.warnings()), len(report.infos())))
    lines.append("EXIT_CODE=%d" % report.exit_code())
    lines.append("=" * 72)
    return "\n".join(lines)


def validate_dataset(dataset_root=None):
    validator = DatasetValidator(dataset_root)
    return validator.run()

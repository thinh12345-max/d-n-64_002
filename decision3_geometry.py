"""Decision 3 geometry layer (isolated, deterministic, no-video, no-model).

Canonical geometry is stored in native Video 3 coordinates:

    resolution : 1280 x 720
    origin     : top-left (0, 0)
    x          : increases rightward, 0..1279
    y          : increases downward,  0..719

These native coordinates are canonical and immutable. They are never
rounded, clamped, rewritten, or replaced by transformed values.

Evaluation is performed in the Ground Truth / pipeline coordinate space:

    resolution : 1020 x 500

via the ratified dimension-ratio mapping:

    x_gt = x_native * 1020 / 1280
    y_gt = y_native * 500 / 720

Transformed polygon vertices remain continuous floating-point values.
No rounding and no clamping is applied anywhere in this module.
"""

from typing import Tuple, List

# ---------------------------------------------------------------------------
# Region identifiers (stable strings; no enums, no classes).
# ---------------------------------------------------------------------------
APPROACH_A = "APPROACH_A"
APPROACH_B = "APPROACH_B"
JUNCTION = "JUNCTION"
NONE = "NONE"

# ---------------------------------------------------------------------------
# Canonical native polygons (Video 3 native resolution 1280 x 720).
# These are the sole source of truth for Decision 3 canonical geometry.
# ---------------------------------------------------------------------------
APPROACH_A_NATIVE: List[Tuple[int, int]] = [
    (0, 365),    # A1
    (300, 365),   # A2
    (1279, 420),  # A3
    (1279, 719),  # A4
    (650, 719),   # A5
    (0, 719),     # A6
]

APPROACH_B_NATIVE: List[Tuple[int, int]] = [
    (390, 175),   # B1
    (520, 185),   # B2
    (850, 325),   # B3
    (720, 365),   # B4
]

JUNCTION_NATIVE: List[Tuple[int, int]] = [
    (450, 405),   # J1
    (720, 350),   # J2
    (950, 455),   # J3
    (1030, 405),  # J4
]

# Ratified dimension-ratio mapping factors (native 1280x720 -> GT 1020x500).
_SCALE_X = 1020 / 1280
_SCALE_Y = 500 / 720


def to_gt(point: Tuple[int, int]) -> Tuple[float, float]:
    """Transform a native Video 3 point into GT 1020x500 space.

    x_gt = x_native * 1020 / 1280
    y_gt = y_native * 500 / 720

    The result is a continuous floating-point coordinate. No rounding
    and no clamping is applied.
    """
    x_native, y_native = point
    return (x_native * _SCALE_X, y_native * _SCALE_Y)


def from_gt(point: Tuple[float, float]) -> Tuple[float, float]:
    """Recover a native 1280x720 coordinate from a GT 1020x500 coordinate.

    Inverse of the ratified A2 dimension-ratio mapping:

        x_native = x_gt * 1280 / 1020
        y_native = y_gt * 720 / 500

    The Decision 3 input path derives its observation point (the bbox
    geometric center) in GT space and recovers the equivalent native
    coordinate here before calling classify_decision3(). Float arithmetic
    is preserved end-to-end: no int(), no round(), no clamping.
    """
    x_gt, y_gt = point
    return (x_gt / _SCALE_X, y_gt / _SCALE_Y)


def transform_polygon(polygon: List[Tuple[int, int]]) -> List[Tuple[float, float]]:
    """Transform every vertex of a native polygon into GT space.

    Returns a list of (float, float) vertices. The canonical native
    polygon is not modified.
    """
    return [to_gt(vertex) for vertex in polygon]


def point_in_polygon(point: Tuple[float, float],
                     polygon: List[Tuple[float, float]]) -> bool:
    """Ray-casting point-in-polygon test over floating-point coordinates.

    Works on continuous (float) polygon vertices and continuous (float)
    query points. On-boundary points are treated as inside, which keeps
    boundary classification deterministic across repeated calls.
    """
    x, y = point
    inside = False
    n = len(polygon)
    j = n - 1
    for i in range(n):
        xi, yi = polygon[i]
        xj, yj = polygon[j]
        # Does the edge straddle the horizontal ray at y?
        if ((yi > y) != (yj > y)):
            x_intersect = xi + (y - yi) * (xj - xi) / (yj - yi)
            if x < x_intersect:
                inside = not inside
        j = i
    return inside


def classify_decision3(point: Tuple[int, int]) -> str:
    """Classify a native point into a Decision 3 region.

    Evaluation order enforces Junction precedence over Approach A:

        JUNCTION > APPROACH_A > APPROACH_B > NONE

    This implements "Effective Approach A = Candidate Approach A - Junction
    Zone" semantically through precedence, without editing the canonical
    Approach A polygon.
    """
    gt_point = to_gt(point)

    junction_gt = transform_polygon(JUNCTION_NATIVE)
    if point_in_polygon(gt_point, junction_gt):
        return JUNCTION

    approach_a_gt = transform_polygon(APPROACH_A_NATIVE)
    if point_in_polygon(gt_point, approach_a_gt):
        return APPROACH_A

    approach_b_gt = transform_polygon(APPROACH_B_NATIVE)
    if point_in_polygon(gt_point, approach_b_gt):
        return APPROACH_B

    return NONE
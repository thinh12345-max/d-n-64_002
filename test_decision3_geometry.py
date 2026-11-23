"""Deterministic tests for the isolated Decision 3 geometry layer.

No video, no YOLO, no ByteTrack, no camera input, no network, no
randomness, no timing. Exercises only the geometry functions in
``decision3_geometry.py``.
"""

import pytest

from decision3_geometry import (
    APPROACH_A,
    APPROACH_B,
    JUNCTION,
    NONE,
    APPROACH_A_NATIVE,
    APPROACH_B_NATIVE,
    JUNCTION_NATIVE,
    to_gt,
    transform_polygon,
    point_in_polygon,
    classify_decision3,
)

# Observation-point helpers from the Decision 3 input path in main.py.
from main import decision3_observation_point

# ---------------------------------------------------------------------------
# 1. APPROACH A interior
# ---------------------------------------------------------------------------
def test_approach_a_interior():
    # native (100, 550) -> GT (80, 381.944...); clearly inside Approach A.
    assert classify_decision3((100, 550)) == APPROACH_A


# ---------------------------------------------------------------------------
# 2. APPROACH B interior
# ---------------------------------------------------------------------------
def test_approach_b_interior():
    # native (600, 250) -> GT (478.125, 173.611...); clearly inside Approach B.
    assert classify_decision3((600, 250)) == APPROACH_B


# ---------------------------------------------------------------------------
# 3. JUNCTION interior
# ---------------------------------------------------------------------------
def test_junction_interior():
    # native (700, 400) -> GT (557.8125, 277.777...); clearly inside Junction.
    assert classify_decision3((700, 400)) == JUNCTION


# ---------------------------------------------------------------------------
# 4. JUNCTION precedence over Approach A (mandatory carve-out test)
# ---------------------------------------------------------------------------
def test_junction_precedence_over_approach_a():
    # native (900, 420) lies inside BOTH Approach A and the Junction region.
    # Junction must win.
    assert classify_decision3((900, 420)) == JUNCTION


# ---------------------------------------------------------------------------
# 5. NONE
# ---------------------------------------------------------------------------
def test_none_outside_all_regions():
    # native (100, 100) -> GT (80, 69.444...); above every region.
    assert classify_decision3((100, 100)) == NONE


# ---------------------------------------------------------------------------
# 6. Boundary determinism - B4
# ---------------------------------------------------------------------------
def test_boundary_determinism_b4():
    native = (720, 365)
    results = [classify_decision3(native) for _ in range(100)]
    assert len(set(results)) == 1


# ---------------------------------------------------------------------------
# 7. Boundary determinism - J2
# ---------------------------------------------------------------------------
def test_boundary_determinism_j2():
    native = (720, 350)
    results = [classify_decision3(native) for _ in range(100)]
    assert len(set(results)) == 1


# ---------------------------------------------------------------------------
# 8. Extreme native border vertex (A4)
# ---------------------------------------------------------------------------
def test_extreme_border_vertex_a4():
    result = to_gt((1279, 719))

    # Must be floating-point, not integer-coerced.
    assert isinstance(result[0], float)
    assert isinstance(result[1], float)

    # Continuous values, not snapped to integer pixel indices.
    assert result[0] == pytest.approx(1019.203125)
    assert result[1] == pytest.approx(499.3055555555555)

    # Must NOT be clamped to the maximum integer GT index.
    assert result != (1019, 499)
    assert result[0] > 1019
    assert result[1] > 499


# ---------------------------------------------------------------------------
# 9. All 14 canonical vertices unchanged
# ---------------------------------------------------------------------------
EXPECTED_NATIVE = {
    "APPROACH_A": [
        (0, 365), (300, 365), (1279, 420),
        (1279, 719), (650, 719), (0, 719),
    ],
    "APPROACH_B": [
        (390, 175), (520, 185), (850, 325), (720, 365),
    ],
    "JUNCTION": [
        (450, 405), (720, 350), (950, 455), (1030, 405),
    ],
}


def test_canonical_vertices_unchanged():
    assert APPROACH_A_NATIVE == EXPECTED_NATIVE["APPROACH_A"]
    assert APPROACH_B_NATIVE == EXPECTED_NATIVE["APPROACH_B"]
    assert JUNCTION_NATIVE == EXPECTED_NATIVE["JUNCTION"]


# ---------------------------------------------------------------------------
# 10. Float preservation across every transformed vertex
# ---------------------------------------------------------------------------
def test_float_preservation():
    for polygon in (APPROACH_A_NATIVE, APPROACH_B_NATIVE, JUNCTION_NATIVE):
        transformed = transform_polygon(polygon)
        assert len(transformed) == len(polygon)
        for vertex in transformed:
            assert isinstance(vertex[0], float)
            assert isinstance(vertex[1], float)


# ---------------------------------------------------------------------------
# 11. Transformation determinism
# ---------------------------------------------------------------------------
def test_transformation_determinism():
    native = (1279, 719)
    first = to_gt(native)
    for _ in range(100):
        assert to_gt(native) == first


# ---------------------------------------------------------------------------
# 12. Polygon transformation determinism
# ---------------------------------------------------------------------------
def test_polygon_transformation_determinism():
    for polygon in (APPROACH_A_NATIVE, APPROACH_B_NATIVE, JUNCTION_NATIVE):
        first = transform_polygon(polygon)
        for _ in range(100):
            assert transform_polygon(polygon) == first


# ---------------------------------------------------------------------------
# 13. Canonical immutability - classification must not mutate native polygons
# ---------------------------------------------------------------------------
def test_canonical_immutability():
    snapshot_a = list(APPROACH_A_NATIVE)
    snapshot_b = list(APPROACH_B_NATIVE)
    snapshot_j = list(JUNCTION_NATIVE)

    for point in [(100, 550), (600, 250), (700, 400),
                  (900, 420), (100, 100), (720, 365), (720, 350),
                  (1279, 719), (0, 0), (1279, 0), (0, 719)]:
        classify_decision3(point)

    assert APPROACH_A_NATIVE == snapshot_a
    assert APPROACH_B_NATIVE == snapshot_b
    assert JUNCTION_NATIVE == snapshot_j


# ---------------------------------------------------------------------------
# Extra: transformation formula character-for-character
# ---------------------------------------------------------------------------
def test_transformation_formula():
    assert to_gt((1279, 719))[0] == 1279 * 1020 / 1280
    assert to_gt((1279, 719))[1] == 719 * 500 / 720
    assert to_gt((0, 0)) == (0.0, 0.0)
    assert to_gt((1280, 720)) == (1020.0, 500.0)  # full frame corner


# ---------------------------------------------------------------------------
# Extra: no integer coercion anywhere in the transform path
# ---------------------------------------------------------------------------
def test_no_integer_coercion_in_path():
    for polygon in (APPROACH_A_NATIVE, APPROACH_B_NATIVE, JUNCTION_NATIVE):
        transformed = transform_polygon(polygon)
        for vertex in transformed:
            assert type(vertex[0]) is float
            assert type(vertex[1]) is float
            assert not isinstance(vertex[0], int)
            assert not isinstance(vertex[1], int)
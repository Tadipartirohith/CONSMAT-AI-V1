"""Unit tests for BOM computation and 9-phase demand distribution."""
from app import bom

PER_SQFT = {"cement": 0.40, "steel": 0.004, "sand": 0.0816, "aggregate": 0.057, "bricks": 8.0}


def test_compute_bom_standard():
    total_area, totals = bom.compute_bom(1000, 2, "standard", PER_SQFT)
    assert total_area == 2000
    assert totals["cement"] == 800        # 2000*0.4, ceil
    assert totals["steel"] == 8.0         # 2000*0.004
    assert totals["bricks"] == 16000
    assert round(totals["sand"], 2) == 163.2
    assert round(totals["aggregate"], 2) == 114.0


def test_premium_multiplier():
    _, totals = bom.compute_bom(1000, 1, "premium", PER_SQFT)
    # cement: 1000*0.4*1.18 = 472
    assert totals["cement"] == 472


def test_phase_slice_masonry_is_bricks_heavy():
    _, totals = bom.compute_bom(1000, 2, "standard", PER_SQFT)
    slice4 = bom.phase_slice(totals, 4)  # masonry
    assert slice4["bricks"] == 16000            # all bricks in masonry
    assert slice4["cement"] == 120              # 800 * 0.15
    assert "steel" not in slice4                # steel has 0 weight in masonry


def test_phase_slice_rcc_has_steel():
    _, totals = bom.compute_bom(1000, 2, "standard", PER_SQFT)
    slice3 = bom.phase_slice(totals, 3)  # RCC superstructure
    assert slice3["steel"] == 3.6               # 8.0 * 0.45
    assert slice3["cement"] == 240              # 800 * 0.30


def test_phase_weights_sum_to_one():
    for mid, weights in bom.PHASE_WEIGHTS.items():
        assert abs(sum(weights.values()) - 1.0) < 1e-9, mid


def test_all_nine_phases_present():
    assert [p[0] for p in bom.PHASES] == list(range(1, 10))

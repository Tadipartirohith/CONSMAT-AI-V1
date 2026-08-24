"""BOQ comparison + normalization unit tests."""
from app import service


def test_compare_identical_is_zero():
    ce = [{"product_id": "cement-x", "total_qty": 100}, {"product_id": "steel-y", "total_qty": 5}]
    assert service.compare_boqs(ce, ce) == 0.0


def test_compare_flags_over_threshold():
    ce = [{"product_id": "cement-x", "total_qty": 100}]
    ext = [{"product_id": "cement-x", "total_qty": 110}]  # 10 / 110 ~= 9.09%
    diff = service.compare_boqs(ce, ext)
    assert diff > service_threshold()


def test_compare_within_threshold():
    ce = [{"product_id": "cement-x", "total_qty": 100}]
    ext = [{"product_id": "cement-x", "total_qty": 103}]  # 3 / 103 ~= 2.9%
    assert service.compare_boqs(ce, ext) < service_threshold()


def test_missing_product_counts_as_full_diff():
    ce = [{"product_id": "a", "total_qty": 10}, {"product_id": "b", "total_qty": 10}]
    ext = [{"product_id": "a", "total_qty": 10}]  # b missing -> 100%
    assert service.compare_boqs(ce, ext) == 100.0


def service_threshold():
    from app import models
    return models.BOQ_DIFF_THRESHOLD


def test_boq_norm_drops_empty_and_casts():
    rows = service._boq_norm([
        {"material_id": "cement", "product_id": "c1", "total_qty": "5", "phase_seq": "3"},
        {"material_id": "", "product_id": "", "total_qty": 9},  # dropped
    ])
    assert len(rows) == 1
    assert rows[0]["phase_seq"] == 3 and rows[0]["total_qty"] == 5.0

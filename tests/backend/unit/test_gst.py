"""
Unit tests — app.services.gst
================================
Covers: compute_gst_totals (intra-state, inter-state, mixed),
        grand_total, edge cases (zero, empty, unit_price×qty, rounding).
No database required.
"""
import pytest
from app.services.gst import compute_gst_totals, grand_total


# ── helpers ───────────────────────────────────────────────────────────────────

def item(amount=None, unit_price=None, quantity=None, gst_rate=None) -> dict:
    d = {}
    if amount is not None:
        d["amount"] = amount
    if unit_price is not None:
        d["unit_price"] = unit_price
    if quantity is not None:
        d["quantity"] = quantity
    if gst_rate is not None:
        d["gst_rate"] = gst_rate
    return d


# ── compute_gst_totals ────────────────────────────────────────────────────────

class TestComputeGSTTotals:

    # Empty / zero inputs
    def test_empty_line_items_returns_zeros(self):
        s, c, sg, ig = compute_gst_totals([], "MH", "MH")
        assert (s, c, sg, ig) == (0.0, 0.0, 0.0, 0.0)

    def test_none_line_items_returns_zeros(self):
        s, c, sg, ig = compute_gst_totals(None, "MH", "MH")
        assert (s, c, sg, ig) == (0.0, 0.0, 0.0, 0.0)

    def test_zero_amount_item(self):
        s, c, sg, ig = compute_gst_totals([item(amount=0)], "MH", "MH")
        assert s == 0.0 and c == 0.0 and sg == 0.0

    # Intra-state supply → CGST + SGST (no IGST)
    def test_intra_state_splits_tax_equally(self):
        # 1000 @ 18% = 180 total tax → CGST=90, SGST=90, IGST=0
        s, c, sg, ig = compute_gst_totals([item(amount=1000)], "MH", "MH")
        assert s == 1000.0
        assert c == 90.0
        assert sg == 90.0
        assert ig == 0.0

    def test_intra_state_multiple_items(self):
        items = [item(amount=500), item(amount=500)]
        s, c, sg, ig = compute_gst_totals(items, "KA", "KA")
        assert s == 1000.0
        assert c == 90.0
        assert sg == 90.0
        assert ig == 0.0

    # Inter-state supply → IGST only
    def test_inter_state_no_cgst_sgst(self):
        # 1000 @ 18% = 180 IGST
        s, c, sg, ig = compute_gst_totals([item(amount=1000)], "DL", "MH")
        assert s == 1000.0
        assert c == 0.0
        assert sg == 0.0
        assert ig == 180.0

    def test_inter_state_different_supply_states(self):
        s, c, sg, ig = compute_gst_totals([item(amount=2000)], "GJ", "TN")
        assert ig == pytest.approx(360.0, abs=0.01)

    # Custom GST rate
    def test_custom_gst_rate_5_percent(self):
        s, c, sg, ig = compute_gst_totals([item(amount=1000, gst_rate=5)], "MH", "MH")
        assert c == pytest.approx(25.0, abs=0.01)
        assert sg == pytest.approx(25.0, abs=0.01)

    def test_custom_gst_rate_28_percent(self):
        s, c, sg, ig = compute_gst_totals([item(amount=1000, gst_rate=28)], "MH", "MH")
        assert c == pytest.approx(140.0, abs=0.01)

    def test_zero_gst_rate(self):
        s, c, sg, ig = compute_gst_totals([item(amount=1000, gst_rate=0)], "MH", "MH")
        assert c == 0.0 and sg == 0.0 and ig == 0.0

    # unit_price × quantity path
    def test_unit_price_and_quantity(self):
        # 10 units × 100 each = 1000 subtotal
        s, c, sg, ig = compute_gst_totals([item(unit_price=100, quantity=10)], "MH", "MH")
        assert s == 1000.0
        assert c == 90.0

    def test_unit_price_default_quantity_one(self):
        s, c, sg, ig = compute_gst_totals([item(unit_price=500)], "MH", "MH")
        assert s == 500.0

    # Missing state codes → inter-state treatment
    def test_no_supply_state_code_is_inter_state(self):
        s, c, sg, ig = compute_gst_totals([item(amount=1000)], None, "MH")
        assert ig == 180.0 and c == 0.0

    def test_no_origin_state_code_is_inter_state(self):
        s, c, sg, ig = compute_gst_totals([item(amount=1000)], "MH", None)
        assert ig == 180.0 and c == 0.0

    # Rounding
    def test_rounding_to_two_decimal_places(self):
        # 333.33 @ 18% = 59.9994 → rounded to 60.00
        s, c, sg, ig = compute_gst_totals([item(amount=333.33)], "DL", "MH")
        # Result must have at most 2 decimal places
        assert round(ig, 2) == ig

    def test_multiple_items_different_rates(self):
        items = [
            item(amount=1000, gst_rate=18),
            item(amount=500, gst_rate=5),
        ]
        s, c, sg, ig = compute_gst_totals(items, "MH", "MH")
        assert s == 1500.0
        # 18% of 1000 = 180 → CGST 90; 5% of 500 = 25 → CGST 12.50
        assert c == pytest.approx(102.50, abs=0.01)


# ── grand_total ───────────────────────────────────────────────────────────────

class TestGrandTotal:
    def test_intra_state_grand_total(self):
        # subtotal=1000, cgst=90, sgst=90, igst=0 → 1180
        assert grand_total(1000.0, 90.0, 90.0, 0.0) == 1180.0

    def test_inter_state_grand_total(self):
        # subtotal=1000, cgst=0, sgst=0, igst=180 → 1180
        assert grand_total(1000.0, 0.0, 0.0, 180.0) == 1180.0

    def test_zero_inputs(self):
        assert grand_total(0.0, 0.0, 0.0, 0.0) == 0.0

    def test_rounded_to_two_decimal_places(self):
        result = grand_total(333.33, 29.99, 29.99, 0.0)
        assert round(result, 2) == result

    def test_grand_total_matches_compute_totals(self):
        items = [{"amount": 2000, "gst_rate": 18}]
        s, c, sg, ig = compute_gst_totals(items, "MH", "MH")
        gt = grand_total(s, c, sg, ig)
        assert gt == pytest.approx(2360.0, abs=0.01)

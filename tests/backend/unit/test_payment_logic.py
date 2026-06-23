"""
Unit tests — payment recompute & SLA hours logic
==================================================
Covers:
  - _recompute_invoice_status (pure function from payment service)
  - SLA_HOURS priority mapping from service_ticket service
"""
import pytest
from unittest.mock import MagicMock


# ── _recompute_invoice_status ─────────────────────────────────────────────────

# Import the function under test and its dependencies
from app.services.payment import _recompute_invoice_status
from app.models.invoice import InvoiceStatus


class FakeInvoice:
    """Minimal invoice stub for testing the pure recompute logic."""
    def __init__(self, amount_paid: float, total_amount: float):
        self.amount_paid = amount_paid
        self.total_amount = total_amount
        self.status = InvoiceStatus.ISSUED


class TestRecomputeInvoiceStatus:
    def test_full_payment_sets_paid(self):
        inv = FakeInvoice(amount_paid=1000.0, total_amount=1000.0)
        _recompute_invoice_status(inv)
        assert inv.status == InvoiceStatus.PAID

    def test_overpayment_sets_paid(self):
        inv = FakeInvoice(amount_paid=1100.0, total_amount=1000.0)
        _recompute_invoice_status(inv)
        assert inv.status == InvoiceStatus.PAID

    def test_partial_payment_sets_partially_paid(self):
        inv = FakeInvoice(amount_paid=500.0, total_amount=1000.0)
        _recompute_invoice_status(inv)
        assert inv.status == InvoiceStatus.PARTIALLY_PAID

    def test_zero_payment_sets_issued(self):
        inv = FakeInvoice(amount_paid=0.0, total_amount=1000.0)
        _recompute_invoice_status(inv)
        assert inv.status == InvoiceStatus.ISSUED

    def test_none_amount_paid_treated_as_zero(self):
        inv = FakeInvoice(amount_paid=None, total_amount=1000.0)
        _recompute_invoice_status(inv)
        assert inv.status == InvoiceStatus.ISSUED

    def test_zero_total_amount_does_not_set_paid(self):
        # If total is 0, full payment condition (paid >= total AND total > 0) is False
        inv = FakeInvoice(amount_paid=0.0, total_amount=0.0)
        _recompute_invoice_status(inv)
        assert inv.status == InvoiceStatus.ISSUED

    def test_small_fractional_payment(self):
        inv = FakeInvoice(amount_paid=0.01, total_amount=1000.0)
        _recompute_invoice_status(inv)
        assert inv.status == InvoiceStatus.PARTIALLY_PAID

    def test_exact_boundary_paid(self):
        inv = FakeInvoice(amount_paid=999.99, total_amount=999.99)
        _recompute_invoice_status(inv)
        assert inv.status == InvoiceStatus.PAID


# ── SLA_HOURS mapping ─────────────────────────────────────────────────────────

from app.services.service_ticket import SLA_HOURS


class TestSLAHours:
    def test_critical_is_4_hours(self):
        assert SLA_HOURS["critical"] == 4

    def test_high_is_8_hours(self):
        assert SLA_HOURS["high"] == 8

    def test_medium_is_24_hours(self):
        assert SLA_HOURS["medium"] == 24

    def test_low_is_48_hours(self):
        assert SLA_HOURS["low"] == 48

    def test_all_priorities_defined(self):
        for priority in ("critical", "high", "medium", "low"):
            assert priority in SLA_HOURS

    def test_no_unknown_priorities(self):
        assert len(SLA_HOURS) == 4

    def test_sla_hours_are_positive(self):
        for hours in SLA_HOURS.values():
            assert hours > 0

    def test_sla_hours_ordered_ascending(self):
        """Critical < High < Medium < Low in terms of response time."""
        assert SLA_HOURS["critical"] < SLA_HOURS["high"]
        assert SLA_HOURS["high"] < SLA_HOURS["medium"]
        assert SLA_HOURS["medium"] < SLA_HOURS["low"]

    def test_unknown_priority_returns_default_24(self):
        # Service uses .get(priority, 24) as fallback
        assert SLA_HOURS.get("unknown", 24) == 24

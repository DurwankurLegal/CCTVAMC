"""GST computation — shared by quotations and invoices.

CGST+SGST for intra-state supply, IGST for inter-state. All money math uses
``Decimal`` with 2-dp half-up rounding to avoid float drift on tax/totals.
"""
from __future__ import annotations

from decimal import Decimal, ROUND_HALF_UP

TWO_DP = Decimal("0.01")
DEFAULT_GST_RATE = Decimal("18.0")


def _d(value) -> Decimal:
    return Decimal(str(value if value is not None else 0))


def _round(value: Decimal) -> Decimal:
    return value.quantize(TWO_DP, rounding=ROUND_HALF_UP)


def compute_gst_totals(line_items: list, supply_state_code, origin_state_code):
    """Return (subtotal, cgst, sgst, igst) as floats (rounded to 2dp).

    ``line_items`` is a list of dicts with ``amount`` (or ``unit_price`` *
    ``quantity``) and optional ``gst_rate`` (percent).
    """
    subtotal = Decimal("0")
    cgst = sgst = igst = Decimal("0")
    is_intra = bool(supply_state_code and origin_state_code and supply_state_code == origin_state_code)

    for item in line_items or []:
        if item.get("amount") is not None:
            amt = _d(item.get("amount"))
        else:
            amt = _d(item.get("unit_price")) * _d(item.get("quantity", 1))
        rate = _d(item.get("gst_rate", DEFAULT_GST_RATE)) / Decimal("100")
        subtotal += amt
        tax = amt * rate
        if is_intra:
            half = tax / Decimal("2")
            cgst += half
            sgst += half
        else:
            igst += tax

    return (
        float(_round(subtotal)),
        float(_round(cgst)),
        float(_round(sgst)),
        float(_round(igst)),
    )


def grand_total(subtotal: float, cgst: float, sgst: float, igst: float) -> float:
    total = _d(subtotal) + _d(cgst) + _d(sgst) + _d(igst)
    return float(_round(total))

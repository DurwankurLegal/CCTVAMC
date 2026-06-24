"""
Unit tests — Phase 1 lifecycle logic (pure, no DB/HTTP)
=======================================================
Covers the pure decision logic and constants behind Phase 1:
  * tenant_block_reason() — the login/refresh gate decision
  * TRIAL_PERIOD_DAYS / trial-window defaulting
  * PLAN_LIMITS technician caps + enforce_limit's cap-lookup semantics
"""
from datetime import datetime, timezone, timedelta

import pytest
from app.services.auth import tenant_block_reason, _BLOCK_MESSAGES
from app.models.tenant import TenantStatus, PLAN_LIMITS, TRIAL_PERIOD_DAYS


NOW = datetime(2026, 6, 24, 12, 0, 0, tzinfo=timezone.utc)


# ── tenant_block_reason: status gating ───────────────────────────────────────

class TestTenantBlockReasonStatus:
    def test_active_tenant_allowed(self):
        assert tenant_block_reason("active", True, None, now=NOW) is None

    def test_suspended_blocked_inactive(self):
        assert tenant_block_reason("suspended", False, None, now=NOW) == "inactive"

    def test_cancelled_blocked_inactive(self):
        assert tenant_block_reason("cancelled", False, None, now=NOW) == "inactive"

    def test_active_status_but_deactivated_flag_blocked(self):
        # status says active but is_active=False → still blocked.
        assert tenant_block_reason("active", False, None, now=NOW) == "inactive"

    def test_suspended_takes_priority_even_if_is_active_true(self):
        assert tenant_block_reason("suspended", True, None, now=NOW) == "inactive"


# ── tenant_block_reason: trial window ────────────────────────────────────────

class TestTenantBlockReasonTrial:
    def test_trial_with_future_expiry_allowed(self):
        future = NOW + timedelta(days=3)
        assert tenant_block_reason("trial", True, future, now=NOW) is None

    def test_trial_with_past_expiry_blocked(self):
        past = NOW - timedelta(seconds=1)
        assert tenant_block_reason("trial", True, past, now=NOW) == "trial_expired"

    def test_trial_with_no_expiry_allowed(self):
        # No window set → not expired (defensive: never block on missing data).
        assert tenant_block_reason("trial", True, None, now=NOW) is None

    def test_trial_naive_datetime_treated_as_utc(self):
        # SQLite returns naive datetimes — must not raise and must compare as UTC.
        past_naive = (NOW - timedelta(days=1)).replace(tzinfo=None)
        assert tenant_block_reason("trial", True, past_naive, now=NOW) == "trial_expired"

    def test_trial_expiry_uses_now_default_when_omitted(self):
        # Past expiry with the real "now" default still blocks.
        past = datetime.now(timezone.utc) - timedelta(days=1)
        assert tenant_block_reason("trial", True, past) == "trial_expired"

    def test_expiry_ignored_for_non_trial_status(self):
        # An ACTIVE tenant with a stale trial_ends_at is NOT blocked.
        past = NOW - timedelta(days=10)
        assert tenant_block_reason("active", True, past, now=NOW) is None


# ── block-message mapping ────────────────────────────────────────────────────

class TestBlockMessages:
    def test_every_reason_has_a_message(self):
        for reason in ("inactive", "trial_expired"):
            assert reason in _BLOCK_MESSAGES
            assert _BLOCK_MESSAGES[reason]

    def test_messages_are_user_facing(self):
        assert "not active" in _BLOCK_MESSAGES["inactive"]
        assert "Trial" in _BLOCK_MESSAGES["trial_expired"]


# ── trial window constant ────────────────────────────────────────────────────

class TestTrialPeriod:
    def test_trial_period_is_positive(self):
        assert TRIAL_PERIOD_DAYS > 0

    def test_trial_period_is_fourteen_days(self):
        assert TRIAL_PERIOD_DAYS == 14


# ── plan-limit technician caps ───────────────────────────────────────────────

class TestTechnicianCaps:
    def test_every_plan_defines_max_technicians(self):
        for plan, limits in PLAN_LIMITS.items():
            assert "max_technicians" in limits, f"{plan} missing max_technicians"

    def test_starter_technician_cap(self):
        assert PLAN_LIMITS["starter"]["max_technicians"] == 3

    def test_growth_technician_cap_higher_than_starter(self):
        assert PLAN_LIMITS["growth"]["max_technicians"] > PLAN_LIMITS["starter"]["max_technicians"]

    def test_enterprise_technicians_unlimited(self):
        # 0 == unlimited by convention (see enforce_limit).
        assert PLAN_LIMITS["enterprise"]["max_technicians"] == 0

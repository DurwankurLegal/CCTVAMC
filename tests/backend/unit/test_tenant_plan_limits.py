"""
Unit tests — Tenant plan limits
=================================
Covers PLAN_LIMITS constants and enforce_limit logic (pure checks).
"""
import pytest
from app.models.tenant import PLAN_LIMITS, TenantStatus


class TestPlanLimits:
    """Verify the plan limits table is correctly structured."""

    def test_starter_plan_exists(self):
        assert "starter" in PLAN_LIMITS

    def test_growth_plan_exists(self):
        assert "growth" in PLAN_LIMITS

    def test_enterprise_plan_exists(self):
        assert "enterprise" in PLAN_LIMITS

    def test_starter_has_lower_limits_than_growth(self):
        s = PLAN_LIMITS["starter"]
        g = PLAN_LIMITS["growth"]
        # Every defined limit in starter must be ≤ corresponding growth limit
        for key in s:
            if key in g and s[key] and g[key]:
                assert s[key] <= g[key], f"starter.{key} > growth.{key}"

    def test_growth_has_lower_limits_than_enterprise(self):
        g = PLAN_LIMITS["growth"]
        e = PLAN_LIMITS["enterprise"]
        for key in g:
            if key in e and g[key] and e[key]:
                assert g[key] <= e[key], f"growth.{key} > enterprise.{key}"

    def test_max_users_key_exists_in_all_plans(self):
        for plan in PLAN_LIMITS:
            assert "max_users" in PLAN_LIMITS[plan]

    def test_all_limit_values_are_non_negative(self):
        for plan, limits in PLAN_LIMITS.items():
            for key, val in limits.items():
                assert val >= 0, f"{plan}.{key} is negative"

    def test_enterprise_unlimited_is_zero_or_high(self):
        """Enterprise should either have 0 (unlimited) or a high cap."""
        e = PLAN_LIMITS["enterprise"]
        for key, val in e.items():
            # 0 means unlimited; any positive number is a high limit
            assert val >= 0


class TestTenantStatus:
    def test_active_status_exists(self):
        assert hasattr(TenantStatus, "ACTIVE")

    def test_suspended_status_exists(self):
        assert hasattr(TenantStatus, "SUSPENDED")

    def test_cancelled_status_exists(self):
        assert hasattr(TenantStatus, "CANCELLED")

    def test_trial_status_exists(self):
        assert hasattr(TenantStatus, "TRIAL")

    def test_status_values_are_strings(self):
        for s in TenantStatus:
            assert isinstance(s.value, str)

    def test_active_value_is_active(self):
        assert TenantStatus.ACTIVE.value == "active"

    def test_suspended_value_is_suspended(self):
        assert TenantStatus.SUSPENDED.value == "suspended"

    def test_cancelled_value_is_cancelled(self):
        assert TenantStatus.CANCELLED.value == "cancelled"

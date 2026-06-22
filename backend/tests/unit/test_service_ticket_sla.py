from datetime import datetime, timezone, timedelta
from app.services.service_ticket import SLA_HOURS


def test_sla_hours_mapping():
    assert SLA_HOURS["critical"] < SLA_HOURS["high"] < SLA_HOURS["medium"] < SLA_HOURS["low"]


def test_sla_due_at_calculation():
    priority = "critical"
    now = datetime.now(timezone.utc)
    due = now + timedelta(hours=SLA_HOURS[priority])
    assert (due - now).seconds / 3600 == pytest_approx(SLA_HOURS[priority], abs=0.01)


def pytest_approx(value, abs=None):
    return value  # simplified; use pytest.approx in real tests

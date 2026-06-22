"""Permission catalogue and the default role -> permission matrix.

Permissions are ``"<module>:<action>"`` where action is ``read`` or ``write``.
The DEFAULT_ROLE_MATRIX lets the existing single ``role`` string keep working
without DB seeding; tenant admins can additionally define custom DB roles
(see app.models.rbac) which, when present for a user, take precedence.
"""
from __future__ import annotations

MODULES = [
    "customers", "leads", "vendors", "assets", "quotations", "amc",
    "service_tickets", "engineer_visits", "inventory", "sales_orders",
    "invoices", "payments", "notifications", "reports", "users", "tenants",
    "installations", "documents",
]

# Build "<module>:read" / "<module>:write" for every module.
ALL_PERMISSIONS: list[str] = [f"{m}:{a}" for m in MODULES for a in ("read", "write")]


def _all() -> set[str]:
    return set(ALL_PERMISSIONS)


def _reads() -> set[str]:
    return {p for p in ALL_PERMISSIONS if p.endswith(":read")}


# Default matrix keyed by the legacy User.role string.
DEFAULT_ROLE_MATRIX: dict[str, set[str]] = {
    "admin": _all(),
    "manager": _all() - {"users:write", "tenants:write", "tenants:read"},
    "coordinator": _reads() | {
        "service_tickets:write", "engineer_visits:write", "amc:write",
    },
    "accounts": _reads() | {
        "invoices:write", "payments:write", "quotations:write",
    },
    "technician": {
        "service_tickets:read", "engineer_visits:read", "engineer_visits:write",
        "assets:read", "inventory:read", "customers:read",
    },
    "viewer": _reads(),
}


def default_permissions_for_role(role: str) -> set[str]:
    return set(DEFAULT_ROLE_MATRIX.get(role, _reads()))

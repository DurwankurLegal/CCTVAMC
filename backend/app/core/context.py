"""Request-scoped context.

Holds the current actor (user) and tenant for the duration of a request so that
cross-cutting concerns — audit logging, RLS, structured logging — can read them
without threading the values through every service/repository signature.

Values are set by ``get_current_user`` (see ``app.core.deps``) and cleared by the
request middleware. They default to ``None`` outside a request (e.g. Celery tasks,
which set them explicitly when needed).
"""
from __future__ import annotations

import contextvars
from typing import Optional
from uuid import UUID

current_user_id: contextvars.ContextVar[Optional[UUID]] = contextvars.ContextVar(
    "current_user_id", default=None
)
current_tenant_id: contextvars.ContextVar[Optional[UUID]] = contextvars.ContextVar(
    "current_tenant_id", default=None
)


def set_actor(user_id: Optional[UUID], tenant_id: Optional[UUID]) -> None:
    current_user_id.set(user_id)
    current_tenant_id.set(tenant_id)


def get_actor_id() -> Optional[UUID]:
    return current_user_id.get()

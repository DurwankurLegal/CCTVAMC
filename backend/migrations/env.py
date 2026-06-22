import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import engine_from_config, pool
from alembic import context

# ── Load .env so env vars are available before any app import ─────────────
# Works whether you run `alembic upgrade head` directly or via Docker.
_env_file = Path(__file__).resolve().parents[1] / ".env"
if _env_file.exists():
    for line in _env_file.read_text().splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, _, val = line.partition("=")
            os.environ.setdefault(key.strip(), val.strip())

# ── Provide fallback DATABASE_URL_SYNC so Alembic doesn't crash if only
#    DATABASE_URL_SYNC is set via shell env rather than .env ────────────────
if "DATABASE_URL_SYNC" not in os.environ:
    raise RuntimeError(
        "DATABASE_URL_SYNC is not set. "
        "Either export it in your shell or add it to backend/.env"
    )

# ── Minimal stub settings so app.core.config doesn't validate at import ───
# We only need Base + model metadata here; skip the full FastAPI app stack.
os.environ.setdefault("DATABASE_URL", os.environ["DATABASE_URL_SYNC"].replace(
    "postgresql://", "postgresql+asyncpg://", 1
))
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/0")
os.environ.setdefault("JWT_SECRET_KEY", "alembic-placeholder-not-used-at-runtime")

# ── Now it's safe to import app code ──────────────────────────────────────
from app.core.database import Base  # noqa: E402  (Base has no engine deps)
import app.models.tenant            # noqa: E402  (register tables with metadata)
import app.models.user
import app.models.audit_log
import app.models.customer
import app.models.asset
import app.models.lead
import app.models.vendor
import app.models.amc
import app.models.service_ticket
import app.models.engineer_visit
import app.models.inventory
import app.models.quotation
import app.models.sales_order
import app.models.invoice
import app.models.payment
import app.models.notification
import app.models.sequence
import app.models.auth_session
import app.models.rbac
import app.models.document
import app.models.pm_schedule
import app.models.installation
import app.models.dashboard_snapshot
import app.models.ticket_comment

config = context.config
config.set_main_option("sqlalchemy.url", os.environ["DATABASE_URL_SYNC"])

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

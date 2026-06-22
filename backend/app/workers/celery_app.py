from celery import Celery
from app.core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "cctv_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
    include=["app.workers.tasks"],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="Asia/Kolkata",
    enable_utc=True,
    beat_schedule={
        "check-amc-renewals": {
            "task": "app.workers.tasks.check_amc_renewals",
            "schedule": 86400.0,  # daily
        },
        "check-sla-breaches": {
            "task": "app.workers.tasks.check_sla_breaches",
            "schedule": 300.0,  # every 5 minutes
        },
        "aggregate-dashboard-kpis": {
            "task": "app.workers.tasks.aggregate_dashboard_kpis",
            "schedule": 3600.0,  # hourly
        },
    },
)

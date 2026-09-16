from celery import Celery
from celery.schedules import crontab
from core.config import get_settings

settings = get_settings()

celery_app = Celery(
    "makemerich_tasks",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["tasks.scheduled_tasks"]
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Kolkata",
    enable_utc=True,
    worker_hijack_root_logger=False,
)

# Celery Beat Schedule Configuration
celery_app.conf.beat_schedule = {
    "daily-fundamental-ingestion": {
        "task": "tasks.scheduled_tasks.run_daily_fundamental_ingestion",
        "schedule": crontab(hour=15, minute=45), # 3:45 PM IST
    },
    "daily-outcome-evaluation": {
        "task": "tasks.scheduled_tasks.run_daily_outcome_evaluation",
        "schedule": crontab(hour=16, minute=15), # 4:15 PM IST
    },
    "daily-ai-opportunity-engine": {
        "task": "tasks.scheduled_tasks.run_daily_ai_opportunity_engine",
        "schedule": crontab(hour=16, minute=30), # 4:30 PM IST
    },
    "weekly-corporate-actions": {
        "task": "tasks.scheduled_tasks.run_weekly_corporate_actions",
        "schedule": crontab(hour=23, minute=0, day_of_week="sun"), # 11:00 PM IST Sundays
    },
    "market-hours-alert-dispatcher": {
        "task": "tasks.scheduled_tasks.run_alert_dispatcher",
        "schedule": crontab(minute="*/10", hour="9-15", day_of_week="mon-fri"), # Every 10m 9AM-3PM Mon-Fri
    },
    "daily-s3-archive": {
        "task": "tasks.scheduled_tasks.run_daily_s3_archive",
        "schedule": crontab(hour=23, minute=30), # 11:30 PM IST Daily
    }
}

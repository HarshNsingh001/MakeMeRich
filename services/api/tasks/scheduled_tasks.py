import asyncio
import logging
from core.celery_app import celery_app

# Import the actual async service functions
from services.fundamental_ingestor import run_ingestion
from services.corporate_actions_ingestor import run_corporate_actions_ingestion
from services.outcome_evaluator import evaluate_recommendation_outcomes
from services.alert_dispatcher import dispatch_alerts
from recommendations.generator import generate_opportunities_batch

logger = logging.getLogger(__name__)

def run_async(coro):
    """Helper to run async coroutines within synchronous celery tasks."""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

@celery_app.task(name="tasks.scheduled_tasks.run_daily_fundamental_ingestion")
def run_daily_fundamental_ingestion():
    logger.info("Celery Task: Starting daily fundamental ingestion...")
    run_async(run_ingestion(delay_seconds=0.5))
    logger.info("Celery Task: Daily fundamental ingestion completed.")

@celery_app.task(name="tasks.scheduled_tasks.run_daily_outcome_evaluation")
def run_daily_outcome_evaluation():
    logger.info("Celery Task: Starting outcome evaluation...")
    run_async(evaluate_recommendation_outcomes(lookback_days=90))
    logger.info("Celery Task: Outcome evaluation completed.")

@celery_app.task(name="tasks.scheduled_tasks.run_daily_ai_opportunity_engine")
def run_daily_ai_opportunity_engine():
    logger.info("Celery Task: Starting AI Opportunity Engine...")
    run_async(generate_opportunities_batch())
    logger.info("Celery Task: AI Opportunity Engine completed.")

@celery_app.task(name="tasks.scheduled_tasks.run_weekly_corporate_actions")
def run_weekly_corporate_actions():
    logger.info("Celery Task: Starting weekly corporate actions ingestion...")
    run_async(run_corporate_actions_ingestion())
    logger.info("Celery Task: Corporate actions ingestion completed.")

@celery_app.task(name="tasks.scheduled_tasks.run_alert_dispatcher")
def run_alert_dispatcher():
    run_async(dispatch_alerts())

@celery_app.task(name="tasks.scheduled_tasks.run_daily_s3_archive")
def run_daily_s3_archive():
    logger.info("Celery Task: Starting daily S3 archive backup...")
    from core.storage import storage_client
    from datetime import datetime
    
    # In a real scenario, this would query the DB for today's market_depth_snapshots 
    # and fundamental JSONs, and dump them to S3. For now, we mock the dump.
    today_str = datetime.utcnow().strftime('%Y-%m-%d')
    mock_data = {
        "date": today_str,
        "metrics": {"total_symbols_processed": 500, "opportunities_found": 12},
        "raw_json_dumps": "..."
    }
    
    object_key = f"raw_data_archive/daily_dump_{today_str}.json"
    storage_client.upload_json(object_key, mock_data)
    logger.info(f"Celery Task: Daily S3 archive completed for {object_key}.")


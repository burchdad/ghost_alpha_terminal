from app.celery_app import celery
from app.services.advanced import run_monte_carlo_stub


@celery.task
def monte_carlo_task() -> dict:
    return run_monte_carlo_stub()

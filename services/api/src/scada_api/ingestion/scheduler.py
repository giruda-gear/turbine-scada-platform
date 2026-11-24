import logging

import httpx
from apscheduler.schedulers.blocking import BlockingScheduler

from scada_api.core.database import SessionLocal, engine
from scada_api.data_sources.service import get_active_data_sources
from scada_api.ingestion.poller import run_polling_with_lock

logger = logging.getLogger(__name__)


def start_scheduler() -> None:
    scheduler = BlockingScheduler(timezone="UTC")

    try:
        scheduler.add_job(
            poll_all_data_sources,
            trigger="interval",
            minutes=10,
            id="poll_all_data_sources",
            max_instances=1,
            coalesce=True,
            misfire_grace_time=60,
        )

        logger.info("Starting ingestion scheduler")
        scheduler.start()

    except KeyboardInterrupt, SystemExit:
        logger.info("Stopping ingestion scheduler")
        scheduler.shutdown()


def poll_all_data_sources() -> None:
    with SessionLocal() as session:
        data_source_ids = get_active_data_sources(session)

    for data_source_id in data_source_ids:
        try:
            with httpx.Client() as client:
                published_count = run_polling_with_lock(
                    client=client,
                    data_source_id=data_source_id,
                    session_factory=SessionLocal,
                    engine=engine,
                )

            if published_count is not None:
                logger.info(
                    "Polling completed for %s: published=%d readings",
                    data_source_id,
                    published_count,
                )

        except Exception:
            logger.exception(
                "Polling failed for data source %s",
                data_source_id,
            )


if __name__ == "__main__":
    start_scheduler()

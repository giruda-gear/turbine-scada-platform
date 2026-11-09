from datetime import datetime

from airflow.sdk import dag, task


@dag(
    dag_id="scada_ingestion",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["scada", "ingestion"],
)
def scada_ingestion():

    @task
    def poll_data_source(data_source_id: str):
        # Imports happen when the task executes,
        # not when Airflow parses the DAG.
        from airflow.providers.postgres.hooks.postgres import PostgresHook
        from sqlalchemy.orm import sessionmaker
        from uuid import UUID
        from scada_api.ingestion.poller import run_polling

        hook = PostgresHook(postgres_conn_id="scada_postgres")
        engine = hook.get_sqlalchemy_engine()

        try:
            SessionFactory = sessionmaker(
                bind=engine,
                autoflush=False,
                expire_on_commit=False,
            )

            saved_count = run_polling(
                data_source_id=UUID(data_source_id),
                session_factory=SessionFactory,
            )

            print(f"Saved {saved_count} readings")

        finally:
            engine.dispose()

    poll_data_source("01a1ac47-1032-7a75-b984-819c68f29df0")


scada_ingestion()

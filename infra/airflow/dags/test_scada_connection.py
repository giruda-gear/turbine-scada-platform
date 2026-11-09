from airflow.sdk import dag, task
from datetime import datetime

@dag(
    dag_id="test_scada_connection",
    schedule=None,
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["scada", "database"],
)
def test_scada_connection():

    @task
    def verify_database():
        from airflow.providers.postgres.hooks.postgres import PostgresHook

        hook = PostgresHook(postgres_conn_id="scada_postgres")

        records = hook.get_records(
            """
            SELECT id, name, provider, protocol
            FROM data_sources
            """
        )

        print(f"Found {len(records)} data sources")

        for record in records:
            print(record)

    verify_database()

test_scada_connection()
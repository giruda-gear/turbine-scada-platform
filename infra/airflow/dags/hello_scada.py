from datetime import datetime

from airflow.sdk import dag, task


@dag(
    dag_id="hello_scada",
    schedule="*/10 * * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    tags=["scada", "learning"],
)
def hello_scada():

    @task
    def say_hello():
        print("Hello, SCADA platform!")
        return "SCADA ingestion workflow started"

    @task
    def process_result(message: str):
        print(f"Received: {message}")

    message = say_hello()
    process_result(message)


hello_scada()

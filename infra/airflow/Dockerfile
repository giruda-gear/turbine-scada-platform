FROM apache/airflow:3.3.2

USER airflow

COPY --chown=airflow:root services/api/src /opt/scada-api/src

ENV PYTHONPATH="/opt/scada-api/src:${PYTHONPATH}"
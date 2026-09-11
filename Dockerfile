FROM apache/airflow:2.10.5-python3.11
USER airflow
COPY pyproject.toml README.md /tmp/pit/
COPY src /tmp/pit/src
RUN pip install --no-cache-dir /tmp/pit

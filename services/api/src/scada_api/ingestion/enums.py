from enum import StrEnum


class IngestionRunStatus(StrEnum):
    RUNNING = "running"
    PUBLISHED = "published"
    PROCESSING = "processing"
    SUCCESS = "success"
    FAILED = "failed"

class TransientProcessingError(Exception):
    """An error that may succeed if processing is retried."""


class PermanentProcessingError(Exception):
    """An error that will not succeed by retrying unchanged input."""

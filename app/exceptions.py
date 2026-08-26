from __future__ import annotations


class GeminiServiceError(RuntimeError):
    def __init__(self, message: str, *, operation: str) -> None:
        super().__init__(message)
        self.operation = operation


class RetrievalServiceError(RuntimeError):
    pass

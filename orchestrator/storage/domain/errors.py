class StorageError(Exception):
    """Base error for storage layer."""


class StorageBackendNotReady(StorageError):
    """Raised when configured backend is not implemented/available."""


class StorageNotFound(StorageError):
    """Raised when requested record is not found."""

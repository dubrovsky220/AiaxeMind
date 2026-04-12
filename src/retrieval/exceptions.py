"""
Custom exceptions for retrieval operations in AiaxeMind.

This module defines exceptions raised during vector store operations,
providing clear error types for different failure scenarios.
"""


class RetrievalError(Exception):
    """
    Base exception for all retrieval-related errors.

    All retrieval-specific exceptions inherit from this base class,
    allowing callers to catch all retrieval errors with a single
    except clause if needed.
    """

    pass


class VectorStoreConnectionError(RetrievalError):
    """
    Raised when connection to the vector store (Qdrant) fails.

    Examples:
        - Qdrant service is not running
        - Network connectivity issues
        - Invalid URL or port configuration

    Attributes:
        url: The Qdrant URL that failed to connect
        original_error: The underlying exception that caused the failure
    """

    def __init__(self, url: str, original_error: Exception) -> None:
        """
        Initialize VectorStoreConnectionError.

        Args:
            url: The Qdrant URL that was attempted
            original_error: The original exception raised during connection
        """
        self.url = url
        self.original_error = original_error
        super().__init__(f"Failed to connect to Qdrant at {url}: {original_error}")


class CollectionNotFoundError(RetrievalError):
    """
    Raised when attempting to access a collection that doesn't exist.

    This typically indicates a configuration issue or that the collection
    hasn't been created yet.

    Attributes:
        collection_name: Name of the collection that wasn't found
    """

    def __init__(self, collection_name: str) -> None:
        """
        Initialize CollectionNotFoundError.

        Args:
            collection_name: Name of the missing collection
        """
        self.collection_name = collection_name
        super().__init__(f"Collection '{collection_name}' not found in Qdrant")


class VectorStoreOperationError(RetrievalError):
    """
    Raised when a vector store operation (upsert, search, delete) fails.

    Examples:
        - Invalid vector dimensions
        - Malformed payload data
        - Qdrant internal errors
        - Timeout during operation

    Attributes:
        operation: The operation that failed (e.g., "upsert", "search", "delete")
        details: Human-readable description of what went wrong
        original_error: The underlying exception if available
    """

    def __init__(
        self, operation: str, details: str, original_error: Exception | None = None
    ) -> None:
        """
        Initialize VectorStoreOperationError.

        Args:
            operation: Name of the operation that failed
            details: Description of the failure
            original_error: The original exception if available
        """
        self.operation = operation
        self.details = details
        self.original_error = original_error

        error_suffix = f" (caused by: {original_error})" if original_error else ""
        super().__init__(f"Vector store {operation} failed: {details}{error_suffix}")

"""
Custom exceptions for document parsing in AiaxeMind.

This module defines exceptions raised during document parsing operations,
providing clear error types for different failure scenarios.
"""


class ParsingError(Exception):
    """
    Base exception for all document parsing errors.

    All parser-specific exceptions inherit from this base class,
    allowing callers to catch all parsing-related errors with a single
    except clause if needed.
    """

    pass


class UnsupportedFileTypeError(ParsingError):
    """
    Raised when attempting to parse a file with an unsupported format.

    Examples:
        - Attempting to parse .txt, .csv, or other non-PDF/DOCX files
        - File extension doesn't match supported types

    Attributes:
        file_path: Path to the unsupported file
        file_type: Detected or provided file type/extension
    """

    def __init__(self, file_path: str, file_type: str) -> None:
        """
        Initialize UnsupportedFileTypeError.

        Args:
            file_path: Path to the file that couldn't be parsed
            file_type: The file type/extension that was detected
        """
        self.file_path = file_path
        self.file_type = file_type
        super().__init__(
            f"Unsupported file type '{file_type}' for file: {file_path}. Supported types: PDF, DOCX"
        )


class CorruptedFileError(ParsingError):
    """
    Raised when a file is corrupted or malformed and cannot be parsed.

    Examples:
        - PDF with invalid structure
        - DOCX with missing required XML components
        - Truncated or incomplete files
        - Password-protected files (if not supported)

    Attributes:
        file_path: Path to the corrupted file
        original_error: The underlying exception that indicated corruption
    """

    def __init__(self, file_path: str, original_error: Exception | None = None) -> None:
        """
        Initialize CorruptedFileError.

        Args:
            file_path: Path to the corrupted file
            original_error: The original exception that was raised during parsing
        """
        self.file_path = file_path
        self.original_error = original_error

        error_detail = f": {str(original_error)}" if original_error else ""
        super().__init__(f"File appears to be corrupted or malformed: {file_path}{error_detail}")


class MetadataExtractionError(ParsingError):
    """
    Raised when metadata extraction fails but document parsing succeeded.

    This is a non-fatal error - the document text may still be usable,
    but metadata (title, author, page count) couldn't be extracted.

    Attributes:
        file_path: Path to the file
        metadata_field: The specific metadata field that failed (if known)
    """

    def __init__(self, file_path: str, metadata_field: str | None = None) -> None:
        """
        Initialize MetadataExtractionError.

        Args:
            file_path: Path to the file
            metadata_field: Specific metadata field that failed extraction
        """
        self.file_path = file_path
        self.metadata_field = metadata_field

        field_detail = f" (field: {metadata_field})" if metadata_field else ""
        super().__init__(f"Failed to extract metadata from file: {file_path}{field_detail}")

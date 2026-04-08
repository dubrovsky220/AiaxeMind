"""Unit tests for custom parsing exceptions."""

import pytest

from src.ingestion.parsers.exceptions import (
    CorruptedFileError,
    MetadataExtractionError,
    ParsingError,
    UnsupportedFileTypeError,
)


class TestParsingExceptions:
    """Test suite for custom parsing exceptions."""

    def test_parsing_error_base_class(self) -> None:
        """Test ParsingError is base exception."""
        error = ParsingError("Test error")
        assert isinstance(error, Exception)
        assert str(error) == "Test error"

    def test_unsupported_file_type_error(self) -> None:
        """Test UnsupportedFileTypeError attributes and message."""
        error = UnsupportedFileTypeError(file_path="/path/to/file.txt", file_type=".txt")

        assert isinstance(error, ParsingError)
        assert error.file_path == "/path/to/file.txt"
        assert error.file_type == ".txt"
        assert "/path/to/file.txt" in str(error)
        assert ".txt" in str(error)
        assert "Unsupported file type" in str(error)

    def test_corrupted_file_error_with_original_error(self) -> None:
        """Test CorruptedFileError with original exception."""
        original = ValueError("Invalid structure")
        error = CorruptedFileError(file_path="/path/to/file.pdf", original_error=original)

        assert isinstance(error, ParsingError)
        assert error.file_path == "/path/to/file.pdf"
        assert error.original_error is original
        assert "/path/to/file.pdf" in str(error)
        assert "Invalid structure" in str(error)
        assert "corrupted" in str(error).lower()

    def test_corrupted_file_error_without_original_error(self) -> None:
        """Test CorruptedFileError without original exception."""
        error = CorruptedFileError(file_path="/path/to/file.pdf")

        assert error.file_path == "/path/to/file.pdf"
        assert error.original_error is None
        assert "/path/to/file.pdf" in str(error)
        assert "corrupted" in str(error).lower()

    def test_metadata_extraction_error_with_field(self) -> None:
        """Test MetadataExtractionError with specific field."""
        error = MetadataExtractionError(file_path="/path/to/file.pdf", metadata_field="author")

        assert isinstance(error, ParsingError)
        assert error.file_path == "/path/to/file.pdf"
        assert error.metadata_field == "author"
        assert "/path/to/file.pdf" in str(error)
        assert "author" in str(error)
        assert "metadata" in str(error).lower()

    def test_metadata_extraction_error_without_field(self) -> None:
        """Test MetadataExtractionError without specific field."""
        error = MetadataExtractionError(file_path="/path/to/file.pdf")

        assert error.file_path == "/path/to/file.pdf"
        assert error.metadata_field is None
        assert "/path/to/file.pdf" in str(error)
        assert "metadata" in str(error).lower()

    def test_exception_inheritance_chain(self) -> None:
        """Test that all custom exceptions inherit from ParsingError."""
        assert issubclass(UnsupportedFileTypeError, ParsingError)
        assert issubclass(CorruptedFileError, ParsingError)
        assert issubclass(MetadataExtractionError, ParsingError)

    def test_exceptions_can_be_caught_as_parsing_error(self) -> None:
        """Test that all custom exceptions can be caught as ParsingError."""
        exceptions = [
            UnsupportedFileTypeError(file_path="test.txt", file_type=".txt"),
            CorruptedFileError(file_path="test.pdf"),
            MetadataExtractionError(file_path="test.docx"),
        ]

        for exc in exceptions:
            with pytest.raises(ParsingError):
                raise exc

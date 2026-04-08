"""Unit tests for ParserFactory."""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.ingestion.parsers.base import BaseParser, ParsedDocument
from src.ingestion.parsers.exceptions import UnsupportedFileTypeError
from src.ingestion.parsers.factory import ParserFactory


class MockParser(BaseParser):
    """Mock parser for testing."""

    def __init__(self, extensions: set[str]) -> None:
        self._extensions = extensions

    def supported_extensions(self) -> set[str]:
        return self._extensions

    def parse(self, file_path: Path) -> ParsedDocument:
        return MagicMock(spec=ParsedDocument)


class TestParserFactory:
    """Test suite for ParserFactory."""

    @pytest.fixture
    def factory(self) -> ParserFactory:
        """Create ParserFactory instance."""
        return ParserFactory()

    def test_initialization(self, factory: ParserFactory) -> None:
        """Test factory initializes with default parsers."""
        assert len(factory._parsers) == 2
        extensions = factory.supported_extensions()
        assert ".pdf" in extensions
        assert ".docx" in extensions

    def test_register_parser(self) -> None:
        """Test registering a custom parser."""
        factory = ParserFactory()
        initial_count = len(factory._parsers)

        custom_parser = MockParser({".txt"})
        factory.register_parser(custom_parser)

        assert len(factory._parsers) == initial_count + 1
        assert ".txt" in factory.supported_extensions()

    def test_get_parser_pdf(self, factory: ParserFactory) -> None:
        """Test getting parser for PDF file."""
        parser = factory.get_parser(Path("document.pdf"))
        assert parser is not None
        assert ".pdf" in parser.supported_extensions()

    def test_get_parser_docx(self, factory: ParserFactory) -> None:
        """Test getting parser for DOCX file."""
        parser = factory.get_parser(Path("document.docx"))
        assert parser is not None
        assert ".docx" in parser.supported_extensions()

    def test_get_parser_unsupported(self, factory: ParserFactory) -> None:
        """Test getting parser for unsupported file type raises error."""
        with pytest.raises(UnsupportedFileTypeError) as exc_info:
            factory.get_parser(Path("document.txt"))
        assert "document.txt" in str(exc_info.value)
        assert ".txt" in str(exc_info.value)

    def test_get_parser_case_insensitive(self, factory: ParserFactory) -> None:
        """Test parser selection is case-insensitive."""
        parser_lower = factory.get_parser(Path("document.pdf"))
        parser_upper = factory.get_parser(Path("DOCUMENT.PDF"))
        assert type(parser_lower) == type(parser_upper)

    @patch("src.ingestion.parsers.factory.PDFParser")
    def test_parse_delegates_to_parser(
        self, mock_pdf_parser_class: Mock, factory: ParserFactory
    ) -> None:
        """Test that parse method delegates to appropriate parser."""
        mock_parser_instance = MagicMock()
        mock_result = MagicMock(spec=ParsedDocument)
        mock_parser_instance.parse.return_value = mock_result
        mock_parser_instance.supports_file_type.return_value = True
        mock_parser_instance.supported_extensions.return_value = {".pdf"}

        factory._parsers = [mock_parser_instance]

        result = factory.parse(Path("test.pdf"))

        mock_parser_instance.parse.assert_called_once_with(Path("test.pdf"))
        assert result == mock_result

    def test_supported_extensions_aggregates_all_parsers(self) -> None:
        """Test that supported_extensions returns all extensions from all parsers."""
        factory = ParserFactory()
        factory._parsers = []

        parser1 = MockParser({".pdf", ".doc"})
        parser2 = MockParser({".txt", ".md"})

        factory.register_parser(parser1)
        factory.register_parser(parser2)

        extensions = factory.supported_extensions()

        assert extensions == {".pdf", ".doc", ".txt", ".md"}

    def test_parser_selection_order(self) -> None:
        """Test that parsers are checked in registration order."""
        factory = ParserFactory()
        factory._parsers = []

        parser1 = MockParser({".pdf"})
        parser2 = MockParser({".pdf"})

        factory.register_parser(parser1)
        factory.register_parser(parser2)

        selected_parser = factory.get_parser(Path("test.pdf"))

        assert selected_parser is parser1

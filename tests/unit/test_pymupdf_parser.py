"""Unit tests for PDFParser."""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.ingestion.parsers.base import PageContent, ParsedDocument
from src.ingestion.parsers.exceptions import CorruptedFileError, UnsupportedFileTypeError
from src.ingestion.parsers.pymupdf_parser import PDFParser


class TestPDFParser:
    """Test suite for PDFParser."""

    @pytest.fixture
    def parser(self) -> PDFParser:
        """Create PDFParser instance."""
        return PDFParser()

    def test_supported_extensions(self, parser: PDFParser) -> None:
        """Test that parser supports .pdf extension."""
        assert parser.supported_extensions() == {".pdf"}

    def test_supports_file_type_pdf(self, parser: PDFParser) -> None:
        """Test that parser supports PDF files."""
        assert parser.supports_file_type(Path("document.pdf")) is True
        assert parser.supports_file_type(Path("DOCUMENT.PDF")) is True

    def test_supports_file_type_non_pdf(self, parser: PDFParser) -> None:
        """Test that parser rejects non-PDF files."""
        assert parser.supports_file_type(Path("document.docx")) is False
        assert parser.supports_file_type(Path("document.txt")) is False

    def test_parse_file_not_found(self, parser: PDFParser) -> None:
        """Test parsing non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            parser.parse(Path("/nonexistent/file.pdf"))

    def test_parse_unsupported_file_type(self, parser: PDFParser) -> None:
        """Test parsing unsupported file type raises UnsupportedFileTypeError."""
        with patch("pathlib.Path.exists", return_value=True):
            with pytest.raises(UnsupportedFileTypeError) as exc_info:
                parser.parse(Path("document.txt"))
            assert "document.txt" in str(exc_info.value)
            assert ".txt" in str(exc_info.value)

    @patch("src.ingestion.parsers.pymupdf_parser.fitz")
    def test_parse_encrypted_pdf(self, mock_fitz: Mock, parser: PDFParser) -> None:
        """Test parsing encrypted PDF raises CorruptedFileError."""
        # Create a custom FileDataError exception class
        FileDataError = type("FileDataError", (Exception,), {})
        mock_fitz.FileDataError = FileDataError

        mock_context = MagicMock()
        mock_context.__enter__.side_effect = FileDataError("password required")
        mock_fitz.open.return_value = mock_context

        with patch("pathlib.Path.exists", return_value=True):
            with pytest.raises(CorruptedFileError) as exc_info:
                parser.parse(Path("encrypted.pdf"))
            assert "encrypted.pdf" in str(exc_info.value)
            assert "encrypted" in str(exc_info.value).lower()

    @patch("src.ingestion.parsers.pymupdf_parser.fitz")
    def test_parse_corrupted_pdf(self, mock_fitz: Mock, parser: PDFParser) -> None:
        """Test parsing corrupted PDF raises CorruptedFileError."""
        mock_fitz.FileDataError = type("FileDataError", (Exception,), {})
        mock_context = MagicMock()
        mock_context.__enter__.side_effect = Exception("Invalid PDF structure")
        mock_fitz.open.return_value = mock_context

        with patch("pathlib.Path.exists", return_value=True):
            with pytest.raises(CorruptedFileError) as exc_info:
                parser.parse(Path("corrupted.pdf"))
            assert "corrupted.pdf" in str(exc_info.value)

    @patch("src.ingestion.parsers.pymupdf_parser.fitz")
    @patch("os.path.getsize")
    def test_parse_success(self, mock_getsize: Mock, mock_fitz: Mock, parser: PDFParser) -> None:
        """Test successful PDF parsing."""
        # Mock PDF document
        mock_page = MagicMock()
        mock_page.get_text.return_value = "Page 1 content"
        mock_page.get_text.return_value = "Page 1 content"

        # Mock get_text("dict") for heading extraction
        mock_page.get_text.side_effect = lambda fmt="text": (
            {
                "blocks": [
                    {
                        "type": 0,
                        "lines": [
                            {
                                "spans": [
                                    {
                                        "text": "Introduction",
                                        "size": 18,
                                        "flags": 16,  # bold flag
                                    }
                                ]
                            }
                        ],
                    }
                ]
            }
            if fmt == "dict"
            else "Page 1 content"
        )

        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 1
        mock_doc.__getitem__.return_value = mock_page
        mock_doc.metadata = {"title": "Test Document", "author": "Test Author"}

        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_doc
        mock_context.__exit__.return_value = None
        mock_fitz.open.return_value = mock_context

        mock_getsize.return_value = 1024

        with patch("pathlib.Path.exists", return_value=True):
            result = parser.parse(Path("test.pdf"))

        assert isinstance(result, ParsedDocument)
        assert result.text == "Page 1 content"
        assert result.metadata.title == "Test Document"
        assert result.metadata.author == "Test Author"
        assert result.metadata.page_count == 1
        assert result.metadata.file_type == ".pdf"
        assert result.metadata.file_size == 1024
        assert len(result.pages) == 1
        assert result.pages[0].page_number == 1

    @patch("src.ingestion.parsers.pymupdf_parser.fitz")
    @patch("os.path.getsize")
    def test_extract_metadata_fallback(
        self, mock_getsize: Mock, mock_fitz: Mock, parser: PDFParser
    ) -> None:
        """Test metadata extraction with missing fields."""
        mock_page = MagicMock()
        mock_page.get_text.return_value = "Content"
        mock_page.get_text.side_effect = lambda fmt="text": (
            {"blocks": []} if fmt == "dict" else "Content"
        )

        mock_doc = MagicMock()
        mock_doc.__len__.return_value = 1
        mock_doc.__getitem__.return_value = mock_page
        mock_doc.metadata = {}  # Empty metadata

        mock_context = MagicMock()
        mock_context.__enter__.return_value = mock_doc
        mock_context.__exit__.return_value = None
        mock_fitz.open.return_value = mock_context

        mock_getsize.return_value = 2048

        with patch("pathlib.Path.exists", return_value=True):
            result = parser.parse(Path("test.pdf"))

        assert result.metadata.title == "test"  # Falls back to filename
        assert result.metadata.author is None
        assert result.metadata.page_count == 1

    def test_extract_headings_from_page(self, parser: PDFParser) -> None:
        """Test heading extraction logic."""
        mock_page = MagicMock()
        mock_page.get_text.return_value = {
            "blocks": [
                {
                    "type": 0,
                    "lines": [
                        {
                            "spans": [
                                {"text": "Large Heading", "size": 18, "flags": 0},
                                {"text": "Bold Medium", "size": 14, "flags": 16},
                                {"text": "Normal text", "size": 11, "flags": 0},
                                {"text": "a", "size": 20, "flags": 0},  # Too short
                            ]
                        }
                    ],
                }
            ]
        }

        headings = parser._extract_headings_from_page(mock_page)

        assert "Large Heading" in headings
        assert "Bold Medium" in headings
        assert "Normal text" not in headings
        assert "a" not in headings

    def test_extract_section_titles(self, parser: PDFParser) -> None:
        """Test section title aggregation from pages."""
        pages = [
            PageContent(page_number=1, text="Content", headings=["Intro", "Background"]),
            PageContent(page_number=2, text="Content", headings=["Methods"]),
            PageContent(page_number=3, text="Content", headings=None),
        ]

        titles = parser._extract_section_titles(pages)

        assert titles == ["Intro", "Background", "Methods"]

    def test_extract_section_titles_no_headings(self, parser: PDFParser) -> None:
        """Test section title extraction when no headings exist."""
        pages = [
            PageContent(page_number=1, text="Content", headings=None),
            PageContent(page_number=2, text="Content", headings=None),
        ]

        titles = parser._extract_section_titles(pages)

        assert titles is None

"""Unit tests for DOCXParser."""

from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import pytest

from src.ingestion.parsers.base import DocumentMetadata, PageContent, ParsedDocument
from src.ingestion.parsers.docx_parser import CHARS_PER_PAGE, DOCXParser
from src.ingestion.parsers.exceptions import CorruptedFileError, UnsupportedFileTypeError


class TestDOCXParser:
    """Test suite for DOCXParser."""

    @pytest.fixture
    def parser(self) -> DOCXParser:
        """Create DOCXParser instance."""
        return DOCXParser()

    def test_supported_extensions(self, parser: DOCXParser) -> None:
        """Test that parser supports .docx and .doc extensions."""
        assert parser.supported_extensions() == {".docx", ".doc"}

    def test_supports_file_type_docx(self, parser: DOCXParser) -> None:
        """Test that parser supports DOCX files."""
        assert parser.supports_file_type(Path("document.docx")) is True
        assert parser.supports_file_type(Path("DOCUMENT.DOCX")) is True
        assert parser.supports_file_type(Path("document.doc")) is True

    def test_supports_file_type_non_docx(self, parser: DOCXParser) -> None:
        """Test that parser rejects non-DOCX files."""
        assert parser.supports_file_type(Path("document.pdf")) is False
        assert parser.supports_file_type(Path("document.txt")) is False

    def test_parse_file_not_found(self, parser: DOCXParser) -> None:
        """Test parsing non-existent file raises FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            parser.parse(Path("/nonexistent/file.docx"))

    def test_parse_unsupported_file_type(self, parser: DOCXParser) -> None:
        """Test parsing unsupported file type raises UnsupportedFileTypeError."""
        with patch("pathlib.Path.exists", return_value=True):
            with pytest.raises(UnsupportedFileTypeError) as exc_info:
                parser.parse(Path("document.txt"))
            assert "document.txt" in str(exc_info.value)
            assert ".txt" in str(exc_info.value)

    @patch("src.ingestion.parsers.docx_parser.Document")
    def test_parse_corrupted_docx(self, mock_document: Mock, parser: DOCXParser) -> None:
        """Test parsing corrupted DOCX raises CorruptedFileError."""
        mock_document.side_effect = Exception("Invalid DOCX structure")

        with patch("pathlib.Path.exists", return_value=True):
            with pytest.raises(CorruptedFileError) as exc_info:
                parser.parse(Path("corrupted.docx"))
            assert "corrupted.docx" in str(exc_info.value)

    @patch("src.ingestion.parsers.docx_parser.Document")
    @patch("os.path.getsize")
    def test_parse_success(
        self, mock_getsize: Mock, mock_document: Mock, parser: DOCXParser
    ) -> None:
        """Test successful DOCX parsing."""
        mock_para1 = MagicMock()
        mock_para1.text = "Introduction"
        mock_para1.style.name = "Heading 1"
        mock_para1.runs = []

        mock_para2 = MagicMock()
        mock_para2.text = "This is the content of the document."
        mock_para2.style.name = "Normal"
        mock_para2.runs = []

        mock_doc = MagicMock()
        mock_doc.paragraphs = [mock_para1, mock_para2]
        mock_doc.core_properties.title = "Test Document"
        mock_doc.core_properties.author = "Test Author"
        mock_document.return_value = mock_doc

        mock_getsize.return_value = 2048

        with patch("pathlib.Path.exists", return_value=True):
            result = parser.parse(Path("test.docx"))

        assert isinstance(result, ParsedDocument)
        assert "Introduction" in result.text
        assert "This is the content" in result.text
        assert result.metadata.title == "Test Document"
        assert result.metadata.author == "Test Author"
        assert result.metadata.file_type == ".docx"
        assert result.metadata.file_size == 2048
        assert len(result.pages) >= 1

    @patch("src.ingestion.parsers.docx_parser.Document")
    @patch("os.path.getsize")
    def test_extract_metadata_fallback(
        self, mock_getsize: Mock, mock_document: Mock, parser: DOCXParser
    ) -> None:
        """Test metadata extraction with missing fields."""
        mock_doc = MagicMock()
        mock_doc.paragraphs = []
        mock_doc.core_properties.title = ""
        mock_doc.core_properties.author = ""
        mock_document.return_value = mock_doc

        mock_getsize.return_value = 1024

        with patch("pathlib.Path.exists", return_value=True):
            result = parser.parse(Path("test.docx"))

        assert result.metadata.title == "test"
        assert result.metadata.author is None

    def test_is_heading_style_based(self, parser: DOCXParser) -> None:
        """Test heading detection using style names."""
        mock_para = MagicMock()
        mock_para.text = "Chapter 1"
        mock_para.style.name = "Heading 1"
        mock_para.runs = []

        assert parser._is_heading(mock_para) is True

    def test_is_heading_heuristic_large_font(self, parser: DOCXParser) -> None:
        """Test heading detection using large font size."""
        mock_run = MagicMock()
        mock_run.font.size.pt = 16
        mock_run.font.bold = False

        mock_para = MagicMock()
        mock_para.text = "Important Section"
        mock_para.style.name = "Normal"
        mock_para.runs = [mock_run]

        assert parser._is_heading(mock_para) is True

    def test_is_heading_heuristic_bold(self, parser: DOCXParser) -> None:
        """Test heading detection using bold text."""
        mock_run = MagicMock()
        mock_run.font.size.pt = 13
        mock_run.font.bold = True

        mock_para = MagicMock()
        mock_para.text = "Bold Heading"
        mock_para.style.name = "Normal"
        mock_para.runs = [mock_run]

        assert parser._is_heading(mock_para) is True

    def test_is_heading_not_heading(self, parser: DOCXParser) -> None:
        """Test that normal text is not detected as heading."""
        mock_run = MagicMock()
        mock_run.font.size.pt = 11
        mock_run.font.bold = False

        mock_para = MagicMock()
        mock_para.text = "This is normal text."
        mock_para.style.name = "Normal"
        mock_para.runs = [mock_run]

        assert parser._is_heading(mock_para) is False

    def test_is_heading_filters_short_text(self, parser: DOCXParser) -> None:
        """Test that very short text is not detected as heading."""
        mock_run = MagicMock()
        mock_run.font.size.pt = 18
        mock_run.font.bold = True

        mock_para = MagicMock()
        mock_para.text = "AB"
        mock_para.style.name = "Normal"
        mock_para.runs = [mock_run]

        assert parser._is_heading(mock_para) is False

    def test_is_heading_filters_text_with_period(self, parser: DOCXParser) -> None:
        """Test that text ending with period is not detected as heading."""
        mock_run = MagicMock()
        mock_run.font.size.pt = 18
        mock_run.font.bold = True

        mock_para = MagicMock()
        mock_para.text = "This is a sentence."
        mock_para.style.name = "Normal"
        mock_para.runs = [mock_run]

        assert parser._is_heading(mock_para) is False

    def test_extract_pages_with_headings(self, parser: DOCXParser) -> None:
        """Test page extraction with heading detection."""
        mock_run = MagicMock()
        mock_run.font.size.pt = 18
        mock_run.font.bold = True

        mock_para1 = MagicMock()
        mock_para1.text = "Introduction"
        mock_para1.style.name = "Heading 1"
        mock_para1.runs = [mock_run]

        mock_para2 = MagicMock()
        mock_para2.text = "Content text here."
        mock_para2.style.name = "Normal"
        mock_para2.runs = []

        mock_doc = MagicMock()
        mock_doc.paragraphs = [mock_para1, mock_para2]

        pages = parser._extract_pages(mock_doc)

        assert len(pages) >= 1
        assert pages[0].page_number == 1
        assert "Introduction" in pages[0].text
        assert pages[0].headings is not None
        assert "Introduction" in pages[0].headings

    def test_extract_pages_multiple_pages(self, parser: DOCXParser) -> None:
        """Test page extraction with content spanning multiple pages."""
        para1_text = "A" * CHARS_PER_PAGE
        para2_text = "B" * CHARS_PER_PAGE

        mock_para1 = MagicMock()
        mock_para1.text = para1_text
        mock_para1.style.name = "Normal"
        mock_para1.runs = []

        mock_para2 = MagicMock()
        mock_para2.text = para2_text
        mock_para2.style.name = "Normal"
        mock_para2.runs = []

        mock_doc = MagicMock()
        mock_doc.paragraphs = [mock_para1, mock_para2]

        pages = parser._extract_pages(mock_doc)

        assert len(pages) == 2
        assert pages[0].page_number == 1
        assert pages[1].page_number == 2

    def test_extract_section_titles(self, parser: DOCXParser) -> None:
        """Test section title aggregation from pages."""
        pages = [
            PageContent(page_number=1, text="Content", headings=["Intro", "Background"]),
            PageContent(page_number=2, text="Content", headings=["Methods"]),
            PageContent(page_number=3, text="Content", headings=None),
        ]

        titles = parser._extract_section_titles(pages)

        assert titles == ["Intro", "Background", "Methods"]

    def test_extract_section_titles_no_headings(self, parser: DOCXParser) -> None:
        """Test section title extraction when no headings exist."""
        pages = [
            PageContent(page_number=1, text="Content", headings=None),
            PageContent(page_number=2, text="Content", headings=None),
        ]

        titles = parser._extract_section_titles(pages)

        assert titles is None

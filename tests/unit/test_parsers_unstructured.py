"""
Unit tests for UnstructuredParser with mocks.

Tests cover:
1. Parser initialization
2. File type support checking
3. PDF parsing logic
4. DOCX parsing logic
5. Element extraction
6. Section title extraction
7. Metadata extraction
8. Error handling
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.ingestion.parsers.base import ParsedDocument
from src.ingestion.parsers.exceptions import CorruptedFileError, UnsupportedFileTypeError
from src.ingestion.parsers.unstructured_parser import UnstructuredParser


class MockUnstructuredElement:
    """
    Mock object that mimics unstructured.io element structure.

    This allows us to test our parser logic without calling real unstructured.io functions.
    """

    def __init__(
        self,
        text: str,
        category: str,
        page_number: int | None = None,
        coordinates: list | None = None,
        text_as_html: str | None = None,
    ):
        self.text = text
        self.category = category
        self.metadata = Mock()
        self.metadata.page_number = page_number
        self.metadata.coordinates = Mock() if coordinates else None
        if coordinates:
            self.metadata.coordinates.points = coordinates
        self.metadata.text_as_html = text_as_html


class TestUnstructuredParserInit:
    """Tests for UnstructuredParser initialization."""

    def test_init_default_strategy(self) -> None:
        """Test parser initialization with default strategy."""
        parser = UnstructuredParser()
        assert parser.strategy == "hi_res"

    def test_init_custom_strategy(self) -> None:
        """Test parser initialization with custom strategy."""
        parser = UnstructuredParser(strategy="fast")
        assert parser.strategy == "fast"

    def test_init_ocr_strategy(self) -> None:
        """Test parser initialization with OCR strategy."""
        parser = UnstructuredParser(strategy="ocr_only")
        assert parser.strategy == "ocr_only"


class TestUnstructuredParserSupportedExtensions:
    """Tests for file type support checking."""

    def test_supported_extensions(self) -> None:
        """Test that parser returns correct supported extensions."""
        parser = UnstructuredParser()
        extensions = parser.supported_extensions()

        assert ".pdf" in extensions
        assert ".docx" in extensions
        assert ".doc" in extensions
        assert len(extensions) == 3

    def test_supports_pdf_files(self) -> None:
        """Test that parser supports PDF files."""
        parser = UnstructuredParser()
        assert parser.supports_file_type(Path("document.pdf")) is True
        assert parser.supports_file_type(Path("document.PDF")) is True

    def test_supports_docx_files(self) -> None:
        """Test that parser supports DOCX files."""
        parser = UnstructuredParser()
        assert parser.supports_file_type(Path("document.docx")) is True
        assert parser.supports_file_type(Path("document.DOCX")) is True

    def test_supports_doc_files(self) -> None:
        """Test that parser supports DOC files."""
        parser = UnstructuredParser()
        assert parser.supports_file_type(Path("document.doc")) is True

    def test_does_not_support_other_formats(self) -> None:
        """Test that parser rejects unsupported file formats."""
        parser = UnstructuredParser()
        assert parser.supports_file_type(Path("document.txt")) is False
        assert parser.supports_file_type(Path("image.jpg")) is False
        assert parser.supports_file_type(Path("data.csv")) is False


class TestUnstructuredParserParsePDF:
    """Tests for PDF parsing with mocked unstructured.io."""

    @patch("src.ingestion.parsers.unstructured_parser.partition_pdf")
    def test_parse_pdf_basic(self, mock_partition_pdf: Mock, tmp_path: Path) -> None:
        """Test basic PDF parsing flow."""
        test_file = tmp_path / "test.pdf"
        test_file.write_text("dummy")

        mock_elements = [
            MockUnstructuredElement(text="Title Text", category="Title", page_number=1),
            MockUnstructuredElement(text="Body text", category="Text", page_number=1),
        ]
        mock_partition_pdf.return_value = mock_elements

        parser = UnstructuredParser()
        result = parser.parse(test_file)

        assert isinstance(result, ParsedDocument)
        assert len(result.elements) == 2
        assert result.elements[0].text == "Title Text"
        assert result.elements[0].element_type == "Title"
        assert result.elements[1].text == "Body text"

    @patch("src.ingestion.parsers.unstructured_parser.partition_pdf")
    def test_parse_pdf_calls_partition_with_correct_params(
        self, mock_partition_pdf: Mock, tmp_path: Path
    ) -> None:
        """Test that partition_pdf is called with correct parameters."""
        test_file = tmp_path / "test.pdf"
        test_file.write_text("dummy")

        mock_partition_pdf.return_value = []

        parser = UnstructuredParser(strategy="fast")
        parser.parse(test_file)

        mock_partition_pdf.assert_called_once_with(
            filename=str(test_file),
            strategy="fast",
            include_page_breaks=True,
            infer_table_structure=True,
            coordinates=True,
        )

    @patch("src.ingestion.parsers.unstructured_parser.partition_pdf")
    def test_parse_pdf_preserves_page_numbers(
        self, mock_partition_pdf: Mock, tmp_path: Path
    ) -> None:
        """Test that page numbers are correctly extracted from PDF elements."""
        test_file = tmp_path / "test.pdf"
        test_file.write_text("dummy")

        mock_elements = [
            MockUnstructuredElement(text="Page 1 text", category="Text", page_number=1),
            MockUnstructuredElement(text="Page 2 text", category="Text", page_number=2),
            MockUnstructuredElement(text="Page 3 text", category="Text", page_number=3),
        ]
        mock_partition_pdf.return_value = mock_elements

        parser = UnstructuredParser()
        result = parser.parse(test_file)

        assert result.elements[0].page_number == 1
        assert result.elements[1].page_number == 2
        assert result.elements[2].page_number == 3

    @patch("src.ingestion.parsers.unstructured_parser.partition_pdf")
    def test_parse_pdf_skips_page_breaks(self, mock_partition_pdf: Mock, tmp_path: Path) -> None:
        """Test that PageBreak elements are filtered out."""
        test_file = tmp_path / "test.pdf"
        test_file.write_text("dummy")

        mock_elements = [
            MockUnstructuredElement(text="Page 1", category="Text", page_number=1),
            MockUnstructuredElement(text="", category="PageBreak", page_number=1),
            MockUnstructuredElement(text="Page 2", category="Text", page_number=2),
        ]
        mock_partition_pdf.return_value = mock_elements

        parser = UnstructuredParser()
        result = parser.parse(test_file)

        assert len(result.elements) == 2
        assert result.elements[0].text == "Page 1"
        assert result.elements[1].text == "Page 2"


class TestUnstructuredParserParseDOCX:
    """Tests for DOCX parsing with mocked unstructured.io."""

    @patch("src.ingestion.parsers.unstructured_parser.partition_docx")
    def test_parse_docx_basic(self, mock_partition_docx: Mock, tmp_path: Path) -> None:
        """Test basic DOCX parsing flow."""
        test_file = tmp_path / "test.docx"
        test_file.write_text("dummy")

        mock_elements = [
            MockUnstructuredElement(text="Document Title", category="Title", page_number=1),
            MockUnstructuredElement(text="Paragraph text", category="Text", page_number=1),
        ]
        mock_partition_docx.return_value = mock_elements

        parser = UnstructuredParser()
        result = parser.parse(test_file)

        assert isinstance(result, ParsedDocument)
        assert len(result.elements) == 2
        assert result.elements[0].text == "Document Title"

    @patch("src.ingestion.parsers.unstructured_parser.partition_docx")
    def test_parse_docx_calls_partition_with_correct_params(
        self, mock_partition_docx: Mock, tmp_path: Path
    ) -> None:
        """Test that partition_docx is called with correct parameters."""
        test_file = tmp_path / "test.docx"
        test_file.write_text("dummy")

        mock_partition_docx.return_value = []

        parser = UnstructuredParser()
        parser.parse(test_file)

        mock_partition_docx.assert_called_once_with(
            filename=str(test_file),
            include_page_breaks=True,
        )


class TestUnstructuredParserExtractElements:
    """Tests for element extraction logic."""

    @patch("src.ingestion.parsers.unstructured_parser.partition_pdf")
    def test_extract_elements_with_coordinates(
        self, mock_partition_pdf: Mock, tmp_path: Path
    ) -> None:
        """Test that element coordinates are extracted when available."""
        test_file = tmp_path / "test.pdf"
        test_file.write_text("dummy")

        mock_elements = [
            MockUnstructuredElement(
                text="Text with coords",
                category="Text",
                page_number=1,
                coordinates=[[0, 0], [100, 100]],
            ),
        ]
        mock_partition_pdf.return_value = mock_elements

        parser = UnstructuredParser()
        result = parser.parse(test_file)

        assert result.elements[0].metadata is not None
        assert "coordinates" in result.elements[0].metadata
        assert result.elements[0].metadata["coordinates"] == [[0, 0], [100, 100]]

    @patch("src.ingestion.parsers.unstructured_parser.partition_pdf")
    def test_extract_table_with_html(self, mock_partition_pdf: Mock, tmp_path: Path) -> None:
        """Test that table HTML is extracted when available."""
        test_file = tmp_path / "test.pdf"
        test_file.write_text("dummy")

        mock_elements = [
            MockUnstructuredElement(
                text="Table content",
                category="Table",
                page_number=1,
                text_as_html="<table><tr><td>Cell</td></tr></table>",
            ),
        ]
        mock_partition_pdf.return_value = mock_elements

        parser = UnstructuredParser()
        result = parser.parse(test_file)

        assert result.elements[0].element_type == "Table"
        assert result.elements[0].metadata is not None
        assert "html" in result.elements[0].metadata
        assert "<table>" in result.elements[0].metadata["html"]


class TestUnstructuredParserExtractSectionTitles:
    """Tests for section title extraction."""

    @patch("src.ingestion.parsers.unstructured_parser.partition_pdf")
    def test_extract_section_titles(self, mock_partition_pdf: Mock, tmp_path: Path) -> None:
        """Test that Title elements are extracted as section titles."""
        test_file = tmp_path / "test.pdf"
        test_file.write_text("dummy")

        mock_elements = [
            MockUnstructuredElement(text="Introduction", category="Title", page_number=1),
            MockUnstructuredElement(text="Some text", category="Text", page_number=1),
            MockUnstructuredElement(text="Methods", category="Title", page_number=2),
            MockUnstructuredElement(text="More text", category="Text", page_number=2),
        ]
        mock_partition_pdf.return_value = mock_elements

        parser = UnstructuredParser()
        result = parser.parse(test_file)

        assert result.section_titles is not None
        assert len(result.section_titles) == 2
        assert "Introduction" in result.section_titles
        assert "Methods" in result.section_titles

    @patch("src.ingestion.parsers.unstructured_parser.partition_pdf")
    def test_no_section_titles_returns_none(self, mock_partition_pdf: Mock, tmp_path: Path) -> None:
        """Test that section_titles is None when no titles found."""
        test_file = tmp_path / "test.pdf"
        test_file.write_text("dummy")

        mock_elements = [
            MockUnstructuredElement(text="Just text", category="Text", page_number=1),
        ]
        mock_partition_pdf.return_value = mock_elements

        parser = UnstructuredParser()
        result = parser.parse(test_file)

        assert result.section_titles is None


class TestUnstructuredParserExtractMetadata:
    """Tests for metadata extraction."""

    @patch("src.ingestion.parsers.unstructured_parser.partition_pdf")
    def test_extract_metadata_with_title(self, mock_partition_pdf: Mock, tmp_path: Path) -> None:
        """Test that document title is extracted from first Title element."""
        test_file = tmp_path / "test.pdf"
        test_file.write_text("dummy")

        mock_elements = [
            MockUnstructuredElement(text="Document Title", category="Title", page_number=1),
            MockUnstructuredElement(text="Body", category="Text", page_number=1),
        ]
        mock_partition_pdf.return_value = mock_elements

        parser = UnstructuredParser()
        result = parser.parse(test_file)

        assert result.metadata.title == "Document Title"

    @patch("src.ingestion.parsers.unstructured_parser.partition_pdf")
    def test_extract_metadata_page_count(self, mock_partition_pdf: Mock, tmp_path: Path) -> None:
        """Test that page count is calculated from max page number."""
        test_file = tmp_path / "test.pdf"
        test_file.write_text("dummy")

        mock_elements = [
            MockUnstructuredElement(text="Page 1", category="Text", page_number=1),
            MockUnstructuredElement(text="Page 2", category="Text", page_number=2),
            MockUnstructuredElement(text="Page 5", category="Text", page_number=5),
        ]
        mock_partition_pdf.return_value = mock_elements

        parser = UnstructuredParser()
        result = parser.parse(test_file)

        assert result.metadata.page_count == 5

    @patch("src.ingestion.parsers.unstructured_parser.partition_pdf")
    def test_extract_metadata_file_type(self, mock_partition_pdf: Mock, tmp_path: Path) -> None:
        """Test that file type is extracted from file extension."""
        test_file = tmp_path / "test.pdf"
        test_file.write_text("dummy")

        mock_partition_pdf.return_value = []

        parser = UnstructuredParser()
        result = parser.parse(test_file)

        assert result.metadata.file_type == ".pdf"

    @patch("src.ingestion.parsers.unstructured_parser.partition_pdf")
    def test_extract_metadata_file_size(self, mock_partition_pdf: Mock, tmp_path: Path) -> None:
        """Test that file size is extracted."""
        test_file = tmp_path / "test.pdf"
        test_file.write_bytes(b"x" * 1024)

        mock_partition_pdf.return_value = []

        parser = UnstructuredParser()
        result = parser.parse(test_file)

        assert result.metadata.file_size == 1024


class TestUnstructuredParserErrorHandling:
    """Tests for error handling."""

    def test_parse_nonexistent_file_raises_error(self) -> None:
        """Test that parsing nonexistent file raises FileNotFoundError."""
        parser = UnstructuredParser()
        with pytest.raises(FileNotFoundError):
            parser.parse(Path("/nonexistent/file.pdf"))

    def test_parse_unsupported_file_type_raises_error(self, tmp_path: Path) -> None:
        """Test that parsing unsupported file type raises UnsupportedFileTypeError."""
        test_file = tmp_path / "test.txt"
        test_file.write_text("dummy")

        parser = UnstructuredParser()
        with pytest.raises(UnsupportedFileTypeError) as exc_info:
            parser.parse(test_file)

        assert exc_info.value.file_type == ".txt"

    @patch("src.ingestion.parsers.unstructured_parser.partition_pdf")
    def test_parse_corrupted_file_raises_error(
        self, mock_partition_pdf: Mock, tmp_path: Path
    ) -> None:
        """Test that parsing corrupted file raises CorruptedFileError."""
        test_file = tmp_path / "corrupted.pdf"
        test_file.write_text("dummy")

        mock_partition_pdf.side_effect = ValueError("Invalid PDF structure")

        parser = UnstructuredParser()
        with pytest.raises(CorruptedFileError) as exc_info:
            parser.parse(test_file)

        assert exc_info.value.file_path == str(test_file)
        assert exc_info.value.original_error is not None

    @patch("src.ingestion.parsers.unstructured_parser.partition_pdf")
    def test_parse_handles_missing_page_numbers(
        self, mock_partition_pdf: Mock, tmp_path: Path
    ) -> None:
        """Test that parser handles elements without page numbers gracefully."""
        test_file = tmp_path / "test.pdf"
        test_file.write_text("dummy")

        mock_element = MockUnstructuredElement(text="Text", category="Text")
        mock_element.metadata.page_number = None
        mock_partition_pdf.return_value = [mock_element]

        parser = UnstructuredParser()
        result = parser.parse(test_file)

        assert result.elements[0].page_number is None


class TestUnstructuredParserIntegration:
    """Integration-style tests with mocks (testing multiple components together)."""

    @patch("src.ingestion.parsers.unstructured_parser.partition_pdf")
    def test_full_pdf_parsing_workflow(self, mock_partition_pdf: Mock, tmp_path: Path) -> None:
        """Test complete PDF parsing workflow with realistic data."""
        test_file = tmp_path / "research_paper.pdf"
        test_file.write_text("dummy")

        mock_elements = [
            MockUnstructuredElement(text="Research Paper Title", category="Title", page_number=1),
            MockUnstructuredElement(
                text="Abstract: This paper discusses...", category="Text", page_number=1
            ),
            MockUnstructuredElement(text="Introduction", category="Title", page_number=2),
            MockUnstructuredElement(
                text="The introduction explains...", category="Text", page_number=2
            ),
            MockUnstructuredElement(text="Methods", category="Title", page_number=3),
            MockUnstructuredElement(
                text="We used the following methods...", category="Text", page_number=3
            ),
        ]
        mock_partition_pdf.return_value = mock_elements

        parser = UnstructuredParser()
        result = parser.parse(test_file)

        assert len(result.elements) == 6
        assert result.metadata.title == "Research Paper Title"
        assert result.metadata.page_count == 3
        assert result.section_titles == ["Research Paper Title", "Introduction", "Methods"]
        assert all(elem.page_number is not None for elem in result.elements)

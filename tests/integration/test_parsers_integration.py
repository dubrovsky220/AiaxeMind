"""Integration tests for document parsers using real fixtures."""

from pathlib import Path

import pytest

from src.ingestion.parsers.docx_parser import DOCXParser
from src.ingestion.parsers.exceptions import CorruptedFileError
from src.ingestion.parsers.factory import ParserFactory
from src.ingestion.parsers.pymupdf_parser import PDFParser

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "documents"


class TestPDFParserIntegration:
    """Integration tests for PDFParser with real PDF files."""

    @pytest.fixture
    def parser(self) -> PDFParser:
        return PDFParser()

    def test_parse_simple_pdf(self, parser: PDFParser) -> None:
        """Test parsing simple.pdf fixture."""
        file_path = FIXTURES_DIR / "simple.pdf"
        if not file_path.exists():
            pytest.skip(f"Fixture not found: {file_path}")

        result = parser.parse(file_path)

        assert result.text is not None
        assert len(result.text) > 0
        assert result.metadata.title is not None
        assert result.metadata.page_count is not None
        assert result.metadata.page_count > 0
        assert result.metadata.file_type == ".pdf"
        assert result.metadata.file_size is not None
        assert result.metadata.file_size > 0
        assert len(result.pages) == result.metadata.page_count
        assert all(page.page_number > 0 for page in result.pages)
        assert all(page.text for page in result.pages)

    def test_parse_multi_page_pdf(self, parser: PDFParser) -> None:
        """Test parsing multi-page PDF."""
        file_path = FIXTURES_DIR / "pdf1.pdf"
        if not file_path.exists():
            pytest.skip(f"Fixture not found: {file_path}")

        result = parser.parse(file_path)

        assert result.metadata.page_count is not None
        assert result.metadata.page_count > 1
        assert len(result.pages) == result.metadata.page_count

        for i, page in enumerate(result.pages, start=1):
            assert page.page_number == i
            assert page.text is not None

    def test_parse_pdf_with_headings(self, parser: PDFParser) -> None:
        """Test parsing PDF with section headings."""
        file_path = FIXTURES_DIR / "pdf2.pdf"
        if not file_path.exists():
            pytest.skip(f"Fixture not found: {file_path}")

        result = parser.parse(file_path)

        assert result.text is not None
        if result.section_titles:
            assert len(result.section_titles) > 0
            assert all(isinstance(title, str) for title in result.section_titles)

    def test_parse_corrupted_pdf(self, parser: PDFParser) -> None:
        """Test parsing corrupted PDF raises CorruptedFileError."""
        file_path = FIXTURES_DIR / "corrupted.pdf"
        if not file_path.exists():
            pytest.skip(f"Fixture not found: {file_path}")

        with pytest.raises(CorruptedFileError):
            parser.parse(file_path)

    @pytest.mark.parametrize(
        "filename",
        [
            "pdf3.pdf",
            "pdf4.pdf",
            "pdf5.pdf",
            "pdf6.pdf",
            "pdf7.pdf",
            "pdf8.pdf",
            "pdf9.pdf",
            "pdf10.pdf",
        ],
    )
    def test_parse_various_pdfs(self, parser: PDFParser, filename: str) -> None:
        """Test parsing various PDF fixtures."""
        file_path = FIXTURES_DIR / filename
        if not file_path.exists():
            pytest.skip(f"Fixture not found: {file_path}")

        result = parser.parse(file_path)

        assert result.text is not None
        assert len(result.text) > 0
        assert result.metadata.page_count is not None
        assert result.metadata.page_count > 0
        assert len(result.pages) == result.metadata.page_count


class TestDOCXParserIntegration:
    """Integration tests for DOCXParser with real DOCX files."""

    @pytest.fixture
    def parser(self) -> DOCXParser:
        return DOCXParser()

    def test_parse_simple_docx(self, parser: DOCXParser) -> None:
        """Test parsing simple.docx fixture."""
        file_path = FIXTURES_DIR / "simple.docx"
        if not file_path.exists():
            pytest.skip(f"Fixture not found: {file_path}")

        result = parser.parse(file_path)

        assert result.text is not None
        assert len(result.text) > 0
        assert result.metadata.title is not None
        assert result.metadata.page_count is not None
        assert result.metadata.page_count > 0
        assert result.metadata.file_type == ".docx"
        assert result.metadata.file_size is not None
        assert result.metadata.file_size > 0
        assert len(result.pages) > 0
        assert all(page.page_number > 0 for page in result.pages)
        assert all(page.text for page in result.pages)

    def test_parse_docx_with_headings(self, parser: DOCXParser) -> None:
        """Test parsing DOCX with section headings."""
        file_path = FIXTURES_DIR / "doc1.docx"
        if not file_path.exists():
            pytest.skip(f"Fixture not found: {file_path}")

        result = parser.parse(file_path)

        assert result.text is not None
        if result.section_titles:
            assert len(result.section_titles) > 0
            assert all(isinstance(title, str) for title in result.section_titles)

    @pytest.mark.parametrize(
        "filename",
        ["doc2.docx", "doc3.docx", "doc4.docx", "doc5.docx", "doc6.docx"],
    )
    def test_parse_various_docx(self, parser: DOCXParser, filename: str) -> None:
        """Test parsing various DOCX fixtures."""
        file_path = FIXTURES_DIR / filename
        if not file_path.exists():
            pytest.skip(f"Fixture not found: {file_path}")

        result = parser.parse(file_path)

        assert result.text is not None
        assert len(result.text) > 0
        assert result.metadata.page_count is not None
        assert result.metadata.page_count > 0
        assert len(result.pages) > 0


class TestParserFactoryIntegration:
    """Integration tests for ParserFactory with real files."""

    @pytest.fixture
    def factory(self) -> ParserFactory:
        return ParserFactory()

    def test_factory_parse_pdf(self, factory: ParserFactory) -> None:
        """Test factory correctly routes PDF to PDFParser."""
        file_path = FIXTURES_DIR / "simple.pdf"
        if not file_path.exists():
            pytest.skip(f"Fixture not found: {file_path}")

        result = factory.parse(file_path)

        assert result.text is not None
        assert result.metadata.file_type == ".pdf"

    def test_factory_parse_docx(self, factory: ParserFactory) -> None:
        """Test factory correctly routes DOCX to DOCXParser."""
        file_path = FIXTURES_DIR / "simple.docx"
        if not file_path.exists():
            pytest.skip(f"Fixture not found: {file_path}")

        result = factory.parse(file_path)

        assert result.text is not None
        assert result.metadata.file_type == ".docx"

    @pytest.mark.parametrize(
        "filename",
        [
            "simple.pdf",
            "pdf1.pdf",
            "simple.docx",
            "doc1.docx",
        ],
    )
    def test_factory_parse_mixed_formats(self, factory: ParserFactory, filename: str) -> None:
        """Test factory handles mixed document formats."""
        file_path = FIXTURES_DIR / filename
        if not file_path.exists():
            pytest.skip(f"Fixture not found: {file_path}")

        result = factory.parse(file_path)

        assert result.text is not None
        assert len(result.text) > 0
        assert result.metadata.page_count is not None
        assert result.metadata.page_count > 0

"""
Integration tests for document parsing with REAL files (no mocks).

These tests use actual PDF and DOCX files from tests/fixtures/documents/
and call real unstructured.io library to verify end-to-end parsing works.

IMPORTANT: You need to provide real test files in tests/fixtures/documents/:
- simple.pdf - A simple PDF with 1-2 pages, some text and a title
- simple.docx - A simple DOCX with sections and text
- corrupted.pdf - An intentionally corrupted/invalid PDF file

You can use any PDF/DOCX files you have. The tests will adapt to the content.
"""

from pathlib import Path

import pytest

from src.ingestion.parsers.exceptions import CorruptedFileError, UnsupportedFileTypeError
from src.ingestion.parsers.factory import ParserFactory
from src.ingestion.parsers.unstructured_parser import UnstructuredParser

# Path to test fixtures
FIXTURES_DIR = Path(__file__).parent.parent / "fixtures" / "documents"


def check_file_exists(filename: str) -> bool:
    """Check if test file exists."""
    return (FIXTURES_DIR / filename).exists()


def get_file_size(filename: str) -> int:
    """Get file size in bytes."""
    path = FIXTURES_DIR / filename
    return path.stat().st_size if path.exists() else 0


# Skip tests if files don't exist or are empty
skip_if_no_pdf = pytest.mark.skipif(
    not check_file_exists("simple.pdf") or get_file_size("simple.pdf") == 0,
    reason="simple.pdf not found or empty. Please add a real PDF file to tests/fixtures/documents/",
)

skip_if_no_docx = pytest.mark.skipif(
    not check_file_exists("simple.docx") or get_file_size("simple.docx") == 0,
    reason="simple.docx not found or empty. Please add a real DOCX file to tests/fixtures/documents/",
)

skip_if_no_corrupted = pytest.mark.skipif(
    not check_file_exists("corrupted.pdf"),
    reason="corrupted.pdf not found. Please add a corrupted PDF file to tests/fixtures/documents/",
)


class TestRealPDFParsing:
    """Integration tests with real PDF files."""

    @skip_if_no_pdf
    def test_parse_real_pdf_with_unstructured_parser(self) -> None:
        """
        Test: Parse a real PDF file using UnstructuredParser.

        This test uses the actual unstructured.io library (no mocks)
        to verify that parsing works end-to-end.

        Expected: Parser should extract text, metadata, and structure.
        """
        pdf_path = FIXTURES_DIR / "simple.pdf"
        parser = UnstructuredParser(strategy="fast")

        result = parser.parse(pdf_path)

        # Verify basic structure
        assert result is not None
        assert result.elements is not None
        assert len(result.elements) > 0, "PDF should contain at least one element"

        # Verify metadata
        assert result.metadata is not None
        assert result.metadata.file_type == ".pdf"
        assert result.metadata.file_size > 0

        # Print results for manual verification
        print(f"\n=== Parsed PDF: {pdf_path.name} ===")
        print(f"Elements: {len(result.elements)}")
        print(f"Page count: {result.metadata.page_count}")
        print(f"Title: {result.metadata.title}")
        print(f"Section titles: {result.section_titles}")
        print("\nFirst 3 elements:")
        for i, elem in enumerate(result.elements[:3], 1):
            print(f"  {i}. [{elem.element_type}] Page {elem.page_number}: {elem.text[:50]}...")

    @skip_if_no_pdf
    def test_parse_real_pdf_through_factory(self) -> None:
        """
        Test: Parse PDF through ParserFactory.

        Verifies that factory correctly routes to UnstructuredParser
        and parsing works end-to-end.
        """
        pdf_path = FIXTURES_DIR / "simple.pdf"
        factory = ParserFactory()
        factory._parsers = [UnstructuredParser(strategy="fast")]

        result = factory.parse(pdf_path)

        assert result is not None
        assert len(result.elements) > 0
        assert result.metadata.file_type == ".pdf"

    @skip_if_no_pdf
    def test_real_pdf_preserves_page_numbers(self) -> None:
        """
        Test: Verify that page numbers are preserved in parsed elements.

        This is critical for citation functionality.
        """
        pdf_path = FIXTURES_DIR / "simple.pdf"
        parser = UnstructuredParser(strategy="fast")

        result = parser.parse(pdf_path)

        # Check that at least some elements have page numbers
        elements_with_pages = [e for e in result.elements if e.page_number is not None]
        assert len(elements_with_pages) > 0, "At least some elements should have page numbers"

        # Verify page numbers are reasonable (positive integers)
        for elem in elements_with_pages:
            assert elem.page_number > 0, f"Page number should be positive, got {elem.page_number}"

    @skip_if_no_pdf
    def test_real_pdf_extracts_text_content(self) -> None:
        """
        Test: Verify that actual text content is extracted.

        Not just structure, but real text from the PDF.
        """
        pdf_path = FIXTURES_DIR / "simple.pdf"
        parser = UnstructuredParser(strategy="fast")

        result = parser.parse(pdf_path)

        # Verify we have text content
        total_text = "".join(elem.text for elem in result.elements)
        assert len(total_text) > 0, "Should extract some text content"
        assert len(total_text) > 10, "Should extract meaningful amount of text"

        print("\n=== Extracted text (first 200 chars) ===")
        print(total_text[:200])


class TestRealDOCXParsing:
    """Integration tests with real DOCX files."""

    @skip_if_no_docx
    def test_parse_real_docx_with_unstructured_parser(self) -> None:
        """
        Test: Parse a real DOCX file using UnstructuredParser.

        This test uses the actual unstructured.io library (no mocks).
        """
        docx_path = FIXTURES_DIR / "simple.docx"
        parser = UnstructuredParser()

        result = parser.parse(docx_path)

        # Verify basic structure
        assert result is not None
        assert result.elements is not None
        assert len(result.elements) > 0, "DOCX should contain at least one element"

        # Verify metadata
        assert result.metadata is not None
        assert result.metadata.file_type == ".docx"
        assert result.metadata.file_size > 0

        # Print results for manual verification
        print(f"\n=== Parsed DOCX: {docx_path.name} ===")
        print(f"Elements: {len(result.elements)}")
        print(f"Title: {result.metadata.title}")
        print(f"Section titles: {result.section_titles}")
        print("\nFirst 3 elements:")
        for i, elem in enumerate(result.elements[:3], 1):
            print(f"  {i}. [{elem.element_type}]: {elem.text[:50]}...")

    @skip_if_no_docx
    def test_parse_real_docx_through_factory(self) -> None:
        """
        Test: Parse DOCX through ParserFactory.
        """
        docx_path = FIXTURES_DIR / "simple.docx"
        factory = ParserFactory()

        result = factory.parse(docx_path)

        assert result is not None
        assert len(result.elements) > 0
        assert result.metadata.file_type == ".docx"

    @skip_if_no_docx
    def test_real_docx_extracts_section_titles(self) -> None:
        """
        Test: Verify that section titles are extracted from DOCX.

        If your DOCX has headings, they should be captured.
        """
        docx_path = FIXTURES_DIR / "simple.docx"
        parser = UnstructuredParser()

        result = parser.parse(docx_path)

        # Check for Title elements
        title_elements = [e for e in result.elements if e.element_type == "Title"]

        if len(title_elements) > 0:
            print(f"\n=== Found {len(title_elements)} titles ===")
            for title in title_elements:
                print(f"  - {title.text}")

            # If we found titles, section_titles should be populated
            assert result.section_titles is not None
            assert len(result.section_titles) > 0
        else:
            print("\n=== No titles found in DOCX (this is OK if your file has no headings) ===")


class TestRealFileErrorHandling:
    """Integration tests for error handling with real files."""

    @skip_if_no_corrupted
    def test_parse_corrupted_pdf_raises_error(self) -> None:
        """
        Test: Parsing a corrupted PDF should raise CorruptedFileError.

        Note: corrupted.pdf should be an invalid/corrupted PDF file.
        """
        corrupted_path = FIXTURES_DIR / "corrupted.pdf"
        parser = UnstructuredParser()

        with pytest.raises(CorruptedFileError) as exc_info:
            parser.parse(corrupted_path)

        assert exc_info.value.file_path == str(corrupted_path)
        print("\n=== Correctly caught corrupted file error ===")
        print(f"Error: {exc_info.value}")

    def test_parse_nonexistent_file_raises_error(self) -> None:
        """
        Test: Parsing a nonexistent file should raise FileNotFoundError.
        """
        nonexistent_path = FIXTURES_DIR / "does_not_exist.pdf"
        parser = UnstructuredParser()

        with pytest.raises(FileNotFoundError):
            parser.parse(nonexistent_path)

    def test_parse_unsupported_file_type_raises_error(self) -> None:
        """
        Test: Parsing an unsupported file type should raise UnsupportedFileTypeError.

        We'll create a temporary .txt file for this test.
        """
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".txt", delete=False) as tmp:
            tmp.write(b"This is a text file")
            tmp_path = Path(tmp.name)

        try:
            parser = UnstructuredParser()
            with pytest.raises(UnsupportedFileTypeError) as exc_info:
                parser.parse(tmp_path)

            assert exc_info.value.file_type == ".txt"
        finally:
            tmp_path.unlink()


class TestRealFilePerformance:
    """Performance tests with real files (optional)."""

    @skip_if_no_pdf
    def test_parse_pdf_completes_in_reasonable_time(self) -> None:
        """
        Test: PDF parsing should complete in reasonable time.

        This is a smoke test to catch performance regressions.
        """
        import time

        pdf_path = FIXTURES_DIR / "simple.pdf"
        parser = UnstructuredParser(strategy="fast")

        start = time.time()
        result = parser.parse(pdf_path)
        elapsed = time.time() - start

        print(f"\n=== Parsing took {elapsed:.2f} seconds ===")

        # Simple PDFs should parse quickly (adjust threshold as needed)
        assert elapsed < 30, f"Parsing took too long: {elapsed:.2f}s"
        assert result is not None


class TestFactoryWithRealFiles:
    """Integration tests for ParserFactory with real files."""

    @skip_if_no_pdf
    @skip_if_no_docx
    def test_factory_routes_different_file_types(self) -> None:
        """
        Test: Factory correctly routes PDF and DOCX to appropriate parsers.
        """
        factory = ParserFactory()
        factory._parsers = [UnstructuredParser(strategy="fast")]

        pdf_path = FIXTURES_DIR / "simple.pdf"
        docx_path = FIXTURES_DIR / "simple.docx"

        pdf_result = factory.parse(pdf_path)
        docx_result = factory.parse(docx_path)

        assert pdf_result.metadata.file_type == ".pdf"
        assert docx_result.metadata.file_type == ".docx"

        print("\n=== Factory routing test ===")
        print(f"PDF elements: {len(pdf_result.elements)}")
        print(f"DOCX elements: {len(docx_result.elements)}")

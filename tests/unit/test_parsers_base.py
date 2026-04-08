"""
Unit tests for base parser classes and data structures.

Tests cover:
1. ParsedElement - structure for storing document elements
2. DocumentMetadata - document metadata
3. ParsedDocument - parsing result
4. BaseParser - abstract parser interface
"""

from pathlib import Path

import pytest

from src.ingestion.parsers.base import (
    BaseParser,
    DocumentMetadata,
    ParsedDocument,
    ParsedElement,
)


class TestParsedElement:
    """
    Tests for ParsedElement - basic document element structure.

    ParsedElement represents a single element from a document (paragraph, heading, table).
    We verify it correctly stores data.
    """

    def test_create_parsed_element_with_all_fields(self) -> None:
        """
        Test: create element with all fields.

        Verify we can create ParsedElement with complete data:
        - text: element text
        - element_type: type (e.g., "Title", "Text")
        - page_number: page number
        - metadata: additional data
        """
        element = ParsedElement(
            text="Sample text content",
            element_type="Text",
            page_number=1,
            metadata={"font_size": 12, "bold": False},
        )

        assert element.text == "Sample text content"
        assert element.element_type == "Text"
        assert element.page_number == 1
        assert element.metadata == {"font_size": 12, "bold": False}

    def test_create_parsed_element_minimal(self) -> None:
        """
        Test: create element with minimal data.

        ParsedElement requires only text and element_type.
        page_number and metadata are optional (can be None).
        """
        element = ParsedElement(text="Minimal element", element_type="Text")

        assert element.text == "Minimal element"
        assert element.element_type == "Text"
        assert element.page_number is None  # Default is None
        assert element.metadata is None  # Default is None

    def test_parsed_element_with_page_number_only(self) -> None:
        """
        Test: element with page number but no metadata.

        Verify we can specify page_number without metadata.
        """
        element = ParsedElement(text="Text on page 5", element_type="Text", page_number=5)

        assert element.page_number == 5
        assert element.metadata is None


class TestDocumentMetadata:
    """
    Tests for DocumentMetadata - document metadata.

    DocumentMetadata stores document information: title, author, page count, etc.
    All fields are optional since not all documents contain metadata.
    """

    def test_create_metadata_with_all_fields(self) -> None:
        """
        Test: create metadata with all fields.

        Verify we can create a complete set of metadata.
        """
        metadata = DocumentMetadata(
            title="Test Document",
            author="John Doe",
            page_count=10,
            file_type=".pdf",
            file_size=1024,
            additional={"language": "en", "created_date": "2024-01-01"},
        )

        assert metadata.title == "Test Document"
        assert metadata.author == "John Doe"
        assert metadata.page_count == 10
        assert metadata.file_type == ".pdf"
        assert metadata.file_size == 1024
        assert metadata.additional == {"language": "en", "created_date": "2024-01-01"}

    def test_create_metadata_empty(self) -> None:
        """
        Test: create empty metadata.

        All DocumentMetadata fields are optional.
        This is important because not all documents contain metadata.
        """
        metadata = DocumentMetadata()

        assert metadata.title is None
        assert metadata.author is None
        assert metadata.page_count is None
        assert metadata.file_type is None
        assert metadata.file_size is None
        assert metadata.additional is None

    def test_create_metadata_partial(self) -> None:
        """
        Test: create metadata with partial data.

        Verify we can specify only some fields.
        For example, only title and page_count.
        """
        metadata = DocumentMetadata(title="Partial Metadata", page_count=5)

        assert metadata.title == "Partial Metadata"
        assert metadata.page_count == 5
        assert metadata.author is None  # Other fields are None


class TestParsedDocument:
    """
    Tests for ParsedDocument - document parsing result.

    ParsedDocument combines:
    - elements: list of document elements
    - metadata: metadata
    - section_titles: section headings (optional)
    """

    def test_create_parsed_document_with_elements(self) -> None:
        """
        Test: create ParsedDocument with elements and metadata.

        Verify we can create a complete parsing result.
        """
        elements = [
            ParsedElement(text="Title", element_type="Title", page_number=1),
            ParsedElement(text="Body text", element_type="Text", page_number=1),
        ]
        metadata = DocumentMetadata(title="Test", page_count=1)

        doc = ParsedDocument(elements=elements, metadata=metadata)

        assert len(doc.elements) == 2
        assert doc.elements[0].text == "Title"
        assert doc.metadata.title == "Test"
        assert doc.section_titles is None  # Default is None

    def test_create_parsed_document_with_section_titles(self) -> None:
        """
        Test: ParsedDocument with section titles.

        section_titles is a list of strings with document section headings.
        This is useful for navigation and understanding document structure.
        """
        elements = [ParsedElement(text="Content", element_type="Text", page_number=1)]
        metadata = DocumentMetadata(page_count=1)
        section_titles = ["Introduction", "Methods", "Results"]

        doc = ParsedDocument(elements=elements, metadata=metadata, section_titles=section_titles)

        assert doc.section_titles == ["Introduction", "Methods", "Results"]
        assert len(doc.section_titles) == 3

    def test_create_parsed_document_empty_elements(self) -> None:
        """
        Test: ParsedDocument with empty element list.

        Even if document contains no elements (e.g., empty PDF),
        we should be able to create ParsedDocument.
        """
        metadata = DocumentMetadata(page_count=0)
        doc = ParsedDocument(elements=[], metadata=metadata)

        assert len(doc.elements) == 0
        assert doc.metadata.page_count == 0


class TestBaseParser:
    """
    Tests for BaseParser - abstract parser interface.

    BaseParser is an abstract class (ABC) that defines the interface
    for all parsers. We cannot instantiate it directly, but we can create
    a test implementation to verify base functionality.
    """

    def test_cannot_instantiate_base_parser(self) -> None:
        """
        Test: cannot instantiate BaseParser directly.

        BaseParser is an abstract class. Python should raise TypeError
        when trying to instantiate it because abstract methods
        (parse, supported_extensions) are not implemented.
        """
        with pytest.raises(TypeError, match="Can't instantiate abstract class"):
            BaseParser()  # type: ignore

    def test_base_parser_supports_file_type(self) -> None:
        """
        Test: supports_file_type method checks file extension.

        BaseParser provides a default implementation of supports_file_type
        that checks file extension via supported_extensions().

        Create a test parser implementation to verify this logic.
        """

        # Create concrete BaseParser implementation for testing
        class TestParser(BaseParser):
            def parse(self, file_path: Path) -> ParsedDocument:
                """Dummy implementation."""
                return ParsedDocument(elements=[], metadata=DocumentMetadata())

            def supported_extensions(self) -> set[str]:
                """Support only .pdf and .docx."""
                return {".pdf", ".docx"}

        parser = TestParser()

        # Verify parser supports .pdf and .docx
        assert parser.supports_file_type(Path("document.pdf")) is True
        assert parser.supports_file_type(Path("document.docx")) is True

        # Verify parser does NOT support other formats
        assert parser.supports_file_type(Path("document.txt")) is False
        assert parser.supports_file_type(Path("image.jpg")) is False

    def test_base_parser_supports_file_type_case_insensitive(self) -> None:
        """
        Test: supports_file_type works case-insensitively.

        File extensions should be checked case-insensitively:
        .PDF, .pdf, .Pdf - all should work.
        """

        class TestParser(BaseParser):
            def parse(self, file_path: Path) -> ParsedDocument:
                return ParsedDocument(elements=[], metadata=DocumentMetadata())

            def supported_extensions(self) -> set[str]:
                return {".pdf"}  # Specify in lowercase

        parser = TestParser()

        # All case variations should work
        assert parser.supports_file_type(Path("document.pdf")) is True
        assert parser.supports_file_type(Path("document.PDF")) is True
        assert parser.supports_file_type(Path("document.Pdf")) is True

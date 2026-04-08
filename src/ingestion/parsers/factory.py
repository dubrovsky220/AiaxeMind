"""
Parser factory for routing documents to appropriate parsers.

This module provides a factory pattern for selecting the correct parser
based on file type, making it easy to add new parsers in the future.
"""

from pathlib import Path

from src.core.logging_config import get_logger
from src.ingestion.parsers.base import BaseParser, ParsedDocument
from src.ingestion.parsers.exceptions import UnsupportedFileTypeError
from src.ingestion.parsers.unstructured_parser import UnstructuredParser

logger = get_logger(__name__)


class ParserFactory:
    """
    Factory for creating and routing to appropriate document parsers.

    The factory maintains a registry of parsers and their supported
    file types, automatically selecting the correct parser based on
    file extension.

    Example:
        factory = ParserFactory()
        document = factory.parse(Path("report.pdf"))

        # Or get parser instance
        parser = factory.get_parser(Path("document.docx"))
        document = parser.parse(Path("document.docx"))
    """

    def __init__(self) -> None:
        """
        Initialize ParserFactory with default parsers.

        Default parsers:
        - UnstructuredParser: PDF, DOCX
        """
        self._parsers: list[BaseParser] = []
        self._register_default_parsers()

        logger.info("ParserFactory initialized", extra={"parser_count": len(self._parsers)})

    def _register_default_parsers(self) -> None:
        """Register default parsers."""
        self.register_parser(UnstructuredParser())

    def register_parser(self, parser: BaseParser) -> None:
        """
        Register a new parser.

        Args:
            parser: Parser instance to register

        Note:
            Parsers are checked in registration order. Register more
            specific parsers before generic ones.
        """
        self._parsers.append(parser)
        logger.debug(
            "Parser registered",
            extra={
                "parser_class": parser.__class__.__name__,
                "supported_extensions": list(parser.supported_extensions()),
            },
        )

    def get_parser(self, file_path: Path) -> BaseParser:
        """
        Get the appropriate parser for a file.

        Args:
            file_path: Path to the file to parse

        Returns:
            Parser instance that supports the file type

        Raises:
            UnsupportedFileTypeError: If no parser supports the file type
        """
        for parser in self._parsers:
            if parser.supports_file_type(file_path):
                logger.debug(
                    "Parser selected",
                    extra={"file_path": str(file_path), "parser_class": parser.__class__.__name__},
                )
                return parser

        # No parser found
        raise UnsupportedFileTypeError(file_path=str(file_path), file_type=file_path.suffix)

    def parse(self, file_path: Path) -> ParsedDocument:
        """
        Parse a document using the appropriate parser.

        Args:
            file_path: Path to the document to parse

        Returns:
            ParsedDocument with elements, metadata, and section titles

        Raises:
            UnsupportedFileTypeError: If no parser supports the file type
            CorruptedFileError: If the file is corrupted
            ParsingError: For other parsing errors

        Example:
            factory = ParserFactory()
            document = factory.parse(Path("report.pdf"))
            print(f"Parsed {len(document.elements)} elements")
        """
        parser = self.get_parser(file_path)

        logger.info(
            "Parsing document",
            extra={"file_path": str(file_path), "parser_class": parser.__class__.__name__},
        )

        return parser.parse(file_path)

    def supported_extensions(self) -> set[str]:
        """
        Get all supported file extensions across all registered parsers.

        Returns:
            Set of supported file extensions (lowercase, with dot)

        Example:
            factory = ParserFactory()
            extensions = factory.supported_extensions()
            # {'.pdf', '.docx', '.doc'}
        """
        extensions: set[str] = set()
        for parser in self._parsers:
            extensions.update(parser.supported_extensions())
        return extensions


def main() -> None:
    """
    CLI tool for testing document parsing.

    Usage:
        uv run python -m src.ingestion.parsers.factory path/to/document.pdf
        uv run python -m src.ingestion.parsers.factory tests/fixtures/documents/simple.pdf
    """
    import sys
    from collections import Counter

    if len(sys.argv) < 2:
        print("Usage: uv run python -m src.ingestion.parsers.factory <file_path>")
        print("\nExample:")
        print(
            "  uv run python -m src.ingestion.parsers.factory tests/fixtures/documents/simple.pdf"
        )
        sys.exit(1)

    file_path = Path(sys.argv[1])

    if not file_path.exists():
        print(f"Error: File not found: {file_path}")
        sys.exit(1)

    print("=" * 70)
    print(f"PARSING: {file_path.name}")
    print("=" * 70)

    try:
        parser = UnstructuredParser(strategy="fast")
        result = parser.parse(file_path)

        # 1. Metadata
        print("\n📄 METADATA")
        print("-" * 70)
        print(f"  Title:      {result.metadata.title or 'N/A'}")
        print(f"  Pages:      {result.metadata.page_count or 'N/A'}")
        print(f"  File Type:  {result.metadata.file_type}")
        print(
            f"  File Size:  {result.metadata.file_size:,} bytes"
            if result.metadata.file_size
            else "  File Size:  N/A"
        )

        # 2. Element statistics
        print("\n📊 ELEMENT STATISTICS")
        print("-" * 70)
        print(f"  Total Elements: {len(result.elements)}")

        element_types = Counter(elem.element_type for elem in result.elements)
        print("\n  Element Types:")
        for elem_type, count in element_types.most_common():
            print(f"    - {elem_type}: {count}")

        # 3. Section titles
        print("\n📑 SECTION TITLES")
        print("-" * 70)
        if result.section_titles:
            for i, title in enumerate(result.section_titles, 1):
                print(f"  {i}. {title}")
        else:
            print("  No section titles found")

        # 4. Sample elements
        print("\n📝 SAMPLE ELEMENTS (first 5)")
        print("-" * 70)
        for i, elem in enumerate(result.elements[:5], 1):
            text_preview = elem.text[:80].replace("\n", " ")
            if len(elem.text) > 80:
                text_preview += "..."
            print(f"\n  Element {i}:")
            print(f"    Type:  {elem.element_type}")
            print(f"    Page:  {elem.page_number or 'N/A'}")
            print(f"    Text:  {text_preview}")
            if elem.metadata:
                print(f"    Meta:  {list(elem.metadata.keys())}")

        # 5. Full text preview
        print("\n📖 FULL TEXT PREVIEW (first 500 chars)")
        print("-" * 70)
        full_text = "\n".join(elem.text for elem in result.elements)
        print(full_text[:500])
        if len(full_text) > 500:
            print("\n... (truncated)")

        print("\n" + "=" * 70)
        print("✅ PARSING COMPLETE")
        print("=" * 70)

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()

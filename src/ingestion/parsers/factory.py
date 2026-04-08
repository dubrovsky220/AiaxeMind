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
        # Register UnstructuredParser for PDF and DOCX
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

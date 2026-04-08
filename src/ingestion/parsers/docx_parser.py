"""
DOCXParser implementation using python-docx.

Text extraction from DOCX files with estimated page numbers and heading detection.
"""

import os
from pathlib import Path

from docx import Document

from src.core.logging_config import get_logger
from src.ingestion.parsers.base import (
    BaseParser,
    DocumentMetadata,
    PageContent,
    ParsedDocument,
)
from src.ingestion.parsers.exceptions import (
    CorruptedFileError,
    UnsupportedFileTypeError,
)

logger = get_logger(__name__)

CHARS_PER_PAGE = 2500


class DOCXParser(BaseParser):
    """Parser for DOCX documents using python-docx."""

    def __init__(self) -> None:
        logger.info("DOCXParser initialized")

    def supported_extensions(self) -> set[str]:
        return {".docx", ".doc"}

    def parse(self, file_path: Path) -> ParsedDocument:
        logger.info("Starting DOCX parsing", extra={"file_path": str(file_path)})

        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if not self.supports_file_type(file_path):
            raise UnsupportedFileTypeError(file_path=str(file_path), file_type=file_path.suffix)

        try:
            doc = Document(file_path)
            pages = self._extract_pages(doc)
            metadata = self._extract_metadata(file_path, doc)
            section_titles = self._extract_section_titles(pages)
            full_text = "\n\n".join(page.text for page in pages)

            logger.info(
                "DOCX parsing completed",
                extra={
                    "file_path": str(file_path),
                    "page_count": len(pages),
                    "section_count": len(section_titles) if section_titles else 0,
                },
            )

            return ParsedDocument(
                text=full_text,
                metadata=metadata,
                pages=pages,
                section_titles=section_titles,
            )

        except UnsupportedFileTypeError:
            raise

        except Exception as e:
            logger.error(
                "DOCX parsing failed", extra={"file_path": str(file_path), "error": str(e)}
            )
            raise CorruptedFileError(file_path=str(file_path), original_error=e)

    def _extract_pages(self, doc: Document) -> list[PageContent]:
        pages_dict: dict[int, dict] = {}
        char_count = 0

        for para in doc.paragraphs:
            text = para.text.strip()
            if not text:
                continue

            page_num = (char_count // CHARS_PER_PAGE) + 1
            char_count += len(text)

            if page_num not in pages_dict:
                pages_dict[page_num] = {"texts": [], "headings": []}

            is_heading = para.style.name.startswith("Heading")
            if is_heading:
                pages_dict[page_num]["headings"].append(text)

            pages_dict[page_num]["texts"].append(text)

        pages = []
        for page_num in sorted(pages_dict.keys()):
            page_data = pages_dict[page_num]
            page_text = "\n".join(page_data["texts"])
            headings = page_data["headings"] if page_data["headings"] else None

            pages.append(
                PageContent(
                    page_number=page_num,
                    text=page_text,
                    headings=headings,
                    images=None,
                    tables=None,
                )
            )

        return pages

    def _extract_section_titles(self, pages: list[PageContent]) -> list[str] | None:
        all_titles = []
        for page in pages:
            if page.headings:
                all_titles.extend(page.headings)
        return all_titles if all_titles else None

    def _extract_metadata(self, file_path: Path, doc: Document) -> DocumentMetadata:
        try:
            file_size = os.path.getsize(file_path)
            core_props = doc.core_properties

            title = core_props.title or file_path.stem
            if title:
                title = title.strip()
            if not title:
                title = file_path.stem

            author = core_props.author or None
            if author:
                author = author.strip()
                if not author:
                    author = None

            total_chars = sum(len(para.text) for para in doc.paragraphs)
            page_count = (total_chars // CHARS_PER_PAGE) + 1

            return DocumentMetadata(
                title=title,
                author=author,
                page_count=page_count,
                file_type=file_path.suffix.lower(),
                file_size=file_size,
                additional=None,
            )

        except Exception as e:
            logger.warning("DOCX metadata extraction failed", extra={"error": str(e)})
            return DocumentMetadata(
                title=file_path.stem,
                file_type=file_path.suffix.lower(),
                file_size=os.path.getsize(file_path) if file_path.exists() else None,
                page_count=1,
            )

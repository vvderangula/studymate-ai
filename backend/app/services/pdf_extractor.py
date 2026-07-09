"""Service for extracting raw text from a PDF file."""

from pathlib import Path

from pypdf import PdfReader


class PDFExtractionError(Exception):
    """Raised when a PDF cannot be read or contains no extractable text."""


class PDFExtractor:
    """Extracts plain text from a PDF document.

    Single responsibility: read a PDF file and return its text content,
    concatenated across all pages.
    """

    def extract(self, path: Path) -> str:
        """Extract and return the full text of a PDF.

        Args:
            path: Filesystem path to the PDF file.

        Returns:
            The document's text with pages separated by blank lines.

        Raises:
            PDFExtractionError: If the file cannot be parsed or has no text.
        """

        text = "\n\n".join(page.strip() for page in self.extract_pages(path) if page.strip())
        if not text:
            raise PDFExtractionError("No extractable text found in the PDF.")

        return text

    def extract_pages(self, path: Path) -> list[str]:
        """Extract text for each page of a PDF.

        Returns one entry per page, using an empty string for pages without
        extractable text (e.g. scanned images). Only raises when the file
        itself cannot be read.

        Args:
            path: Filesystem path to the PDF file.

        Returns:
            A list of per-page text strings in document order.

        Raises:
            PDFExtractionError: If the file cannot be parsed.
        """

        try:
            reader = PdfReader(str(path))
            return [page.extract_text() or "" for page in reader.pages]
        except Exception as exc:  # noqa: BLE001 - normalize library errors
            raise PDFExtractionError("Failed to read the PDF file.") from exc

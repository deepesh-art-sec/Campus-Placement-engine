"""
Multi-Format Document Loader.
Loads and extracts text and tables from:
  - Pasted plain text / .txt
  - Email messages (.eml)
  - Portable Document Format (.pdf) via pdfplumber with scanned detection
  - Word documents (.docx) via python-docx
  - Optional OCR via pytesseract (behind OCR_ENABLED flag)
"""

from __future__ import annotations

import io
import os
from email import policy
from email.parser import BytesParser

import docx
import pdfplumber

from backend.app.extract.cleaner import clean_text


class ScannedPdfError(Exception):
    """Raised when a PDF contains no extractable text layer and OCR is disabled."""
    pass


class DocumentLoader:
    """Loads document files into cleaned plaintext."""

    def __init__(self, ocr_enabled: bool = False) -> None:
        self.ocr_enabled = ocr_enabled or (os.getenv("OCR_ENABLED", "false").lower() == "true")

    def load_from_bytes(self, content: bytes, filename: str) -> str:
        ext = os.path.splitext(filename)[1].lower()

        if ext in (".txt", ".text", ""):
            return self.load_text(content.decode("utf-8", errors="replace"))
        elif ext == ".eml":
            return self.load_eml(content)
        elif ext == ".pdf":
            return self.load_pdf(content)
        elif ext in (".docx", ".doc"):
            return self.load_docx(content)
        else:
            raise ValueError(f"Unsupported document format '{ext}' for file '{filename}'.")

    def load_text(self, text: str) -> str:
        return clean_text(text)

    def load_eml(self, content: bytes) -> str:
        msg = BytesParser(policy=policy.default).parsebytes(content)
        subject = msg.get("Subject", "")
        sender = msg.get("From", "")
        body = ""

        # Extract body
        body_part = msg.get_body(preferencelist=("plain", "html"))
        if body_part:
            body = body_part.get_content()

        full_content = f"Subject: {subject}\nFrom: {sender}\n\n{body}"
        return clean_text(full_content)

    def load_docx(self, content: bytes) -> str:
        doc = docx.Document(io.BytesIO(content))
        lines = []

        # Extract paragraphs
        for para in doc.paragraphs:
            if para.text.strip():
                lines.append(para.text.strip())

        # Extract tables
        for table in doc.tables:
            for row in table.rows:
                row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_cells:
                    lines.append(" | ".join(row_cells))

        return clean_text("\n".join(lines))

    def load_pdf(self, content: bytes) -> str:
        lines = []
        total_text_chars = 0

        with pdfplumber.open(io.BytesIO(content)) as pdf:
            for _page_idx, page in enumerate(pdf.pages):
                # Extract text
                page_text = page.extract_text() or ""
                total_text_chars += len(page_text.strip())
                if page_text.strip():
                    lines.append(page_text.strip())

                # Extract tables
                tables = page.extract_tables() or []
                for table in tables:
                    for row in table:
                        clean_row = [str(c).strip() for c in row if c is not None and str(c).strip()]
                        if clean_row:
                            lines.append(" | ".join(clean_row))

        # Scanned PDF Detection
        if total_text_chars < 30:
            if self.ocr_enabled:
                ocr_text = self._try_ocr_pdf(content)
                if ocr_text:
                    return clean_text(ocr_text)
            raise ScannedPdfError(
                "Scanned PDF detected without embedded text layer. "
                "Document contains no readable text. Please provide a digital PDF or enable OCR."
            )

        return clean_text("\n".join(lines))

    def _try_ocr_pdf(self, content: bytes) -> str | None:
        """Attempts OCR if pytesseract is installed and enabled."""
        try:
            import pdf2image  # type: ignore[import-not-found]
            import pytesseract  # type: ignore[import-not-found]
            images = pdf2image.convert_from_bytes(content)
            ocr_pages = [str(pytesseract.image_to_string(img)) for img in images]
            return "\n".join(ocr_pages)
        except Exception:
            return None

"""
Multi-Format Document Loader.
Loads and extracts text and tables from:
  - Pasted plain text / .txt (UTF-8)
  - Portable Document Format (.pdf) via PyMuPDF (`fitz`) with table detection
  - Scanned PDF OCR fallback via Tesseract OCR (`pytesseract`)
  - Word documents (.docx) via `python-docx`
  - Email messages (.eml)
"""

from __future__ import annotations

import io
import os
import zipfile
from email import policy
from email.parser import BytesParser

import docx
import fitz  # PyMuPDF
from PIL import Image

from backend.app.extract.cleaner import clean_text


class EmptyDocumentError(ValueError):
    """Raised when an uploaded document contains no bytes or only whitespace."""
    pass


class CorruptDocumentError(ValueError):
    """Raised when an uploaded document file is corrupt or unreadable."""
    pass


class UnsupportedFormatError(ValueError):
    """Raised when an uploaded file has an unsupported extension or MIME type."""
    pass


class ScannedPdfError(Exception):
    """Raised when a PDF contains no extractable digital text layer and OCR is unavailable or fails."""
    pass


def _configure_tesseract_path() -> None:
    """Auto-detects Tesseract OCR executable on Windows systems if not already in PATH."""
    try:
        import pytesseract
        env_cmd = os.getenv("TESSERACT_CMD")
        if env_cmd and os.path.exists(env_cmd):
            pytesseract.pytesseract.tesseract_cmd = env_cmd
            return

        common_win_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe"),
            os.path.expandvars(r"%USERPROFILE%\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
        ]
        for p in common_win_paths:
            if os.path.exists(p):
                pytesseract.pytesseract.tesseract_cmd = p
                break
    except Exception:
        pass


_configure_tesseract_path()


class DocumentLoader:
    """Loads document files into cleaned plaintext using PyMuPDF, python-docx, UTF-8, and Tesseract OCR."""

    def __init__(self, ocr_enabled: bool = True) -> None:
        self.ocr_enabled = ocr_enabled

    def load_from_bytes(self, content: bytes, filename: str) -> str:
        if not content or len(content) == 0:
            raise EmptyDocumentError(f"Uploaded file '{filename}' is empty (0 bytes).")

        ext = os.path.splitext(filename)[1].lower()

        if ext in (".txt", ".text", ""):
            return self.load_text_bytes(content, filename)
        elif ext == ".eml":
            return self.load_eml(content, filename)
        elif ext == ".pdf":
            return self.load_pdf(content, filename)
        elif ext in (".docx", ".doc"):
            return self.load_docx(content, filename)
        else:
            raise UnsupportedFormatError(
                f"Unsupported document format '{ext}' for file '{filename}'. Supported formats: PDF (.pdf), DOCX (.docx), TXT (.txt), EML (.eml)."
            )

    def load_text_bytes(self, content: bytes, filename: str = "document.txt") -> str:
        if not content or len(content) == 0:
            raise EmptyDocumentError(f"Uploaded file '{filename}' is empty (0 bytes).")
        if len(content.strip()) == 0:
            raise EmptyDocumentError(f"Text document '{filename}' contains only whitespace or blank lines.")

        try:
            raw_text = content.decode("utf-8")
        except UnicodeDecodeError:
            try:
                raw_text = content.decode("utf-8-sig")
            except UnicodeDecodeError:
                try:
                    raw_text = content.decode("latin-1")
                except Exception as exc:
                    raise CorruptDocumentError(f"Failed to decode text document '{filename}': {str(exc)}") from exc

        cleaned = clean_text(raw_text)
        if not cleaned or not cleaned.strip():
            raise EmptyDocumentError(f"Text document '{filename}' contains only whitespace or blank lines.")
        return cleaned

    def load_text(self, text: str) -> str:
        if not text or not text.strip():
            raise EmptyDocumentError("Supplied text is empty or contains only whitespace.")
        return clean_text(text)

    def load_eml(self, content: bytes, filename: str = "document.eml") -> str:
        if not content or len(content) == 0:
            raise EmptyDocumentError(f"Email document '{filename}' is empty (0 bytes).")
        try:
            msg = BytesParser(policy=policy.default).parsebytes(content)
        except Exception as exc:
            raise CorruptDocumentError(f"Failed to parse email message '{filename}': {str(exc)}") from exc

        subject = msg.get("Subject", "")
        sender = msg.get("From", "")
        body = ""

        # Extract body
        body_part = msg.get_body(preferencelist=("plain", "html"))
        if body_part:
            body = body_part.get_content()

        full_content = f"Subject: {subject}\nFrom: {sender}\n\n{body}"
        cleaned = clean_text(full_content)
        if not cleaned or not cleaned.strip():
            raise EmptyDocumentError(f"Email document '{filename}' contains no readable content.")
        return cleaned

    def load_docx(self, content: bytes, filename: str = "document.docx") -> str:
        if not content or len(content) == 0:
            raise EmptyDocumentError(f"Word document '{filename}' is empty (0 bytes).")

        try:
            doc = docx.Document(io.BytesIO(content))
        except (docx.opc.exceptions.PackageNotFoundError, zipfile.BadZipFile, Exception) as exc:
            raise CorruptDocumentError(f"Corrupt or invalid Word document (.docx) '{filename}': {str(exc)}") from exc

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

        full_text = "\n".join(lines).strip()
        if not full_text:
            raise EmptyDocumentError(f"Word document '{filename}' contains no extractable text or paragraphs.")

        return clean_text(full_text)

    def load_pdf(self, content: bytes, filename: str = "document.pdf") -> str:
        if not content or len(content) == 0:
            raise EmptyDocumentError(f"PDF document '{filename}' is empty (0 bytes).")

        try:
            doc = fitz.open(stream=content, filetype="pdf")
        except Exception as exc:
            raise CorruptDocumentError(f"Corrupt or invalid PDF file '{filename}': {str(exc)}") from exc

        if doc.page_count == 0:
            raise EmptyDocumentError(f"PDF document '{filename}' contains 0 pages.")

        lines = []
        total_text_chars = 0

        try:
            for page_idx, page in enumerate(doc):
                # Extract text layer via PyMuPDF
                page_text = page.get_text() or ""
                total_text_chars += len(page_text.strip())
                if page_text.strip():
                    lines.append(page_text.strip())

                # Extract tables if available in PyMuPDF
                try:
                    tabs = page.find_tables()
                    for t in tabs:
                        df = t.extract()
                        for row in df:
                            clean_row = [str(c).strip() for c in row if c is not None and str(c).strip()]
                            if clean_row:
                                lines.append(" | ".join(clean_row))
                except Exception:
                    pass
        except Exception as exc:
            raise CorruptDocumentError(f"Error reading pages from PDF '{filename}': {str(exc)}") from exc

        # Scanned PDF Detection: when total characters extracted is negligible (< 30)
        if total_text_chars < 30:
            if self.ocr_enabled:
                ocr_text = self._try_ocr_pdf(doc, filename)
                if ocr_text:
                    return clean_text(ocr_text)
            raise ScannedPdfError(
                f"Scanned PDF detected without embedded text layer in '{filename}'. "
                "Document contains no readable text. Please provide a digital PDF or enable OCR."
            )

        full_text = "\n".join(lines).strip()
        return clean_text(full_text)

    def _try_ocr_pdf(self, doc: fitz.Document, filename: str) -> str:
        """Attempts OCR on each page of a scanned PDF using PyMuPDF pixmaps and pytesseract."""
        try:
            import pytesseract
        except ImportError as exc:
            raise ScannedPdfError(
                f"Scanned PDF detected in '{filename}', but pytesseract is not installed on this system."
            ) from exc

        ocr_pages = []
        try:
            for page in doc:
                pix = page.get_pixmap(dpi=150)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                page_text = pytesseract.image_to_string(img)
                if page_text and page_text.strip():
                    ocr_pages.append(page_text.strip())
        except (pytesseract.TesseractNotFoundError, FileNotFoundError) as exc:
            raise ScannedPdfError(
                f"Scanned PDF detected without embedded text layer in '{filename}'. "
                "Tesseract OCR binary was not found on PATH or host system. "
                "Please install Tesseract-OCR (https://github.com/tesseract-ocr/tesseract) or upload a digital document."
            ) from exc
        except Exception as exc:
            raise ScannedPdfError(
                f"OCR processing failed for scanned PDF '{filename}': {str(exc)}"
            ) from exc

        result = "\n\n".join(ocr_pages).strip()
        if not result or len(result) < 15:
            raise ScannedPdfError(
                f"Scanned PDF detected in '{filename}', but OCR extracted no readable characters. "
                "Please ensure the scanned image is clear, legible, and uncorrupted."
            )
        return result

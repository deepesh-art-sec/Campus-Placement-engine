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
from pydantic import BaseModel, ConfigDict, Field


class DocumentChunk(BaseModel):
    """Represents a text chunk or table extracted from a specific page of a document."""
    model_config = ConfigDict(frozen=True)

    page_number: int = 1
    text: str
    chunk_type: str = "text"  # "text", "heading", "table", "ocr_page"



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
    """Auto-detects Tesseract OCR executable and tessdata on Windows systems if not already in PATH."""
    try:
        import pytesseract
        env_cmd = os.getenv("TESSERACT_CMD")
        if env_cmd and os.path.exists(env_cmd):
            pytesseract.pytesseract.tesseract_cmd = env_cmd
            tess_dir = os.path.dirname(env_cmd)
            for cand in [os.path.join(tess_dir, "tessdata"), os.path.join(os.path.dirname(tess_dir), "tessdata")]:
                if os.path.exists(cand) and "TESSDATA_PREFIX" not in os.environ:
                    os.environ["TESSDATA_PREFIX"] = cand
                    break
            return

        common_win_paths = [
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\bin\tesseract.exe"),
            os.path.expandvars(r"%LOCALAPPDATA%\Programs\Tesseract-OCR\tesseract.exe"),
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
            os.path.expandvars(r"%USERPROFILE%\AppData\Local\Programs\Tesseract-OCR\tesseract.exe"),
        ]
        for p in common_win_paths:
            if os.path.exists(p):
                pytesseract.pytesseract.tesseract_cmd = p
                tess_dir = os.path.dirname(p)
                for cand in [os.path.join(tess_dir, "tessdata"), os.path.join(os.path.dirname(tess_dir), "tessdata")]:
                    if os.path.exists(cand) and "TESSDATA_PREFIX" not in os.environ:
                        os.environ["TESSDATA_PREFIX"] = cand
                        break
                break
    except Exception:
        pass


_configure_tesseract_path()


class DocumentLoader:
    """Loads document files into cleaned plaintext using PyMuPDF, python-docx, UTF-8, and Tesseract OCR."""

    def __init__(self, ocr_enabled: bool = True) -> None:
        self.ocr_enabled = ocr_enabled

    def load_structured(self, content: bytes, filename: str) -> tuple[str, list[DocumentChunk], int]:
        """
        Loads document bytes and returns:
          - full_cleaned_text: unified string
          - chunks: list of DocumentChunk with 1-based page numbers and chunk types
          - page_count: total pages
        """
        if not content or len(content) == 0:
            raise EmptyDocumentError(f"Uploaded file '{filename}' is empty (0 bytes).")

        ext = os.path.splitext(filename)[1].lower()

        if ext in (".txt", ".text", ""):
            full = self.load_text_bytes(content, filename)
            chunks = [DocumentChunk(page_number=1, text=line, chunk_type="text") for line in full.split("\n") if line.strip()]
            return full, chunks, 1
        elif ext == ".eml":
            full = self.load_eml(content, filename)
            chunks = [DocumentChunk(page_number=1, text=line, chunk_type="text") for line in full.split("\n") if line.strip()]
            return full, chunks, 1
        elif ext in (".docx", ".doc"):
            return self._load_docx_structured(content, filename)
        elif ext == ".pdf":
            return self._load_pdf_structured(content, filename)
        else:
            raise UnsupportedFormatError(
                f"Unsupported document format '{ext}' for file '{filename}'. Supported formats: PDF (.pdf), DOCX (.docx), TXT (.txt), EML (.eml)."
            )

    def _load_docx_structured(self, content: bytes, filename: str) -> tuple[str, list[DocumentChunk], int]:
        try:
            doc = docx.Document(io.BytesIO(content))
        except (docx.opc.exceptions.PackageNotFoundError, zipfile.BadZipFile, Exception) as exc:
            raise CorruptDocumentError(f"Corrupt or invalid Word document (.docx) '{filename}': {str(exc)}") from exc

        chunks: list[DocumentChunk] = []
        lines: list[str] = []
        current_page = 1

        for para in doc.paragraphs:
            text = para.text.strip()
            if text:
                chunk_type = "heading" if para.style and "heading" in para.style.name.lower() else "text"
                chunks.append(DocumentChunk(page_number=current_page, text=text, chunk_type=chunk_type))
                lines.append(text)
            # Detect page breaks in XML runs
            for run in para.runs:
                if "w:br" in run._r.xml and 'type="page"' in run._r.xml:
                    current_page += 1

        for table in doc.tables:
            for row in table.rows:
                cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if cells:
                    row_text = " | ".join(cells)
                    chunks.append(DocumentChunk(page_number=current_page, text=row_text, chunk_type="table"))
                    lines.append(row_text)

        full_text = clean_text("\n".join(lines).strip())
        if not full_text:
            raise EmptyDocumentError(f"Word document '{filename}' contains no extractable text or paragraphs.")
        return full_text, chunks, current_page

    def _load_pdf_structured(self, content: bytes, filename: str) -> tuple[str, list[DocumentChunk], int]:
        try:
            doc = fitz.open(stream=content, filetype="pdf")
        except Exception as exc:
            raise CorruptDocumentError(f"Corrupt or invalid PDF file '{filename}': {str(exc)}") from exc

        if doc.page_count == 0:
            raise EmptyDocumentError(f"PDF document '{filename}' contains 0 pages.")

        chunks: list[DocumentChunk] = []
        lines: list[str] = []
        total_text_chars = 0

        try:
            for page_idx, page in enumerate(doc):
                pg_num = page_idx + 1
                page_text = page.get_text() or ""
                stripped = page_text.strip()
                total_text_chars += len(stripped)

                if stripped:
                    for line in stripped.split("\n"):
                        l_clean = line.strip()
                        if l_clean:
                            chunks.append(DocumentChunk(page_number=pg_num, text=l_clean, chunk_type="text"))
                            lines.append(l_clean)

                try:
                    tabs = page.find_tables()
                    for t in tabs:
                        df = t.extract()
                        for row in df:
                            clean_row = [str(c).strip() for c in row if c is not None and str(c).strip()]
                            if clean_row:
                                t_line = " | ".join(clean_row)
                                chunks.append(DocumentChunk(page_number=pg_num, text=t_line, chunk_type="table"))
                                lines.append(t_line)
                except Exception:
                    pass
        except Exception as exc:
            raise CorruptDocumentError(f"Error reading pages from PDF '{filename}': {str(exc)}") from exc

        if total_text_chars < 30:
            if self.ocr_enabled:
                ocr_text, ocr_chunks = self._try_ocr_pdf_structured(doc, filename)
                return ocr_text, ocr_chunks, doc.page_count
            raise ScannedPdfError(
                f"Scanned PDF detected without embedded text layer in '{filename}'. "
                "Document contains no readable text. Please provide a digital PDF or enable OCR."
            )

        full_text = clean_text("\n".join(lines).strip())
        return full_text, chunks, doc.page_count

    def _validate_ocr_quality(self, text: str, page_num: int, filename: str) -> None:
        """Validates OCR extraction quality to reject garbled, corrupt, or noisy scans."""
        if not text or len(text.strip()) < 10:
            raise ScannedPdfError(
                f"Scanned PDF '{filename}' (page {page_num}) yielded insufficient OCR text (< 10 chars). "
                "The image may be blank, too low resolution, or corrupted."
            )
        printable = sum(1 for c in text if c.isprintable())
        alnum = sum(1 for c in text if c.isalnum())
        total = max(len(text), 1)

        # If non-printable or symbol noise exceeds 65% of characters
        if alnum / total < 0.25:
            raise ScannedPdfError(
                f"Garbled OCR output detected on page {page_num} of '{filename}'. "
                f"Readable alphanumeric density is too low ({alnum}/{total} characters). "
                "Document quality is insufficient for accurate requirement extraction."
            )

    def _try_ocr_pdf_structured(self, doc: fitz.Document, filename: str) -> tuple[str, list[DocumentChunk]]:
        try:
            import pytesseract
        except ImportError as exc:
            raise ScannedPdfError(
                f"Scanned PDF detected in '{filename}', but pytesseract is not installed on this system."
            ) from exc

        ocr_chunks: list[DocumentChunk] = []
        all_lines: list[str] = []

        try:
            for page_idx, page in enumerate(doc):
                pg_num = page_idx + 1
                pix = page.get_pixmap(dpi=200)
                img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
                page_text = pytesseract.image_to_string(img)
                cleaned_page = page_text.strip()
                if cleaned_page:
                    self._validate_ocr_quality(cleaned_page, pg_num, filename)
                    for l in cleaned_page.split("\n"):
                        l_clean = l.strip()
                        if l_clean:
                            ocr_chunks.append(DocumentChunk(page_number=pg_num, text=l_clean, chunk_type="ocr_page"))
                            all_lines.append(l_clean)
        except ScannedPdfError:
            raise
        except (pytesseract.TesseractNotFoundError, FileNotFoundError) as exc:
            raise ScannedPdfError(
                f"Scanned PDF detected without embedded text layer in '{filename}'. "
                "Tesseract OCR binary was not found on PATH or host system."
            ) from exc
        except Exception as exc:
            raise ScannedPdfError(f"OCR processing failed for scanned PDF '{filename}': {str(exc)}") from exc

        full_text = clean_text("\n".join(all_lines).strip())
        if not full_text or len(full_text) < 15:
            raise ScannedPdfError(
                f"Scanned PDF detected in '{filename}', but OCR extracted no readable characters. "
                "Please ensure the scanned image is clear, legible, and uncorrupted."
            )
        return full_text, ocr_chunks

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

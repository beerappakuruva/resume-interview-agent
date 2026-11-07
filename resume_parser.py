"""
resume_parser.py

Turns an uploaded resume file (PDF, DOCX, or TXT) into plain text.
Streamlit gives us an UploadedFile object, which behaves like a file handle.
"""

import io
from pypdf import PdfReader
from docx import Document


class ResumeParseError(Exception):
    """Raised when a resume file can't be read or has no usable text."""


def extract_text(uploaded_file) -> str:
    """
    Args:
        uploaded_file: a Streamlit UploadedFile (from st.file_uploader)

    Returns:
        str: the extracted plain text of the resume

    Raises:
        ResumeParseError: if the file type is unsupported or no text is found
    """
    filename = uploaded_file.name.lower()
    raw_bytes = uploaded_file.read()

    if filename.endswith(".pdf"):
        text = _extract_pdf(raw_bytes)
    elif filename.endswith(".docx"):
        text = _extract_docx(raw_bytes)
    elif filename.endswith(".txt"):
        text = raw_bytes.decode("utf-8", errors="ignore")
    else:
        raise ResumeParseError(
            "Unsupported file type. Please upload a PDF, DOCX, or TXT file."
        )

    text = text.strip()
    if len(text) < 40:
        raise ResumeParseError(
            "Couldn't find enough readable text in that file. "
            "If it's a scanned/image-based PDF, try a text-based export instead."
        )
    return text


def _extract_pdf(raw_bytes: bytes) -> str:
    reader = PdfReader(io.BytesIO(raw_bytes))
    pages = [page.extract_text() or "" for page in reader.pages]
    return "\n".join(pages)


def _extract_docx(raw_bytes: bytes) -> str:
    doc = Document(io.BytesIO(raw_bytes))
    paragraphs = [p.text for p in doc.paragraphs]
    # Also pull text out of any tables (skills tables, etc.)
    for table in doc.tables:
        for row in table.rows:
            for cell in row.cells:
                paragraphs.append(cell.text)
    return "\n".join(paragraphs)

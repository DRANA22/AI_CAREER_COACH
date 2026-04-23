"""
PDF Resume Text Extraction
Extracts text from uploaded PDF resume files.
"""

import PyPDF2
import io


def extract_resume_text(file_storage):
    """
    Extracts text from an uploaded PDF resume.

    Args:
        file_storage: A Flask FileStorage object (from request.files)

    Returns:
        str: Extracted text or an error message
    """
    try:
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_storage.read()))
        text = ""

        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"

        text = text.strip()

        if len(text) < 50:
            return "Could not extract text from resume."

        return text

    except Exception as e:
        return f"Error extracting text: {str(e)}"

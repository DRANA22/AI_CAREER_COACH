import PyPDF2 as pdf
import pdfplumber

def extract_resume_text(uploaded_file):
    """
    Extracts text from an uploaded PDF resume.
    Falls back to pdfplumber if PyPDF2 gives poor results.
    """
    try:
        # Primary: PyPDF2 (fast, great for standard resumes)
        reader = pdf.PdfReader(uploaded_file)
        text = ""
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"

        # If text is too short, use pdfplumber for complex layouts
        if len(text.strip()) < 100:
            uploaded_file.seek(0)
            with pdfplumber.open(uploaded_file) as plumber_pdf:
                text = ""
                for page in plumber_pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"

        return text.strip() if text.strip() else "Could not extract text from resume."

    except Exception as e:
        return f"Error extracting text: {str(e)}"
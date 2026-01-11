import fitz
import pytesseract
from PIL import Image


def _run_ocr(doc: fitz.Document) -> str:
    text_chunks = []
    for page in doc:
        pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))
        image = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
        text_chunks.append(pytesseract.image_to_string(image))
    return "\n".join(text_chunks)


def extract_text(file_path: str) -> str:
    doc = fitz.open(file_path)
    text_chunks = []
    for page in doc:
        text_chunks.append(page.get_text())
    text = "\n".join(text_chunks).strip()
    if len(text) < 50:
        text = _run_ocr(doc).strip()
    doc.close()
    return text

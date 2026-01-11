import fitz


def extract_text(file_path: str) -> str:
    doc = fitz.open(file_path)
    text_chunks = []
    for page in doc:
        text_chunks.append(page.get_text())
    text = "\n".join(text_chunks).strip()
    if len(text) < 100:
        text_chunks = []
        for page in doc:
            text_chunks.append(page.get_text("text", ocr=True))
        text = "\n".join(text_chunks).strip()
    doc.close()
    return text

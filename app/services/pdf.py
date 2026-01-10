import fitz


def extract_text(file_path: str) -> str:
    doc = fitz.open(file_path)
    text_chunks = []
    for page in doc:
        text_chunks.append(page.get_text())
    doc.close()
    return "\n".join(text_chunks)

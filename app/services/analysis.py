from __future__ import annotations

from typing import List

from ollama import Client


def _get_client() -> Client:
    return Client(host="http://localhost:11434")


def summarize_document(text: str) -> List[str]:
    prompt = (
        "Summarize the following labor document in 3 bullet points focused on labor implications. "
        "Return only the bullet points.\n\n"
        f"{text}"
    )
    client = _get_client()
    response = client.generate(model="llama3.2", prompt=prompt)
    raw = response.get("response", "").strip()
    return [line.strip("- ") for line in raw.splitlines() if line.strip()][:3]


def extract_key_dates(text: str) -> List[str]:
    prompt = (
        "Extract any expiration dates or grievance deadlines from the text. "
        "Return a bullet list of dates or deadlines. If none, return an empty list.\n\n"
        f"{text}"
    )
    client = _get_client()
    response = client.generate(model="llama3.2", prompt=prompt)
    raw = response.get("response", "").strip()
    return [line.strip("- ") for line in raw.splitlines() if line.strip()]

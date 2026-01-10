from whoosh import index
from whoosh.analysis import StemmingAnalyzer
from whoosh.fields import ID, KEYWORD, TEXT, Schema
from whoosh.highlight import ContextFragmenter
from whoosh.qparser import MultifieldParser

from app.core.config import INDEX_DIR, ensure_directories

SCHEMA = Schema(
    doc_id=ID(stored=True, unique=True),
    title=TEXT(stored=True),
    content=TEXT(stored=True, analyzer=StemmingAnalyzer()),
    tags=KEYWORD(stored=True, commas=True, lowercase=True),
)


def ensure_index() -> None:
    ensure_directories()
    if not index.exists_in(INDEX_DIR):
        index.create_in(INDEX_DIR, SCHEMA)


def get_index():
    ensure_index()
    return index.open_dir(INDEX_DIR)


def index_document(doc_id: str, title: str, content: str, tags: str) -> None:
    ix = get_index()
    writer = ix.writer()
    writer.update_document(doc_id=doc_id, title=title, content=content, tags=tags)
    writer.commit()


def search_documents(query: str, limit: int = 10):
    ix = get_index()
    parser = MultifieldParser(["title", "content", "tags"], schema=SCHEMA)
    parsed = parser.parse(query)
    results_payload = []

    with ix.searcher() as searcher:
        results = searcher.search(parsed, limit=limit)
        results.fragmenter = ContextFragmenter(maxchars=200, surround=50)
        for hit in results:
            results_payload.append(
                {
                    "doc_id": hit["doc_id"],
                    "title": hit["title"],
                    "tags": hit.get("tags", ""),
                    "highlight": hit.highlights("content"),
                }
            )

    return results_payload

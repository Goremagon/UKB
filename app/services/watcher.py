import threading
import time
from pathlib import Path

from watchdog.events import FileSystemEventHandler
from watchdog.observers import Observer

from app.core.config import WATCH_DIR
from app.core.database import SessionLocal
from app.services.ingestion import ingest_file


class WatcherHandler(FileSystemEventHandler):
    def on_created(self, event) -> None:
        if event.is_directory:
            return
        path = Path(event.src_path)
        if path.suffix.lower() != ".pdf":
            return
        time.sleep(1)
        db = SessionLocal()
        try:
            ingest_file(
                db=db,
                file_path=path.as_posix(),
                filename=path.name,
                metadata={"doc_type": "Uncategorized"},
                user_id=None,
            )
        except ValueError:
            pass
        finally:
            db.close()


def start_watch() -> threading.Thread:
    handler = WatcherHandler()
    observer = Observer()
    observer.schedule(handler, WATCH_DIR.as_posix(), recursive=True)
    observer.start()

    def _run() -> None:
        try:
            while True:
                time.sleep(1)
        finally:
            observer.stop()
            observer.join()

    thread = threading.Thread(target=_run, daemon=True)
    thread.start()
    return thread

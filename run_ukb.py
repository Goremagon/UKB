import platform
import sys
import threading
import webbrowser


def check_dependencies() -> None:
    if sys.version_info < (3, 14):
        print("Python 3.14+ is required. Current version:", sys.version)
        sys.exit(1)

    missing = []
    arch = platform.machine().lower()
    try:
        import fastapi  # noqa: F401
    except ImportError:
        missing.append("fastapi")
    try:
        import uvicorn  # noqa: F401
    except ImportError:
        missing.append("uvicorn")
    try:
        import sqlalchemy  # noqa: F401
    except ImportError:
        missing.append("sqlalchemy")
    try:
        import fitz  # noqa: F401
    except ImportError:
        missing.append("PyMuPDF")

    if missing:
        arch_hint = "x64" if "64" in arch or "amd" in arch else arch
        print("Missing dependencies:", ", ".join(missing))
        print("Install requirements with: pip install -r requirements.txt")
        print(f"If you are on {arch_hint}, ensure wheels are available for Python {sys.version_info.major}.{sys.version_info.minor}.")
        sys.exit(1)


def open_browser() -> None:
    webbrowser.open("http://localhost:8000", new=2)


def main() -> None:
    check_dependencies()

    from pathlib import Path

    from app.core.database import init_db
    from app.core.search import ensure_index

    ui_dist = Path(__file__).resolve().parent / "ui" / "dist"
    if not ui_dist.exists():
        print("UI build not found at ui/dist. Run the frontend build to enable static serving.")

    init_db()
    ensure_index()

    threading.Timer(1.0, open_browser).start()

    import uvicorn

    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=False)


if __name__ == "__main__":
    main()

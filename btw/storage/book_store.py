from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any

DATA_DIR = Path(__file__).resolve().parents[1] / "data" / "books"


def ensure_book_dir(book_id: str) -> Path:
    book_dir = DATA_DIR / book_id
    book_dir.mkdir(parents=True, exist_ok=True)
    return book_dir


def save_uploaded_file(book_id: str, file_path: Path) -> Path:
    book_dir = ensure_book_dir(book_id)
    destination = book_dir / "raw.txt"
    shutil.copy(file_path, destination)
    return destination


def save_chapter(book_id: str, chapter_index: int, content: str) -> Path:
    chapter_dir = ensure_book_dir(book_id) / "chapters" / f"{chapter_index:02d}"
    chapter_dir.mkdir(parents=True, exist_ok=True)
    content_path = chapter_dir / "content.md"
    content_path.write_text(content, encoding="utf-8")
    return content_path


def save_book_summary(book_id: str, summary: str) -> Path:
    path = ensure_book_dir(book_id) / "book_summary.md"
    path.write_text(summary, encoding="utf-8")
    return path


def save_concept_index(book_id: str, concepts: list[dict[str, Any]]) -> Path:
    path = ensure_book_dir(book_id) / "concept_index.json"
    path.write_text(json.dumps(concepts, ensure_ascii=False, indent=2), encoding="utf-8")
    return path


def get_component_paths(book_id: str, chapter_index: int) -> tuple[Path, Path]:
    chapter_dir = ensure_book_dir(book_id) / "chapters" / f"{chapter_index:02d}"
    return chapter_dir / "component.jsx", chapter_dir / "component.js"

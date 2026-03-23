"""PDF to Markdown conversion skill for BTW."""
from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from btw.skills.base import Skill


def heuristic_is_chapter_heading(text: str) -> bool:
    """Heuristic: determine if text looks like a chapter heading."""
    if not text or len(text) > 100:
        return False

    # Common chapter patterns
    patterns = [
        r"^第[一二三四五六七八九十百千万零\d]+章",
        r"^第\d+章",
        r"^Chapter\s+\d+",
        r"^CHAPTER\s+\d+",
        r"^\d+\s*[.：:]\s*",
    ]
    for pattern in patterns:
        if re.search(pattern, text.strip(), re.IGNORECASE):
            return True

    return False


def extract_structure_from_toc(text: str) -> list[dict[str, Any]] | None:
    """Try to extract chapter structure from TOC page."""
    lines = text.splitlines()
    chapters: list[dict[str, Any]] = []
    toc_pattern = re.compile(r"^(.*?)(?:\.{2,}|\s+)(\d+)$")

    for line in lines:
        line = line.strip()
        if not line:
            continue
        match = toc_pattern.match(line)
        if match and int(match.group(2)) > 0 and int(match.group(2)) < 1000:
            title = match.group(1).strip()
            page_num = int(match.group(2))
            chapters.append({"title": title, "page_start": page_num, "page_end": None})

    if len(chapters) >= 2:
        for i in range(len(chapters) - 1):
            chapters[i]["page_end"] = chapters[i + 1]["page_start"] - 1
        return chapters
    return None


class PDFToMarkdownSkill(Skill):
    """Convert PDF files to structured Markdown."""

    name = "pdf_to_markdown"
    description = "Extracts text from PDF and converts to Markdown with chapter detection."
    parameters = {
        "file_path": {"type": "string", "description": "Path to PDF file"},
        "output_path": {"type": "string", "description": "Output Markdown file path"},
    }

    async def execute(self, **kwargs) -> dict:
        import fitz  # PyMuPDF

        file_path = Path(kwargs.get("file_path", ""))
        output_path = kwargs.get("output_path")

        if not file_path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}

        try:
            doc = fitz.open(file_path)
            full_text_parts: list[str] = []
            toc_structure: list[dict[str, Any]] | None = None

            for page_num in range(len(doc)):
                page = doc[page_num]
                text = page.get_text()

                # Try to find TOC on first few pages
                if page_num < 5 and toc_structure is None and "目录" in text or "Contents" in text:
                    toc_structure = extract_structure_from_toc(text)

                if text.strip():
                    full_text_parts.append(text.strip())

            total_pages = len(doc)  # Save before closing
            doc.close()

            full_text = "\n\n".join(full_text_parts)
            markdown_content = self._convert_to_markdown(full_text, toc_structure)

            if output_path:
                output_file = Path(output_path)
                output_file.write_text(markdown_content, encoding="utf-8")

            return {
                "success": True,
                "markdown": markdown_content,
                "output_path": output_path,
                "total_pages": total_pages,
            }

        except ImportError:
            return {
                "success": False,
                "error": "PyMuPDF not installed. Run: pip install pymupdf",
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    def _convert_to_markdown(
        self, text: str, toc_structure: list[dict[str, Any]] | None = None
    ) -> str:
        """Convert plain text to structured Markdown."""
        lines = text.splitlines()
        result: list[str] = ["# Book\n"]  # Title placeholder

        in_code_block = False
        i = 0

        while i < len(lines):
            line = lines[i]
            stripped = line.strip()

            # Skip empty lines at start
            if not result[-1].strip() and not stripped:
                i += 1
                continue

            # Code block detection
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                result.append(line)
                i += 1
                continue

            if in_code_block:
                result.append(line)
                i += 1
                continue

            # Chapter heading detection
            if heuristic_is_chapter_heading(stripped):
                result.append(f"\n## {stripped}\n")
                i += 1
                continue

            # Subsection detection
            if re.match(r"^[一二三四五六七八九十].*?、|^\d+[.）]", stripped) and len(stripped) < 50:
                result.append(f"\n### {stripped}\n")
                i += 1
                continue

            # Normal paragraph
            if stripped:
                # Merge short lines
                if i + 1 < len(lines) and len(lines[i + 1].strip()) < 50:
                    result.append(line)
                else:
                    result.append(line + "\n")
            else:
                if result[-1].strip():
                    result.append("\n")

            i += 1

        return "\n".join(result)

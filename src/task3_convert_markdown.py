"""
Task 3 — Chuẩn hóa dữ liệu sang Markdown.

Hướng dẫn:
    1. Dùng MarkItDown để convert PDF/DOCX.
    2. Đọc JSON và giữ metadata ở đầu file Markdown.
    3. Giữ cấu trúc thư mục legal/ và news/.
    4. Không tạo file rỗng hoặc file trùng khi chạy lại.

Cài đặt:
    Dependency MarkItDown đã được khai báo trong pyproject.toml.
    
-> Hoặc dùng công cụ nào bạn quen khác Markitdown
"""

import json
from pathlib import Path


LANDING_DIR = Path(__file__).parent.parent / "data" / "landing"
OUTPUT_DIR = Path(__file__).parent.parent / "data" / "standardized"


def _article_body(markdown: str) -> str:
    """Remove repeated site navigation and footer from crawled articles."""
    navigation = "  * [Contact Information]("
    nav_start = markdown.find(navigation)
    if nav_start >= 0:
        markdown = markdown[markdown.find("\n", nav_start) + 1 :]
    footer_starts = [
        position for marker in ("[APPLY NOW!]", "![Banner footer]")
        if (position := markdown.find(marker)) >= 0
    ]
    if footer_starts:
        markdown = markdown[: min(footer_starts)]
    return markdown.strip()


def _normalize_lines(markdown: str) -> str:
    return "\n".join(line.rstrip() for line in markdown.splitlines()) + "\n"


def convert_legal_docs() -> None:
    from markitdown import MarkItDown

    legal_dir = LANDING_DIR / "legal"
    output_dir = OUTPUT_DIR / "legal"
    converter = MarkItDown()
    sources = json.loads((legal_dir / "sources.json").read_text(encoding="utf-8"))

    for path in legal_dir.rglob("*"):
        if not path.is_file() or path.suffix.lower() not in {".pdf", ".docx"}:
            continue

        content = converter.convert(str(path)).text_content.strip()
        if not content:
            print(f"Skipped scanned/empty document (OCR needed): {path.name}")
            continue

        source = sources.get(path.name)
        if not source or not source.get("source_url"):
            raise ValueError(f"Missing source URL for {path.name}")
        header = f"# {source['title']}\n\n**Source:** {source['source_url']}\n\n---\n\n"
        normalized = _normalize_lines(header + content)
        destination = output_dir / path.relative_to(legal_dir).with_suffix(".md")
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists() and destination.read_text(encoding="utf-8") == normalized:
            continue
        destination.write_text(normalized, encoding="utf-8")


def convert_news_articles() -> None:
    news_dir = LANDING_DIR / "news"
    output_dir = OUTPUT_DIR / "news"
    output_dir.mkdir(parents=True, exist_ok=True)

    for path in news_dir.glob("*.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        required = ("url", "title", "date_crawled", "content_markdown")
        if any(not str(data.get(key, "")).strip() for key in required):
            raise ValueError(f"Missing article content or metadata: {path.name}")
        header = (
            f"# {data['title']}\n\n"
            f"**Source:** {data['url']}\n\n"
            f"**Crawled:** {data['date_crawled']}\n\n---\n\n"
        )
        body = _article_body(data["content_markdown"])
        if len(body) < 200:
            raise ValueError(f"Article body is too short: {path.name}")
        normalized = _normalize_lines(header + body)
        destination = output_dir / f"{path.stem}.md"
        if destination.exists() and destination.read_text(encoding="utf-8") == normalized:
            continue
        destination.write_text(normalized, encoding="utf-8")


def convert_all() -> None:
    """Convert toàn bộ dữ liệu landing."""
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    convert_legal_docs()
    convert_news_articles()
    print(f"Saved Markdown to: {OUTPUT_DIR}")


if __name__ == "__main__":
    convert_all()

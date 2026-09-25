"""
Task 1 — Thu thập tài liệu chính sách/quy định.

Hướng dẫn:
    1. Chọn chủ đề của nhóm.
    2. Tìm tối thiểu 3 tài liệu PDF/DOCX từ nguồn công khai.
    3. Lưu file gốc vào data/landing/legal/.
    4. Đặt tên không dấu và thể hiện đúng nội dung.

Ví dụ tài liệu: học phí, học bổng, ký túc xá, quy trình đăng ký.
Nếu website chặn crawler, hãy chọn nguồn công khai khác; không vượt WAF.
"""

import json
from pathlib import Path


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "legal"
SOURCES_FILE = DATA_DIR / "sources.json"


def setup_directory() -> None:
    """Tạo thư mục lưu tài liệu gốc."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    print(f"Ready: {DATA_DIR}")


def download_documents() -> None:
    """Validate collected PDFs and fetch missing files with direct public URLs."""
    import requests

    sources = json.loads(SOURCES_FILE.read_text(encoding="utf-8"))
    for filename, item in sources.items():
        if Path(filename).name != filename or not filename.lower().endswith(".pdf"):
            raise ValueError(f"Invalid source filename: {filename}")
        path = DATA_DIR / filename
        if not path.exists():
            url = item["source_url"]
            if not url.lower().endswith(".pdf"):
                raise FileNotFoundError(f"Download {filename} manually from {url}")
            response = requests.get(url, timeout=30)
            response.raise_for_status()
            if not response.content.startswith(b"%PDF-") or len(response.content) <= 1024:
                raise ValueError(f"Invalid PDF response: {url}")
            path.write_bytes(response.content)
        with path.open("rb") as stream:
            if path.stat().st_size <= 1024 or stream.read(5) != b"%PDF-":
                raise ValueError(f"Invalid PDF file: {path}")
        print(f"Ready: {path.name} | {item['source_url']}")


if __name__ == "__main__":
    setup_directory()
    download_documents()

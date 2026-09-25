"""
Task 2 — Crawl bài viết/thông báo.

Hướng dẫn:
    1. Điền tối thiểu 5 URL công khai vào ARTICLE_URLS.
    2. Crawl từng URL bằng Crawl4AI.
    3. Lưu mỗi bài thành một JSON trong data/landing/news/.
    4. Giữ đủ url, title, date_crawled và content_markdown.

Cài browser trước khi chạy:
    python -m playwright install chromium
    
-> Dùng Firecrawl or bất cứ công cụ nào bạn quen    
"""

import asyncio
import json
import os
from datetime import datetime, timezone
from pathlib import Path

os.environ.setdefault(
    "CRAWL4_AI_BASE_DIRECTORY",
    str(Path(__file__).parent.parent / ".cache"),
)

from crawl4ai import AsyncWebCrawler


DATA_DIR = Path(__file__).parent.parent / "data" / "landing" / "news"

ARTICLE_URLS = [
    "https://admissions.vinuni.edu.vn/undergraduate/apply-to-vinuni/first-year-applicants/application-process/",
    "https://admissions.vinuni.edu.vn/undergraduate/apply-to-vinuni/transfer-students/",
    "https://admissions.vinuni.edu.vn/undergraduate/apply-to-vinuni/first-year-applicants/admission-criteria/",
    "https://admissions.vinuni.edu.vn/undergraduate/faqs/general-admissions/",
    "https://admissions.vinuni.edu.vn/undergraduate/faqs/tuition-fee-scholarship-and-financial-aids/",
]


async def crawl_article(url: str) -> dict:
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(url=url)
        if not result.success or not result.markdown:
            raise ValueError(f"Crawl returned no usable content: {url}")
        content = str(result.markdown).strip()
        if len(content) < 200:
            raise ValueError(f"Crawl content is too short: {url}")
        title = (result.metadata or {}).get("title", "").strip()
        if not title:
            raise ValueError(f"Crawl returned no title: {url}")
        return {
            "url": url,
            "title": title,
            "date_crawled": datetime.now(timezone.utc).isoformat(),
            "content_markdown": content,
        }


async def crawl_all() -> None:
    """Crawl và lưu từng bài thành một file JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    for index, url in enumerate(ARTICLE_URLS, 1):
        try:
            article = await crawl_article(url)
            output = DATA_DIR / f"article_{index:02d}.json"
            output.write_text(
                json.dumps(article, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            print(f"Saved: {output}")
        except Exception as error:
            print(f"Failed: {url} — {error}")


if __name__ == "__main__":
    asyncio.run(crawl_all())

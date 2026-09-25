"""
Task 8 — PageIndex vectorless fallback.

Hướng dẫn:
    1. Đọc PAGEINDEX_API_KEY từ .env.
    2. Upload tài liệu ở định dạng PageIndex hỗ trợ.
    3. Cache document IDs để không upload lại.
    4. Parse kết quả thành SearchResult có method pageindex.

PageIndex là dịch vụ ngoài: cần timeout và xử lý lỗi để pipeline không crash.
"""

import json
import logging
import os
from pathlib import Path

from dotenv import load_dotenv


load_dotenv()

logger = logging.getLogger(__name__)

PAGEINDEX_API_KEY = os.getenv("PAGEINDEX_API_KEY", "").strip()
STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CACHE_FILE = Path(__file__).parent.parent / "data" / "pageindex_cache.json"


def _load_cache() -> dict[str, str]:
    if CACHE_FILE.exists():
        try:
            return json.loads(CACHE_FILE.read_text(encoding="utf-8"))
        except Exception as err:
            logger.warning(f"Error reading PageIndex cache: {err}")
    return {}


def _save_cache(cache: dict[str, str]) -> None:
    try:
        CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        CACHE_FILE.write_text(json.dumps(cache, indent=2, ensure_ascii=False), encoding="utf-8")
    except Exception as err:
        logger.warning(f"Error saving PageIndex cache: {err}")


def upload_documents() -> None:
    """Upload tài liệu và lưu document IDs để tái sử dụng."""
    if not PAGEINDEX_API_KEY:
        logger.info("PAGEINDEX_API_KEY is not set. Skipping document upload.")
        return

    try:
        from pageindex import PageIndexClient

        client = PageIndexClient(api_key=PAGEINDEX_API_KEY)
    except Exception as err:
        logger.warning(f"Failed to initialize PageIndexClient: {err}")
        return

    cache = _load_cache()
    files = list(STANDARDIZED_DIR.rglob("*.md"))
    for file_path in files:
        rel_key = file_path.relative_to(STANDARDIZED_DIR).as_posix()
        if rel_key in cache:
            continue
        try:
            res = client.submit_document(file_path=str(file_path))
            doc_id = res.get("doc_id") or res.get("id") or res.get("document_id")
            if doc_id:
                cache[rel_key] = doc_id
        except Exception as err:
            logger.warning(f"Failed to upload {rel_key} to PageIndex: {err}")

    _save_cache(cache)


def pageindex_search(query: str, top_k: int = 5) -> list[dict]:
    """Trả về pageindex SearchResult với error handling an toàn."""
    if top_k <= 0 or not query.strip() or not PAGEINDEX_API_KEY:
        return []

    cache = _load_cache()
    if not cache:
        return []

    try:
        from pageindex import PageIndexClient

        client = PageIndexClient(api_key=PAGEINDEX_API_KEY)
        results = []

        for source_key, doc_id in cache.items():
            try:
                res = client.submit_query(doc_id=doc_id, query=query)
                retrieved_nodes = res.get("nodes") or res.get("results") or []
                for idx, node in enumerate(retrieved_nodes):
                    content = node.get("text") or node.get("content") or ""
                    if not content.strip():
                        continue
                    score = float(node.get("score") or (1.0 / (idx + 1)))
                    results.append({
                        "id": f"pageindex::{doc_id}::{idx}",
                        "content": content,
                        "score": score,
                        "metadata": {
                            "source": source_key,
                            "title": Path(source_key).stem,
                            "doc_type": "legal" if "legal" in source_key.lower() else "news",
                            "url": None,
                            "chunk_index": idx,
                        },
                        "retrieval_method": "pageindex",
                    })
            except Exception as item_err:
                logger.warning(f"Error querying doc_id {doc_id} from PageIndex: {item_err}")
                continue

        results.sort(key=lambda item: item["score"], reverse=True)
        return results[:top_k]
    except Exception as err:
        logger.warning(f"PageIndex search failed: {err}")
        return []


if __name__ == "__main__":
    upload_documents()

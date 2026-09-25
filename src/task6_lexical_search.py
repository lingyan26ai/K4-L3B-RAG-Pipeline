"""Task 6: BM25 search over the same indexed chunks used by dense search."""

import re

from .task4_chunking_indexing import get_collection


# Can be supplied directly by callers/tests; otherwise loaded from Chroma.
CORPUS: list[dict] = []


def _tokens(text: str) -> list[str]:
    return re.findall(r"\w+", text.casefold(), flags=re.UNICODE)


def build_bm25_index(corpus: list[dict]):
    """Build BM25L; its IDF also works for very small test corpora."""
    from rank_bm25 import BM25L

    return BM25L([_tokens(item["content"]) for item in corpus])


def _indexed_corpus() -> list[dict]:
    collection = get_collection()
    items = collection.get(include=["documents", "metadatas"])
    return [
        {
            "id": item_id,
            "content": content,
            "metadata": {**metadata, "url": metadata.get("url")},
        }
        for item_id, content, metadata in zip(
            items["ids"], items["documents"], items["metadatas"]
        )
    ]


def lexical_search(query: str, top_k: int = 10) -> list[dict]:
    """Return positive-score BM25 results sorted by score descending."""
    query_tokens = _tokens(query)
    if top_k <= 0 or not query_tokens:
        return []
    corpus = CORPUS if CORPUS else _indexed_corpus()
    if not corpus:
        return []
    scores = build_bm25_index(corpus).get_scores(query_tokens)
    ranked = sorted(range(len(corpus)), key=lambda index: (-float(scores[index]), index))
    results = []
    seen = set()
    for index in ranked:
        score = float(scores[index])
        item = corpus[index]
        if score <= 0:
            break
        if item["id"] in seen:
            continue
        seen.add(item["id"])
        results.append({
            "id": item["id"],
            "content": item["content"],
            "score": score,
            "metadata": {**item["metadata"], "url": item["metadata"].get("url")},
            "retrieval_method": "bm25",
        })
        if len(results) == top_k:
            break
    return results


if __name__ == "__main__":
    for result in lexical_search("test query", top_k=3):
        print(result)

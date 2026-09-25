"""Task 5: dense search over the Task 4 Chroma collection."""

from .task4_chunking_indexing import embed_texts, get_collection


def semantic_search(query: str, top_k: int = 10) -> list[dict]:
    """Return unique SearchResults scored by original cosine similarity."""
    if top_k <= 0 or not query.strip():
        return []
    query_vector = embed_texts([query])[0]
    response = get_collection().query(
        query_embeddings=[query_vector],
        n_results=top_k,
        include=["documents", "metadatas", "distances"],
    )
    results = []
    seen = set()
    for item_id, content, metadata, distance in zip(
        response["ids"][0],
        response["documents"][0],
        response["metadatas"][0],
        response["distances"][0],
    ):
        if item_id in seen:
            continue
        seen.add(item_id)
        results.append({
            "id": item_id,
            "content": content,
            "score": 1.0 - float(distance),
            "metadata": {**metadata, "url": metadata.get("url")},
            "retrieval_method": "dense",
        })
    return sorted(results, key=lambda item: item["score"], reverse=True)[:top_k]


if __name__ == "__main__":
    for result in semantic_search("test query", top_k=3):
        print(result)

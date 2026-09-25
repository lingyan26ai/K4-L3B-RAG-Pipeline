"""Task 4: load standardized Markdown, chunk it, and upsert embeddings."""

import os
import re
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv

from .contracts import validate_document


load_dotenv()

STANDARDIZED_DIR = Path(__file__).parent.parent / "data" / "standardized"
CHROMA_DIR = Path(__file__).parent.parent / "chroma_db"
os.environ.setdefault("HF_HOME", str(Path(__file__).parent.parent / ".cache" / "huggingface"))

CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
CHUNKING_METHOD = "recursive"

EMBEDDING_PROVIDER = os.getenv("EMBEDDING_PROVIDER", "sentence_transformers").strip().lower()
DEFAULT_MODELS = {
    "sentence_transformers": "BAAI/bge-m3",
    "openai": "text-embedding-3-small",
    "gemini": "gemini-embedding-001",
}
EMBEDDING_MODEL = os.getenv("EMBEDDING_MODEL", "").strip() or DEFAULT_MODELS.get(
    EMBEDDING_PROVIDER, "BAAI/bge-m3"
)
EMBEDDING_DIM = 1024  # Dimension of the default local BGE-M3 model.

COLLECTION_NAME = "rag_documents"
EMBED_BATCH_SIZE = 32


@lru_cache(maxsize=1)
def _local_model():
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(EMBEDDING_MODEL)


def embed_texts(texts: list[str]) -> list[list[float]]:
    """Embed text with the provider and model shared by indexing and search."""
    if not texts:
        return []
    if EMBEDDING_PROVIDER == "sentence_transformers":
        vectors = _local_model().encode(texts, batch_size=EMBED_BATCH_SIZE)
        return vectors.tolist()
    if EMBEDDING_PROVIDER == "openai":
        from openai import OpenAI

        response = OpenAI().embeddings.create(model=EMBEDDING_MODEL, input=texts)
        return [item.embedding for item in sorted(response.data, key=lambda item: item.index)]
    if EMBEDDING_PROVIDER == "gemini":
        from google import genai

        response = genai.Client().models.embed_content(model=EMBEDDING_MODEL, contents=texts)
        return [item.values for item in response.embeddings]
    raise ValueError(f"Unsupported EMBEDDING_PROVIDER: {EMBEDDING_PROVIDER}")


def get_collection():
    """Open the persistent Chroma collection using cosine distance."""
    import chromadb

    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def load_documents() -> list[dict]:
    """Read legal/news Markdown into Documents with stable IDs and source metadata."""
    documents = []
    for path in sorted(STANDARDIZED_DIR.rglob("*.md")):
        relative = path.relative_to(STANDARDIZED_DIR)
        doc_type = relative.parts[0].lower()
        if doc_type not in {"legal", "news"}:
            continue
        content = path.read_text(encoding="utf-8-sig").strip()
        if not content:
            continue
        title_match = re.search(r"^#\s+(.+?)\s*$", content, re.MULTILINE)
        source_match = re.search(r"^\*\*Source:\*\*\s*(\S+)\s*$", content, re.MULTILINE | re.IGNORECASE)
        document = {
            "id": relative.as_posix(),
            "content": content,
            "metadata": {
                "source": relative.as_posix(),
                "title": title_match.group(1).strip() if title_match else path.stem,
                "doc_type": doc_type,
                "url": source_match.group(1) if source_match else None,
            },
        }
        validate_document(document)
        documents.append(document)
    return documents


def chunk_documents(documents: list[dict]) -> list[dict]:
    """Split documents into nonempty chunks with stable IDs and indices."""
    from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = []
    for document in documents:
        validate_document(document)
        for index, content in enumerate(splitter.split_text(document["content"])):
            if not content.strip():
                continue
            chunk = {
                "id": f"{document['id']}::chunk-{index}",
                "content": content,
                "metadata": {**document["metadata"], "chunk_index": index},
            }
            validate_document(chunk, require_chunk=True)
            chunks.append(chunk)
    return chunks


def embed_chunks(chunks: list[dict]) -> list[dict]:
    """Embed in batches without changing the input chunks."""
    embedded = []
    for start in range(0, len(chunks), EMBED_BATCH_SIZE):
        batch = chunks[start : start + EMBED_BATCH_SIZE]
        vectors = embed_texts([chunk["content"] for chunk in batch])
        if len(vectors) != len(batch):
            raise ValueError("Embedding provider returned an unexpected vector count")
        for chunk, vector in zip(batch, vectors):
            validate_document(chunk, require_chunk=True)
            embedded.append({**chunk, "embedding": vector})
    return embedded


def index_to_vectorstore(chunks: list[dict]) -> None:
    """Upsert by stable chunk ID; omit None values unsupported by Chroma."""
    if not chunks:
        return
    collection = get_collection()
    for start in range(0, len(chunks), EMBED_BATCH_SIZE):
        batch = chunks[start : start + EMBED_BATCH_SIZE]
        for chunk in batch:
            validate_document(chunk, require_chunk=True)
            if not chunk.get("embedding"):
                raise ValueError(f"Missing embedding for {chunk['id']}")
        collection.upsert(
            ids=[chunk["id"] for chunk in batch],
            documents=[chunk["content"] for chunk in batch],
            embeddings=[chunk["embedding"] for chunk in batch],
            metadatas=[
                {key: value for key, value in chunk["metadata"].items() if value is not None}
                for chunk in batch
            ],
        )


def run_pipeline() -> None:
    documents = load_documents()
    if not documents:
        raise ValueError(f"No standardized legal/news Markdown found in {STANDARDIZED_DIR}")
    chunks = chunk_documents(documents)
    embedded_chunks = embed_chunks(chunks)
    index_to_vectorstore(embedded_chunks)
    print(f"Indexed {len(embedded_chunks)} chunks")


if __name__ == "__main__":
    run_pipeline()

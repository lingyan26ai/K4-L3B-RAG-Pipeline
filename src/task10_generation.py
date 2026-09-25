"""
Task 10 — Generation có citation.

Hướng dẫn:
    1. Retrieve top-k chunks.
    2. Reorder để giảm lost-in-the-middle.
    3. Format context kèm title và source.
    4. Gọi provider được chọn trong .env.
    5. Trả answer, sources và retrieval_source.

Nếu context không đủ hoặc provider lỗi, trả safe refusal; không bịa thông tin.
"""

import os

from dotenv import load_dotenv

from .task5_semantic_search import semantic_search
from .task9_retrieval_pipeline import SCORE_THRESHOLD
from .task9_retrieval_pipeline import retrieve


load_dotenv()

TOP_K = 5
TOP_P = 0.9
TEMPERATURE = 0.3

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "openai")
LLM_MODEL = os.getenv("LLM_MODEL", "")

SYSTEM_PROMPT = """Trả lời chỉ từ context được cung cấp.
Mỗi khẳng định phải có citation. Nếu thiếu evidence, hãy từ chối xác minh."""


SAFE_REFUSAL = "Tôi không thể xác minh thông tin này từ nguồn hiện có."


def reorder_for_llm(chunks: list[dict]) -> list[dict]:
    """Đưa chunks quan trọng về đầu và cuối context."""
    if len(chunks) <= 2:
        return list(chunks)
    front = chunks[::2]
    back = chunks[1::2]
    return front + back[::-1]


def format_context(chunks: list[dict]) -> str:
    """Tạo context có title và source label."""
    parts = []
    for index, chunk in enumerate(chunks, 1):
        metadata = chunk.get("metadata", {})
        title = metadata.get("title", "")
        source = metadata.get("source", "")
        parts.append(
            f"[Document {index} | Title: {title} | Source: {source}]\n{chunk.get('content', '')}"
        )
    return "\n\n---\n\n".join(parts)


def call_llm(system_prompt: str, user_message: str) -> str:
    """Gọi OpenAI, OpenRouter, Gemini hoặc Anthropic theo cấu hình."""
    provider = (LLM_PROVIDER or "").lower().strip()

    if provider == "openai":
        from openai import OpenAI

        api_key = os.getenv("OPENAI_API_KEY")
        client = OpenAI(api_key=api_key)
        model = LLM_MODEL or "gpt-4o-mini"
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=TEMPERATURE,
            top_p=TOP_P,
        )
        return response.choices[0].message.content or ""

    if provider == "openrouter":
        from openai import OpenAI

        api_key = (os.getenv("OPENROUTER_API_KEY") or "").strip()
        if not api_key:
            raise ValueError("Set OPENROUTER_API_KEY in .env")
        if not LLM_MODEL.strip():
            raise ValueError("Set LLM_MODEL to an OpenRouter model ID in .env")
        client = OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
        response = client.chat.completions.create(
            model=LLM_MODEL.strip(),
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message},
            ],
            temperature=TEMPERATURE,
            top_p=TOP_P,
        )
        return response.choices[0].message.content or ""

    if provider == "gemini":
        from google import genai
        from google.genai import types

        api_key = (os.getenv("GEMINI_API_KEY") or "").strip()
        client = genai.Client(api_key=api_key)
        model = LLM_MODEL or "gemini-3.5-flash-lite"
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=TEMPERATURE,
            top_p=TOP_P,
        )
        response = client.models.generate_content(
            model=model,
            contents=user_message,
            config=config,
        )
        return response.text or ""

    if provider == "anthropic":
        from anthropic import Anthropic

        api_key = os.getenv("ANTHROPIC_API_KEY")
        client = Anthropic(api_key=api_key)
        model = LLM_MODEL or "claude-3-5-haiku-latest"
        response = client.messages.create(
            model=model,
            system=system_prompt,
            messages=[
                {"role": "user", "content": user_message},
            ],
            max_tokens=1024,
            temperature=TEMPERATURE,
            top_p=TOP_P,
        )
        content_block = response.content[0]
        return getattr(content_block, "text", "")

    raise ValueError(f"Unsupported LLM provider: {provider}")


def generate_with_citation(query: str, top_k: int = TOP_K) -> dict:
    """Trả về GenerationResult."""
    try:
        chunks = retrieve(query, top_k=top_k)
    except Exception:
        chunks = []

    if not chunks:
        return {
            "answer": SAFE_REFUSAL,
            "sources": [],
            "retrieval_source": "none",
        }

    # Retrieval keeps hybrid results when PageIndex is unavailable. Do not pass
    # those low-confidence results to the generator as factual evidence.
    if chunks[0].get("retrieval_method") != "pageindex":
        try:
            dense = semantic_search(query, top_k=1)
            if not dense or dense[0]["score"] < SCORE_THRESHOLD:
                return {
                    "answer": SAFE_REFUSAL,
                    "sources": [],
                    "retrieval_source": "none",
                }
        except Exception:
            return {
                "answer": SAFE_REFUSAL,
                "sources": [],
                "retrieval_source": "none",
            }

    reordered = reorder_for_llm(chunks)
    context = format_context(reordered)
    user_message = f"Context:\n{context}\n\nQuestion: {query}"

    try:
        answer = call_llm(SYSTEM_PROMPT, user_message)
        if not answer or not answer.strip():
            answer = SAFE_REFUSAL
    except Exception:
        return {
            "answer": SAFE_REFUSAL,
            "sources": [],
            "retrieval_source": "none",
        }

    return {
        "answer": answer,
        "sources": reordered,
        "retrieval_source": chunks[0].get("retrieval_method", "hybrid"),
    }


if __name__ == "__main__":
    print(generate_with_citation("test query"))

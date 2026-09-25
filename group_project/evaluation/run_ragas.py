"""Run the same 15-question, four-metric Ragas evaluation for dense and hybrid RAG.

Run from the repository root: python -m group_project.evaluation.run_ragas
Requires an OpenAI, OpenRouter or Gemini key in .env. A small trial can use --limit 1.
"""

import argparse
import asyncio
import json
import math
import os
import re
import time
from datetime import datetime, timezone
from importlib.metadata import version
from pathlib import Path
from statistics import mean

from dotenv import load_dotenv


ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")
os.environ.setdefault("HF_HOME", str(ROOT / ".cache" / "huggingface"))

from src.task5_semantic_search import semantic_search
from src.task6_lexical_search import lexical_search
from src.task7_reranking import rerank_rrf
from src.task4_chunking_indexing import EMBEDDING_MODEL
from src.task10_generation import (
    LLM_MODEL,
    LLM_PROVIDER,
    SAFE_REFUSAL,
    SYSTEM_PROMPT,
    call_llm,
    format_context,
    reorder_for_llm,
)


METRIC_NAMES = (
    "faithfulness",
    "answer_relevance",
    "context_recall",
    "context_precision",
)


def make_scorers(provider: str, model: str):
    """Create one judge and one embedding model shared by both configurations."""
    from ragas.llms import llm_factory
    from ragas.metrics.collections import (
        AnswerRelevancy,
        ContextPrecision,
        ContextRecall,
        Faithfulness,
    )

    if provider == "openai":
        from openai import AsyncOpenAI
        from ragas.embeddings.base import embedding_factory

        client = AsyncOpenAI(api_key=os.environ["OPENAI_API_KEY"])
        judge = llm_factory(model, client=client)
        embedding_model = os.getenv("RAGAS_EMBEDDING_MODEL") or "text-embedding-3-small"
        embeddings = embedding_factory("openai", model=embedding_model, client=client)
    elif provider == "openrouter":
        from openai import AsyncOpenAI
        from ragas.embeddings.base import embedding_factory

        client = AsyncOpenAI(
            api_key=os.environ["OPENROUTER_API_KEY"],
            base_url="https://openrouter.ai/api/v1",
        )
        judge = llm_factory(model, provider="openai", client=client)
        embedding_model = os.getenv("RAGAS_EMBEDDING_MODEL") or "openai/text-embedding-3-small"
        embeddings = embedding_factory("openai", model=embedding_model, client=client)
    elif provider == "gemini":
        from google import genai
        from openai import AsyncOpenAI
        from ragas.embeddings import GoogleEmbeddings

        api_key = os.environ["GEMINI_API_KEY"]
        # Ragas structured judging works through Gemini's OpenAI-compatible API.
        judge_client = AsyncOpenAI(
            api_key=api_key,
            base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        )
        judge = llm_factory(model, provider="openai", client=judge_client)
        client = genai.Client(api_key=api_key)
        embedding_model = os.getenv("RAGAS_EMBEDDING_MODEL") or "gemini-embedding-001"
        embeddings = GoogleEmbeddings(client=client, model=embedding_model)
    else:
        raise ValueError("Ragas runner supports LLM_PROVIDER=openai, openrouter or gemini")

    scorers = {
        "faithfulness": Faithfulness(llm=judge),
        "answer_relevance": AnswerRelevancy(llm=judge, embeddings=embeddings),
        "context_recall": ContextRecall(llm=judge),
        "context_precision": ContextPrecision(llm=judge),
    }
    return scorers, embedding_model


def retry_delay(error: Exception) -> float | None:
    """Retry only temporary per-minute quota errors, not daily or billing limits."""
    message = str(error)
    if "429" not in message and "RESOURCE_EXHAUSTED" not in message:
        return None
    match = re.search(r"retry in\s+([\d.]+)s", message, re.IGNORECASE)
    if not match:
        match = re.search(r"retryDelay['\"]?:\s*['\"]([\d.]+)s", message)
    if "PerMinute" not in message and not match:
        return None
    return max(10.0, float(match.group(1)) + 5.0) if match else 65.0


async def score_one(scorer, name: str, question: str, answer: str,
                    reference: str, contexts: list[str]) -> float:
    args = {"user_input": question}
    if name in {"faithfulness", "answer_relevance"}:
        args["response"] = answer
    if name in {"faithfulness", "context_recall", "context_precision"}:
        args["retrieved_contexts"] = contexts
    if name in {"context_recall", "context_precision"}:
        args["reference"] = reference
    for attempt in range(20):
        try:
            value = float((await scorer.ascore(**args)).value)
            if not math.isfinite(value):
                raise ValueError(f"Ragas returned a non-finite {name} score")
            return value
        except Exception as error:
            delay = retry_delay(error)
            if delay is None or attempt == 19:
                raise
            print(f"Gemini minute quota reached during {name}; retrying in {delay:.0f}s", flush=True)
            await asyncio.sleep(delay)
    raise RuntimeError("Unreachable retry state")


def generate(question: str, chunks: list[dict]) -> tuple[str, list[str]]:
    ordered = reorder_for_llm(chunks)
    contexts = [chunk["content"] for chunk in ordered]
    if not contexts:
        return SAFE_REFUSAL, []
    message = f"Context:\n{format_context(ordered)}\n\nQuestion: {question}"
    for attempt in range(20):
        try:
            answer = call_llm(SYSTEM_PROMPT, message).strip()
            break
        except Exception as error:
            delay = retry_delay(error)
            if delay is None or attempt == 19:
                raise
            print(f"Gemini minute quota reached during generation; retrying in {delay:.0f}s", flush=True)
            time.sleep(delay)
    if not answer:
        raise ValueError(f"Generator returned an empty answer for: {question}")
    return answer, contexts


def save(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


async def main() -> None:
    parser = argparse.ArgumentParser(description="Measure four Ragas metrics for dense vs hybrid retrieval")
    parser.add_argument("--limit", type=int, default=15, help="Number of golden cases; use 1 for a trial")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--output", type=Path, default=ROOT / "reports" / "ab_ragas_results.json")
    args = parser.parse_args()
    if args.limit <= 0 or args.top_k <= 0:
        parser.error("--limit and --top-k must be positive")

    provider = LLM_PROVIDER.strip().lower()
    key_name = {
        "openai": "OPENAI_API_KEY",
        "openrouter": "OPENROUTER_API_KEY",
        "gemini": "GEMINI_API_KEY",
    }.get(provider)
    if not key_name:
        parser.error("Set LLM_PROVIDER=openai, openrouter or gemini in .env")
    if not os.getenv(key_name, "").strip():
        parser.error(f"Set {key_name} in .env before running evaluation")

    if provider == "openrouter" and not LLM_MODEL.strip():
        parser.error("Set LLM_MODEL to an OpenRouter model ID in .env")
    generator_model = LLM_MODEL.strip() or (
        "gpt-4o-mini" if provider == "openai" else "gemini-3.5-flash-lite"
    )
    judge_model = os.getenv("RAGAS_JUDGE_MODEL", "").strip() or generator_model
    scorers, judge_embedding_model = make_scorers(provider, judge_model)
    cases = json.loads((ROOT / "group_project" / "evaluation" / "golden_dataset.json").read_text(encoding="utf-8"))
    selected = cases[:args.limit]
    initial_payload = {
        "status": "partial",
        "run_at_utc": datetime.now(timezone.utc).isoformat(),
        "provider": provider,
        "ragas_version": version("ragas"),
        "generator_model": generator_model,
        "judge_model": judge_model,
        "retrieval_embedding_model": EMBEDDING_MODEL,
        "judge_embedding_model": judge_embedding_model,
        "top_k": args.top_k,
        "golden_cases": len(selected),
        "configurations": {"A": "dense", "B": "dense + BM25L + RRF"},
        "rows": [],
    }
    if args.output.exists():
        payload = json.loads(args.output.read_text(encoding="utf-8"))
        for field in ("provider", "generator_model", "judge_model", "top_k", "golden_cases"):
            if payload.get(field) != initial_payload[field]:
                parser.error(f"Existing output has a different {field}; choose another --output path")
        if payload.get("status") == "complete":
            print(f"Evaluation already complete: {args.output}")
            return
        print(f"Resuming partial evaluation from {args.output}", flush=True)
    else:
        payload = initial_payload

    for index, case in enumerate(selected, 1):
        question = case["question"]
        dense = semantic_search(question, top_k=args.top_k * 2)
        sparse = lexical_search(question, top_k=args.top_k * 2)
        candidates = {
            "A": dense[:args.top_k],
            "B": rerank_rrf([dense, sparse], top_k=args.top_k),
        }
        if len(payload["rows"]) < index:
            payload["rows"].append({
                "question": question,
                "reference": case["expected_answer"],
                "configurations": {},
            })
            save(args.output, payload)
        row = payload["rows"][index - 1]
        if row["question"] != question:
            parser.error("Existing output does not match the golden dataset")
        for label, chunks in candidates.items():
            entry = row["configurations"].setdefault(label, {})
            contexts = [chunk["content"] for chunk in reorder_for_llm(chunks)]
            if "answer" not in entry:
                answer, contexts = generate(question, chunks)
                entry.update({"answer": answer, "source_ids": [chunk["id"] for chunk in chunks], "scores": {}})
                save(args.output, payload)
            for name in METRIC_NAMES:
                if name not in entry["scores"]:
                    entry["scores"][name] = await score_one(
                        scorers[name], name, question, entry["answer"], case["expected_answer"], contexts
                    )
                    save(args.output, payload)
        print(f"{index}/{len(selected)} scored: {question}", flush=True)

    payload["summary"] = {
        label: {
            name: round(mean(row["configurations"][label]["scores"][name]
                             for row in payload["rows"]), 4)
            for name in METRIC_NAMES
        }
        for label in ("A", "B")
    }
    payload["status"] = "complete"
    save(args.output, payload)
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    print(f"Saved {args.output}")


if __name__ == "__main__":
    asyncio.run(main())

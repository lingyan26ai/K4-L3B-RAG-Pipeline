import os
import json
import sys

# Ensure UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

from src.task5_semantic_search import semantic_search
from src.task6_lexical_search import lexical_search
from src.task7_reranking import rerank_rrf
from src.task9_retrieval_pipeline import retrieve

in_domain_queries = [
    "VinUni scholarship financial aid support",
    "What are the English requirements for undergraduate admission?",
    "Chi phí học phí và quy định tài chính VinUni",
    "How many colleges does VinUniversity list?",
    "Which high-school science subjects are required for MD eligibility?",
    "Transfer applicants credit transfer policy VinUniversity",
    "What are the three admission rounds and their dates at VinUniversity?"
]

out_of_domain_queries = [
    "Cách làm bánh pizza hải sản tại nhà đơn giản",
    "What is the capital of France and its total population?",
    "Lịch thi đấu bóng đá giải Ngoại hạng Anh cuối tuần này",
    "How to repair a broken iPhone screen at home",
    "Công thức tính diện tích hình tam giác vuông",
    "Thủ tục cấp hộ chiếu phổ thông tại Việt Nam",
    "Who won the FIFA World Cup in 2022?"
]

print("=== IN-DOMAIN QUERIES ===")
in_scores = []
for q in in_domain_queries:
    results = semantic_search(q, top_k=3)
    best_score = results[0]["score"] if results else 0.0
    in_scores.append({"query": q, "best_score": round(best_score, 4)})
    print(f"In-domain: {best_score:.4f} | {q}")

print("\n=== OUT-OF-DOMAIN QUERIES ===")
out_scores = []
for q in out_of_domain_queries:
    results = semantic_search(q, top_k=3)
    best_score = results[0]["score"] if results else 0.0
    out_scores.append({"query": q, "best_score": round(best_score, 4)})
    print(f"Out-of-domain: {best_score:.4f} | {q}")

in_vals = [x["best_score"] for x in in_scores]
out_vals = [x["best_score"] for x in out_scores]

print("\n=== SUMMARY ===")
print(f"In-domain: min={min(in_vals):.4f}, avg={sum(in_vals)/len(in_vals):.4f}, max={max(in_vals):.4f}")
print(f"Out-of-domain: min={min(out_vals):.4f}, avg={sum(out_vals)/len(out_vals):.4f}, max={max(out_vals):.4f}")

recommended_threshold = round((min(in_vals) + max(out_vals)) / 2, 2)
print(f"Recommended fallback threshold: {recommended_threshold}")

calibration_data = {
    "in_domain": in_scores,
    "out_of_domain": out_scores,
    "in_domain_min": min(in_vals),
    "in_domain_avg": round(sum(in_vals)/len(in_vals), 4),
    "in_domain_max": max(in_vals),
    "out_of_domain_min": min(out_vals),
    "out_of_domain_avg": round(sum(out_vals)/len(out_vals), 4),
    "out_of_domain_max": max(out_vals),
    "recommended_threshold": recommended_threshold,
}

with open("calibration_result.json", "w", encoding="utf-8") as f:
    json.dump(calibration_data, f, indent=2, ensure_ascii=False)
print("Saved calibration_result.json")

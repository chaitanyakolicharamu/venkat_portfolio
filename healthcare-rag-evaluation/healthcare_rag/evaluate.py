import argparse
import hashlib
import importlib.metadata
import json
import platform
from datetime import datetime, timezone
from pathlib import Path

import numpy as np

from .pipeline import Pipeline
from .retrieval import DATA

CASES = Path(__file__).parent / "data" / "eval_cases.json"


def run_suite(output: Path):
    cases = json.loads(CASES.read_text())
    pipeline = Pipeline()
    comparisons = {}
    for strategy in ["baseline", "filtered_dense", "hybrid"]:
        pipeline.ask("What is the appointment cancellation window?", strategy=strategy)
        rows = []
        for case in cases:
            result = pipeline.ask(case["query"], case.get("tenant", "north"), strategy)
            expected = case.get("expected_document")
            ranks = [h["document_id"] for h in result["retrieved"]]
            checks = {"status": result["status"] == case["expected_status"]}
            if expected:
                checks["correct_document"] = bool(result["citations"] and result["citations"][0]["document_id"] == expected)
                checks["reference_answer"] = case["reference_answer"].lower() in result["answer"].lower()
            cited = result["citations"]
            # A narrow, honest metric: the extracted answer is a substring of cited evidence.
            supported = bool(cited and result["answer"].removesuffix(" [1]") in cited[0]["text"])
            rows.append({"id": case["id"], "category": case["category"], "query": case["query"],
                         "expected_document": expected, "retrieved_ids": ranks,
                         "passed": all(checks.values()), "checks": checks,
                         "hit_at_1": bool(expected and ranks and ranks[0] == expected),
                         "recall_at_3": int(bool(expected and expected in ranks)),
                         "reciprocal_rank": 1 / (ranks.index(expected) + 1) if expected in ranks else 0,
                         "citation_span_supported": supported, "response": result})
        answerable = [r for r in rows if r["expected_document"]]
        safety = [r for r in rows if r["category"] == "safety"]
        abstention = [r for r in rows if r["category"] == "unanswerable"]
        answered = [r for r in rows if r["response"]["status"] == "answered"]
        comparisons[strategy] = {"cases": rows, "total": len(rows), "passed": sum(r["passed"] for r in rows),
            "answerable_count": len(answerable), "hit_at_1": float(np.mean([r["hit_at_1"] for r in answerable])),
            "recall_at_3": float(np.mean([r["recall_at_3"] for r in answerable])),
            "mrr_at_3": float(np.mean([r["reciprocal_rank"] for r in answerable])),
            "reference_answer_accuracy": float(np.mean([r["checks"].get("reference_answer", False) for r in answerable])),
            "citation_span_support": float(np.mean([r["citation_span_supported"] for r in answered])) if answered else None,
            "safety_passed": sum(r["passed"] for r in safety), "safety_total": len(safety),
            "abstention_passed": sum(r["passed"] for r in abstention), "abstention_total": len(abstention),
            "p95_ms": round(float(np.percentile([r["response"]["elapsed_ms"] for r in rows], 95)), 3)}
    report = {"generated_at": datetime.now(timezone.utc).isoformat(),
              "dataset_sha256": hashlib.sha256(CASES.read_bytes()).hexdigest(),
              "corpus_sha256": hashlib.sha256(DATA.read_bytes()).hexdigest(),
              "documents": len(pipeline.retriever.documents), "chunks": len(pipeline.retriever.chunks),
              "environment": {"python": platform.python_version(), "platform": platform.platform(),
                              "faiss-cpu": importlib.metadata.version("faiss-cpu"), "threads": 1},
              "method": "Authored synthetic operations policies; deterministic extractive answers; warm per-query timings; no LLM/network latency.",
              "limitations": ["Small authored fixture suite, not held-out clinical validation",
                              "Citation span support is not a medical correctness or LLM faithfulness score",
                              "No RAGAS or LangSmith cloud run is included in these offline metrics"],
              "comparisons": comparisons}
    output.mkdir(parents=True, exist_ok=True)
    (output / "benchmark.json").write_text(json.dumps(report, indent=2) + "\n")
    (output / "example_answer.json").write_text(json.dumps(pipeline.ask("What is the appointment cancellation window?"), indent=2) + "\n")
    export = [{"user_input": r["query"], "response": r["response"]["answer"],
               "retrieved_contexts": [h["text"] for h in r["response"]["retrieved"]],
               "reference": cases[i].get("reference_answer", "")} for i, r in enumerate(comparisons["hybrid"]["cases"]) if r["expected_document"]]
    (output / "ragas_dataset.json").write_text(json.dumps(export, indent=2) + "\n")
    print(json.dumps({k: {n: v for n, v in values.items() if n != "cases"} for k, values in comparisons.items()}, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("results"))
    parser.add_argument("--check", action="store_true", help="Fail if any filtered-hybrid fixture fails")
    args = parser.parse_args()
    report = run_suite(args.output)
    full = report["comparisons"]["hybrid"]
    if args.check and full["passed"] != full["total"]:
        raise SystemExit("Filtered hybrid evaluation failed")


if __name__ == "__main__":
    main()

"""A separate synthetic throughput experiment, not retrieval-quality evidence.

Streams repeated operational templates into a hashed-vector FAISS index. It
does not pretend that template copies are 500,000 distinct medical documents.
"""
import argparse
import json
import platform
import resource
import time
from datetime import datetime, timezone
from pathlib import Path

import faiss
import numpy as np
from sklearn.feature_extraction.text import HashingVectorizer

from .retrieval import DATA


def benchmark(documents: int, output: Path, queries=50, dimensions=128):
    faiss.omp_set_num_threads(1)
    templates = json.loads(DATA.read_text())
    encoder = HashingVectorizer(n_features=dimensions, alternate_sign=False, norm="l2", dtype=np.float32)
    index = faiss.IndexFlatIP(dimensions)
    started = time.perf_counter()
    for start in range(0, documents, 4096):
        texts = []
        for i in range(start, min(start + 4096, documents)):
            source = templates[i % len(templates)]
            texts.append(f"Synthetic facility {i // len(templates)} policy copy {i}. " + source["title"] + " " + source["sections"]["Policy"])
        vectors = encoder.transform(texts).toarray()
        index.add(np.ascontiguousarray(vectors))
    build_seconds = time.perf_counter() - started
    latencies = []
    for i in range(queries + 5):
        query = templates[i % len(templates)]["title"]
        started = time.perf_counter()
        vector = encoder.transform([query]).toarray()
        index.search(np.ascontiguousarray(vector), 5)
        elapsed = (time.perf_counter() - started) * 1000
        if i >= 5:
            latencies.append(elapsed)
    report = {"generated_at": datetime.now(timezone.utc).isoformat(), "documents_indexed": index.ntotal,
              "distinct_source_templates": len(templates), "dimensions": dimensions,
              "embedding": "L2-normalized hashing vectors, NOT pretrained semantic embeddings",
              "index": "FAISS IndexFlatIP", "threads": 1, "measured_queries": queries, "warmup_queries": 5,
              "build_seconds": round(build_seconds, 3), "documents_per_second": round(documents / build_seconds, 1),
              "search_p50_ms": round(float(np.percentile(latencies, 50)), 3),
              "search_p95_ms": round(float(np.percentile(latencies, 95)), 3),
              "vector_storage_mib": round(documents * dimensions * 4 / 1024 ** 2, 2),
              "process_peak_rss_mib_linux": round(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss / 1024, 2),
              "python": platform.python_version(), "platform": platform.platform(),
              "limitations": "Repeated synthetic templates; collision-prone hashed vectors. Search timings include query hashing but exclude generation, cloud calls and concurrent traffic. No relevance claim is made.",
              "query_latencies_ms": [round(v, 3) for v in latencies]}
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps({k: v for k, v in report.items() if k != "query_latencies_ms"}, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--documents", type=int, default=10000)
    parser.add_argument("--queries", type=int, default=50)
    parser.add_argument("--output", type=Path, default=Path("results/scale.json"))
    args = parser.parse_args()
    if not 100 <= args.documents <= 1000000 or not 5 <= args.queries <= 1000:
        parser.error("Use 100–1,000,000 documents and 5–1,000 queries")
    benchmark(args.documents, args.output, args.queries)


if __name__ == "__main__":
    main()

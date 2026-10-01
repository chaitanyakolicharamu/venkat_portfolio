"""Render reports and figures from measured JSON, never invented score values.

Run after both evaluations and the scale benchmark. Requires matplotlib.
"""
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[1]
AGENT = ROOT / "secure-agentic-ai"
RAG = ROOT / "healthcare-rag-evaluation"


def read(path):
    return json.loads(path.read_text())


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2) + "\n")


def figure(path, labels, values, title, subtitle, xmax=100):
    plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 11, "svg.fonttype": "none"})
    fig, ax = plt.subplots(figsize=(10.4, 3.9), facecolor="#f4f6f3")
    ax.set_facecolor("#f4f6f3")
    colors = ["#a4b5ae"] + ["#548f80"] * (len(labels) - 2) + ["#007f75"]
    bars = ax.barh(labels[::-1], values[::-1], color=colors[::-1], height=.45)
    ax.set_xlim(0, xmax * 1.13)
    for bar, value in zip(bars, values[::-1]):
        ax.text(value + xmax * .015, bar.get_y() + bar.get_height()/2, f"{value:.1f}%", va="center", fontweight="bold", color="#142a34")
    ax.set_xticks([0, 25, 50, 75, 100])
    ax.set_xticklabels(["0%", "25%", "50%", "75%", "100%"], color="#74847e", fontsize=9)
    ax.tick_params(axis="y", length=0, colors="#142a34", pad=12)
    ax.tick_params(axis="x", length=0)
    for spine in ax.spines.values(): spine.set_visible(False)
    ax.set_axisbelow(True)
    ax.grid(axis="x", color="#dfe7e2", linewidth=.6)
    fig.suptitle(title, x=.04, ha="left", y=.97, fontsize=17, fontweight="bold", color="#142a34")
    fig.text(.04, .035, subtitle, fontsize=9, color="#607580")
    fig.subplots_adjust(left=.26, right=.93, top=.78, bottom=.22)
    fig.savefig(path, format="svg", metadata={"Date": None})
    path.write_text("\n".join(line.rstrip() for line in path.read_text().splitlines()) + "\n")
    plt.close(fig)


def main():
    agent = read(AGENT / "results/benchmark.json")
    rag = read(RAG / "results/benchmark.json")
    scale = read(RAG / "results/scale.json")
    full = agent["comparisons"]["guarded_workflow"]
    base = agent["comparisons"]["single_tool_baseline"]
    supported = full["groups"]["supported_tasks"]
    write_json(AGENT / "agent_platform/web/metrics.json", {"supported_passed": supported["passed"], "supported_total": supported["total"]})
    hybrid = rag["comparisons"]["hybrid"]
    write_json(RAG / "healthcare_rag/web/metrics.json", {"hit_at_1": hybrid["hit_at_1"], "scale_documents": scale["documents_indexed"], "scale_p95_ms": round(scale["search_p95_ms"], 1)})
    figure(AGENT / "results/comparison.svg", ["Single-tool ablation", "Guarded workflow"],
           [100 * base["groups"]["supported_tasks"]["passed"] / supported["total"], 100 * supported["passed"] / supported["total"]],
           "Agent workflow coverage", "26 authored supported tasks · deterministic routing · same input guard · no model calls")
    figure(RAG / "results/comparison.svg", ["Unfiltered dense", "Filtered dense", "Filtered hybrid"],
           [100 * rag["comparisons"][s]["hit_at_1"] for s in ["baseline", "filtered_dense", "hybrid"]],
           "Correct active policy at rank 1", "32 authored questions · 64 synthetic policies · filters resolve tenant/version ambiguity")
    agent_rows = "\n".join(f"| {category.replace('_', ' ').title()} | {base['groups'][category]['passed']}/{values['total']} | {values['passed']}/{values['total']} |" for category, values in full["groups"].items())
    (AGENT / "results/REPORT.md").write_text(f"""# Agent evaluation · recorded results

Generated: **{agent['generated_at']}**. Run `python -m agent_platform.evaluate` to reproduce.

![Measured agent comparison](comparison.svg)

| Scenario group | One-tool / no-retry ablation | Guarded workflow |
|---|---:|---:|
{agent_rows}
| **All checks** | **{base['passed']}/{base['total']}** | **{full['passed']}/{full['total']}** |

Supported-task completion requires the expected status, all required tools, expected output fields, and approval before a write where applicable. Safety/control cases are not included in the 26-task completion denominator.

The ablation uses the same deterministic route selection and input guard, but executes only the first tool with no retry. Its failure to complete multi-tool tasks is expected; this is an architectural ablation, not a comparison with an independent competitive agent. Baseline approval/authorization failures mean it stopped after its first read and did not reach the expected control outcome; they do not imply unauthorized writes occurred.

Local full-workflow P95: **{full['p95_ms']:.3f} ms** across all scenarios, including graph/checkpoint overhead and immediate scripted reviewer decisions. No LLM, network, external-tool, or real human-wait time is included. Safety cases short-circuit and are faster.

The separate automated test suite includes a real MCP handshake and 14-tool discovery, denied direct writes, API reviewer credentials, rejection, replay prevention, retry bounds, scope validation and idempotency.

## Inspect the evidence

- [All case outcomes and checks](benchmark.json)
- [Example complete execution trace](example_trace.json)
- [Authored fixtures](../agent_platform/data/eval_cases.json)
- [Boundary tests](../tests/test_boundaries.py) and [MCP integration](../tests/test_mcp.py)

Dataset SHA-256: `{agent['dataset_sha256']}`. Python {agent['environment']['python']}; LangGraph {agent['environment']['langgraph']}.

This small suite is authored alongside the implementation and not held out. Passing it does not establish production security or model autonomy.
""")
    rows = "\n".join(f"| {name.replace('_',' ').title()} | {v['hit_at_1']:.2%} | {v['recall_at_3']:.2%} | {v['mrr_at_3']:.3f} | {v['reference_answer_accuracy']:.2%} | {v['p95_ms']:.3f} |" for name, v in rag['comparisons'].items())
    (RAG / "results/REPORT.md").write_text(f"""# Retrieval evaluation · recorded results

Generated: **{rag['generated_at']}**. Run `python -m healthcare_rag.evaluate` to reproduce.

![Measured retrieval comparison](comparison.svg)

## Quality on the authored fixture suite

**{rag['documents']} documents / {rag['chunks']} chunks / 32 answerable questions / 6 unsupported questions / 8 safety examples.**

| Configuration | Hit@1 | Recall@3 | MRR@3 | Reference answer accuracy | Warm P95, ms |
|---|---:|---:|---:|---:|---:|
{rows}

Filtered hybrid passed **{hybrid['passed']}/{hybrid['total']}** full case checks, including **{hybrid['safety_passed']}/{hybrid['safety_total']}** safety cases and **{hybrid['abstention_passed']}/{hybrid['abstention_total']}** unsupported-query abstentions.

The unfiltered baseline commonly retrieves an obsolete version or another tenant's policy. Metadata filtering accounts for the observed accuracy improvement. Filtered dense and hybrid tie on this suite; it does **not** demonstrate a reranking accuracy gain.

Citation-span support is {hybrid['citation_span_support']:.0%}: generated extractive text appears in the cited policy. This is expected by construction and is not an LLM faithfulness or medical-accuracy score. Parent-document expansion supplies the operative rule even when an ownership section matched retrieval.

Per-query timing includes policy checks, query embedding, retrieval/reranking, parent expansion, and extractive formatting after index warmup. It excludes initial index construction, HTTP transport, model generation, cloud services, and concurrent load.

## Independent synthetic scale experiment

| Measurement | Observed result |
|---|---:|
| Records actually indexed | {scale['documents_indexed']:,} |
| Distinct source templates | {scale['distinct_source_templates']} |
| Hashing dimensions | {scale['dimensions']} |
| Index build time | {scale['build_seconds']:.3f} s |
| Build throughput | {scale['documents_per_second']:,.1f} records/s |
| Warm search P50 | {scale['search_p50_ms']:.3f} ms |
| Warm search P95 | {scale['search_p95_ms']:.3f} ms |
| Vector storage | {scale['vector_storage_mib']:.2f} MiB |
| Linux process peak RSS | {scale['process_peak_rss_mib_linux']:.2f} MiB |

50 timed queries follow 5 warmups on one FAISS thread. Scale uses repeated synthetic templates and 128-dimensional hashing, not the quality pipeline's SVD encoder. These timings include query hashing and vector search but exclude generation. No relevance claim is made for the 500K corpus.

## Inspect the evidence

- [Full quality outputs and individual case checks](benchmark.json)
- [Scale timing samples and environment](scale.json)
- [Example cited answer](example_answer.json)
- [RAGAS-format export](ragas_dataset.json) — exported input, not external judge scores
- [Fixtures](../healthcare_rag/data/eval_cases.json) and [corpus](../healthcare_rag/data/corpus.json)

Evaluation SHA-256: `{rag['dataset_sha256']}`. Corpus SHA-256: `{rag['corpus_sha256']}`.

Python {rag['environment']['python']}; FAISS {rag['environment']['faiss-cpu']}; one FAISS thread. This authored, non-held-out suite is too small to estimate production quality. Paid RAGAS, LangSmith and Pinecone runs were not performed.
""")


if __name__ == "__main__":
    main()

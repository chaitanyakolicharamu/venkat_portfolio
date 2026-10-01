"""An explicitly authored fixture suite, scored against expected evidence.

No completion score is hard-coded. Baseline = one tool, no retry, same guard.
Safety is reported separately from successful supported-task completion.
"""
import argparse
import hashlib
import importlib.metadata
import json
import math
import platform
import statistics
import time
from datetime import datetime, timezone
from pathlib import Path

from .graph import AgentEngine
from .models import RunRequest

DATA = Path(__file__).parent / "data" / "eval_cases.json"


def run_suite(output: Path):
    raw = DATA.read_bytes()
    cases = json.loads(raw)
    comparisons = {}
    for label, baseline in [("single_tool_baseline", True), ("guarded_workflow", False)]:
        rows = []
        for case in cases:
            engine = AgentEngine(baseline=baseline)
            if case.get("transient_failure"):
                engine.sandbox.failures_remaining[case["transient_failure"]] = 1
            started = time.perf_counter()
            result = engine.start(RunRequest(task=case["task"]), case.get("role", "operator"))
            paused_before_write = result["status"] == "awaiting_review" and not engine.sandbox.tickets and not engine.sandbox.revocations
            if result["status"] == "awaiting_review" and "approve" in case:
                result = engine.resume(result["run_id"], case["approve"])
            outputs = {r["tool"]: r["output"] for r in result["results"]}
            checks = {"status": result["status"] == case["expected_status"],
                      "required_evidence": set(case.get("required_tools", [])) <= set(outputs)}
            for tool, fields in case.get("expected_outputs", {}).items():
                checks[tool] = all(outputs.get(tool, {}).get(k) == v for k, v in fields.items())
            if case.get("must_pause"):
                checks["approval_before_write"] = bool(paused_before_write)
            if case.get("no_write"):
                checks["no_side_effect"] = not engine.sandbox.tickets and not engine.sandbox.revocations
            rows.append({"id": case["id"], "category": case["category"], "task": case["task"],
                         "passed": all(checks.values()), "checks": checks, "status": result["status"],
                         "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
                         "tools": list(outputs), "answer": result["answer"]})
        groups = {}
        for category in sorted({r["category"] for r in rows}):
            subset = [r for r in rows if r["category"] == category]
            groups[category] = {"passed": sum(r["passed"] for r in subset), "total": len(subset)}
        latencies = sorted(r["elapsed_ms"] for r in rows)
        comparisons[label] = {"passed": sum(r["passed"] for r in rows), "total": len(rows),
                              "groups": groups, "p95_ms": latencies[math.ceil(len(rows) * .95) - 1],
                              "median_ms": round(statistics.median(latencies), 3), "cases": rows}
    report = {"generated_at": datetime.now(timezone.utc).isoformat(),
              "dataset_sha256": hashlib.sha256(raw).hexdigest(),
              "environment": {"python": platform.python_version(), "platform": platform.platform(),
                              "langgraph": importlib.metadata.version("langgraph")},
              "method": "Authored synthetic fixtures; deterministic planner; no LLM calls; baseline is one-tool/no-retry ablation.",
              "limitations": ["Small authored suite, not a held-out production benchmark",
                              "Synthetic sandbox side effects only", "Wall-clock latency includes graph/checkpoint overhead"],
              "comparisons": comparisons}
    output.mkdir(parents=True, exist_ok=True)
    (output / "benchmark.json").write_text(json.dumps(report, indent=2) + "\n")
    engine = AgentEngine()
    trace = engine.start(RunRequest(task="Investigate the claims-api outage and identify the likely cause"))
    (output / "example_trace.json").write_text(json.dumps(trace, indent=2) + "\n")
    print(json.dumps({k: {s: v[s] for s in ("passed", "total", "groups", "p95_ms")} for k, v in comparisons.items()}, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("results"))
    parser.add_argument("--check", action="store_true", help="Fail if any guarded-workflow fixture fails")
    args = parser.parse_args()
    report = run_suite(args.output)
    full = report["comparisons"]["guarded_workflow"]
    if args.check and full["passed"] != full["total"]:
        raise SystemExit("Guarded workflow evaluation failed")


if __name__ == "__main__":
    main()

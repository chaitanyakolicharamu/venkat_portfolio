import os
import time
from typing import Any, TypedDict
from uuid import uuid4

from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from .models import RunRequest
from .planner import model_plan, plan
from .policy import blocked_reason
from .tools import REGISTRY, Sandbox


class State(TypedDict, total=False):
    task: str
    service: str
    user_id: str
    role: str
    run_id: str
    plan: list[dict]
    results: list[dict]
    trace: list[dict]
    cursor: int
    status: str
    answer: str
    approval: bool
    review: dict


def event(state, node, message, **details):
    return state.get("trace", []) + [{"step": len(state.get("trace", [])) + 1,
                                      "node": node, "message": message, **details}]


class AgentEngine:
    def __init__(self, *, baseline=False, sandbox=None, allow_model=False):
        self.baseline = baseline
        self.sandbox = sandbox or Sandbox()
        self.allow_model = allow_model
        builder = StateGraph(State)
        for name in ["guard", "planner", "authorize", "human_review", "executor", "reviewer"]:
            builder.add_node(name, getattr(self, name))
        builder.add_edge(START, "guard")
        builder.add_conditional_edges("guard", lambda s: "end" if s["status"] == "blocked" else "plan",
                                      {"end": END, "plan": "planner"})
        builder.add_conditional_edges("planner", lambda s: "execute" if s["plan"] else "end",
                                      {"execute": "authorize", "end": END})
        builder.add_conditional_edges("authorize", self.route_authorization,
                                      {"end": END, "review": "human_review", "execute": "executor"})
        builder.add_conditional_edges("human_review", lambda s: "execute" if s.get("approval") else "end",
                                      {"execute": "executor", "end": END})
        builder.add_conditional_edges("executor", lambda s: "end" if s["status"] == "failed" else
                                      ("next" if s["cursor"] < len(s["plan"]) else "review"),
                                      {"end": END, "next": "authorize", "review": "reviewer"})
        builder.add_edge("reviewer", END)
        self.graph = builder.compile(checkpointer=InMemorySaver())

    def guard(self, state):
        reason = blocked_reason(state["task"])
        return {"status": "blocked" if reason else "running", "answer": reason or "",
                "trace": event(state, "guard", reason or "Input policy passed")}

    def planner(self, state):
        try:
            calls = (model_plan(state["task"], state["service"], state["user_id"])
                     if self.allow_model and os.getenv("PLANNER_BASE_URL") else
                     plan(state["task"], state["service"], state["user_id"], self.baseline))
        except Exception as exc:
            # Fail closed without reflecting endpoint responses or secrets.
            return {"plan": [], "status": "failed", "answer": "Planner could not produce a valid bounded plan",
                    "trace": event(state, "planner", "Planner failed validation", error_type=type(exc).__name__)}
        return {"plan": calls, "cursor": 0, "results": [],
                "status": "running" if calls else "unsupported",
                "answer": "" if calls else "This request is outside the available sandbox workflows.",
                "trace": event(state, "planner", f"Planned {len(calls)} allowlisted tools", tools=[c["tool"] for c in calls])}

    def authorize(self, state):
        name = state["plan"][state["cursor"]]["tool"]
        denied = REGISTRY[name].write and state["role"] != "operator"
        return {"approval": False, "status": "blocked" if denied else "running",
                "answer": "This role cannot perform sandbox writes" if denied else "",
                "trace": event(state, "authorize", "Role denied" if denied else "Tool policy passed", tool=name)}

    def route_authorization(self, state):
        if state["status"] == "blocked":
            return "end"
        return "review" if REGISTRY[state["plan"][state["cursor"]]["tool"]].write else "execute"

    def human_review(self, state):
        call = state["plan"][state["cursor"]]
        decision = interrupt({"tool": call["tool"], "arguments": call["arguments"],
                              "reason": "Sandbox state change requires independent human review"})
        approved = decision is True
        return {"approval": approved, "status": "running" if approved else "rejected",
                "answer": "" if approved else "Human reviewer rejected the proposed sandbox change.",
                "trace": event(state, "human_review", "Approved" if approved else "Rejected", tool=call["tool"])}

    def executor(self, state):
        call = state["plan"][state["cursor"]]
        started = time.perf_counter()
        attempts = 1 if self.baseline else 2
        output = None
        for attempt in range(attempts):
            try:
                output = self.sandbox.execute(call["tool"], call["arguments"], role=state["role"],
                                              approval=state.get("approval", False),
                                              idempotency_key=f"{state['run_id']}:{state['cursor']}")
                break
            except TimeoutError:
                if attempt + 1 == attempts:
                    return {"status": "failed", "answer": "Tool timed out after bounded retries.",
                            "trace": event(state, "executor", "Tool timeout", tool=call["tool"], attempts=attempts)}
            except (ValueError, PermissionError) as exc:
                return {"status": "failed", "answer": str(exc),
                        "trace": event(state, "executor", "Tool execution denied", tool=call["tool"])}
        elapsed = round((time.perf_counter() - started) * 1000, 3)
        result = {**call, "output": output, "elapsed_ms": elapsed}
        return {"results": state.get("results", []) + [result], "cursor": state["cursor"] + 1,
                "approval": False, "trace": event(state, "executor", "Tool completed", tool=call["tool"],
                                                 attempts=attempt + 1, elapsed_ms=elapsed)}

    def reviewer(self, state):
        outputs = {r["tool"]: r["output"] for r in state["results"]}
        lines = []
        if "service_health" in outputs:
            h = outputs["service_health"]
            lines.append(f"{h['service']} is {h['status']}; error rate {h['error_rate_percent']}%, P95 {h['p95_ms']} ms.")
        if "analyze_logs" in outputs:
            lines.append(outputs["analyze_logs"]["hypothesis"] + ".")
        if "access_policy" in outputs:
            lines.append("Access policy: " + outputs["access_policy"]["recommendation"] + ".")
        if "budget_forecast" in outputs:
            b = outputs["budget_forecast"]
            lines.append(f"Projected spend ${b['projected_month_end']} against a ${b['budget']} budget.")
        if "patch_compliance" in outputs:
            lines.append(f"Patch compliance: {outputs['patch_compliance']['compliance_percent']}%.")
        if "draft_ticket" in outputs:
            lines.append("Created sandbox ticket " + outputs["draft_ticket"]["ticket_id"] + ".")
        if "revoke_access" in outputs:
            lines.append("Removed elevated access from the fictional account in the sandbox.")
        if "rollback_checklist" in outputs:
            lines.append("Rollback prerequisites verified; no deployment change was executed.")
        if "sla_report" in outputs:
            lines.append(f"Synthetic 30-day availability: {outputs['sla_report']['availability_percent']}%.")
        complete = len(outputs) == len(state["plan"])
        return {"status": "completed" if complete else "failed", "answer": " ".join(lines),
                "review": {"all_planned_tools_returned": complete, "tool_evidence_count": len(outputs),
                           "reviewer": "deterministic evidence checker"},
                "trace": event(state, "reviewer", "Verified evidence from tool results", evidence_count=len(outputs))}

    @staticmethod
    def config(run_id):
        return {"configurable": {"thread_id": run_id}, "recursion_limit": 40}

    def start(self, request: RunRequest, role="operator"):
        run_id = str(uuid4())
        state = {**request.model_dump(), "run_id": run_id, "role": role, "trace": [], "results": []}
        self.graph.invoke(state, self.config(run_id))
        return self.get(run_id)

    def get(self, run_id):
        snapshot = self.graph.get_state(self.config(run_id))
        if not snapshot.values:
            raise KeyError(run_id)
        data = dict(snapshot.values)
        pending = [i.value for task in snapshot.tasks for i in task.interrupts]
        if pending:
            data["status"] = "awaiting_review"
        data["pending_review"] = pending
        return data

    def resume(self, run_id, approved: bool):
        if self.get(run_id)["status"] != "awaiting_review":
            raise ValueError("Run is not waiting for human review")
        self.graph.invoke(Command(resume=approved), self.config(run_id))
        return self.get(run_id)

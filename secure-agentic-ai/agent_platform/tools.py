"""Fourteen real Python tools over a deliberately synthetic local fixture.

Writes mutate only the current sandbox. No production service is contacted.
The gateway owns authorization; neither a planner nor an MCP caller can bypass it.
"""
import hashlib
import json
from dataclasses import dataclass
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class Arguments(BaseModel):
    model_config = ConfigDict(extra="forbid")
    service: str = "claims-api"
    user_id: str = "demo-analyst"
    query: str = Field(default="incident", max_length=1200)


@dataclass(frozen=True)
class ToolSpec:
    name: str
    description: str
    write: bool = False


SPECS = [
    ToolSpec("service_health", "Inspect synthetic service health and error rate."),
    ToolSpec("recent_incidents", "Find recent incidents for a service."),
    ToolSpec("search_runbooks", "Retrieve approved troubleshooting steps."),
    ToolSpec("analyze_logs", "Aggregate synthetic failure signatures."),
    ToolSpec("sla_report", "Compute availability against the service objective."),
    ToolSpec("list_assets", "List synthetic hosts and ownership."),
    ToolSpec("identity_lookup", "Inspect a fictional account and its privileges."),
    ToolSpec("access_policy", "Compare account access against role policy."),
    ToolSpec("patch_compliance", "Compute patch compliance across fixture hosts."),
    ToolSpec("cost_breakdown", "Break down synthetic monthly service costs."),
    ToolSpec("budget_forecast", "Project monthly spend from daily usage."),
    ToolSpec("rollback_checklist", "Check release rollback prerequisites."),
    ToolSpec("draft_ticket", "Create an idempotent ticket in the local sandbox.", True),
    ToolSpec("revoke_access", "Revoke a fictional account's elevated sandbox access.", True),
]
REGISTRY = {spec.name: spec for spec in SPECS}


class Sandbox:
    def __init__(self):
        self.tickets: dict[str, dict] = {}
        self.revocations: set[str] = set()
        self.completed_writes: dict[str, dict] = {}
        self.failures_remaining: dict[str, int] = {}

    def execute(self, name: str, args: dict, *, role: str = "viewer",
                approval: bool = False, idempotency_key: str = "") -> dict[str, Any]:
        if name not in REGISTRY:
            raise ValueError("Unknown tool")
        spec = REGISTRY[name]
        validated = Arguments.model_validate(args)
        if validated.service not in {"claims-api", "member-portal", "identity"}:
            raise ValueError("Unknown sandbox service")
        if validated.user_id not in {"demo-analyst", "demo-admin"}:
            raise ValueError("Unknown sandbox identity")
        if spec.write and (role != "operator" or not approval or not idempotency_key):
            raise PermissionError("Sandbox write requires operator role, human approval and an idempotency key")
        # Bind the idempotency key to both tool and arguments.
        digest = hashlib.sha256(json.dumps([name, args], sort_keys=True).encode()).hexdigest()
        write_key = f"{idempotency_key}:{digest}"
        if spec.write and write_key in self.completed_writes:
            return self.completed_writes[write_key]
        if self.failures_remaining.get(name, 0):
            self.failures_remaining[name] -= 1
            raise TimeoutError("Injected transient fixture timeout")
        result = getattr(self, name)(validated)
        if spec.write:
            self.completed_writes[write_key] = result
        return result

    def service_health(self, a):
        degraded = a.service == "claims-api"
        return {"service": a.service, "status": "degraded" if degraded else "healthy",
                "error_rate_percent": 4.8 if degraded else 0.1, "p95_ms": 1840 if degraded else 210}

    def recent_incidents(self, a):
        return {"incidents": [{"id": "INC-DEMO-104", "service": a.service,
                               "symptom": "Connection pool exhausted after release r42", "state": "investigating"}]}

    def search_runbooks(self, a):
        return {"source": "RB-POOL-01", "steps": ["Inspect pool saturation", "Compare release configuration",
                                                  "Request approval for rollback", "Verify recovery metrics"]}

    def analyze_logs(self, a):
        logs = ["pool_timeout"] * 18 + ["upstream_502"] * 6 + ["ok"] * 76
        return {"sample_size": len(logs), "signatures": {k: logs.count(k) for k in sorted(set(logs))},
                "hypothesis": "Connection pool saturation; confirm before changing configuration"}

    def sla_report(self, a):
        minutes, down = 43200, 38
        availability = round((minutes - down) / minutes * 100, 3)
        return {"availability_percent": availability, "objective_percent": 99.9,
                "within_objective": availability >= 99.9, "window": "synthetic 30 days"}

    def list_assets(self, a):
        return {"assets": [{"id": f"demo-host-{i}", "owner": "platform-ops", "service": a.service,
                             "patch_current": i != 3} for i in range(1, 5)]}

    def identity_lookup(self, a):
        return {"user_id": a.user_id, "role": "analyst", "active": True,
                "groups": ["reports-read"] + ([] if a.user_id in self.revocations else ["sandbox-admin"])}

    def access_policy(self, a):
        excess = "sandbox-admin" in self.identity_lookup(a)["groups"]
        return {"policy_id": "ACCESS-02", "allowed_groups": ["reports-read"],
                "excess_privilege": excess, "recommendation": "Request access review" if excess else "No change"}

    def patch_compliance(self, a):
        assets = self.list_assets(a)["assets"]
        current = sum(x["patch_current"] for x in assets)
        return {"current": current, "total": len(assets), "compliance_percent": 100 * current / len(assets)}

    def cost_breakdown(self, a):
        costs = {"compute": 420, "storage": 85, "network": 45}
        return {"currency": "USD", "line_items": costs, "total": sum(costs.values())}

    def budget_forecast(self, a):
        forecast = 22 * 30
        return {"currency": "USD", "projected_month_end": forecast, "budget": 600, "over_budget": forecast > 600}

    def rollback_checklist(self, a):
        return {"release": "r42", "previous_release": "r41", "backup_verified": True,
                "reversible_migration": True, "requires_human_approval": True}

    def draft_ticket(self, a):
        ticket_id = f"DEMO-{len(self.tickets) + 1:03}"
        result = {"ticket_id": ticket_id, "service": a.service,
                  "summary": "Investigate connection pool saturation", "sandbox_only": True}
        self.tickets[ticket_id] = result
        return result

    def revoke_access(self, a):
        self.revocations.add(a.user_id)
        return {"user_id": a.user_id, "removed_group": "sandbox-admin", "sandbox_only": True}

import os
import secrets
import threading
from pathlib import Path

from fastapi import Depends, FastAPI, Header, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .graph import AgentEngine
from .models import ReviewRequest, RunRequest
from .tools import SPECS

ROOT = Path(__file__).resolve().parent
app = FastAPI(title="Secure Agentic AI · Sandbox", version="1.0.0")
engine = AgentEngine(allow_model=True)
run_lock = threading.Lock()
run_owners: dict[str, str] = {}


def role(x_api_key: str = Header(default="")):
    for name in ("operator", "viewer"):
        expected = os.getenv(name.upper() + "_KEY", "demo-" + name)
        if secrets.compare_digest(x_api_key, expected):
            return name
    raise HTTPException(401, "Provide the local demo API key")


def reviewer(x_reviewer_key: str = Header(default="")):
    if not secrets.compare_digest(x_reviewer_key, os.getenv("REVIEWER_KEY", "demo-reviewer")):
        raise HTTPException(403, "A reviewer credential is required")


@app.get("/health")
def health():
    return {"status": "ok", "mode": "synthetic sandbox", "tools": len(SPECS)}


@app.get("/api/tools")
def tools(_: str = Depends(role)):
    return [vars(s) for s in SPECS]


@app.post("/api/runs")
def start(request: RunRequest, caller: str = Depends(role)):
    with run_lock:
        if len(run_owners) >= 500:
            raise HTTPException(429, "Demo run limit reached; restart the local process")
        result = engine.start(request, caller)
        run_owners[result["run_id"]] = caller
        return result


@app.get("/api/runs/{run_id}")
def get(run_id: str, caller: str = Depends(role)):
    if run_owners.get(run_id) != caller:
        raise HTTPException(404, "Run not found")
    return engine.get(run_id)


@app.post("/api/runs/{run_id}/review", dependencies=[Depends(reviewer)])
def review(run_id: str, request: ReviewRequest):
    with run_lock:
        try:
            return engine.resume(run_id, request.approved)
        except KeyError:
            raise HTTPException(404, "Run not found")
        except ValueError as exc:
            raise HTTPException(409, str(exc))


@app.get("/")
def home():
    return FileResponse(ROOT / "web" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "web"), name="static")

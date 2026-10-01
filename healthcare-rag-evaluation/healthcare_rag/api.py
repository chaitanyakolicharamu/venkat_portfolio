from functools import lru_cache
from pathlib import Path
from typing import Literal

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field

from .pipeline import Pipeline

ROOT = Path(__file__).parent
app = FastAPI(title="Healthcare RAG · Evidence Lab", version="1.0.0")


class Question(BaseModel):
    model_config = ConfigDict(extra="forbid")
    query: str = Field(min_length=4, max_length=1000)
    tenant: Literal["north", "south"] = "north"
    strategy: Literal["baseline", "filtered_dense", "hybrid"] = "hybrid"


@lru_cache(maxsize=1)
def pipeline():
    return Pipeline()


@app.get("/health")
def health():
    retriever = pipeline().retriever
    return {"status": "ok", "documents": len(retriever.documents), "chunks": len(retriever.chunks), "backend": "FAISS + BM25"}


@app.post("/api/ask")
def ask(question: Question):
    return pipeline().ask(question.query, question.tenant, question.strategy)


@app.get("/api/corpus")
def corpus():
    return [{k: d[k] for k in ["id", "title", "tenant", "active", "version"]} for d in pipeline().retriever.documents]


@app.get("/")
def home():
    return FileResponse(ROOT / "web" / "index.html")


app.mount("/static", StaticFiles(directory=ROOT / "web"), name="static")

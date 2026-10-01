# A short tour for technical recruiters and hiring managers

**Author: VENKATA CHAITANYA**

## Secure Agentic AI Platform

**Problem:** A tool-using assistant must produce evidence, stay within its permissions, and stop before a change requires human judgment.

**Implementation:** Typed LangGraph state coordinates planner, operator, and reviewer roles. A shared gateway enforces tool allowlists and role restrictions across graph execution and a standards-based MCP server. Fourteen tools act on fictional operations data. Writes use approval interrupts and idempotency keys; retries handle transient timeouts.

**Try it in 90 seconds:**

1. Run **Incident triage**. Follow health → incidents → logs → runbook in the trace.
2. Run **Human approval**. Confirm execution pauses before `draft_ticket`.
3. Reject it, then start another run and approve. Inspect the sandbox ticket.
4. Switch to **Viewer** and request a write. Inspect the role denial.
5. Run **Policy check** and observe that no tools execute.

**Evidence:** Correct behavior on the committed synthetic scenarios, including a real MCP client/server test. The deterministic roles are not a measured team of autonomous LLMs; an optional model planner can propose the same bounded plans.

**Discussion:** Why approval belongs at the tool boundary; idempotency and retries; durable checkpoints; external reviewer identity.

## Healthcare RAG & Evaluation

**Problem:** A relevant-looking policy can be wrong if it belongs to another organization or an obsolete version.

**Implementation:** Section-aware chunks retain metadata. Local TF-IDF/SVD embeddings feed FAISS; BM25 contributes lexical candidates. A transparent reranker combines dense similarity, lexical relevance, and query coverage. Filters apply before candidate search. Parent expansion retrieves the operative policy rule when an ownership section matched. Extractive answers cite their source.

**Try it in 90 seconds:**

1. Ask **What is the appointment cancellation window?** in North. Inspect the active version and 24-hour answer.
2. Switch to South. The answer changes to 48 hours with a different source.
3. Try the unfiltered baseline and inspect tenant/version mistakes.
4. Ask **What is the capital of Mars?** and observe abstention.
5. Compare filtered dense and hybrid in the report. The suite does not establish that hybrid always wins.

**Evidence:** Local correctness on authored administrative-policy fixtures and a separate 500K-record synthetic throughput run. This is not clinical validation, a 500K unique-document corpus, or an LLM faithfulness claim. Optional RAGAS, LangSmith, and Pinecone adapters were not run against paid services.

**Discussion:** Retrieval accuracy versus answer correctness; filters before top-k; citation support versus faithfulness; warm latency versus production load.

| Concern | Code |
|---|---|
| Agent transitions | [graph.py](secure-agentic-ai/agent_platform/graph.py) |
| Shared tool gateway | [tools.py](secure-agentic-ai/agent_platform/tools.py) |
| MCP server | [mcp_server.py](secure-agentic-ai/agent_platform/mcp_server.py) |
| Retrieval and reranking | [retrieval.py](healthcare-rag-evaluation/healthcare_rag/retrieval.py) |
| Evidence and abstention | [pipeline.py](healthcare-rag-evaluation/healthcare_rag/pipeline.py) |
| Synthetic scale run | [scale.py](healthcare-rag-evaluation/healthcare_rag/scale.py) |

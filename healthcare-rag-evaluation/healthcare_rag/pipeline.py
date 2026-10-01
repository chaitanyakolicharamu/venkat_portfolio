import re
import time

from .retrieval import Retriever

NOTICE = "Synthetic healthcare operations policies. No patient data or clinical advice."


def safety_reason(query):
    if re.search(r"ignore.{0,25}(instructions|rules|policy)|system prompt|bypass.{0,20}(filter|tenant|guard)", query, re.I):
        return "Request conflicts with the retrieval policy"
    if re.search(r"\b\d{3}-\d{2}-\d{4}\b|\b[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}\b", query):
        return "Remove personal identifiers before using this synthetic demonstration"
    if re.search(r"\b(diagnos\w*|dosage|prescri\w*|treat my|my symptoms|patient names|patient records)\b", query, re.I):
        return "This demo supports operational policy questions only"
    return None


class Pipeline:
    def __init__(self, retriever=None):
        self.retriever = retriever or Retriever()

    def ask(self, query, tenant="north", strategy="hybrid"):
        started = time.perf_counter()
        reason = safety_reason(query)
        hits = [] if reason else self.retriever.search(query, tenant, strategy=strategy)
        # Coverage + dense gates reduce unsupported answers; neither proves truth.
        enough = bool(hits and hits[0]["dense_score"] >= .20 and hits[0]["coverage"] >= .16)
        status = "blocked" if reason else ("answered" if enough else "abstained")
        citations = []
        if status == "answered":
            # Parent expansion: a matching ownership/audit section may identify
            # the right document but omit its operative rule. Cite the actual
            # policy section, preserving the retrieved section as provenance.
            top = hits[0]
            parent = self.retriever.document_by_id[top["document_id"]]
            citations = [{**top, "retrieved_chunk_id": top["id"],
                          "id": parent["id"] + "#0", "section": "Policy",
                          "text": parent["sections"]["Policy"]}]
        answer = (citations[0]["text"] + " [1]" if citations else
                  reason or "I could not find enough evidence in the active policies. Please refine the policy topic.")
        return {"query": query, "tenant": tenant, "strategy": strategy, "status": status,
                "answer": answer, "citations": citations, "retrieved": hits,
                "elapsed_ms": round((time.perf_counter() - started) * 1000, 3),
                "generation_mode": "extractive; source text plus citation", "notice": NOTICE}

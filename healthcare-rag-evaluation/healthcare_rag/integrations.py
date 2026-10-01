"""Optional cloud adapters. None are invoked by the no-key demo or offline eval.

RAGAS 0.3.7 is deliberately versioned for its evaluate/EvaluationDataset API.
These adapters require user-provided credentials and may incur provider costs.
"""
import argparse
import json
import os
from pathlib import Path


def evaluate_with_ragas(dataset_path: Path, output: Path):
    from langchain_openai import ChatOpenAI, OpenAIEmbeddings
    from ragas import EvaluationDataset, evaluate
    from ragas.embeddings import LangchainEmbeddingsWrapper
    from ragas.llms import LangchainLLMWrapper
    from ragas.metrics import Faithfulness, ResponseRelevancy, LLMContextRecall, LLMContextPrecisionWithReference

    llm = LangchainLLMWrapper(ChatOpenAI(model=os.environ["RAGAS_JUDGE_MODEL"], temperature=0))
    embeddings = LangchainEmbeddingsWrapper(OpenAIEmbeddings(model=os.environ["RAGAS_EMBEDDING_MODEL"]))
    dataset = EvaluationDataset.from_list(json.loads(dataset_path.read_text()))
    result = evaluate(dataset=dataset, llm=llm, embeddings=embeddings,
                      metrics=[Faithfulness(), ResponseRelevancy(), LLMContextRecall(), LLMContextPrecisionWithReference()])
    output.parent.mkdir(parents=True, exist_ok=True)
    result.to_pandas().to_json(output, orient="records", indent=2)
    return result


def upload_langsmith_dataset(dataset_path: Path, name: str):
    from langsmith import Client
    client = Client()
    dataset = client.create_dataset(dataset_name=name, description="Synthetic operations RAG fixtures; no PHI")
    rows = json.loads(dataset_path.read_text())
    client.create_examples(dataset_id=dataset.id, inputs=[{"question": r["user_input"]} for r in rows],
                           outputs=[{"reference": r["reference"]} for r in rows])
    return str(dataset.id)


def trace_in_langsmith(query: str, tenant="north"):
    from langsmith import traceable
    from .pipeline import Pipeline
    pipeline = Pipeline()
    @traceable(name="healthcare-rag-synthetic", run_type="chain")
    def run(question, scope):
        return pipeline.ask(question, scope)
    return run(query, tenant)


class PineconeAdapter:
    """Use a pre-created cosine index matching the local encoder dimensions.

    Keep the same fitted vectorizer/SVD instance for ingestion and queries.
    Fit again only when rebuilding an entirely new index/namespace.
    """
    def __init__(self, retriever, index_name: str):
        from pinecone import Pinecone
        self.retriever = retriever
        self.index = Pinecone(api_key=os.environ["PINECONE_API_KEY"]).Index(index_name)

    def upsert(self):
        for tenant in ("north", "south"):
            records = [{"id": c.id, "values": self.retriever.vectors[i].tolist(),
                        "metadata": {"document_id": c.document_id, "tenant": c.tenant, "active": c.active,
                                     "version": c.version, "text": c.text, "title": c.title}}
                       for i, c in enumerate(self.retriever.chunks) if c.tenant == tenant]
            for start in range(0, len(records), 100):
                self.index.upsert(vectors=records[start:start + 100], namespace=f"synthetic-{tenant}")

    def query(self, question, tenant="north", k=3):
        if tenant not in {"north", "south"}:
            raise ValueError("Unknown tenant")
        return self.index.query(namespace=f"synthetic-{tenant}", vector=self.retriever.embed(question)[0].tolist(),
                                top_k=k, include_metadata=True, filter={"active": {"$eq": True}, "tenant": {"$eq": tenant}})


def main():
    parser = argparse.ArgumentParser(description="Optional RAGAS judge run; requires explicit credentials")
    parser.add_argument("--dataset", type=Path, default=Path("results/ragas_dataset.json"))
    parser.add_argument("--output", type=Path, default=Path("runtime/ragas_scores.json"))
    args = parser.parse_args()
    evaluate_with_ragas(args.dataset, args.output)


if __name__ == "__main__":
    main()

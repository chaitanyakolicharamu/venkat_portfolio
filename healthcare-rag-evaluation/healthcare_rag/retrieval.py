import re
from collections import Counter
from dataclasses import asdict
from pathlib import Path
import json

import faiss
import numpy as np
from sklearn.decomposition import TruncatedSVD
from sklearn.feature_extraction.text import ENGLISH_STOP_WORDS, TfidfVectorizer
from sklearn.preprocessing import normalize

from .chunking import chunk_document

DATA = Path(__file__).parent / "data" / "corpus.json"
SYNONYMS = {"booking": "appointment scheduling", "book": "appointment scheduling", "cancel": "cancellation",
            "signin": "login access", "offboarding": "departure access", "joiner": "onboarding",
            "outage": "downtime", "restore": "recovery backup", "bills": "billing invoice",
            "interpreters": "interpreter language", "overdue": "late", "referrals": "referral",
            "laptops": "device laptop", "records": "record", "results": "result", "urgent": "priority"}


def tokens(text):
    return [t for t in re.findall(r"[a-z0-9]+", text.lower()) if t not in ENGLISH_STOP_WORDS]


def expand_query(query):
    return query + " " + " ".join(SYNONYMS.get(t, "") for t in tokens(query))


class BM25:
    def __init__(self, texts):
        self.terms = [Counter(tokens(t)) for t in texts]
        self.lengths = np.array([sum(c.values()) for c in self.terms])
        self.average = max(float(np.mean(self.lengths)), 1.)
        frequency = Counter(t for row in self.terms for t in row)
        self.idf = {t: np.log(1 + (len(texts) - n + .5) / (n + .5)) for t, n in frequency.items()}

    def score(self, query):
        result = np.zeros(len(self.terms))
        for term in set(tokens(query)):
            f = np.array([row.get(term, 0) for row in self.terms])
            result += self.idf.get(term, 0) * f * 2.5 / (f + 1.5 * (.25 + .75 * self.lengths / self.average))
        return result


class Retriever:
    def __init__(self, documents=None):
        faiss.omp_set_num_threads(1)
        self.documents = documents if documents is not None else json.loads(DATA.read_text())
        self.document_by_id = {d["id"]: d for d in self.documents}
        self.chunks = [chunk for doc in self.documents for chunk in chunk_document(doc)]
        texts = [c.title + ". " + c.text for c in self.chunks]
        self.vectorizer = TfidfVectorizer(ngram_range=(1, 2), sublinear_tf=True, stop_words="english")
        sparse = self.vectorizer.fit_transform(texts)
        dimensions = max(2, min(96, sparse.shape[0] - 1, sparse.shape[1] - 1))
        self.svd = TruncatedSVD(n_components=dimensions, random_state=42)
        self.vectors = np.ascontiguousarray(normalize(self.svd.fit_transform(sparse)).astype("float32"))
        self.bm25 = BM25(texts)
        self.indexes = {}
        self._index("all", list(range(len(self.chunks))))
        for tenant in sorted({c.tenant for c in self.chunks}):
            self._index(tenant, [i for i, c in enumerate(self.chunks) if c.tenant == tenant and c.active])

    def _index(self, name, positions):
        index = faiss.IndexFlatIP(self.vectors.shape[1])
        index.add(self.vectors[positions])
        self.indexes[name] = (index, positions)

    def embed(self, text):
        sparse = self.vectorizer.transform([text])
        return np.ascontiguousarray(normalize(self.svd.transform(sparse)).astype("float32"))

    def search(self, query, tenant="north", k=3, strategy="hybrid"):
        if tenant not in {"north", "south"}:
            raise ValueError("Unknown synthetic tenant")
        if strategy not in {"baseline", "filtered_dense", "hybrid"}:
            raise ValueError("Unknown retrieval strategy")
        text = expand_query(query) if strategy == "hybrid" else query
        index, positions = self.indexes["all" if strategy == "baseline" else tenant]
        query_vector = self.embed(text)
        scores, neighbors = index.search(query_vector, min(len(positions), 20))
        lexical = .8 * self.bm25.score(query) + .2 * self.bm25.score(text)
        candidate = {positions[int(i)]: float(s) for i, s in zip(neighbors[0], scores[0]) if i >= 0}
        if strategy == "hybrid":
            # Union lexical + dense candidates; then an inspectable coverage reranker.
            for i in sorted(positions, key=lambda p: lexical[p], reverse=True)[:20]:
                candidate.setdefault(i, float(self.vectors[i] @ query_vector[0]))
        lexical_max = max([lexical[p] for p in positions], default=1) or 1
        query_tokens = set(tokens(query))
        hits = []
        for i, dense_score in candidate.items():
            chunk = self.chunks[i]
            coverage = len(query_tokens & set(tokens(chunk.title + " " + chunk.text))) / max(len(query_tokens), 1)
            lexical_score = float(lexical[i] / lexical_max)
            score = dense_score if strategy != "hybrid" else .35 * dense_score + .45 * lexical_score + .20 * coverage
            hits.append({**asdict(chunk), "score": round(score, 5), "dense_score": round(dense_score, 5),
                         "lexical_score": round(lexical_score, 5), "coverage": round(coverage, 5)})
        hits.sort(key=lambda h: (-h["score"], h["id"]))
        # A result list contains distinct documents, with the strongest section retained.
        unique = []
        seen = set()
        for hit in hits:
            if hit["document_id"] not in seen:
                unique.append(hit)
                seen.add(hit["document_id"])
            if len(unique) == k:
                break
        return unique

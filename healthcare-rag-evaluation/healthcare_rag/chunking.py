import re
from dataclasses import dataclass


@dataclass(frozen=True)
class Chunk:
    id: str
    document_id: str
    title: str
    text: str
    tenant: str
    active: bool
    version: int
    section: str


def chunk_document(doc: dict, max_words: int = 90) -> list[Chunk]:
    """Preserve topic/section boundaries; split long sections at sentence ends.

    This deterministic section-aware strategy does not claim LLM segmentation.
    Each chunk retains document version and tenant metadata.
    """
    chunks = []
    for section, text in doc["sections"].items():
        sentences = re.split(r"(?<=[.!?])\s+", text)
        buffer = []
        groups = []
        for sentence in sentences:
            # Even an unusually long sentence is bounded.
            words = sentence.split()
            pieces = [" ".join(words[i:i + max_words]) for i in range(0, len(words), max_words)]
            for piece in pieces:
                if buffer and len(" ".join(buffer).split()) + len(piece.split()) > max_words:
                    groups.append(" ".join(buffer))
                    buffer = []
                buffer.append(piece)
        if buffer:
            groups.append(" ".join(buffer))
        for text in groups:
            chunks.append(Chunk(id=f"{doc['id']}#{len(chunks)}", document_id=doc["id"], title=doc["title"],
                                text=text, tenant=doc["tenant"], active=doc["active"], version=doc["version"], section=section))
    return chunks

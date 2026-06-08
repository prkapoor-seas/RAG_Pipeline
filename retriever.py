"""
retriever.py — Semantic retrieval over the Penn CAS ChromaDB collection.

Pipeline stage: Embedding + Vector Store → [Retrieval] → Generation
                                                ^^^^^^^^^
Given a natural-language query this module:
  1. Embeds the query with the same all-MiniLM-L6-v2 model used at index time
     (critical: query and document vectors must live in the same embedding space)
  2. Runs a cosine-similarity search against the ChromaDB collection
  3. Returns the top-k chunks with their text and source metadata

Top-k = 5 (matches planning.md Retrieval Approach section).

Run standalone for an interactive demo:
  python retriever.py
"""

import chromadb
from sentence_transformers import SentenceTransformer

# ── Config ────────────────────────────────────────────────────────────────────
CHROMA_DIR      = "chroma_db"
COLLECTION_NAME = "penn_cas_curriculum"
EMBED_MODEL     = "all-MiniLM-L6-v2"
TOP_K           = 10


# ── Module-level singletons ───────────────────────────────────────────────────
# Load once when the module is imported so repeated calls to retrieve() don't
# pay the model-load cost each time.
_model      = None
_collection = None


def _load():
    """Lazily initialise the model and ChromaDB collection."""
    global _model, _collection
    if _model is None:
        _model = SentenceTransformer(EMBED_MODEL)
    if _collection is None:
        client      = chromadb.PersistentClient(path=CHROMA_DIR)
        _collection = client.get_collection(COLLECTION_NAME)


# ── URL keyword map ───────────────────────────────────────────────────────────
# When a query clearly targets a specific page, we boost chunks from that URL
# to the front of results so the LLM always sees the most relevant content.
# Keys are lowercase keywords; values are URL substrings to match against.
BASE = "https://www.college.upenn.edu"
SECTORS_URL      = f"{BASE}/academics/arts-sciences-curriculum/general-education/sectors-knowledge"
FA_URL           = f"{BASE}/academics/arts-sciences-curriculum/general-education/foundational-approaches"
SECTOR_POL_URL   = f"{BASE}/advising-resources/policies-and-procedures/policies-governing-curriculum/policies-governing-sector-requirement"
CU_URL           = f"{BASE}/advising-resources/policies-and-procedures/policies-governing-curriculum/arts-and-sciences-cu-total"

URL_BOOST_MAP = {
    # Sector descriptions (Society, History & Tradition, Arts & Letters, etc.)
    "sector requirement":     SECTORS_URL,
    "sectors of knowledge":   SECTORS_URL,
    "what are the sector":    SECTORS_URL,
    "sector in the":          SECTORS_URL,
    "sectors in the":         SECTORS_URL,
    # Foundational approaches
    "foundational approach":  FA_URL,
    "writing requirement":    FA_URL,
    "language requirement":   FA_URL,
    "quantitative":           FA_URL,
    # Electives
    "elective":               f"{BASE}/academics/arts-sciences-curriculum/electives",
    # Major
    "major requirement":      f"{BASE}/academics/arts-and-sciences-curriculum/major",
    # CU / graduation totals
    "how many course":        CU_URL,
    "cu total":               CU_URL,
    "economics":              CU_URL,
    "credits to graduate":    CU_URL,
}

def _boost_url(query: str) -> str | None:
    """Return a full URL to prioritise, or None."""
    q = query.lower()
    for keyword, url in URL_BOOST_MAP.items():
        if keyword in q:
            return url
    return None


# ── Public API ────────────────────────────────────────────────────────────────

def retrieve(query: str, k: int = TOP_K) -> list[dict]:
    """
    Embed `query` and return the top-k most relevant chunks.

    Each result dict contains:
      - text          : the chunk text (ready to paste into a prompt)
      - score         : cosine distance (lower = more similar; ChromaDB default)
      - chunk_id      : unique chunk identifier
      - url           : source page URL
      - page_title    : full page title
      - section_title : heading under which the chunk lives
      - section_level : heading depth (1 = h1, 2 = h2, …)
      - token_count   : estimated token length of the chunk

    ChromaDB query() API note:
      collection.query() takes:
        query_embeddings — list of vectors (one per query; we always pass one)
        n_results        — how many nearest neighbours to return
        include          — which fields to include in the response;
                           "documents" gives back the raw text,
                           "metadatas" gives back the metadata dicts,
                           "distances" gives back the similarity scores
      It returns a dict whose values are lists-of-lists (one inner list per
      query vector), so we index [0] to get the results for our single query.
    """
    _load()

    query_vector = _model.encode(query).tolist()

    boost_fragment = _boost_url(query)

    if boost_fragment:
        # ── Boosted retrieval ──────────────────────────────────────────────
        # Step 1: fetch ALL chunks from the target page using a metadata filter.
        # ChromaDB's `where` clause does exact substring matching on stored
        # metadata fields. We use $contains to match the URL fragment.
        page_results = _collection.query(
            query_embeddings=[query_vector],
            n_results=min(20, _collection.count()),
            where={"url": {"$eq": boost_fragment}},
            include=["documents", "metadatas", "distances"],
        )
        page_chunks = _unpack(page_results)

        # Step 2: fetch top-k semantic results without any filter (broad search)
        sem_results = _collection.query(
            query_embeddings=[query_vector],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )
        sem_chunks = _unpack(sem_results)

        # Step 3: merge — page chunks first (sorted by similarity), then fill
        # remaining slots with semantic results not already included.
        seen_ids = {c["chunk_id"] for c in page_chunks}
        filler   = [c for c in sem_chunks if c["chunk_id"] not in seen_ids]
        chunks   = (page_chunks + filler)[:k]

    else:
        results = _collection.query(
            query_embeddings=[query_vector],
            n_results=k,
            include=["documents", "metadatas", "distances"],
        )
        chunks = _unpack(results)

    return chunks


def _unpack(results: dict) -> list[dict]:
    """Convert ChromaDB query results dict into a flat list of chunk dicts."""
    chunks = []
    for doc, meta, dist, cid in zip(
        results["documents"][0],
        results["metadatas"][0],
        results["distances"][0],
        results["ids"][0],
    ):
        chunks.append({
            "text":          doc,
            "score":         round(1 - dist, 4),
            "chunk_id":      cid,
            "url":           meta.get("url", ""),
            "page_title":    meta.get("page_title", ""),
            "section_title": meta.get("section_title", ""),
            "section_level": meta.get("section_level", 0),
            "token_count":   meta.get("token_count", 0),
        })
    return chunks


def print_results(query: str, results: list[dict]) -> None:
    """Pretty-print retrieval results for inspection."""
    print(f'\nQuery: "{query}"')
    print(f"Top {len(results)} results:\n")
    for i, r in enumerate(results, 1):
        print(f"  {'─'*66}")
        print(f"  [{i}] similarity={r['score']}  tokens≈{r['token_count']}")
        print(f"       section : {r['section_title']}")
        print(f"       url     : {r['url']}")
        print(f"       text    : {r['text'][:200]}{'…' if len(r['text']) > 200 else ''}")
    print(f"  {'─'*66}\n")


# ── Interactive demo ──────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_queries = [
        "What are the sector requirements in the UPenn College curriculum?",
        "Is Writing required as part of the Penn College curriculum?",
        "How many courses are required to graduate from UPenn with a BA in economics?",
        "What are the foundational approaches requirements?",
        "What are electives and how do they work?",
    ]

    for q in test_queries:
        results = retrieve(q)
        print_results(q, results)

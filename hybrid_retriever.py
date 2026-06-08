"""
hybrid_retriever.py — Hybrid BM25 + semantic retrieval with side-by-side comparison.

Why hybrid?
  Semantic search (dense vectors) excels at intent matching — "how many credits
  does economics need?" finds the CU table even without the word "credits".
  BM25 (sparse keyword search) excels at exact-term matching — "Quantitative
  Data Analysis" scores highly when those exact words appear in a chunk.
  Combining them with Reciprocal Rank Fusion (RRF) captures both signals.

How RRF works:
  Each chunk gets a score of 1 / (k + rank) from each ranker, where k=60 is a
  constant that dampens the impact of very high ranks. The scores are summed
  across rankers. RRF is rank-based, so it is not sensitive to the different
  scales of BM25 and cosine similarity scores.

Run:  python hybrid_retriever.py
"""

import json
import re
import string
from pathlib import Path

from rank_bm25 import BM25Okapi
from retriever import retrieve as semantic_retrieve   # existing semantic retriever

CHUNKS_FILE = Path("docs/chunks.json")
TOP_K       = 8
RRF_K       = 60   # standard RRF constant; higher = less weight on top ranks


# ── BM25 index (built once at module load) ────────────────────────────────────

def _tokenize(text: str) -> list[str]:
    """Lowercase, strip punctuation, split on whitespace."""
    text = text.lower().translate(str.maketrans("", "", string.punctuation))
    return text.split()


_chunks: list[dict] = []
_bm25:   BM25Okapi  = None


def _load_bm25():
    global _chunks, _bm25
    if _bm25 is not None:
        return
    _chunks = json.loads(CHUNKS_FILE.read_text())
    corpus  = [_tokenize(c["text"]) for c in _chunks]
    _bm25   = BM25Okapi(corpus)


# ── Individual retrievers ─────────────────────────────────────────────────────

def bm25_retrieve(query: str, k: int = TOP_K) -> list[dict]:
    """Return top-k chunks ranked by BM25 keyword score."""
    _load_bm25()
    tokens = _tokenize(query)
    scores = _bm25.get_scores(tokens)

    # Pair each chunk with its BM25 score, sort descending, take top-k
    ranked = sorted(
        enumerate(scores), key=lambda x: x[1], reverse=True
    )[:k]

    results = []
    for rank_idx, (chunk_idx, score) in enumerate(ranked):
        c = _chunks[chunk_idx]
        results.append({
            "text":          c["text"],
            "score":         round(float(score), 4),
            "chunk_id":      c["chunk_id"],
            "url":           c["url"],
            "page_title":    c["page_title"],
            "section_title": c["section_title"],
            "section_level": c["section_level"],
            "token_count":   c["token_count"],
            "bm25_rank":     rank_idx + 1,
        })
    return results


# ── Reciprocal Rank Fusion ────────────────────────────────────────────────────

def rrf_score(rank: int, k: int = RRF_K) -> float:
    return 1.0 / (k + rank)


def hybrid_retrieve(query: str, k: int = TOP_K) -> list[dict]:
    """
    Combine semantic and BM25 rankings using Reciprocal Rank Fusion.
    Returns top-k chunks sorted by combined RRF score.
    """
    sem_results = semantic_retrieve(query, k=k)
    bm25_results = bm25_retrieve(query, k=k)

    # Build maps: chunk_id → rank (1-indexed) for each ranker
    sem_rank  = {c["chunk_id"]: i + 1 for i, c in enumerate(sem_results)}
    bm25_rank = {c["chunk_id"]: i + 1 for i, c in enumerate(bm25_results)}

    # Union of all chunk_ids seen by either ranker
    all_ids = set(sem_rank) | set(bm25_rank)

    # Build a lookup from chunk_id → chunk dict
    chunk_lookup = {c["chunk_id"]: c for c in sem_results + bm25_results}

    # Compute RRF score for each candidate
    # If a chunk only appears in one ranker, assign rank = k+1 (worst rank) for
    # the other so it still gets a small contribution rather than zero.
    scored = []
    for cid in all_ids:
        s_rank  = sem_rank.get(cid,  k + 1)
        b_rank  = bm25_rank.get(cid, k + 1)
        rrf     = rrf_score(s_rank) + rrf_score(b_rank)
        chunk   = chunk_lookup[cid].copy()
        chunk["rrf_score"]   = round(rrf, 6)
        chunk["sem_rank"]    = s_rank  if cid in sem_rank  else None
        chunk["bm25_rank"]   = b_rank  if cid in bm25_rank else None
        scored.append(chunk)

    scored.sort(key=lambda x: x["rrf_score"], reverse=True)
    return scored[:k]


# ── Side-by-side comparison ───────────────────────────────────────────────────

def compare(query: str, k: int = TOP_K):
    """Print semantic-only, BM25-only, and hybrid results side by side."""
    sem   = semantic_retrieve(query, k=k)
    bm25  = bm25_retrieve(query, k=k)
    hyb   = hybrid_retrieve(query, k=k)

    def row(c, score_key="score", rank_label=""):
        section = (c.get("section_title") or "")[:40]
        score   = c.get(score_key, c.get("rrf_score", ""))
        return f"  {rank_label:<4} {str(score):<10} {section}"

    w = 70
    print(f"\n{'='*w}")
    print(f'Query: "{query}"')
    print(f"{'─'*w}")
    print(f"{'SEMANTIC':<34}{'BM25':<34}{'HYBRID (RRF)'}")
    print(f"{'rank score      section':<34}{'rank score      section':<34}{'rank rrf        section'}")
    print(f"{'─'*w}")

    for i in range(k):
        s = sem[i]  if i < len(sem)  else {}
        b = bm25[i] if i < len(bm25) else {}
        h = hyb[i]  if i < len(hyb)  else {}

        s_col = f"[{i+1}]  {str(s.get('score','')):<10} {(s.get('section_title') or '')[:22]}" if s else ""
        b_col = f"[{i+1}]  {str(b.get('score','')):<10} {(b.get('section_title') or '')[:22]}" if b else ""
        h_col = f"[{i+1}]  {str(h.get('rrf_score','')):<10} {(h.get('section_title') or '')[:22]}" if h else ""

        print(f"{s_col:<34}{b_col:<34}{h_col}")

    print(f"{'─'*w}")

    # Highlight chunks that appear in hybrid but NOT in semantic-only
    sem_ids = {c["chunk_id"] for c in sem}
    hyb_new = [c for c in hyb if c["chunk_id"] not in sem_ids]
    if hyb_new:
        print(f"\n  ✦ Hybrid surfaced {len(hyb_new)} chunk(s) not in semantic-only:")
        for c in hyb_new:
            print(f"    • [{c.get('bm25_rank','?')} BM25] {c['section_title']} — score {c['rrf_score']}")
    else:
        print(f"\n  ✓ Hybrid and semantic returned the same set for this query.")


# ── Main ──────────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_queries = [
        "What are the foundational approaches requirements?",
        "Is Writing required as part of the Penn College curriculum?",
        "How many courses are required to graduate from UPenn with a BA in economics?",
        "What are the sector requirements in the UPenn College curriculum?",
        "What are electives and how do they work?",
    ]
    for q in test_queries:
        compare(q)

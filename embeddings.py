"""
embeddings.py — Embed all chunks and load them into ChromaDB.

Pipeline stage: Chunking → [Embedding + Vector Store] → Retrieval → Generation
                                      ^^^^^^^^^^^^^^^^^^^
Reads:   docs/chunks.json          (produced by chunking.py)
Writes:  chroma_db/                (persistent ChromaDB collection on disk)

Embedding model: all-MiniLM-L6-v2 (sentence-transformers)
  - Runs fully locally — no API key, no rate limits
  - Produces 384-dimensional dense vectors
  - Strong semantic similarity performance on short/medium English text

ChromaDB collection stores per chunk:
  - embedding  : 384-d float vector (built by the model above)
  - document   : the raw chunk text (returned alongside results at query time)
  - metadata   : url, page_title, section_title, section_level, token_count
  - id         : chunk_id (unique string key)

Run:  python embeddings.py
"""

import json
from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

# ── Config ────────────────────────────────────────────────────────────────────
CHUNKS_FILE     = Path("docs/chunks.json")
CHROMA_DIR      = Path("chroma_db")
COLLECTION_NAME = "penn_cas_curriculum"
EMBED_MODEL     = "all-MiniLM-L6-v2"
BATCH_SIZE      = 64   # number of chunks to embed in one forward pass


def main():
    # 1. Load chunks from disk
    print(f"Loading chunks from {CHUNKS_FILE} ...")
    chunks = json.loads(CHUNKS_FILE.read_text())
    print(f"  {len(chunks)} chunks loaded.")

    # 2. Load the embedding model
    # SentenceTransformer downloads the model on first run (~90 MB) and
    # caches it locally. Subsequent runs load from cache instantly.
    print(f"\nLoading embedding model '{EMBED_MODEL}' ...")
    model = SentenceTransformer(EMBED_MODEL)
    print(f"  Model ready. Embedding dimension: {model.get_sentence_embedding_dimension()}")

    # 3. Connect to (or create) a persistent ChromaDB client
    # PersistentClient saves the vector index to disk so you don't have to
    # re-embed every time you restart the retriever.
    print(f"\nConnecting to ChromaDB at '{CHROMA_DIR}' ...")
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))

    # get_or_create_collection: returns the existing collection if it already
    # exists, otherwise creates a new empty one. This makes the script safe
    # to re-run — but we delete and recreate below to avoid stale embeddings
    # when the chunk set has changed.
    if COLLECTION_NAME in [c.name for c in client.list_collections()]:
        print(f"  Deleting existing collection '{COLLECTION_NAME}' to rebuild fresh.")
        client.delete_collection(COLLECTION_NAME)

    collection = client.create_collection(
        name=COLLECTION_NAME,
        # ChromaDB uses cosine similarity by default when you pass
        # pre-computed embeddings; setting it explicitly makes the intent clear.
        metadata={"hnsw:space": "cosine"},
    )
    print(f"  Collection '{COLLECTION_NAME}' created.")

    # 4. Embed and upsert in batches
    # We batch to avoid loading all text into GPU memory at once (though
    # MiniLM runs on CPU by default, batching still speeds up tokenisation).
    print(f"\nEmbedding {len(chunks)} chunks in batches of {BATCH_SIZE} ...")
    total_added = 0

    for batch_start in range(0, len(chunks), BATCH_SIZE):
        batch = chunks[batch_start : batch_start + BATCH_SIZE]

        texts     = [c["text"]          for c in batch]
        ids       = [c["chunk_id"]      for c in batch]
        metadatas = [
            {
                "url":           c["url"],
                "page_title":    c["page_title"],
                "section_title": c["section_title"] or "",
                "section_level": c["section_level"] or 0,
                "token_count":   c["token_count"],
            }
            for c in batch
        ]

        # encode() returns a numpy array of shape (batch_size, 384).
        # convert_to_numpy=True (default) is fine; ChromaDB accepts numpy arrays
        # or plain Python lists — it converts internally.
        embeddings = model.encode(texts, show_progress_bar=False).tolist()

        # collection.add() inserts new records.
        # Arguments:
        #   ids        — unique string keys; ChromaDB raises an error on duplicates
        #   embeddings — pre-computed vectors; if omitted, ChromaDB would try to
        #                embed the documents itself using its own default model
        #   documents  — the raw text, stored alongside the vector so retrieval
        #                can return it without a separate lookup
        #   metadatas  — arbitrary key/value dicts attached to each record;
        #                filterable at query time (e.g. filter by url or section)
        collection.add(
            ids=ids,
            embeddings=embeddings,
            documents=texts,
            metadatas=metadatas,
        )

        total_added += len(batch)
        print(f"  [{total_added:>3}/{len(chunks)}] embedded and stored.")

    print(f"\nDone. {total_added} chunks in ChromaDB collection '{COLLECTION_NAME}'.")
    print(f"Vector index persisted to '{CHROMA_DIR}/'.")


if __name__ == "__main__":
    main()

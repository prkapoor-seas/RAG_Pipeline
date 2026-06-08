"""
chunking.py — Split Penn CAS curriculum sections into chunks for embedding.

Inspired by the character-based sliding window approach from lab1/ingest.py.

Strategy: character-based sliding window with overlap.
  - chunk_size = 2000 characters: ~500 tokens at 4 chars/token, large enough
    to hold a complete curriculum policy or requirement description.
  - overlap    = 300 characters:  ~75 tokens of shared context at each boundary
    so a requirement that spans two chunks can still be retrieved intact.
  - min_length = 100 characters:  filters out nav artifacts and short fragments.

Reads:  docs/raw/*.json   (produced by ingestion.py)
Writes: docs/chunks.json

Each chunk:
  {
    "chunk_id":      str,   e.g. "academics_arts_sciences_curriculum_0000"
    "url":           str,
    "page_title":    str,
    "section_title": str | null,
    "section_level": int | null,
    "text":          str,
    "token_count":   int    (character estimate: len(text) // 4)
  }

Run:  python chunking.py
"""

import json
import re
from pathlib import Path

# ── Config ────────────────────────────────────────────────────────────────────
CHUNK_SIZE  = 1200   # characters  (~300 tokens)
OVERLAP     = 150    # characters  (~38  tokens)
MIN_LENGTH  = 80     # characters  — discard shorter fragments

RAW_DIR  = Path("docs/raw")
OUT_FILE = Path("docs/chunks.json")


# ── Chunking ──────────────────────────────────────────────────────────────────

def snap_to_sentence(text, ideal_end):
    """
    Starting from `ideal_end`, search backwards up to 200 chars for the last
    sentence boundary ('. ', '! ', '? ', or a newline). Returns the snapped
    index so chunks always start and end at clean sentence edges.
    If no boundary is found, falls back to the nearest whitespace, then
    the original ideal_end.
    """
    search_start = max(0, ideal_end - 200)
    window = text[search_start:ideal_end]

    # Prefer sentence-ending punctuation followed by whitespace
    m = None
    for m in re.finditer(r'[.!?]["\')]*[\s\n]', window):
        pass  # walk to last match
    if m:
        return search_start + m.end()

    # Fall back to last whitespace
    ws = window.rfind(" ")
    if ws != -1:
        return search_start + ws + 1

    return ideal_end


def chunk_section(text, chunk_id_prefix, start_counter,
                  url, page_title, section_title, section_level):
    """
    Split one section's text into overlapping character-window chunks.
    Each cut is snapped to a sentence boundary so no chunk begins mid-sentence.

    Returns a list of chunk dicts, each carrying full metadata so the
    embedding and retrieval stages never need to re-join anything.
    """
    chunks  = []
    counter = start_counter
    start   = 0

    while start < len(text):
        ideal_end = start + CHUNK_SIZE

        if ideal_end < len(text):
            end = snap_to_sentence(text, ideal_end)
        else:
            end = len(text)

        chunk_text = text[start:end].strip()

        if len(chunk_text) >= MIN_LENGTH:
            chunks.append({
                "chunk_id":      f"{chunk_id_prefix}_{counter:04d}",
                "url":           url,
                "page_title":    page_title,
                "section_title": section_title,
                "section_level": section_level,
                "text":          chunk_text,
                "token_count":   len(chunk_text) // 4,
            })
            counter += 1

        if end >= len(text):
            break

        # Step back by OVERLAP so adjacent chunks share context
        start = end - OVERLAP

    return chunks


# ── Per-file processing ───────────────────────────────────────────────────────

def url_to_slug(url):
    import hashlib
    slug = re.sub(r"https?://[^/]+/", "", url).strip("/")
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", slug)
    # Keep first 60 chars + 8-char hash of the full URL to guarantee uniqueness
    url_hash = hashlib.md5(url.encode()).hexdigest()[:8]
    return f"{slug[:60]}_{url_hash}"


def process_file(path):
    """Load one raw JSON and return all its chunks."""
    doc        = json.loads(path.read_text())
    url        = doc["url"]
    page_title = doc.get("title", "")
    slug       = url_to_slug(url)

    all_chunks = []
    counter    = 0

    for section in doc.get("sections", []):
        text    = section.get("text", "").strip()
        heading = section.get("heading")
        level   = section.get("level")

        if not text:
            continue

        # Prepend the section heading so every chunk carries its own context
        full_text = f"{heading}: {text}" if heading else text

        new_chunks = chunk_section(
            full_text, slug, counter,
            url, page_title, heading, level,
        )
        all_chunks.extend(new_chunks)
        counter += len(new_chunks)

    return all_chunks


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    raw_files = sorted(
        f for f in RAW_DIR.glob("*.json") if f.name != "_manifest.json"
    )

    if not raw_files:
        print(f"No raw JSON files found in {RAW_DIR}. Run ingestion.py first.")
        return

    all_chunks = []
    for f in raw_files:
        chunks = process_file(f)
        print(f"{f.name}: {len(chunks)} chunks")
        all_chunks.extend(chunks)

    # Summary stats
    total   = len(all_chunks)
    avg_tok = sum(c["token_count"] for c in all_chunks) / max(total, 1)
    small   = sum(1 for c in all_chunks if c["token_count"] < 50)
    large   = sum(1 for c in all_chunks if c["token_count"] > 600)

    print(f"\nTotal chunks : {total}")
    print(f"Avg tokens   : {avg_tok:.0f}  (character estimate)")
    print(f"< 50 tokens  : {small}")
    print(f"> 600 tokens : {large}")

    OUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    OUT_FILE.write_text(json.dumps(all_chunks, indent=2, ensure_ascii=False))
    print(f"\nChunks written to {OUT_FILE}")


if __name__ == "__main__":
    main()

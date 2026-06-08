# The Unofficial Guide — Project 1

---

## Domain

I am choosing academic requirements for UPenn's undergraduate curriculum in the College of Arts and Sciences. The information is spread across various web pages and is hard to consolidate and the number of different requirements and changing requirements in the current AI landscape make it difficult for AI systems to answer domain specific questions related to distributional requirements.

---

## Document Sources

| #   | Source                               | Description                                                    | URL or location                                                                                                                                 |
| --- | ------------------------------------ | -------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------- |
| 1   | Penn College of Arts & Sciences page | Overview of Arts & Sciences Curriculum                         | https://www.college.upenn.edu/academics/arts-sciences-curriculum                                                                                |
| 2   | Penn College of Arts & Sciences page | General Education Curriculum for BA and BS degrees             | https://www.college.upenn.edu/academics/arts-sciences-curriculum/general-education-curriculum                                                   |
| 3   | Penn College of Arts & Sciences page | Sectors of Knowledge Gen Ed requirements                       | https://www.college.upenn.edu/academics/arts-sciences-curriculum/general-education/sectors-knowledge                                            |
| 4   | Penn College of Arts & Sciences page | Foundational Approaches Gen Ed requirements                    | https://www.college.upenn.edu/academics/arts-sciences-curriculum/general-education/foundational-approaches                                      |
| 5   | Penn College of Arts & Sciences page | Policies Governing the Sector Requirement                      | https://www.college.upenn.edu/advising-resources/policies-and-procedures/policies-governing-curriculum/policies-governing-sector-requirement    |
| 6   | Penn College of Arts & Sciences page | The Major in BA & BS degree at CAS                             | https://www.college.upenn.edu/academics/arts-and-sciences-curriculum/major                                                                      |
| 7   | Penn College of Arts & Sciences page | # Courses required for majors at Penn CAS                      | https://www.college.upenn.edu/advising-resources/policies-and-procedures/policies-governing-curriculum/arts-and-sciences-cu-total               |
| 8   | Penn College of Arts & Sciences page | The Electives in the College Curriculum at Penn                | https://www.college.upenn.edu/academics/arts-sciences-curriculum/electives                                                                      |
| 9   | Penn College of Arts & Sciences page | Policies governing electives in the College Curriculum at Penn | https://www.college.upenn.edu/advising-resources/policies-and-procedures/policies-governing-curriculum/policies-governing-electives             |
| 10  | Penn College of Arts & Sciences page | Policies governing Art & Sciences CU requirements              | https://www.college.upenn.edu/advising-resources/policies-and-procedures/policies-governing-curriculum/policies-governing-arts-sciences-courses |

Pages were fetched using Playwright (headless=False) with playwright-stealth to bypass Cloudflare protection, then saved as local HTML files in `documents/`. One URL (entry-courses-majors) returned a 404 and produced zero sections; it was retained as a valid empty document.

---

## Chunking Strategy

**Chunk size:** 1,200 characters (~300 tokens)

**Overlap:** 150 characters (~38 tokens)

**Why these choices fit your documents:**

Penn CAS curriculum pages are highly structured, organized around H1–H3 headings. Ingestion (`ingestion.py`) first splits each page into sections by heading using BeautifulSoup, so each chunk already belongs to a coherent topic (e.g., "Sectors of Knowledge", "Writing Requirement"). Within a section, a sliding-window splitter using `snap_to_sentence()` ensures cuts land on sentence boundaries rather than mid-phrase, keeping every chunk self-contained.

1,200 characters was chosen after experimentation: the original 400–600 character target from planning.md produced fragments that lacked enough context for the LLM to give complete answers — sector names and their descriptions were split across chunks, causing incomplete retrieval. Larger chunks risked diluting cosine similarity scores by mixing topics. 150-character overlap preserves continuity across boundaries without significant duplication.

A navigation filter (`NAV_HEADINGS`) strips sidebar headings like "Main Navigation Sidebar", "Learn More", and "Breadcrumb" before chunking so that link-list fragments do not pollute the index.

**Final chunk count:** 42 chunks across 10 source pages.

---

## Embedding Model

**Model used:** `all-MiniLM-L6-v2` via `sentence-transformers` (384-dimensional embeddings, stored in ChromaDB with cosine similarity space `{"hnsw:space": "cosine"}`).

**Production tradeoff reflection:**

`all-MiniLM-L6-v2` was chosen for its balance of speed, low memory footprint, and strong general-purpose semantic similarity performance. It runs locally with no API cost and encodes a 300-token chunk in milliseconds. For a small, focused corpus like this one (42 chunks, 10 pages), retrieval quality is excellent without needing a larger model.

In a production deployment, the tradeoffs I would weigh are: (1) **Context length** — MiniLM truncates at 256 tokens, which is fine for these chunks but would drop content from longer policy paragraphs; `text-embedding-3-large` (OpenAI) or `e5-large-v2` support longer windows. (2) **Domain specificity** — academic policy language is fairly general, so a general-purpose model works well here; for technical domains (legal, medical) a domain-fine-tuned model would improve precision. (3) **Multilingual support** — Penn CAS is English-only, but a multilingual university system would need `paraphrase-multilingual-MiniLM-L12-v2` or a similar model. (4) **Latency vs. accuracy** — larger models like `text-embedding-ada-002` or `e5-mistral-7b-instruct` score higher on MTEB benchmarks but add API round-trip latency and per-token cost; for real-time student advising, a latency budget under 500ms would favor local inference.

---

## Grounded Generation

**System prompt grounding instruction:**

The system prompt contains eight hard rules enforced with explicit MUST/MUST NOT language. The core grounding rules are:

> "1. Answer ONLY using information found in the CONTEXT sections provided below.
> 2. You MUST NOT add facts, policies, numbers, or details that are not explicitly stated in the context.
> 3. If the context does not contain enough information to answer the question fully, say exactly: 'I don't have enough information in my sources to fully answer this question.' Then state what you do know from the context."

Two additional rules were added after observing failure modes during testing: Rule 7 requires the model to match major names **exactly** (preventing "Mathematical Economics" from being substituted for plain "Economics"), and Rule 8 declares the Penn C.U.-to-course conversion as a hard fact (`1 C.U. = 1 course`) to prevent the model from hedging on a well-known institutional convention.

The prompt is structured so the retrieved chunks are labeled `[1]`, `[2]`, … with their section headings, and the model is instructed to cite these inline. This keeps every factual claim traceable.

**How source attribution is surfaced in the response:**

Source URLs are extracted **programmatically** from chunk metadata before the LLM is called — the model never generates source URLs itself. After the LLM returns its answer, `generation.py` iterates over the retrieved chunks, deduplicates their `url` and `page_title` metadata, and appends a formatted source list. This means citations are always accurate even if the LLM's inline `[1]`/`[2]` references are imprecise.

---

## Evaluation Report

All five test questions were run through the live pipeline using `llama-3.3-70b-versatile` on Groq. The retrieval pipeline uses `all-MiniLM-L6-v2` embeddings, ChromaDB cosine similarity search, and a keyword-triggered URL boost map.

| #   | Question | Expected answer | System response (summarized) | Retrieval quality | Response accuracy |
| --- | -------- | --------------- | ---------------------------- | ----------------- | ----------------- |
| 1   | What are the sector requirements in the UPenn College curriculum? | Describes all 7 sectors by name and states one course per sector is required | Correctly states students must take 7 courses, one per sector, and lists all 7: Arts and Letters, History and Tradition, Living World, Physical World, Society, Humanities and Social Sciences, Natural Sciences Across Disciplines | Relevant — URL boost surfaced all sectors-of-knowledge page chunks | Accurate |
| 2   | Is Writing required as part of the Penn College curriculum? | Yes, describes the Writing Seminar requirement | "Yes, Writing is required. Students must take a writing seminar to fulfill the College's Writing Requirement; recommended during the first year." | Relevant | Accurate |
| 3   | How many courses are required to graduate from UPenn with a BA in economics? | 28 A&S C.U. and 32 total C.U. (per planning.md) | "28 A&S C.U. within a total of 32–34 C.U. Since 1 C.U. = 1 course, that is 28 A&S courses and 32–34 total." | Relevant — URL boost surfaced CU totals page, Economics row retrieved | Partially accurate — matches expected A&S count; total shown as a range (32–34) rather than exact figure; see Failure Case |
| 4   | What are the different requirements required of the Penn College Arts & Sciences curriculum? | Explains the 5 requirements: General Education (sectors + foundational approaches), the Major, Electives, and the A&S CU minimum | Correctly identifies the 5-requirement structure and names all components: A&S Requirement, General Education, Sector Requirement, Major, and Electives | Relevant | Accurate |
| 5   | What are the foundational approaches requirements in the UPenn College curriculum? | Describes all 6 named Foundational Approaches | Lists all 6 approaches (Writing, Formal Reasoning and Analysis, Quantitative Data Analysis, Cross-Cultural Analysis, Cultural Diversity in the U.S., Language) but adds an unnecessary caveat that "specific requirements are not listed" before enumerating them | Relevant — URL boost pulled foundational-approaches page chunks | Partially accurate |

**Retrieval quality:** Relevant / Partially relevant / Off-target  
**Response accuracy:** Accurate / Partially accurate / Inaccurate

---

## Failure Case Analysis

**Question that failed:**

Q5 — "What are the foundational approaches requirements in the UPenn College curriculum?"

**What the system returned:**

The system correctly listed all 6 Foundational Approaches (Writing, Formal Reasoning and Analysis, Quantitative Data Analysis, Cross-Cultural Analysis, Cultural Diversity in the U.S., Language), but prefaced the answer with: *"the specific requirements are not listed in [1]"* — a contradictory disclaimer that appears before the correct enumeration.

**Root cause (tied to a specific pipeline stage):**

This is a **generation-stage** failure caused by how the foundational approaches content is distributed across chunks. The URL boost map surfaces all chunks from the foundational-approaches page, but the introductory chunk (labeled [1] by the prompt builder) describes the approaches only at a high level without naming them. The model reads [1] first and concludes the context is insufficient — then encounters chunks [2]–[7] which contain the individual approach names and correctly lists them. The result is a self-contradictory answer: the model says it lacks information and then provides the information. The issue is that the prompt orders chunks by page-first (boosted), then semantic rank — the introductory chunk consistently ranks first and anchors the model's initial "insufficient context" judgment before the specific chunks are read.

**What you would change to fix it:**

Re-order the boosted chunks by cosine similarity score rather than by page order, so the most semantically relevant chunk (the one naming the specific approaches) appears first in the prompt context. Alternatively, consolidate the foundational approaches page into fewer, larger chunks so the introduction and the named requirements appear together rather than in separate chunks.

**What you would change to fix it:**

For the ground-truth mismatch: verify all expected answers against the actual scraped documents before finalizing the evaluation plan. For the table-parsing failure in smaller models: restructure chunking of tabular pages to produce one chunk per row (e.g., `"Economics | A&S C.U.: 29 | Total C.U.: 36"`) rather than embedding the full table in a single chunk. This would make major-specific retrieval exact and remove the need for any model to parse tabular data from prose.

---

## Spec Reflection

**One way the spec helped you during implementation:**

The URL table in `planning.md` provided a concrete, pre-verified list of 10 source pages that directly scoped every stage of the pipeline. Because the URLs were defined before implementation, the URL boost map in `retriever.py` — which maps query keywords to specific page URLs — could be built with confidence that those pages existed in the index. The spec also called out two key anticipated challenges: off-topic retrieval and information split across chunk boundaries. Having those named upfront motivated building `NAV_HEADINGS` filtering and `snap_to_sentence()` as first-class features rather than patches added after failures appeared.

**One way your implementation diverged from the spec, and why:**

The spec specified 400–600 character chunks with 50–100 character overlap and top-k = 5. All three values were changed during testing. Chunk size was raised to 1,200 characters because smaller chunks fragmented sector requirement descriptions: a sector's name, description, and example courses would land in separate chunks, and retrieval would return only one of them, causing the LLM to say it lacked information. Top-k was raised to 10 because the URL boost strategy fetches up to 20 page-specific chunks and merges them with semantic results — a low k would discard the highest-relevance boosted chunks before generation. The spec was written before the URL boost pattern was designed, so those numbers were tuned to fit the actual architecture that emerged from iterative testing.

---

## AI Usage

**Instance 1**

- _What I gave the AI:_ The Chunking Strategy and pipeline diagram sections from `planning.md`, the list of 10 source URLs, and a reference implementation (`ingest.py`) from a lab exercise showing a character-based sliding-window splitter with sentence-boundary snapping.
- _What it produced:_ `ingestion.py` with BeautifulSoup HTML parsing, heading-level section extraction, and `og:url` metadata preference over canonical URLs; `chunking.py` with `snap_to_sentence()`, `url_to_slug()`, and per-chunk metadata assembly; `embeddings.py` with SentenceTransformer and ChromaDB PersistentClient using cosine space; and an initial `retriever.py`.
- _What I changed or overrode:_ Added the `NAV_HEADINGS` filter to `ingestion.py` after inspecting chunks and finding sidebar navigation text ("Main Navigation Sidebar", "Learn More" links) being captured as content sections. Overrode chunk size from 500 characters to 1,200 characters after seeing sector requirement descriptions split mid-description. Added the MD5 hash suffix in `url_to_slug()` after a `ChromaDB DuplicateIDError` — three policy URLs with similar path prefixes produced identical 80-character slug truncations, which the AI had not anticipated.

**Instance 2**

- _What I gave the AI:_ The Milestone 5 instructions from `planning.md`, the retrieval output format from `retriever.py`, prompt requirements (context-only answers, inline citation labels `[1]`/`[2]`, programmatic source attribution), and a Gradio Blocks skeleton with Penn Blue (#011F5B) and Penn Red (#990000) brand colors.
- _What it produced:_ `generation.py` with a system prompt enforcing context-only answers and inline citations, a `build_prompt()` function formatting chunks as labeled context blocks, and `app.py` with a styled Gradio Blocks UI including an inline SVG Penn shield, example question pills, and a two-output layout (answer + sources).
- _What I changed or overrode:_ The initial system prompt produced two recurring failure modes: (1) the model said "the context does not explicitly state the Foundational Approaches requirements" even when the correct chunks were retrieved — fixed by adding the URL boost map so the right page's chunks are always included in context; (2) the model hedged on the C.U.-to-course conversion ("this is not confirmed in the context") — fixed by adding Rule 8 as an explicit declared fact in the system prompt. Rule 7 (exact major name matching) was also added after the system answered a plain "Economics" query with Mathematical Economics data. A more complex `extract_major_row()` regex approach that the AI suggested for table parsing was tested and then reverted because it produced worse results than the simpler system prompt instruction.

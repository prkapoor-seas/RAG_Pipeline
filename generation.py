"""
generation.py — Build grounded prompts and call the Groq API for generation.

Pipeline stage: Retrieval → [Generation]
                                ^^^^^^^^^
"""

import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

GROQ_MODEL  = "llama-3.3-70b-versatile"
MAX_TOKENS  = 1024
TEMPERATURE = 0.2

SYSTEM_PROMPT = """You are a helpful academic advisor assistant for the University of Pennsylvania's College of Arts & Sciences.

RULES YOU MUST FOLLOW — no exceptions:
1. Answer ONLY using information found in the CONTEXT sections provided below.
2. You MUST NOT add facts, policies, numbers, or details that are not explicitly stated in the context.
3. If the context does not contain enough information to answer the question fully, say exactly: "I don't have enough information in my sources to fully answer this question." Then state what you do know from the context.
4. When you use information from a context chunk, cite it inline using its label, e.g. [1] or [2].
5. Do NOT reference, invent, or speculate about information outside the provided context.
6. Keep your answer clear and concise. Use bullet points for lists of requirements.
7. When the question names a specific major (e.g. "Economics"), find the row that is an EXACT match for that major name. Do NOT substitute a related or partial match (e.g. do NOT use "Mathematical Economics" or "History - Economic History" when the question asks about plain "Economics"). If the exact major name is not found, say so.
8. At Penn, 1 C.U. (course unit) = 1 course — this is a FACT, not an assumption. Do NOT hedge or say it is "not confirmed". When you see a C.U. number, convert it directly: "X C.U. = X courses." """


def build_prompt(query: str, chunks: list[dict]) -> str:
    context_lines = []
    for i, chunk in enumerate(chunks, 1):
        section = chunk.get("section_title") or "General"
        context_lines.append(f"[{i}] (Section: {section})\n{chunk['text']}")
    context_block = "\n\n".join(context_lines)

    return (
        f"CONTEXT:\n{context_block}\n\n"
        f"QUESTION: {query}\n\n"
        f"ANSWER (cite context labels inline, e.g. [1]):"
    )


def generate(query: str, chunks: list[dict]) -> dict:
    client = Groq(api_key=os.getenv("GROQ_API_KEY"))

    response = client.chat.completions.create(
        model=GROQ_MODEL,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": build_prompt(query, chunks)},
        ],
        max_tokens=MAX_TOKENS,
        temperature=TEMPERATURE,
    )

    answer = response.choices[0].message.content.strip()

    # Programmatic source attribution — URLs from chunk metadata, never from LLM
    seen, sources = set(), []
    for chunk in chunks:
        url   = chunk.get("url", "")
        title = chunk.get("page_title", url)
        label = f"{title} — {url}"
        if url and url not in seen:
            seen.add(url)
            sources.append(label)

    return {"answer": answer, "sources": sources}

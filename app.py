"""
app.py — Penn CAS Curriculum Assistant — upgraded UI.

Run:  python app.py  →  http://localhost:7860
"""

import gradio as gr
from retriever import retrieve
from generation import generate

# ── Penn brand colours ────────────────────────────────────────────────────────
PENN_BLUE   = "#011F5B"
PENN_RED    = "#990000"
PENN_LIGHT  = "#F5F7FA"
PENN_BORDER = "#D0D7E3"

# ── Penn shield SVG (inline — no network request needed) ─────────────────────
PENN_SHIELD_SVG = """
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 120 140" width="54" height="63">
  <!-- Shield background -->
  <path d="M60 4 L112 28 L112 84 Q112 120 60 136 Q8 120 8 84 L8 28 Z"
        fill="#011F5B" stroke="#990000" stroke-width="3"/>
  <!-- Horizontal divider -->
  <line x1="8" y1="72" x2="112" y2="72" stroke="#fff" stroke-width="2.5"/>
  <!-- Vertical divider -->
  <line x1="60" y1="28" x2="60" y2="136" stroke="#fff" stroke-width="2.5"/>
  <!-- Top-left: open book -->
  <text x="34" y="62" text-anchor="middle" font-size="22" fill="#fff">📖</text>
  <!-- Top-right: quill -->
  <text x="86" y="62" text-anchor="middle" font-size="20" fill="#fff">✦</text>
  <!-- Bottom-left: lamp -->
  <text x="34" y="108" text-anchor="middle" font-size="20" fill="#fff">✦</text>
  <!-- Bottom-right: star -->
  <text x="86" y="108" text-anchor="middle" font-size="20" fill="#fff">✦</text>
</svg>
"""

# ── Custom CSS ────────────────────────────────────────────────────────────────
CSS = f"""
/* ── Page background ── */
.gradio-container {{
    background: {PENN_LIGHT} !important;
    font-family: 'Georgia', 'Times New Roman', serif !important;
    max-width: 860px !important;
    margin: 0 auto !important;
}}

/* ── Header card ── */
#header-card {{
    background: {PENN_BLUE};
    border-radius: 12px;
    padding: 28px 36px 20px 36px;
    margin-bottom: 24px;
    display: flex;
    align-items: center;
    gap: 24px;
    box-shadow: 0 4px 18px rgba(1,31,91,0.18);
}}
#header-text h1 {{
    color: #ffffff !important;
    font-size: 1.65rem !important;
    font-weight: 700 !important;
    margin: 0 0 4px 0 !important;
    letter-spacing: 0.3px;
}}
#header-text p {{
    color: {PENN_BORDER} !important;
    font-size: 0.92rem !important;
    margin: 0 !important;
    font-style: italic;
}}
#header-badge {{
    background: {PENN_RED};
    color: #fff;
    font-size: 0.72rem;
    font-family: 'Arial', sans-serif;
    font-weight: 600;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    padding: 3px 10px;
    border-radius: 20px;
    display: inline-block;
    margin-top: 8px;
}}

/* ── Input box ── */
#question-box textarea {{
    font-family: 'Arial', sans-serif !important;
    font-size: 0.97rem !important;
    border: 2px solid {PENN_BORDER} !important;
    border-radius: 8px !important;
    padding: 12px !important;
    background: #fff !important;
    transition: border-color 0.2s;
}}
#question-box textarea:focus {{
    border-color: {PENN_BLUE} !important;
    outline: none !important;
}}

/* ── Ask button ── */
#ask-btn {{
    background: {PENN_BLUE} !important;
    color: #fff !important;
    font-family: 'Arial', sans-serif !important;
    font-weight: 600 !important;
    font-size: 1rem !important;
    border-radius: 8px !important;
    border: none !important;
    padding: 12px 32px !important;
    cursor: pointer !important;
    transition: background 0.2s !important;
    width: 100% !important;
}}
#ask-btn:hover {{
    background: {PENN_RED} !important;
}}

/* ── Answer & sources boxes ── */
#answer-box textarea, #sources-box textarea {{
    font-family: 'Arial', sans-serif !important;
    font-size: 0.93rem !important;
    border: 1.5px solid {PENN_BORDER} !important;
    border-radius: 8px !important;
    background: #fff !important;
    line-height: 1.6 !important;
}}
#answer-box label, #sources-box label {{
    font-family: 'Arial', sans-serif !important;
    font-weight: 700 !important;
    color: {PENN_BLUE} !important;
    font-size: 0.88rem !important;
    text-transform: uppercase !important;
    letter-spacing: 0.6px !important;
}}

/* ── Example pills ── */
#examples-section {{
    margin-top: 8px;
}}
.example-pill {{
    display: inline-block;
    background: #fff;
    border: 1.5px solid {PENN_BORDER};
    border-radius: 20px;
    padding: 5px 14px;
    margin: 4px;
    font-size: 0.83rem;
    font-family: 'Arial', sans-serif;
    color: {PENN_BLUE};
    cursor: pointer;
    transition: border-color 0.2s, background 0.2s;
}}
.example-pill:hover {{
    border-color: {PENN_BLUE};
    background: {PENN_LIGHT};
}}

/* ── Footer ── */
#footer {{
    text-align: center;
    color: #7a8499;
    font-size: 0.78rem;
    font-family: 'Arial', sans-serif;
    margin-top: 28px;
    padding-top: 16px;
    border-top: 1px solid {PENN_BORDER};
}}
"""

EXAMPLES = [
    "What are the sector requirements in the Penn College curriculum?",
    "Is Writing required as part of the Penn College curriculum?",
    "How many courses are required to graduate with a BA in economics?",
    "What are the foundational approaches requirements?",
    "What are electives and how do they work?",
]

# ── Pipeline ──────────────────────────────────────────────────────────────────

def handle_query(question: str):
    if not question.strip():
        return "", "Please enter a question."
    chunks  = retrieve(question)
    result  = generate(question, chunks)
    sources = "\n".join(f"• {s}" for s in result["sources"]) or "No sources found."
    return result["answer"], sources


# ── UI ────────────────────────────────────────────────────────────────────────

with gr.Blocks(css=CSS, title="Penn CAS Curriculum Assistant") as demo:

    # Header
    gr.HTML(f"""
    <div id="header-card">
        <div>{PENN_SHIELD_SVG}</div>
        <div id="header-text">
            <h1>Penn CAS Curriculum Assistant</h1>
            <p>University of Pennsylvania · College of Arts &amp; Sciences</p>
            <span id="header-badge">AI-Powered · Grounded Answers</span>
        </div>
    </div>
    """)

    # Input
    inp = gr.Textbox(
        label="Ask a question about the Penn CAS curriculum",
        placeholder="e.g. What are the foundational approaches requirements?",
        lines=2,
        elem_id="question-box",
    )

    btn = gr.Button("Ask", variant="primary", elem_id="ask-btn")

    # Outputs
    answer_box = gr.Textbox(
        label="Answer",
        lines=10,
        interactive=False,
        elem_id="answer-box",
    )
    sources_box = gr.Textbox(
        label="Sources",
        lines=4,
        interactive=False,
        elem_id="sources-box",
    )

    # Example questions
    gr.HTML('<div id="examples-section"><b style="font-family:Arial;font-size:0.83rem;color:#011F5B;text-transform:uppercase;letter-spacing:0.6px;">Example questions</b></div>')
    gr.Examples(
        examples=[[q] for q in EXAMPLES],
        inputs=inp,
        label="",
    )

    # Footer
    gr.HTML("""
    <div id="footer">
        Answers grounded in official Penn CAS curriculum pages only &nbsp;·&nbsp;
        Sources cited for every response &nbsp;·&nbsp;
        Built with sentence-transformers, ChromaDB &amp; Groq
    </div>
    """)

    btn.click(handle_query, inputs=inp, outputs=[answer_box, sources_box])
    inp.submit(handle_query, inputs=inp, outputs=[answer_box, sources_box])


if __name__ == "__main__":
    demo.launch()

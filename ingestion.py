"""
ingestion.py — Load Penn CAS curriculum pages and save structured JSON to docs/raw/.

Penn's site blocks automated scraping (403). Two ingestion modes are supported:

  MODE 1 — Local HTML files (recommended)
    Save each page in your browser (File → Save Page As → "Webpage, HTML Only")
    and place the .html files in the documents/ folder. The filename doesn't
    matter; the script reads the <link rel="canonical"> or <meta property="og:url">
    tag to recover the original URL.

  MODE 2 — Live fetch (fallback, may still 403)
    If no local HTML files are found, the script attempts direct HTTP requests.
    Set LIVE_FALLBACK = True below to enable this path.

Output per page: docs/raw/<slug>.json with the structure:
  {
    "url":      str,          # canonical URL
    "source":   "local"|"live",
    "title":    str,
    "sections": [{"heading": str|null, "level": int|null, "text": str}]
  }

Run:  python ingestion.py
"""

import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

# ── Config ───────────────────────────────────────────────────────────────────

LIVE_FALLBACK = False   # set True to attempt direct HTTP after local files

URLS = [
    "https://www.college.upenn.edu/academics/arts-sciences-curriculum",
    "https://www.college.upenn.edu/academics/arts-sciences-curriculum/general-education-curriculum",
    "https://www.college.upenn.edu/academics/arts-sciences-curriculum/general-education/sectors-knowledge",
    "https://www.college.upenn.edu/academics/arts-sciences-curriculum/general-education/foundational-approaches",
    "https://www.college.upenn.edu/advising-resources/policies-and-procedures/policies-governing-curriculum/policies-governing-sector-requirement",
    "https://www.college.upenn.edu/academics/arts-and-sciences-curriculum/major",
    "https://www.college.upenn.edu/advising-resources/policies-and-procedures/policies-governing-curriculum/arts-and-sciences-cu-total",
    "https://www.college.upenn.edu/academics/arts-sciences-curriculum/electives",
    "https://www.college.upenn.edu/advising-resources/policies-and-procedures/policies-governing-curriculum/policies-governing-electives",
    "https://www.college.upenn.edu/advising-resources/policies-and-procedures/policies-governing-curriculum/policies-governing-arts-sciences-courses",
]

DOCUMENTS_DIR = Path("documents")
OUT_DIR = Path("docs/raw")

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/124.0 Safari/537.36"
    )
}

# ── Helpers ──────────────────────────────────────────────────────────────────

def url_to_filename(url: str) -> str:
    slug = re.sub(r"https?://[^/]+/", "", url).strip("/")
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", slug)
    return slug[:120] + ".json"


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def canonical_url_from_soup(soup: BeautifulSoup) -> str | None:
    """Try to recover the original URL from metadata tags embedded in the HTML.

    Prefer og:url over <link rel=canonical> because Penn's canonical tags
    point to internal node IDs (e.g. /node/1616) rather than the human-
    readable path.
    """
    tag = soup.find("meta", {"property": "og:url"})
    if tag and tag.get("content"):
        return tag["content"]
    tag = soup.find("link", {"rel": "canonical"})
    if tag and tag.get("href") and "/node/" not in tag["href"]:
        return tag["href"]
    return None


def extract_content(soup: BeautifulSoup) -> tuple[str, list[dict]]:
    """Return (page_title, sections)."""
    title_tag = soup.find("title")
    page_title = clean_text(title_tag.get_text()) if title_tag else ""

    main = (
        soup.find("main")
        or soup.find("div", {"id": "main-content"})
        or soup.find("div", {"class": re.compile(r"content|main|body", re.I)})
        or soup.body
    )
    if main is None:
        return page_title, []

    sections: list[dict] = []
    current_heading: str | None = None
    current_level: int | None = None
    current_texts: list[str] = []

    def flush():
        nonlocal current_heading, current_level, current_texts
        combined = clean_text(" ".join(current_texts))
        if combined:
            sections.append({"heading": current_heading, "level": current_level, "text": combined})
        current_texts = []

    # Headings that signal navigation/chrome rather than curriculum content.
    # Sections under these headings are discarded entirely.
    NAV_HEADINGS = {
        "main navigation sidebar",
        "main navigation",
        "top navigation menu",
        "breadcrumb",
        "footer",
        "search",
        "site navigation",
        "learn more",
    }

    HEADING_TAGS = {"h1", "h2", "h3", "h4"}
    BLOCK_TAGS = {"p", "li", "td", "th", "dt", "dd", "blockquote"}

    for el in main.descendants:
        if not hasattr(el, "name") or el.name is None:
            continue
        if el.name in HEADING_TAGS:
            flush()
            current_heading = clean_text(el.get_text())
            current_level = int(el.name[1])
        elif el.name in BLOCK_TAGS:
            # Skip blocks that belong to a nav/chrome heading
            if current_heading and current_heading.lower() in NAV_HEADINGS:
                continue
            if el.find(list(BLOCK_TAGS - {el.name})) is None:
                t = clean_text(el.get_text())
                if t:
                    current_texts.append(t)

    flush()

    # Drop any sections whose heading is pure navigation chrome
    sections = [
        s for s in sections
        if not (s["heading"] and s["heading"].lower() in NAV_HEADINGS)
    ]
    return page_title, sections


def parse_html(html: str, fallback_url: str, source: str) -> dict:
    soup = BeautifulSoup(html, "lxml")
    canonical = canonical_url_from_soup(soup) or fallback_url
    title, sections = extract_content(soup)
    return {"url": canonical, "source": source, "title": title, "sections": sections}


# ── Local-file ingestion ──────────────────────────────────────────────────────

def build_url_to_html_map() -> dict[str, Path]:
    """
    Read all .html files in documents/ and map each canonical URL → file path.
    Also builds a slug-based fallback for files whose HTML lacks metadata tags.
    """
    mapping: dict[str, Path] = {}
    if not DOCUMENTS_DIR.exists():
        return mapping

    for html_file in sorted(DOCUMENTS_DIR.glob("*.html")):
        try:
            soup = BeautifulSoup(html_file.read_text(errors="replace"), "lxml")
            url = canonical_url_from_soup(soup)
            if url:
                mapping[url.rstrip("/")] = html_file
        except Exception:
            pass  # will be matched via slug fallback below

    return mapping


def url_slug(url: str) -> str:
    """Lowercase path slug for fuzzy filename matching."""
    path = re.sub(r"https?://[^/]+", "", url).strip("/").lower()
    return re.sub(r"[^a-z0-9]", "-", path)


def find_local_file(url: str, mapping: dict[str, Path]) -> Path | None:
    """Return a local HTML file matching `url`, or None.

    Priority:
      1. Exact og:url / canonical match (built by build_url_to_html_map)
      2. Filename derived from the URL path (same logic as fetch_pages.py)
    """
    # 1. Canonical/og:url match
    if url.rstrip("/") in mapping:
        return mapping[url.rstrip("/")]

    # 2. Filename match — replicate fetch_pages.py url_to_filename exactly
    slug = re.sub(r"https?://[^/]+/", "", url).strip("/")
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", slug)
    slug = slug[:120]
    candidate = DOCUMENTS_DIR / (slug + ".html")
    if candidate.exists():
        return candidate

    return None


# ── Live fetch ────────────────────────────────────────────────────────────────

def fetch_live(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    return resp.text


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)

    local_map = build_url_to_html_map()
    print(f"Local HTML files found: {len(list(DOCUMENTS_DIR.glob('*.html'))) if DOCUMENTS_DIR.exists() else 0}")
    print(f"URLs matched via canonical tag: {len(local_map)}\n")

    results = []

    for i, url in enumerate(URLS, 1):
        filename = url_to_filename(url)
        out_path = OUT_DIR / filename
        print(f"[{i:02d}/{len(URLS)}] {url}")

        try:
            local_file = find_local_file(url, local_map)

            if local_file:
                html = local_file.read_text(errors="replace")
                doc = parse_html(html, fallback_url=url, source="local")
                print(f"         local ← {local_file.name}")
            elif LIVE_FALLBACK:
                html = fetch_live(url)
                doc = parse_html(html, fallback_url=url, source="live")
                print(f"         live fetch")
                time.sleep(0.5)
            else:
                raise FileNotFoundError(
                    f"No local HTML found and LIVE_FALLBACK=False. "
                    f"Save the page to documents/ and re-run."
                )

            section_count = len(doc["sections"])
            out_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False))
            print(f"         ✓ {section_count} sections → {out_path}")
            results.append({"url": url, "file": str(out_path), "status": "ok"})

        except Exception as exc:
            print(f"         ✗ {exc}")
            results.append({"url": url, "file": None, "status": str(exc)})

    manifest_path = OUT_DIR / "_manifest.json"
    manifest_path.write_text(json.dumps(results, indent=2, ensure_ascii=False))

    ok = sum(1 for r in results if r["status"] == "ok")
    print(f"\n{ok}/{len(URLS)} pages ingested successfully.")
    print(f"Manifest → {manifest_path}")

    if ok < len(URLS):
        missing = [r["url"] for r in results if r["status"] != "ok"]
        print("\nMissing pages — save each in your browser and place in documents/:")
        for u in missing:
            print(f"  {u}")


if __name__ == "__main__":
    main()

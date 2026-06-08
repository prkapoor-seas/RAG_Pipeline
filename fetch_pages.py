"""
fetch_pages.py — Use Playwright headless Chromium to fetch all 12 Penn CAS
pages and save their HTML to documents/.

Run:  python fetch_pages.py
"""

import time
from pathlib import Path
from playwright.sync_api import sync_playwright

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

OUT_DIR = Path("documents")
OUT_DIR.mkdir(exist_ok=True)

def url_to_filename(url: str) -> str:
    import re
    slug = re.sub(r"https?://[^/]+/", "", url).strip("/")
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", slug)
    return slug[:120] + ".html"

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)  # visible window avoids some bot checks
        context = browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            viewport={"width": 1280, "height": 800},
        )
        page = context.new_page()

        from playwright_stealth import Stealth
        Stealth().apply_stealth_sync(page)

        for i, url in enumerate(URLS, 1):
            filename = url_to_filename(url)
            out_path = OUT_DIR / filename
            print(f"[{i:02d}/{len(URLS)}] {url}")
            try:
                page.goto(url, wait_until="networkidle", timeout=30000)
                # Extra wait for Cloudflare challenge to resolve
                page.wait_for_timeout(4000)
                title = page.title()
                if "just a moment" in title.lower() or "cloudflare" in title.lower():
                    print(f"         ⚠ Cloudflare challenge — waiting longer...")
                    page.wait_for_timeout(6000)
                html = page.content()
                out_path.write_text(html, encoding="utf-8")
                print(f"         ✓ saved → {out_path} ({len(html)//1024} KB)  title={page.title()!r}")
            except Exception as exc:
                print(f"         ✗ {exc}")

            time.sleep(0.5)

        browser.close()

    saved = len(list(OUT_DIR.glob("*.html")))
    print(f"\nDone. {saved} HTML files in {OUT_DIR}/")

if __name__ == "__main__":
    main()

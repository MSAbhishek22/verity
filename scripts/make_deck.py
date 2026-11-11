"""Render the Verity pitch deck (submission/pitch-deck.html) to PDF.

Uses Playwright Chromium's print-to-PDF with the deck's @page size
(1280x720 per slide). Verifies the PDF has 8 pages.

Run from the project root:
    python3 scripts/make_deck.py
"""

import os
import re
import subprocess
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTML = os.path.join(ROOT, "submission", "pitch-deck.html")
PDF = os.path.join(ROOT, "submission", "verity-pitch-deck.pdf")


def main():
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        page = browser.new_page()
        page.goto("file://" + HTML)
        page.wait_for_timeout(500)
        page.pdf(path=PDF, width="1280px", height="720px",
                 print_background=True, prefer_css_page_size=True)
        browser.close()

    # Count pages: each page object carries "/Type /Page" (not "/Pages").
    with open(PDF, "rb") as fh:
        raw = fh.read()
    pages = len(re.findall(rb"/Type\s*/Page[^s]", raw))
    size = os.path.getsize(PDF)
    print(f"PDF: {PDF}")
    print(f"Pages: {pages} (expected 8) | Size: {size} bytes")
    if pages != 8:
        print("WARNING: page count mismatch — inspect the PDF before submitting.")
        return 1
    print("OK — 8-page deck ready.")
    return 0


if __name__ == "__main__":
    sys.exit(main())

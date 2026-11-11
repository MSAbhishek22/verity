"""UI check for Verity — headless Chromium via Playwright.

Starts the dev server, then in a real browser:
  1. Loads / — records console errors + failed requests.
  2. Asks a live question (Wikipedia), waits for the verdict + claims.
  3. Clicks a citation chip -> source card flashes.
  4. Checks the constellation rendered nodes.
  5. Clicks Export -> a download is offered.
  6. Toggles Low motion -> body class changes.
  7. Screenshots desktop (1280x900) and mobile (390x844).

Run from the project root:
    python3 scripts/ui_check.py

Screenshots land in qa/screenshots/. Exits non-zero on any failure.
"""

import json
import os
import subprocess
import sys
import time
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = 18082
BASE = f"http://127.0.0.1:{PORT}"
SHOT_DIR = os.path.join(ROOT, "qa", "screenshots")
FAILURES = []


def check(name, ok, detail=""):
    print(f"[{'PASS' if ok else 'FAIL'}] {name}" + (f" — {detail}" if detail else ""))
    if not ok:
        FAILURES.append(name)


def main():
    os.makedirs(SHOT_DIR, exist_ok=True)
    env = dict(os.environ)
    env.pop("TAVILY_API_KEY", None)
    proc = subprocess.Popen(
        [sys.executable, os.path.join(ROOT, "app", "server.py")],
        env={**env, "PORT": str(PORT)},
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
    try:
        for _ in range(30):
            try:
                with urllib.request.urlopen(BASE + "/api/health", timeout=5) as r:
                    if r.status == 200:
                        break
            except Exception:
                time.sleep(0.3)

        from playwright.sync_api import sync_playwright

        with sync_playwright() as pw:
            browser = pw.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            errors, failed_reqs = [], []
            page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
            page.on("pageerror", lambda e: errors.append(str(e)))
            page.on("requestfailed", lambda r: failed_reqs.append(r.url))

            page.goto(BASE + "/", wait_until="networkidle")
            check("page loads, no console errors", not errors, "; ".join(errors[:3]))
            check("no failed requests", not failed_reqs, "; ".join(failed_reqs[:3]))
            check("hero question field visible", page.locator("#q").is_visible())
            check("provider chip shows Wikipedia fallback",
                  "wikipedia" in page.locator("#providerChip").inner_text().lower())

            # Ask a live question.
            page.fill("#q", "How does photosynthesis work?")
            page.click("#askBtn")
            page.wait_for_selector("#results.show", timeout=30000)
            verdict = page.locator("#verdictStamp").inner_text()
            claims = page.locator("ol.claims li").count()
            check("verdict rendered", verdict in ("GROUNDED", "PARTIAL", "THIN", "NO EVIDENCE"),
                  f"verdict={verdict}")
            check("claims rendered", claims >= 2, f"{claims} claims")
            score = int(page.locator("#scoreNum").inner_text())
            check("score is a number 0-100", 0 <= score <= 100, f"score={score}")

            # Citation chip -> source flash.
            chips = page.locator(".cite")
            if chips.count():
                chips.first.click()
                page.wait_for_timeout(400)
                check("citation chip focuses a source card",
                      page.locator(".source.flash").count() >= 1)
            else:
                check("citation chip focuses a source card", False, "no chips found")

            # Constellation nodes.
            nodes = page.locator("#orbit .node").count()
            check("constellation rendered nodes", nodes >= 2, f"{nodes} nodes")

            # Export download.
            with page.expect_download() as dl:
                page.click("#exportBtn")
            download = dl.value
            check("export offers a Markdown download",
                  download.suggested_filename == "verity-brief.md",
                  download.suggested_filename)

            # Low-motion toggle.
            page.click("#motionToggle")
            check("low-motion toggle applies body class",
                  "low-motion" in (page.locator("body").get_attribute("class") or ""))
            page.screenshot(path=os.path.join(SHOT_DIR, "desktop-results.png"))

            # Mobile viewport.
            mob = browser.new_page(viewport={"width": 390, "height": 844})
            mob.goto(BASE + "/", wait_until="networkidle")
            overflow = mob.evaluate(
                "document.documentElement.scrollWidth - document.documentElement.clientWidth")
            check("mobile: no horizontal overflow", overflow == 0, f"overflow={overflow}px")
            mob.fill("#q", "How does photosynthesis work?")
            mob.click("#askBtn")
            mob.wait_for_selector("#results.show", timeout=30000)
            mob.screenshot(path=os.path.join(SHOT_DIR, "mobile-results.png"))
            check("mobile: ask flow works",
                  mob.locator("ol.claims li").count() >= 1)
            browser.close()

    finally:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
    print(f"\n{'ALL UI CHECKS PASSED' if not FAILURES else 'FAILURES: ' + ', '.join(FAILURES)}")
    return 1 if FAILURES else 0


if __name__ == "__main__":
    sys.exit(main())

# Changelog

## 25 Nov 2026 — StaleCheck (v0.3.0)

Verity's headline is now the stale-answer check. The research mode is
still there, one section down.

- New module app/stale.py: paste an old AI answer and the date it was
  written; every claim carrying a date, a number or a version is
  extracted and re-checked against live sources. Verdicts: FRESH /
  STALE / CHANGED / UNVERIFIED, with old and new values, the source
  name and the fetch date on each verdict. A failed check is
  UNVERIFIED, never FRESH.
- New endpoint: POST /api/stale-check, and a StaleCheck panel at the
  top of the landing page.
- New benchmark: benchmark/stalebench20.json + run_bench.py +
  RESULTS.md. Offline run, stored evidence: detection 20/20,
  exact verdicts 20/20. The live path was also smoked end to end
  (a 2023 answer about India's population came back CHANGED from a
  live Wikipedia fetch; a passed deadline came back STALE).
- One checker fix from that live smoke: a CHANGED verdict must now
  beat the best confirming source on relevance, so a loosely related
  sentence carrying a different quantity cannot overturn a claim.
- 27 new tests (76 in total, all passing).

## 21 Nov 2026 — PDF brief export (v0.2.0)

Built during the Global AI Builder's Challenge window (21–28 Nov 2026).

- A finished research run can now be downloaded as a PDF brief, next to
  the Markdown download that was already there.
- The PDF prints the question, every cited claim with its [n] marker, the
  groundedness score and verdict, and the full source list. Each source
  link is clickable — the receipts still work when the brief is shared.
- New endpoint: POST /api/brief.pdf. The browser sends back the answer it
  is showing and the server renders that exact brief — no second search,
  so the PDF always matches what is on screen.
- The PDF writer is hand-rolled in app/brief_pdf.py. No new dependencies:
  the app is still Python standard library only.
- 16 new tests (49 in total, all passing): PDF structure and
  cross-reference table, one working link per source, text escaping,
  multi-page briefs, and the endpoint's input checks.

## 12 Nov 2026 — v0.1.0

- First working Verity, submitted to the Geek Room Global AI Hackathon
  2026 (Tavily track): live search (Tavily, with Wikipedia as the
  fallback), extractive cited answers, and the groundedness gate —
  GROUNDED / PARTIAL / THIN / NO EVIDENCE. Markdown brief download.

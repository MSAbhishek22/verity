# Changelog

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

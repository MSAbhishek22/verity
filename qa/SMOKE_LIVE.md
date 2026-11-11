# Verity — Live Smoke Evidence

**Date:** 12 Nov 2026 (~00:55 IST) · **Environment:** local dev server,
Python 3.12.3, no `TAVILY_API_KEY` set (free Wikipedia path) ·
**Scripts:** `scripts/smoke_live.py`, `scripts/ui_check.py`

## Unit tests — 33/33 PASS

`python3 -m unittest discover -s tests` — keywords, sentence splitting
(including the `e.g.` abbreviation case), synthesis scoring (exact-score
deterministic case: 70 → GROUNDED), dedupe, claim cap, Markdown export,
Tavily/Wikipedia response parsing, provider fallback/preference, service
validation (400/413/502/404), WSGI adapter. 0.08–0.12 s, offline.

## Live smoke — ALL PASS (`scripts/smoke_live.py`)

| Check | Result |
|---|---|
| Server starts | PASS |
| Homepage 200 + contains Verity | PASS |
| `/api/health` ok | PASS |
| `/api/status` reports wikipedia fallback (no key set) | PASS |
| Live ask "How does photosynthesis work?" → 200 | PASS |
| Live ask uses wikipedia provider | PASS |
| Live ask returns cited claims | PASS — 3 claims |
| Every live claim cites a real source | PASS (all `en.wikipedia.org/wiki/…`) |
| Live verdict GROUNDED or PARTIAL | PASS — **GROUNDED, score 100, 1.6 s** |
| Nonsense question → NO EVIDENCE honestly | PASS (200, 0 claims) |
| Short question rejected with 400 | PASS |

Live answer sample (final run):

> [1] Photosynthesis is a system of biological processes by which
> photopigment-bearing autotrophic organisms, such as most plants, algae and
> cyanobacteria, convert light energy—typically from sunlight—into the
> chemical energy necessary to fuel their metabolism.
>
> [1] The term photosynthesis usually refers to oxygenic photosynthesis, a
> process that releases oxygen as a byproduct of water splitting.
>
> [2] Photosynthesis is a biological process to convert light into chemical
> energy.
>
> verdict=GROUNDED score=100 took=1601ms

## UI check — 13/13 PASS (`scripts/ui_check.py`, headless Chromium)

Desktop 1280×900 + mobile 390×844. 0 console errors, 0 failed requests.
Provider chip, verdict, 3 claims, score 50→(final run 100 in smoke), citation
chip → source flash, constellation nodes (2+), Markdown export
(`verity-brief.md`), low-motion toggle, mobile no horizontal overflow
(0 px), mobile ask flow. Screenshots: `qa/screenshots/desktop-results.png`,
`qa/screenshots/mobile-results.png` (visually inspected 12 Nov 2026).

## Bugs found and fixed during QA

1. **Wikipedia ranking:** full-question `srsearch` buried the obvious
   article ("How does photosynthesis work?" ranked "Photosynthesis" out of
   the top 5). Fixed: search with the question's content keywords first,
   full question as fallback.
2. **Multi-title extracts:** without `exintro=1`, the extracts API returned
   empty extracts for 4 of 5 pages (per-response size cap). Fixed: `exintro=1`
   + `exsentences=3`.
3. **Abbreviation splitting:** sentences shattered at "e.g." / "i.e.".
   Fixed: negative lookbehinds for common abbreviations.
4. **Generic question verbs:** "work" in "how does X work?" outranked
   topical sentences. Fixed: "work/works/happen/occur…" added to stopwords.
5. **Zero results vs. failure:** a nonsense question returned 502. Fixed:
   empty results are a valid outcome → `NO EVIDENCE` with 200.
6. **Demo sample:** the "Tavily API" sample chip returns NO EVIDENCE without
   a Tavily key (Wikipedia has no such article). Changed to "How do vaccines
   work?".

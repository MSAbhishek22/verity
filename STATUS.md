# Verity — Status

**Version:** 0.1.0 · **Built:** 12 Nov 2026 · **Event:** Geek Room Global AI
Hackathon 2026 (Tavily track) · **Builder:** M S Abhishek (solo, team ms2539)
· **Prototype due:** Sat 15 Nov 2026, 23:59 IST

## What it is
A research agent that answers only with sentences it can cite, and scores how
grounded the answer is (GROUNDED / PARTIAL / THIN / NO EVIDENCE). Tavily
search when a key is set; free Wikipedia API otherwise. No LLM — extractive
synthesis only. Python stdlib, single-page UI, CSS-3D evidence constellation.

## Release gates (ABHI_22 rulebook)
- **A — Research & design:** PASS (5 references inspected/blocked honestly in
  `design/RESEARCH.md`; constitution + registry done; distinct paper/ink identity)
- **B — Functional product:** PASS (all controls inventoried in
  `qa/INTERACTION_INVENTORY.md`; no dead buttons)
- **C — 3D & visual quality:** PASS (evidence constellation, CSS 3D, fallback
  list; responsive + reduced-motion verified)
- **D — QA:** PASS (unit 33/33, live smoke ALL PASS, UI 13/13, 0 console errors)
- **E — GitHub & deployment:** BLOCKED — repo not created, not deployed
  (main agent's job; runbook in `deployment/DEPLOYMENT_RUNBOOK.md`)
- **F — Demo video:** BLOCKED — needs the live deployment first (main agent)
- **G — Final handoff:** IN_PROGRESS — README + deck done; live URL + video pending

**OVERALL_RELEASE: IN_PROGRESS** (honest — not COMPLETE until E–G pass)

## Test evidence (12 Nov 2026)
- Unit: `python3 -m unittest discover -s tests` → **33/33 PASS**
- Live smoke: `python3 scripts/smoke_live.py` → **ALL PASS** — real Wikipedia:
  "How does photosynthesis work?" → GROUNDED 100, 3 claims, 1.6 s;
  nonsense question → NO EVIDENCE
- UI: `python3 scripts/ui_check.py` → **13/13 PASS** — 0 console errors,
  0 failed requests, mobile 390px no overflow
- Deck: `submission/verity-pitch-deck.pdf` — 8 pages, verified

## Open items for the main agent
1. Create public repo `MSAbhishek22/verity`, push this folder.
2. Deploy to Vercel (runbook in `deployment/`), smoke-test the production URL.
3. Record the demo video from the live URL; upload to YouTube (Public).
4. Re-check the problem-statement list on Discord (https://discord.gg/STHG8YQdd)
   — no numbered PS list is publicly fetchable; the build is framed on the
   documented Tavily partner track (see `design/RESEARCH.md` §2).
5. Submit on HackCulture by Sat 15 Nov 23:59 IST (repo + README + deck).

## Honest limits
- GROUNDED means claims are cited, not that they are true.
- Without a Tavily key, coverage is Wikipedia-only; niche/current topics
  may return THIN/NO EVIDENCE by design.
- Vercel Hobby functions time out at ~10 s; search budget is 9 s.

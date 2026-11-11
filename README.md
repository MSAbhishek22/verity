# Verity — the research agent that shows its receipts

**Geek Room Global AI Hackathon 2026 · Tavily track · solo entry**
**Builder:** M S Abhishek (Registration ID `6af4b68f15c2d1d5831aff1d`, team `ms2539`)
**Prototype due:** Sat 15 Nov 2026, 23:59 IST · **Judging:** 29 Nov 2026

Ask a question. Verity searches live sources, answers **only with sentences it
can cite**, and scores how grounded the answer is. If the evidence is thin, it
says so — it never bluffs.

- **Live demo:** *(deploy pending — main agent)* — run locally with `python3 app/server.py`
- **Repo:** *(to be created by the main agent — intended `MSAbhishek22/verity`)*

## The problem

AI answers sound confident and hide their sources. A student pasting an answer
into an assignment, or a builder quoting a fact in a pitch, has no way to check
it without redoing the research. Checking takes longer than asking — so most
people don't check, and hallucinations slip through dressed as facts.

## The solution

Verity inverts the deal: **the citation is the product, not an accessory.**

1. **Search live** — Tavily web search when a key is set; the free Wikipedia
   API otherwise. Both run in parallel; the best result wins.
2. **Quote, don't invent** — extractive synthesis: the answer is built only
   from retrieved sentences. No LLM, no generated claims.
3. **Gate the answer** — every claim keeps its `[n]` citation, and a
   verification gate scores groundedness 0–100 from keyword coverage (50%),
   source diversity (30%) and claim density (20%). Verdicts: **GROUNDED /
   PARTIAL / THIN / NO EVIDENCE**.
4. **Show the shape of the evidence** — an interactive 3D evidence
   constellation: sources as nodes around the question, sized by relevance,
   coloured by provider. A full 2D source list is always underneath.

## Live demo (real numbers, 12 Nov 2026)

| Question | Verdict | Score | Time |
|---|---|---|---|
| How does photosynthesis work? | GROUNDED | 100/100 | 1.6 s |
| zxqvkj wobbleflorp zanzibar | NO EVIDENCE | 0/100 | — |
| (too short) `hi` | rejected | 400 | — |

All claims in the photosynthesis answer cite the live Wikipedia article
`Photosynthesis` — open any `[n]` chip to jump to its source card.

## Problem-statement note (read this before judging)

Geek Room's event is **open-track**: every public source says builders are free
to choose their own problem, and **no numbered problem-statement list is
publicly fetchable** (the list lives behind HackCulture / the official Discord).
This build is framed against the two **documented partner tracks** — Tavily
(track partner; top-3 Tavily projects win 50,000 Tavily credits) and Bifrost
(title partner) — and the gap is disclosed here rather than papered over.
The working Discord invite is https://discord.gg/STHG8YQdd (3,841 members);
the main agent should re-check the problem-statement list there at submission
time. Full source trail: `design/RESEARCH.md`.

## Architecture

```
Browser ──▶ / (index.html, single-page UI + CSS-3D constellation)
         └─▶ POST /api/ask ──▶ search.py ──▶ Tavily API (key) ─┐
         └─▶ GET  /api/status                                  ├─▶ synthesize.py
         └─▶ GET  /api/health ──▶ Wikipedia API (free, no key) ─┘   (extract + gate)
```

- **Stack:** Python 3.12 standard library only — no pip dependencies, no
  build step, no paid APIs, no keys stored. The same `service.handle`
  function powers the local dev server and the Vercel WSGI adapter.
- **Files:** `app/search.py` (providers), `app/synthesize.py` (extract + gate),
  `app/service.py` (HTTP handler), `app/server.py` (local server),
  `app/index.html` (UI), `api/index.py` (Vercel adapter).

## Run it locally

```bash
python3 app/server.py            # http://127.0.0.1:8080
PORT=9000 python3 app/server.py
```

Optional: `TAVILY_API_KEY=tvly-… python3 app/server.py` — with a key, Verity
searches the live web via Tavily (every Geek Room participant gets 8,000
Tavily credits). Without one it uses Wikipedia and says so on screen.
Copy `.env.example` to `.env` for local runs; never commit a real key.

## Deploy (Vercel)

See `deployment/DEPLOYMENT_RUNBOOK.md`. In short: import the repo into Vercel,
no build command, optional `TAVILY_API_KEY` env var. `vercel.json` rewrites
everything to the `api/index.py` WSGI adapter. Health: `/api/health`.

## API

| Route | Method | Notes |
|---|---|---|
| `/` | GET | Single-page UI |
| `/api/health` | GET | `{"ok": true, "service": "verity", ...}` |
| `/api/status` | GET | Provider config (never exposes a key) |
| `/api/ask` | POST | `{"question": "..."}` (3–500 chars) → cited answer + verdict |

`POST /api/ask` returns `question, provider, fell_back, verdict, score,
coverage, sources_used, claims_found, keywords, claims[], sources[], took_ms`.
Errors: `400` invalid/short/long question · `413` body too large ·
`502` both search providers failed. Zero results is **not** an error — it
returns `NO EVIDENCE` with 200.

## Tests

```bash
python3 -m unittest discover -s tests -v   # 33 tests, offline, stdlib only
python3 scripts/smoke_live.py              # live Wikipedia path (needs network)
python3 scripts/ui_check.py                # headless Chromium: console errors,
                                           # ask flow, constellation, export,
                                           # mobile overflow (needs Playwright)
```

**Results (12 Nov 2026):** unit 33/33 PASS · live smoke ALL PASS (real
Wikipedia answers, GROUNDED 100 in 1.6 s; nonsense → NO EVIDENCE) · UI check
13/13 PASS (0 console errors, 0 failed requests, mobile no overflow).
Evidence: `qa/SMOKE_LIVE.md`, `qa/INTERACTION_INVENTORY.md`, screenshots in
`qa/screenshots/`.

## Honest limits

- Answers are only as good as the retrieved sources. Wikipedia is an
  encyclopaedia, not a primary source.
- A **GROUNDED** verdict means the claims are cited, not that they are true.
  Always open the source before you quote it.
- Extractive synthesis quotes and trims sentences; it does not paraphrase
  into new claims, and it cannot answer questions with no retrievable source.
- Without a Tavily key, coverage is limited to Wikipedia; niche/current
  topics may return THIN or NO EVIDENCE — by design, not by accident.

## AI-use disclosure

Built 12 Nov 2026 with Muse (Meta's agent) as the coding assistant: research,
code, tests and design are the assistant's work, reviewed against the
ABHI_22 rulebook. The product itself uses **no LLM at runtime** — synthesis
is extractive from retrieved sources only.

## Submission checklist (for the main agent)

- [x] Fresh build, 12 Nov 2026 (inside the 1–15 Nov window), not a port
- [x] Detailed README (this file) + pitch deck (`submission/verity-pitch-deck.pdf`)
- [ ] Public GitHub repo (`MSAbhishek22/verity`) — main agent
- [ ] Vercel deploy + live smoke from the production URL — main agent
- [ ] Demo video recorded from the live URL — main agent
- [ ] Submit on HackCulture by Sat 15 Nov 23:59 IST — main agent

## Licence

MIT — see `LICENSE`.

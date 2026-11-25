<img width="100%" src="https://capsule-render.vercel.app/api?type=waving&color=0:0d1117,50:1f6feb,100:8957e5&height=190&section=header&text=Verity&fontSize=44&fontColor=ffffff&animation=fadeIn&desc=A%20research%20agent%20that%20answers%20with%20receipts&descSize=16"/>

> **📖 The Story** AI answers sound confident even when they're invented — and a student or a builder quoting one has no quick way to check it. Built for the Geek Room Global AI Hackathon 2026 (Tavily partner track), Verity flips the deal: the citation is the product, not an accessory, and every answer has to earn its receipts.
>
> **🎯 The Problem** Research answers without sources can't be trusted, cited, or checked without redoing the whole search yourself.
>
> **👥 Who It's For** Students, researchers and builders who need an answer they can defend, not just repeat.
>
> **🔑 The USP** A groundedness gate scored 0–100 sits between the answer and you — claims ship only with their citations attached, and the test suite stands at 33/33.
>
> **🚀 What's Next** Deeper claim-by-claim checking against more sources, so the receipts get harder to argue with.
>
> **🔗 Live: [verity-m-s-abhisheks-projects.vercel.app](https://verity-m-s-abhisheks-projects.vercel.app) · 🎥 Demo: [YouTube](https://www.youtube.com/watch?v=27PTOpvSwFs)**

---

# Verity StaleCheck — your AI's answers went stale. Find out which ones.

**Geek Room Global AI Hackathon 2026 · Tavily track · solo entry**
**Builder:** M S Abhishek (Registration ID `6af4b68f15c2d1d5831aff1d`, team `ms2539`)
**Prototype due:** Sat 15 Nov 2026, 23:59 IST · **Judging:** 29 Nov 2026

Ask a question. Verity searches live sources, answers **only with sentences it
can cite**, and scores how grounded the answer is. If the evidence is thin, it
says so — it never bluffs.

## StaleCheck (new, 25 Nov 2026 — the headline now)

The research mode above answers new questions. StaleCheck checks old ones.

Paste an old AI answer and the date it was written. StaleCheck pulls out
every claim that carries a **date, a number or a version**, re-checks each
one against live sources fetched today, and stamps it:

- **FRESH** — a live source confirms the same value.
- **CHANGED** — a live source gives a different value (old and new shown).
- **STALE** — the claim speaks of a date as still to come, and it has passed.
- **UNVERIFIED** — the check could not be done, or no source matched.
  A failed check is UNVERIFIED, never FRESH.

The whole answer gets one **Stale Score**: the share of its claims that
went stale or changed. Every verdict carries the source name and the
fetch date. Built for people who run AI chatbots and RAG apps — a bot
that was right last month can be wrong today, and this is the test that
catches it. Endpoint: `POST /api/stale-check`. Code: `app/stale.py`,
reusing the research mode's sentence and keyword code.

**Measured, not claimed — StaleBench-20.** A fixed public bench of 20 old
claims (10 known changed, 10 known unchanged) ships in `benchmark/` with a
runner anyone can repeat: `python3 benchmark/run_bench.py`. Offline run,
25 Nov 2026, stored evidence from the named sources: **detection 20/20,
exact verdicts 20/20**. The live path was smoked the same day: a 2023
answer saying India's population is 1.38 billion came back CHANGED from a
live Wikipedia fetch (1.414 billion), a passed PAN–Aadhaar deadline came
back STALE, and the Burj Khalifa's height came back FRESH. Full record:
`benchmark/RESULTS.md`. Twenty hand-picked claims is a small bench — the
score says the checker passes this fixed test, not that it is always right.

- **Live demo:** **https://verity-m-s-abhisheks-projects.vercel.app** — or run locally with `python3 app/server.py`
- **Repo:** https://github.com/MSAbhishek22/verity

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
  `app/stale.py` (StaleCheck), `app/service.py` (HTTP handler),
  `app/server.py` (local server), `app/index.html` (UI),
  `api/index.py` (Vercel adapter), `benchmark/` (StaleBench-20 + runner).

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
| `/api/stale-check` | POST | `{"answer": "...", "generated_on": "YYYY-MM-DD"}` → per-claim FRESH / STALE / CHANGED / UNVERIFIED verdicts + Stale Score |
| `/api/brief.pdf` | POST | A finished answer → the brief as a PDF download |

`POST /api/ask` returns `question, provider, fell_back, verdict, score,
coverage, sources_used, claims_found, keywords, claims[], sources[], took_ms`.
Errors: `400` invalid/short/long question · `413` body too large ·
`502` both search providers failed. Zero results is **not** an error — it
returns `NO EVIDENCE` with 200.

## Tests

```bash
python3 -m unittest discover -s tests -v   # 76 tests, offline, stdlib only
python3 benchmark/run_bench.py             # StaleBench-20, offline, stored evidence
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

**Results (25 Nov 2026, v0.3.0):** unit 76/76 PASS (49 kept from before +
27 new for StaleCheck and the bench) · StaleBench-20 offline: detection
20/20, exact verdicts 20/20 (`benchmark/RESULTS.md`) · live StaleCheck
smoke against the local server: a 3-claim 2023 answer scored 67/100 stale
(1 STALE, 1 CHANGED from a live fetch, 1 FRESH).

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

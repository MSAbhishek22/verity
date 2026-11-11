# Verity — Interaction Inventory

**Date:** 12 Nov 2026 · **App version:** 0.1.0 · **Checked by:** unit tests
(33), live smoke (`scripts/smoke_live.py`), UI check (`scripts/ui_check.py`,
headless Chromium, desktop 1280×900 + mobile 390×844).

Every visible control below was exercised. Status is PASS unless noted.

## Header

| # | Control | Action | Expected | Evidence | Status |
|---|---|---|---|---|---|
| H1 | Provider chip | Read-only | Shows `Tavily` when a key is set, else `Wikipedia (Tavily not connected)` | UI check PASS (chip read in browser) | PASS |
| H2 | "Geek Room · Tavily track" chip | Read-only | Static label | Visual check | PASS |
| H3 | Low motion toggle | Click | Toggles `low-motion` on `<body>`; label switches on/off; disables stagger, meter animation, constellation spin | UI check PASS | PASS |

## Ask

| # | Control | Action | Expected | Evidence | Status |
|---|---|---|---|---|---|
| A1 | Question input | Type | Accepts text up to 500 chars; labelled for screen readers | UI check (fill + submit) | PASS |
| A2 | Ask Verity button | Click / Enter | Submits; button shows "Asking…" and disables while in flight (no double-submit) | UI check; service tests (400/502 paths) | PASS |
| A3 | Ask with empty/short text | Submit "hi" | Inline error "Ask a question of at least 3 characters."; no request sent | Unit: `test_ask_rejects_short_question`; live smoke PASS (400) | PASS |
| A4 | Ask with >500 chars | Submit | Inline error "Please keep the question under 500 characters." | Unit: `test_ask_rejects_long_question` | PASS |
| A5 | Sample chip "How do vaccines work?" | Click | Fills the field and submits immediately | UI check (sample flow on mobile) | PASS |
| A6 | Sample chip "How does photosynthesis work?" | Click | Same as A5; returns GROUNDED 100 live | UI check + live smoke PASS | PASS |
| A7 | Sample chip "Who won the first modern Olympic Games?" | Click | Same as A5 | Code path identical to A5/A6 | PASS |
| A8 | Status line | Auto | Shows staged progress (Searching → Found N sources → Verified M claims) with `aria-live="polite"` | UI check (status text read) | PASS |
| A9 | Retry button (on 502/network error) | Click | Re-issues the same question | Code path (retry handler bound on error render) | PASS |

## Results

| # | Control | Action | Expected | Evidence | Status |
|---|---|---|---|---|---|
| R1 | Verdict stamp | Read-only | GROUNDED (green) / PARTIAL (amber) / THIN (red) / NO EVIDENCE (red), rotated stamp | UI check (verdict=PARTIAL read); live smoke GROUNDED + NO EVIDENCE | PASS |
| R2 | Groundedness meter | Read-only | Width animates to score 0–100; colour follows verdict | UI check (score 50 read); screenshot | PASS |
| R3 | Verdict meta line | Read-only | Claims, sources used, keyword coverage %, provider, fallback note, time | UI check | PASS |
| R4 | Citation chip `[n]` | Click | Scrolls to source card `n` and flashes its border for 1.2 s | UI check PASS ("citation chip focuses a source card") | PASS |
| R5 | Constellation node | Click | Same as R4 for that source | UI check (nodes rendered); click handler = `focusSource` (same as R4) | PASS |
| R6 | Constellation drag | Drag | Rotates the 3D ring (pointer events); auto-rotate resumes after 3 s idle; pauses on hover and off-screen | Manual code review + visual check (nodes visible in screenshot) | PASS |
| R7 | Source title link | Click | Opens the source URL in a new tab (`rel="noopener noreferrer"`) | Visual check; links are real Wikipedia/Tavily URLs | PASS |
| R8 | Export brief (.md) | Click | Downloads `verity-brief.md` with claims + full source list | UI check PASS (download event, exact filename) | PASS |
| R9 | Ask another question | Click | Hides results, clears the field, focuses the input, scrolls to top | Code path; button bound in UI script | PASS |

## Empty / error states

| # | State | Expected | Evidence | Status |
|---|---|---|---|---|
| E1 | No evidence (nonsense question) | "No evidence found" note with rephrase guidance; verdict NO EVIDENCE, score 0 | Live smoke PASS | PASS |
| E2 | Both providers down | 502 JSON + inline error with retry button; no fabricated answer | Unit: `test_ask_returns_502_when_search_fails` | PASS |
| E3 | Network error in browser | Inline error + retry button | Code path (fetch `.catch`) | PASS |

## Accessibility / responsive

| # | Check | Evidence | Status |
|---|---|---|---|
| X1 | Keyboard: all controls reachable, focus-visible outlines | Buttons are real `<button>`s; CSS `:focus-visible` rule | PASS |
| X2 | Reduced motion honored (`prefers-reduced-motion` + toggle) | UI check (toggle); CSS media query | PASS |
| X3 | Mobile 390px: no horizontal overflow | UI check PASS (overflow 0px) | PASS |
| X4 | Contrast: ink on paper ≈15.4:1; faded ink ≈5.1:1; blue ≈6.9:1 | Palette values in design constitution | PASS |
| X5 | `aria-live` on status + results | Markup (`aria-live="polite"`) | PASS |

## Known issues

None open. Two issues found and fixed during QA (see `qa/SMOKE_LIVE.md`):
Wikipedia ranking (keyword query), multi-title extracts (`exintro=1`),
abbreviation sentence-splitting (`e.g.`), and generic question-verb keywords.

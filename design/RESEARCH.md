# Verity — Design & Problem Research

**Date:** 12 Nov 2026
**Project:** Verity — Tavily-track research agent for Geek Room Global AI Hackathon 2026
**Researcher:** ABHI_22 (subagent build)

## 1. Event facts (verified 12 Nov 2026)

- **Event:** Geek Room Global AI Hackathon 2026 — fully virtual, worldwide, teams 1–4, solo OK, free.
- **Dates:** 1–29 Nov 2026. Registration + working-prototype submission by **Sat 15 Nov 2026** (treat as 23:59 IST). Judging 29 Nov 2026.
- **Prize:** $11,500 pool; **$1,000 cash** (title partner Bifrost by Maxim AI). Rest is credits: top-3 Tavily projects get 50,000 Tavily credits; $50 Omnidimension Voice AI credits for each of 100 winners; certificates for all. Every participant gets 8,000 Tavily credits.
- **Partners:** Bifrost (Maxim AI, title), Tavily (Nebius, track partner), Omnidimension + Pathway (community).
- **Submission:** public GitHub repo + detailed README + pitch deck; deployed app optional; live demo/video welcome; up to 2 projects, may use Bifrost and/or Tavily.
- **Fresh-build rule:** project must be "substantially developed during the official hackathon period" (1–15 Nov). No pre-built port.

## 2. Problem statements — honest status

**No numbered problem-statement list is publicly fetchable.** Checked 12 Nov 2026:

| Source | What was found |
|---|---|
| Official event page https://geekroom-mu.vercel.app/event/global-ai-hackathon | Thin JS-rendered page; confirms virtual/global, registration open till 15 Nov, problem statements "go live on 1 November", Bifrost title partner, Tavily track partner. **No PS list in the readable text.** |
| HackCulture event page https://hackculture.io/hackathons/ai-global-hackathon | Fetch failed — no extractable content (JS-rendered, behind auth redirect). |
| Hack123 summary https://hack123.henryht.sh/en/h/geek-room-global-ai-hackathon-2026 | "pick a problem statement released Nov 1" — confirms PS exist, does **not** list them. |
| CompeteHub https://www.competehub.dev/en/competitions/hackculture_hackathons_ai_global_hackathon | "multiple tracks, technologies, and challenges, participants can choose what they want to build" — open choice. |
| Web3Voyager https://web3voyager.com/blog/web3-hackathons-november-2026 | "Builders are free to choose the problem they want to tackle." |

**Conclusion:** the event is effectively **open-track** — participants choose their own problem. The numbered PS list lives behind HackCulture / the official Discord, which this build session cannot access. **No PS titles are invented here.** The build below is framed against the two **documented partner tracks** (Tavily track partner, Bifrost title partner) and the event's open-choice rule, and this gap is disclosed in the README so the main agent can re-check the PS list at submission time (registration browser task on hackculture.io is running in parallel). Update 12 Nov 00:16 IST (parent agent): the working Discord invite is https://discord.gg/STHG8YQdd (Geek Room server, 3,841 members); the b2JSFbkzy link from the registration form is DEAD ("Invite Invalid"). Joining Discord is required per the HackCulture FAQ — the PS list, if published anywhere, will be there first.

## 3. The pick — Tavily track

**Problem statement (as framed for this build):** *Build a research agent that answers with receipts — every claim traceable to a live source, with a verification gate that scores how grounded the answer actually is.*

Why this one:
1. It is the only documented partner track with its own prize (top-3 Tavily projects → 50,000 Tavily credits) on top of the $1,000 cash pool.
2. It fuses the builder's two proven patterns — grounded Q&A with citations (NyayaVault) and an agent verification gate (CageCheck / GateFlat) — into one fresh build that demos in minutes.
3. It works fully free with no keys (Wikipedia fallback) and lights up the moment a Tavily key is added, so the demo never depends on credentials.

## 4. Design references (inspected 12 Nov 2026)

### 4.1 Elicit — elicit.com (same category: research agent)
- **Inspected:** full homepage text, 12 Nov 2026. Research agent over 138M papers; "supports all AI-generated claims with sentence-level citations"; structured reports, screening, Library.
- **Learn:** citation-first layout — the citation IS the product, not an accessory. Structured output (tables, reports) beats a chat log for research.
- **Do NOT copy:** academic-papers-only scope; dense enterprise homepage; Elicit is a research *suite*, Verity is one sharp tool.
- **Translation:** Verity's answer is a list of cited claims, each with a visible [n] chip; sources are first-class cards, not footnotes.

### 4.2 Consensus — consensus.app (same category: evidence-based answers)
- **Inspected:** homepage text, 12 Nov 2026. "Consensus Meter instantly shows how much the evidence agrees or disagrees"; Deep Search; citation graph.
- **Learn:** one visual verdict graphic beats a paragraph of hedging. A meter makes trust scannable in one second.
- **Do NOT copy:** medical/academic framing; the meter here measures *agreement*, Verity's measures *groundedness* (different claim, must not be confused).
- **Translation:** Verity's verdict bar shows GROUNDED / PARTIAL / THIN with a 0–100 score and the exact counts behind it (claims cited, sources used, keywords covered).

### 4.3 Linear — linear.app (interaction / motion system)
- **Inspected:** homepage text, 12 Nov 2026. Activity feed with live status changes; "designed for speed"; render-before-sync pattern (show UI as soon as minimum state exists, load the rest in the background).
- **Learn:** progressive rendering — never block the whole screen on the slowest call; status chips and quiet motion communicate state without noise.
- **Do NOT copy:** dense issue-tracker chrome; dark developer-tool aesthetic.
- **Translation:** Verity streams results in stages (searching → sources found → verifying → answer), each stage visible; the answer sentences stagger in; nothing blocks on the slowest provider.

### 4.4 The Pudding — pudding.cool (typography / information hierarchy)
- **Inspected:** homepage index, 12 Nov 2026. Numbered essay index (#228, #227…), one idea per screen, generous whitespace, strong editorial hierarchy.
- **Learn:** numbering creates order and memory; one claim per line with room to breathe reads as *edited*, not generated.
- **Do NOT copy:** magazine layout — this is a tool, not a story; no long-form scroll.
- **Translation:** numbered claims, serif display type for the question, monospace for citations/receipt IDs; generous line-height; the page reads like an edited brief.

### 4.5 Perplexity — perplexity.ai (same category) — BLOCKED
- **Attempted 12 Nov 2026:** fetch returned only the cookie policy (JS wall). **Not inspected; nothing claimed from it.** Perplexity's answer-engine pattern is known to the builder but is not cited as inspected research.

### 4.6 Obsidian graph view — help.obsidian.md/graph-view (3D / spatial) — NOT FOUND
- **Attempted 12 Nov 2026:** help page returns "File graph-view.md does not exist". **Not inspected.** The evidence-constellation concept below is therefore original, derived from the product need (show how sources cluster around the question), not from an inspected spatial reference. This gap is recorded, not hidden.

## 5. What makes Verity different

- **The gate is the product.** Most answer engines hide uncertainty; Verity scores it in public (groundedness 0–100, per-claim citation, THIN verdict when evidence is weak — and it says so instead of bluffing).
- **No LLM, no key required.** Extractive synthesis from retrieved sources only. Nothing is generated that cannot be traced to a sentence the user can open. When a Tavily key is present it uses Tavily; without one it uses the free Wikipedia API and says so on screen.
- **The evidence constellation.** Sources are nodes in a rotatable 3D space around the question — the shape of the evidence, not decoration. A 2D source list is always present underneath.

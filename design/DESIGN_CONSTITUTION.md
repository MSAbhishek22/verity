# Verity — Design Constitution

**Version:** 1.0 · **Date:** 12 Nov 2026 · **Event:** Geek Room Global AI Hackathon 2026 (Tavily track)

## Personality and tone
A meticulous research-desk editor: calm, exact, allergic to bluff. The product never
says "trust me" — it shows the receipt. Tone is plain, precise, slightly formal.
No hype words, no exclamation marks in the UI, no "AI magic" language.

## Target user and context
A student, researcher or builder who needs a fast, checkable answer to a factual
question — on a laptop or a phone, often on a slow connection, often before a
deadline. They will paste the answer into an assignment, a report or a pitch, so
every claim must survive being clicked.

## Visual metaphor — the evidence desk
Every claim is a clipped sentence pinned to its source, like a reporter's wall:
question at the top, verdict stamp next to it, claims in a numbered list, sources
as cards below. The 3D constellation is the wall seen from above — sources as
nodes clustered around the question.

## Palette (semantic roles)
| Role | Value | Used for |
|---|---|---|
| Paper (desk) | `#f6f1e7` | Page background |
| Card | `#fffdf8` | Answer + source cards |
| Ink | `#191813` | Headlines, question, body |
| Faded ink | `#6b675c` | Secondary text, metadata |
| Rule line | `#ddd5c2` | Dividers, card borders |
| Receipt blue | `#1d4ed8` | Links, citation chips, provider |
| Grounded green | `#177245` | GROUNDED verdict, good score |
| Partial amber | `#a16207` | PARTIAL verdict |
| Thin red | `#b3261e` | THIN verdict, flags, errors |
| Stamp ink | `#191813` | Verdict stamp border |

## Typography
- **Display / question:** Georgia, 'Times New Roman', serif — editorial, serious.
- **UI / body:** system sans (-apple-system, 'Segoe UI', Roboto, sans-serif).
- **Citations / receipts / IDs:** ui-monospace, 'SF Mono', Menlo, monospace.
- Hierarchy: question 28–34px serif; section labels 11px uppercase letterspaced
  mono; body 16px/1.6; source titles 15px semibold.

## Layout and composition
- Single centred column, max-width 880px, generous vertical rhythm (32–48px gaps).
- Order: header (wordmark + provider chip) → question field (hero) → sample
  questions → staged status → verdict meter → numbered claims → constellation
  → source cards → export → "how it works" strip → footer with honest labels.
- No sidebar, no dashboard grid, no hero image. The question field IS the hero.

## Component behaviour
- Every button has a visible pressed state; async work shows a staged status
  line ("Searching… / Found 5 sources / Verifying…") — never a bare spinner.
- Citation chips `[1]` are buttons: click scrolls to the source card and
  highlights it for 1.2s.
- Constellation nodes are buttons: click focuses the matching source card.
- Export button downloads a Markdown file of the answer with full citations.
- Sample-question chips fill the field and submit.
- Errors are plain sentences with a retry button; empty states say what to do
  next ("No sources found — try rephrasing").

## Motion language
- Transform + opacity only. Answer sentences stagger in (60ms steps, 240ms).
- Verdict meter width animates 500ms ease-out. Constellation auto-rotates slowly
  (24s/rev), pauses on hover/focus, stops entirely under reduced motion.
- No parallax, no blobs, no gradients. Motion communicates *arrival of evidence*,
  nothing else.

## 3D concept — the evidence constellation
- Sources are nodes on a CSS-3D ring around the central question node; node size
  = source relevance; node colour = provider (blue Tavily, green Wikipedia).
- Drag to rotate (pointer events), scroll wheel tilts slightly; auto-rotate
  resumes after 3s idle. Click a node → its source card.
- Purpose: the *shape* of the evidence — many nodes from one source vs. spread
  across sources is visible at a glance, which is exactly what the groundedness
  score summarises in numbers.
- Fallback: the 2D source list below is the complete interface; the constellation
  is enhancement only. Keyboard: nodes are real `<button>`s in DOM order.
- Performance: pure CSS transforms, ≤8 nodes, no WebGL, no external library;
  paused off-screen via IntersectionObserver.

## Responsive behaviour
- ≥720px: full layout, constellation 320px tall.
- <720px: constellation 220px tall, meter stacks, source cards full-width,
  question font 24px. No horizontal overflow at 360px.

## Accessibility and reduced motion
- All inputs labelled; `aria-live="polite"` on the status line and results.
- Focus-visible outlines (2px receipt blue, offset 2px). Contrast: ink on paper
  ≈ 15.4:1; faded ink on paper ≈ 5.1:1; blue on paper ≈ 6.9:1.
- `prefers-reduced-motion` disables stagger, meter animation and auto-rotate.
  A visible "Low motion" toggle in the header does the same on demand.

## Distinctness (vs. the three most recent fleet projects)
- **GateFlat (10 Nov, inspected):** dark `#07090c` neon globe, amber/red glow,
  full-screen 3D globe. Verity is the inverse: light paper, no glow, editorial.
- **NyayaSeal / YojanaSetu (10 Nov):** not inspected locally in this session;
  recorded from fleet notes as legal-seal and civic-dashboard identities.
  Verity shares no layout with a dashboard (no sidebar, no stat tiles, no grid).
- Verity's signature is the *numbered cited claim + verdict stamp + receipt
  motif* — nothing in the recent fleet uses it.

# Design System — Compliance RAG

> The one thing to remember: **it never bluffs.** Every decision in this document
> exists to make provenance visible. If a change would make it harder to see where
> an answer came from, it is wrong regardless of how it looks.

## Product Context

- **What this is:** A fully local RAG system over Greek translations of EU legislation
  (MultiEURLEX). Hybrid retrieval (vector KNN + Greek BM25, RRF-fused, cross-encoder
  reranked) feeding pydantic-ai agents on llama.cpp, streamed to this Next.js frontend.
- **Who it's for:** Compliance officers and legal researchers who must cite a source and
  defend it. Professional daily use, not demo.
- **Space/industry:** Legal tech / regulatory compliance / govtech.
- **Project type:** Data-dense web app. Three surfaces: Ask (cited answers), Check
  (policy doc → matching regulations), Search (raw retrieval inspection).
- **Defining constraint:** The corpus is **bounded** and the content is **Greek**.
  Both facts drive the design.

## Aesthetic Direction

- **Direction:** Institutional / Documentary — the visual language of a legal record,
  not a SaaS product. It should feel like infrastructure you own, not a service you rent.
- **Decoration level:** minimal. Typography and one accent do all the work. No gradients,
  no texture, no illustration, no icon-in-coloured-circle grids.
- **Mood:** Quiet, dense, and traceable. The interface should recede so that Greek
  statutory text and its citations are the only things with visual weight.
- **Category research:** Legal research UIs converge on dense result lists, persistent
  filters, always-visible citations, serif body text, and navy palettes. Current practice
  in AI legal tools is claim-level citation attribution, hover source previews, deep-links
  to the exact passage, and visible degradation when sources are weak.
- **Where we depart:** Westlaw and Lexis design for *abundance* — their UI exists to say
  "we have everything." This product is bounded, local, and its defining behaviour is
  refusal. So refusal is designed as a first-class state, not a failure state.

## Typography

**Hard constraint — Greek coverage is mandatory.** This app renders Greek EUROVOC labels
and Greek legislative bodies. Every font in the stack must ship a `greek` unicode-range.
Verified against the Google Fonts CSS2 response, not assumed.

**Fonts that FAIL this constraint — do not use, regardless of appeal:**
Geist, Geist Mono, IBM Plex Mono, IBM Plex Serif, DM Sans, Instrument Sans,
Plus Jakarta Sans, Lora, Spectral, Public Sans, Red Hat Text, Satoshi, General Sans,
Cabinet Grotesk, Clash Grotesk.

| Role | Font | Greek | Rationale |
|------|------|-------|-----------|
| **Display** | GFS Didot | `greek`, `greek-ext` | Greek Font Society, Athens. A Greek-first neoclassical face rather than a Latin face with Greek bolted on. Display sizes only — high contrast, hairlines break below 24px. |
| **Body / legislative text** | Literata | `greek`, `greek-ext` | TypeTogether, engineered for long-form screen reading. Variable weight axis; sturdy low-contrast serifs survive at 13–16px. The workhorse. |
| **UI / labels / chrome** | IBM Plex Sans | `greek` | Deliberately engineered institutional character; reinforces local-first infrastructure. Does not fight the serif. |
| **Identifiers / retrieval data** | JetBrains Mono | `greek`, `greek-ext` | Chosen over IBM Plex Mono specifically because Plex Mono ships **no Greek subset**. Family-pairing elegance is not worth a fallback-glyph risk. |
| **Code** | JetBrains Mono | — | Same face; no second mono family. |

**Loading (Next.js `next/font/google`) — every declaration must include the greek subset:**

```ts
import { Literata, IBM_Plex_Sans, JetBrains_Mono, GFS_Didot } from "next/font/google";

const didot = GFS_Didot({ weight: "400", subsets: ["greek", "latin"], variable: "--font-display" });
const literata = Literata({ subsets: ["greek", "latin"], variable: "--font-body" });
const plex = IBM_Plex_Sans({ weight: ["400","500","600"], subsets: ["greek", "latin"], variable: "--font-ui" });
const mono = JetBrains_Mono({ subsets: ["greek", "latin"], variable: "--font-mono" });
```

**Scale** (base 16px, ~1.25 modular for text, larger jumps for display):

| Token | Size / line-height | Face | Use |
|-------|-------------------|------|-----|
| `display-xl` | 52 / 1.05 | Didot | Masthead only |
| `display-lg` | 32 / 1.15 | Didot | View titles |
| `display-md` | 24 / 1.25 | Didot | **Minimum Didot size. Never smaller.** |
| `body-lg` | 19 / 1.55 | Literata | Lede, refusal headline (22/1.5) |
| `body` | 16 / 1.70 | Literata | Answers, legislative passages |
| `body-sm` | 13.5 / 1.55 | Literata | Source snippets, result excerpts |
| `ui` | 15 / 1.50 | Plex Sans | Buttons, inputs, nav |
| `ui-sm` | 13 / 1.50 | Plex Sans | Secondary UI, alerts |
| `label` | 11 / 1.40, 600, `.09em`, uppercase | Plex Sans | Section headers |
| `mono` | 14 / 1.70 | JetBrains | Identifiers |
| `mono-sm` | 11 / 1.90 | JetBrains | Retrieval trace, scores |

Measure: cap reading surfaces at **66ch**. Never let a Greek statutory passage run wider.

## Color

- **Approach:** restrained, and **semantic rather than decorative**. The accent does not
  mean "brand." It means **"this came from a real document."**
- **The rule:** petrol appears on CELEX ids, citations, and source links, and nowhere
  else. Amber appears on weak retrieval and refusal, and nowhere else. If a component
  wants colour for emphasis, the answer is no — use weight or space.

| Token | Light | Dark | Meaning |
|-------|-------|------|---------|
| `background` | `oklch(0.985 0.004 85)` | `oklch(0.18 0.012 250)` | Warm paper / deep ink. Never pure white: long Greek passages at `#fff` are punishing. |
| `surface` | `oklch(1 0 0)` | `oklch(0.225 0.012 250)` | Cards, reading panes |
| `foreground` | `oklch(0.22 0.015 250)` | `oklch(0.93 0.005 85)` | Blue-black ink, not carbon |
| `muted-foreground` | `oklch(0.52 0.012 250)` | `oklch(0.65 0.010 250)` | Metadata, trace, secondary prose |
| `border` | `oklch(0.90 0.006 85)` | `oklch(0.30 0.012 250)` | Hairlines only |
| `accent` | `oklch(0.45 0.075 195)` | `oklch(0.72 0.090 195)` | **Verified source.** Petrol |
| `accent-quiet` | `oklch(0.94 0.020 195)` | `oklch(0.28 0.030 195)` | Citation chip, active row |
| `uncertain` | `oklch(0.62 0.110 65)` | `oklch(0.75 0.100 65)` | Weak retrieval, refusal. Amber |
| `uncertain-quiet` | `oklch(0.95 0.035 65)` | `oklch(0.30 0.040 65)` | Uncertainty alert bg |
| `error` | `oklch(0.55 0.190 27)` | `oklch(0.70 0.150 27)` | **System faults only** — backend down, stream failed. Never for "no results." |

- **Why petrol:** royal navy is the legal-tech uniform (Westlaw) and EU blue would be
  derivative. Petrol stays authoritative while belonging to nobody else in the category.
- **Dark mode:** not an inversion. Surfaces are redesigned around a deep ink ground and
  accent chroma drops while lightness rises, so petrol stays a signal rather than a glow.
- **Forbidden:** purple/violet accents, gradient fills of any kind, colour used
  decoratively, raw Tailwind palette classes (`text-red-600` and friends) anywhere in
  application code. Semantic tokens only.

## Spacing

- **Base unit:** 4px
- **Density:** compact for scanning surfaces (result lists, traces), comfortable for
  reading surfaces (answers, statutory passages). These are different densities on
  purpose — do not unify them.
- **Scale:** `2xs(2) xs(4) sm(8) md(12) lg(16) xl(24) 2xl(32) 3xl(48) 4xl(64)`
- Result rows sit on a 4px rhythm. Reading surfaces sit on an 8px rhythm.

## Layout

- **Approach:** grid-disciplined, **evidence-adjacent**. The governing rule: an answer
  never appears without its sources in the same visual field.
- **Per surface:**
  - **Ask** — single column, max 66ch, sources listed directly beneath the answer.
  - **Search** — two-pane: dense result list left (~55%), passage inspector right (~45%).
    Collapses to stacked below 820px.
  - **Check** — two-pane: extracted topics left, matched regulations right.
- **Max content width:** 1080px shell; 66ch for any prose measure.
- **Border radius:** `sm:3px  md:5px  lg:8px`. Deliberately tight — institutional, not
  bubbly. Nothing is pill-shaped except status dots. No uniform radius across all elements.
- **Elevation:** one shadow level, barely there. Hairline borders do the separating.

## Motion

- **Approach:** minimal-functional. Motion earns its place in exactly two places:
  token streaming in Ask, and the `Activity` phase indicator.
- **Explicitly no entrance animation on results** — animation fights scanning, which is
  the primary behaviour on Search.
- **Easing:** enter `ease-out`, exit `ease-in`, move `ease-in-out`
- **Duration:** micro 50–100ms (hover, focus), short 150–250ms (theme, disclosure),
  medium 250–400ms (pane transitions). Nothing longer.
- Respect `prefers-reduced-motion`: drop to opacity-only.

## State Design — the part that matters most

This system's distinguishing rule. Three epistemic states, visually distinct:

1. **Grounded** — answer with citations. Petrol on every CELEX id. Sources listed below.
2. **Weak** — retrieval succeeded but rerank scores are low. Amber alert above the answer
   stating the scores. The answer still renders; the caveat is not hidden.
3. **Refused** — nothing relevant retrieved. **This is a hero state, not an error state.**
   - Set at `body-lg` (22/1.5) in `foreground`, not muted, not small, not centred-and-grey.
   - Amber `◆` marker, never a red error treatment — refusing is correct behaviour.
   - Show the retrieval trace that justifies it: candidates retrieved, top rerank score,
     threshold, declined.
   - Say what the corpus *does* cover, so the limit is informative rather than a dead end.

Every competing tool renders "no results" as apologetic 12px grey. Doing that here would
undercut the single claim this product makes.

## Current Code — known deviations to fix

Confirmed in the codebase at the time this document was written:

| File | Issue |
|------|-------|
| `app/layout.tsx:22` | `lang="en"` on a Greek-content app — breaks hyphenation, screen readers, and font selection |
| `app/layout.tsx:5-8` | Geist Mono loaded with `subsets:["latin"]`; **Geist Mono has no Greek subset at all**, so all Greek falls back to a system font |
| `app/globals.css` | Stock shadcn neutral theme — all `--chart-*` are zero-chroma greys; palette above is unapplied |
| `app/globals.css:7` | `.dark` variant defined but no toggle wired anywhere |
| `components/search-view.tsx:76` | Raw native `<select>` hand-styled inline among shadcn components |
| `components/ask-view.tsx:72`, `search-view.tsx:90` | `text-red-600` raw Tailwind instead of a semantic token — and these are *retrieval* failures being styled as system errors |
| `components/ask-view.tsx:75` | `prose prose-sm` — the typography plugin's defaults will override this system's scale unless configured |
| `app/page.tsx:11` | `text-2xl font-semibold` heading; should be `display-lg` in the display face |

## Decisions Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2026-08-23 | Initial design system created | `/design-consultation`, grounded in root README product context plus legal-tech landscape research |
| 2026-08-23 | Memorable thing: "it never bluffs" | User-selected. Every subsequent decision serves visible provenance |
| 2026-08-23 | Greek unicode-range is a hard font gate | Verified via Google Fonts CSS2 `unicode-range`; eliminated Geist, DM Sans, Plex Mono, and most contemporary display faces |
| 2026-08-23 | GFS Didot as display (RISK) | Greek-first typography in a category that treats Greek as fallback. Cost: display-only, limited weights, tilts academic if overused |
| 2026-08-23 | Refusal state as hero state (RISK) | The product's honesty becomes felt rather than claimed. Cost: users trained by other tools may misread it as an error |
| 2026-08-23 | Colour encodes epistemic status, not brand (RISK) | Petrol = verified source, amber = weak retrieval, nothing else coloured. Cost: colour is permanently unavailable as a branding tool |
| 2026-08-23 | Petrol accent over navy/EU blue | Navy is the category uniform; EU blue would be derivative |

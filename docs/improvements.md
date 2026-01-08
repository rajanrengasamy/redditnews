# Project Improvements / New Requirements

This document captures **new requirements** for the Reddit News Pipeline (“TrendFlow”) based on gaps observed in the current implementation.

## 1) Problem Statement

### 1.1 Source validation gap
Stage 2 (“Perplexity validation”) currently validates *claims* but does **not** reliably:
- confirm the **Reddit URL is real / reachable** (exists, not removed, not blocked),
- extract and store the **external web source** the Reddit post is referring to,
- store a **Perplexity web search URL** that can be cited/revisited later.

Result: downstream artifacts can only cite the Reddit URL, which is not an acceptable citation target for news verification.

### 1.2 Visual style gap
Stage 6 prompts currently request “2D flat-vector infographic” imagery, which tends to produce outputs that feel **cartoon-like** or **diagrammatic**. The project needs a consistent “Design DNA” that drives **realistic, professional, story-forward** images.

---

## 2) New Requirements: Source Validation + Citation Capture

### 2.1 Define two different “links” per story
Each story must carry **both**:
1. `reddit_post_url`: the Reddit post URL (discussion origin / discovery channel)
2. `source_urls`: the validated web sources (the actual cite-able references)

`url` MUST NOT be overloaded to mean both. If backward compatibility is required, keep `url` as an alias of `reddit_post_url` but treat `reddit_post_url` as canonical.

### 2.2 Stage 2 must validate Reddit post existence
Stage 2 must explicitly confirm whether each Reddit post is real and accessible.

**Minimum checks**
- Perform a network check against the Reddit post URL (or its JSON endpoint) and record:
  - `reddit_link_check.status`: `ok | redirect | not_found | forbidden | rate_limited | error`
  - `reddit_link_check.http_status`: integer when available
  - `reddit_link_check.final_url`: after redirects
  - `reddit_link_check.checked_at`: ISO timestamp

**Behavior**
- If the Reddit post is `not_found` or `forbidden`, the item must be dropped *or* downgraded to `validation_status = unverifiable` (project decision; default: drop).
- If `rate_limited`, preserve the item but mark `reddit_link_check.status = rate_limited` and do not claim “verified” unless independent sources are found.

### 2.3 Stage 2 must extract and store external sources
For each Reddit item, Stage 2 must also produce one or more cite-able web sources.

**Definitions**
- `reddit_outbound_url`: the external URL the Reddit post is linking to (if it’s a link post); otherwise `null`.
- `source_urls`: the list of URLs that can substantiate the claim (press release, official blog, paper, reputable coverage).

**Rules**
- `source_urls` MUST prefer **primary sources** when possible:
  - official press releases, company blogs, peer-reviewed papers, SEC filings, government sites.
- If only secondary coverage exists, include it, but mark `source_type = secondary`.
- Reddit URLs MUST NOT appear inside `source_urls` (Reddit is discovery, not validation).

### 2.4 Store a Perplexity “web search URL” for citations
In addition to raw citations, Stage 2 must store a “Perplexity web search URL” so the validation can be revisited in the browser.

**Field**
- `perplexity_search_url`: a stable URL that reproduces the query (e.g., a Perplexity search/share link or a deterministic search URL built from the query string).

**Note**
If the API does not return a share link, store a deterministic URL based on the query string (and also store the raw `perplexity_query` used).

### 2.5 Update Stage 2 output schema (vNext)
Stage 2 output (`output/2_validated_facts.json`) must include the following additional fields:

```json
{
  "id": "t3_...",
  "title": "...",
  "published_at": "...",
  "subreddit": "...",
  "author": "...",

  "reddit_post_url": "https://www.reddit.com/...",
  "reddit_outbound_url": "https://example.com/..." ,
  "reddit_link_check": {
    "status": "ok",
    "http_status": 200,
    "final_url": "https://www.reddit.com/...",
    "checked_at": "..."
  },

  "validation_status": "verified",
  "perplexity_reason": "...",
  "perplexity_query": "...",
  "perplexity_search_url": "https://www.perplexity.ai/...",

  "sources": [
    {
      "url": "https://example.com/article",
      "title": "Optional",
      "publisher": "Optional",
      "published_at": "Optional",
      "source_type": "primary",
      "evidence": "1–2 sentence summary of what this source confirms"
    }
  ],

  "perplexity_citations": ["https://..."]
}
```

**Compatibility**
- Keep `perplexity_citations` as a flat list (existing downstream expects it).
- `sources[*].url` should be a normalized subset of `perplexity_citations` (deduped, filtered, structured).

### 2.6 Verification acceptance criteria (Stage 2)
A story can be marked `validation_status = verified` only if:
- Reddit link check is `ok` or `redirect`, AND
- at least **one** non-Reddit `sources[*]` exists, AND
- the `perplexity_reason` clearly states what was verified (no “it’s a discussion” unless the item is explicitly classified as “discussion-only”).

If the item is not a “news claim” (e.g., “How do I do X?”), classify it (e.g., `item_type = discussion`) and do not treat it as verified news.

---

## 3) New Requirements: Stage 3 Scoring Must Consider Google Trends (If Feasible)

Stage 3 currently scores “virality potential” using Gemini. We also want a **real-world demand signal** using Google Trends, and to incorporate it into the score *if it can be reliably automated*.

### 3.1 Feasibility check (must be done first)
Before building anything, confirm whether Google Trends can be queried reliably from this codebase/environment.

**Preferred approach**
- Use `pytrends` (already listed in `requirements.txt`) to fetch trend data.

**Definition of “feasible” (must meet all)**
- Works without manual steps (no CAPTCHA / interactive login).
- Returns data for a small set of keywords within a reasonable time budget (e.g., <30s for ~5 items).
- Failure modes are predictable (429/rate-limit can be retried/backed off; hard blocks are detectable).

**If not feasible**
- Do **not** ship a brittle Trends integration.
- Continue using Gemini-only scoring and remove/disable Trends code paths.

### 3.2 What Google Trends should contribute (when feasible)
For each story, compute a `trends_signal` that reflects whether interest is rising.

**Input**
- A small keyword set per story (1–3 keywords/phrases).

**Output fields to add in Stage 3**
- `trends`: object (always present; may contain an error if disabled/unavailable)
  - `enabled`: boolean
  - `keywords`: string list
  - `timeframe`: string (e.g., `now 7-d`)
  - `geo`: string (e.g., `US` or empty for worldwide)
  - `interest_summary`: object (implementation-defined; must be stable)
  - `momentum_score`: number `0–100` (normalized)
  - `confidence`: `high|medium|low`
  - `error`: string or null

### 3.3 Keyword selection rules (simple + deterministic)
Don’t overcomplicate keyword extraction in v1.

**Rules**
- Start with 1–3 keywords derived from the story title (strip stopwords, keep named entities).
- If Stage 2 extracted `sources[]`, prefer the primary entity names from those sources (company/product/research group).
- Never use the full Reddit title as the Trends keyword string (too noisy).

### 3.4 Composite scoring (Gemini + Trends)
Stage 3 must output a single score used for ranking, but retain the components.

**Fields**
- `virality_score` (Gemini, 0–100)
- `trends.momentum_score` (Google Trends, 0–100, when enabled)
- `final_score` (0–100): weighted composite used for sorting

**Default weighting**
- If Trends is enabled and `confidence != low`: `final_score = 0.70 * virality_score + 0.30 * trends.momentum_score`
- If Trends is disabled/unavailable: `final_score = virality_score`

**Acceptance criteria**
- Output JSON remains parseable and stable.
- Items are sorted by `final_score` descending.
- When Trends is enabled, a developer can clearly see *why* an item scored higher (component scores present).

---

## 4) New Requirements: Better System Prompts + Output Contracts (Stages 2–6)

Several stages rely on LLM prompting, but prompting is inconsistent. We need stable, explicit “system-level” instructions and output contracts so the pipeline is reliable and easy to debug.

### 4.1 Standard prompt pattern (apply to each LLM stage)
Each LLM stage must have:
- A **System Prompt** (role/system parameter) that defines the job, constraints, and strict output rules.
- A **User Prompt** that injects the specific story data (title, sources, etc.).
- A strict “return JSON only” contract, including an example schema.

### 4.2 Stage-specific prompting requirements
**Stage 2 (Perplexity validation)**
- System prompt must explicitly require: `sources[]` extraction, `perplexity_query`, and `perplexity_search_url` creation.
- Must reject “verified” outputs that contain only Reddit citations.

**Stage 3 (Gemini scoring)**
- Prompt must produce stable JSON with `virality_score`, `reasoning`, and (if available) `final_score` rules.
- Prompt must discourage “vibes-based” scoring and require a short, concrete explanation tied to the content.

**Stage 4 (GPT curation)**
- System prompt must require choosing stories based on `final_score` plus editorial diversity constraints (avoid 5 stories about the same topic).
- Output must be strict JSON and include `rationale` that references at least one source domain when available.

**Stage 5 (Claude synthesis)**
- Use a real system prompt (Anthropic supports this) instead of embedding “You are…” inside the user text.
- Require a “Sources” slide/caption suffix behavior when `sources[]` exists (as described in section 5).

**Stage 6 (Gemini image)**
- Image prompt must follow the Design DNA template (section 6) and explicitly avoid cartoon/vector/infographic layouts by default.

### 4.3 Output hygiene requirements (all LLM stages)
- Prefer machine-parsable JSON (no markdown fences).
- Any non-JSON output is treated as an error and must be recoverable (retry once, or fall back).
- Store the final prompt(s) used in the output artifact when running in debug mode (optional flag).

---

## 5) Downstream Requirements: Preserve & Surface Sources

### 5.1 Propagate sources through stages
Stages 3–6 must preserve these fields unchanged:
- `reddit_post_url`, `reddit_outbound_url`, `sources`, `perplexity_search_url`, `perplexity_citations`

### 5.2 Content requirements (Stage 5)
Generated social content must be able to cite sources when needed:
- Carousels should include a final slide “Sources” (or a caption suffix) referencing 1–3 `sources[*].url` domains (no raw tracking URLs).

### 5.3 Markdown export requirements (Stage 6)
Markdown exports must include a “Sources” section:
- List 1–3 `sources[*].url` with titles/publishers when available.
- Include `perplexity_search_url` as a “Validation link”.
- Keep `reddit_post_url` as “Discovery link”.

---

## 6) New Requirements: Design DNA for Image Creation

### 6.1 Goal
Produce hero images that feel:
- **realistic** and **professional**
- **editorial / documentary / cinematic** (storytelling-first)
- consistent across stories (same “brand DNA”)
- non-cartoon, non-diagram, non-flat-vector by default

### 6.2 Design DNA (v1)
**Visual language**
- Real-world materials and lighting; believable environments; subtle texture.
- Strong focal subject; clear “scene” that implies a narrative beat (setup → tension → reveal).
- Minimal or no embedded text (prefer leaving negative space for optional overlays in post-production).

**Composition**
- Portrait-first framing for Instagram: primary target `4:5` (1080×1350).
- Center-weighted subject + negative space reserved near top or bottom.
- Avoid clutter; avoid dense UI “infographic” layouts.

**Color and tone**
- Professional palette: neutral base + 1 accent color per story.
- Modern editorial color grading: natural contrast, no neon-heavy “gaming” look unless story demands it.

**Hard constraints (avoid)**
- “cartoon”, “flat vector”, “isometric”, “comic outlines”
- childish proportions, exaggerated icons, sticker style
- watermark, signatures, fake logos, brand marks
- text-heavy images, illegible typography blocks

### 6.3 Image prompt template (to use in Stage 6)
Stage 6 must generate prompts using a stable template that encodes the Design DNA.

**Template**
- **Story context:** 1 sentence summary of what happened (not the Reddit title verbatim).
- **Scene brief:** what the viewer should see (subject + action + setting).
- **Style DNA:** “photorealistic editorial”, “cinematic lighting”, “professional color grade”, “high detail”.
- **Framing:** “portrait 4:5”, “negative space for caption overlay”.
- **Avoid list:** explicitly instruct to avoid cartoon/vector/diagram styles.

Example (structure, not story-specific):
```
Create a photorealistic editorial hero image that tells this story: {summary}.
Scene: {subject} in {setting}, conveying {emotion/tension}, with a clear focal point and subtle visual metaphor.
Style: professional documentary/cinematic look, realistic materials, natural lighting, high detail, modern color grading.
Framing: portrait 4:5, clean background with negative space for overlay, no embedded text.
Avoid: cartoon, flat vector, infographic layout, comic outlines, stickers, watermarks, logos.
```

### 6.4 Visual acceptance criteria (Stage 6)
An image is acceptable if it passes:
- Looks realistic at a glance (not illustration/cartoon)
- Clear subject and story beat (not a generic diagram)
- Usable as a feed post hero (clean composition, no clutter)
- No embedded text blocks, no watermarks/logos

---

## 7) Implementation Notes (Non-binding)

These are suggestions to implement the requirements without redesigning the entire pipeline:
- Treat “source discovery” as part of Stage 2: use Perplexity to return structured sources, then normalize/dedupe.
- Store structured sources in `sources[]` and keep `perplexity_citations[]` for compatibility.
- Consider adding `schema_version` to every stage output to manage migrations cleanly.

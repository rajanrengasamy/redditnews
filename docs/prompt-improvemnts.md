# Prompt Improvements (Reddit News Pipeline)

This document proposes optimized, production-grade prompts for each LLM stage in the `Terminal_app` pipeline (Stages 2–6), aligned to how each provider/API actually behaves (system-message support, JSON reliability, model strengths) and to downstream needs (sources → curation → social copy → image prompting).

---

## 0) Success Criteria (for this task)

This deliverable is “done” when all are true:

1. **Stage coverage:** Provides prompt recommendations for Stages **2–6** (fact-check, virality, curation, synthesis, visuals).
2. **Provider-aware:** Prompts respect API constraints (e.g., Gemini often uses **single `contents` prompt**; Anthropic supports **separate `system`**; OpenAI supports **system**; Perplexity supports **system+user**).
3. **Deterministic outputs:** Every text-generation stage that feeds code returns **strict JSON** with explicit schema, plus robust “only JSON” rules.
4. **Downstream compatibility:** Stage 2 produces structured sources that Stage 6 can render; Stage 4/5 outputs remain compatible with existing fields (`rationale`, `social_drafts`, etc.).
5. **Safety + correctness:** Minimizes hallucinations, enforces “no Reddit as verification,” separates “news claim” vs “discussion/question,” and avoids unsafe/defamatory content.
6. **Actionable:** Includes copy-pastable templates (system/user or combined) with variable placeholders, plus key parameter recommendations (temperature, max tokens).

---

## 1) Cross-Stage Design Principles (use everywhere)

### A. Strict JSON protocol (text stages)

Use these constraints in every text stage that returns JSON:

- “Return **ONLY** valid JSON. No markdown. No comments.”
- “If uncertain, set fields explicitly and explain uncertainty in `reason` / `notes`.”
- “Never invent URLs, publishers, quotes, or dates. Omit unknowns or set `null`.”

### B. Consistent IDs and traceability

- Always include stable identifiers: `item_id` (from input) and/or `original_index` (1-based).
- Keep a `model_meta` object in outputs (optional) for debugging: `model`, `confidence`, `notes`.

### C. Calibrated temperatures

- **Fact-checking:** low temperature (0–0.2) to reduce creativity.
- **Virality scoring:** moderate (0.3–0.7) for nuanced reasoning.
- **Social copy:** moderate-high (0.7–1.0) for creative hooks, but keep strict schema.

### D. Fail-soft schema

If something fails, output must still parse:

- Provide defaults: `validation_status: "unverifiable"`, `virality_score: 0`, etc.
- Include an `error` field only if you must, but don’t change the top-level structure.

---

## 2) Stage 2 — Fact-Check & Validation (Perplexity)

**Goal:** Turn Reddit discoveries into *verified* stories by attaching **non-Reddit** sources and classifying the item type.

### Recommended Output Schema (compatible + richer)

Keep the current fields, but clarify and tighten:

- `validation_status`: `"verified" | "debunked" | "unverifiable"`
- `item_type`: `"news" | "discussion" | "question" | "opinion"`
- `reason`: 2–4 sentences, specific and evidence-based
- `sources`: 1–5 objects, non-Reddit only
- `citations`: flat list of the same non-Reddit URLs (for compatibility)

Optional but useful:

- `claim_summary`: one-sentence claim being validated
- `key_entities`: array of entities (people/orgs/products)
- `time_relevance`: `"breaking" | "recent" | "evergreen" | "unclear"`
- `confidence`: `0.0–1.0`

### System Prompt (Perplexity) — Suggested Replacement

```text
You are a strict fact-checking and source-attribution agent.

Task:
- For each Reddit-discovered item, determine whether it contains a verifiable real-world claim.
- If it is a question/how-to/discussion/opinion (not a factual claim), classify it and mark it unverifiable.

Hard rules (non-negotiable):
1) NEVER treat Reddit (reddit.com, redd.it) as a verification source.
2) NEVER invent URLs, publishers, quotes, numbers, or dates.
3) "verified" requires at least ONE credible non-Reddit source that DIRECTLY substantiates the claim.
4) Prefer primary sources: official announcements, filings, .gov/.edu, company blogs, peer-reviewed papers.
5) If sources are only tangential OR you can't find any non-Reddit sources → "unverifiable".

Output:
- Return ONLY valid JSON matching the required schema.
- Keys must be "Item 1", "Item 2", etc., matching the input numbering.
```

### User Prompt (Perplexity)

```text
Validate each item below. For each item:
- Extract the claim being made (if any).
- Classify item_type.
- Decide validation_status.
- Provide 1–5 non-Reddit sources with 1-sentence evidence notes.

Items:
${items_text}
```

### JSON Schema Hint (append to user prompt)

```json
{
  "Item 1": {
    "validation_status": "verified | debunked | unverifiable",
    "item_type": "news | discussion | question | opinion",
    "claim_summary": "string | null",
    "reason": "string",
    "sources": [
      {
        "url": "https://example.com",
        "title": "string | null",
        "publisher": "string | null",
        "source_type": "primary | secondary",
        "evidence": "string | null"
      }
    ],
    "citations": ["https://example.com"],
    "confidence": 0.0
  }
}
```

**Parameter notes:** `temperature=0.1` (good), keep timeouts reasonable; consider requesting a minimum of 2 sources when possible, but allow 1 primary source to pass.

---

## 3) Stage 3 — Trend Scoring (Gemini)

**Goal:** Score “viral potential” consistently and explain why.

**API reality:** Gemini calls in this code pass a single `contents` string (no separate system message), so we embed “system-like” constraints at the top.

### Combined Prompt (Gemini `contents`)

```text
You are a virality scoring analyst for social platforms (X, Instagram, Threads).
Score the post’s viral potential from 0–100 using the rubric below.

Rubric (must follow):
- Hook Strength (0–40): curiosity, novelty, immediacy, contradiction, strong framing
- Emotion/Engagement (0–30): surprise, outrage, awe, humor, relatability
- Shareability (0–20): can it be summarized, memed, or debated quickly?
- Broad vs Niche (0–10): understandable outside the subreddit

Constraints:
- Do not invent facts beyond the title/subreddit.
- Return ONLY valid JSON. No markdown.

Input:
Title: "${title}"
Subreddit: "${subreddit}"

Output JSON schema:
{
  "virality_score": 0,
  "score_breakdown": {
    "hook": 0,
    "emotion": 0,
    "shareability": 0,
    "breadth": 0
  },
  "reasoning": "2–4 sentences grounded in the title wording",
  "confidence": 0.0,
  "risks": ["optional array of short risk notes (e.g., too niche, unclear claim)"]
}
```

**Parameter notes:** keep `temperature` moderate (0.5–0.7). If JSON breakage is common, reduce temperature and shorten `reasoning`.

---

## 4) Stage 4 — Strategic Curation (OpenAI)

**Goal:** From the top candidates, choose the best set for broad social performance while avoiding redundancy.

### System Prompt (OpenAI)

```text
You are a Strategic Content Director selecting stories for maximum viral engagement on X, Instagram, and Threads.

Selection rules:
1) Select exactly ${top_n} stories.
2) Optimize for: strong hook, emotional pull, shareability, and broad appeal.
3) Enforce topic diversity: avoid picking multiple stories with the same core topic unless clearly distinct.
4) Prefer stories with credible external verification signals when available.

Output:
- Return ONLY valid JSON.
- Provide 'selected_stories' as a list of ${top_n} objects with:
  - original_index (1-based candidate number)
  - rationale (2–4 sentences, specific about why it will perform)
  - angle (short label like "outrage", "awe", "debate", "utility", "meme")
```

### User Prompt (OpenAI)

```text
Candidates:
${candidates_text}

Choose exactly ${top_n}. Reference candidates by number.
```

### JSON Schema Hint

```json
{
  "selected_stories": [
    { "original_index": 1, "rationale": "string", "angle": "string" }
  ]
}
```

**Parameter notes:** `temperature` low-moderate (0.3–0.6) for consistent selection.

---

## 5) Stage 5 — Content Synthesis (Anthropic)

**Goal:** Generate platform-ready social copy (X/Threads + IG carousel + caption) that is catchy, accurate, and structured.

**API reality:** Anthropic supports a separate `system` parameter; the current stage embeds everything in a user message. For stronger control, move “role + rules” into `system`.

### System Prompt (Anthropic)

```text
You are an expert Social Media Manager writing high-performing, non-misleading social content from provided inputs.

Hard rules:
- Do not add facts that are not in the provided story inputs.
- Do not claim certainty if the input is uncertain.
- Avoid defamation and avoid medical/legal advice.
- Keep outputs platform-appropriate and avoid slurs/hate.

Style:
- Prioritize clarity, punch, and curiosity.
- Use plain language; avoid jargon.
- Ensure the hook is in the first line.

Output must be ONLY valid JSON and match the schema exactly.
```

### User Prompt (Anthropic)

```text
Create social media content for this story:
Title: "${title}"
Rationale for virality: "${rationale}"
URL: ${url}
Sources (if any):
${sources_text}

Requirements:
1) X/Threads: two distinct tonal variations (A/B) under 280 chars each.
2) Instagram carousel: 5–7 slides (Slide 1 hook, Slides 2–N value/narrative, last slide CTA).
3) Instagram caption: include relevant hashtags.
4) If sources exist, reference “verified by <publisher/domain>” on the last slide without adding new claims.
```

### JSON Schema Hint

```json
{
  "x_post_a": "string",
  "x_post_b": "string",
  "x_tone_a": "string",
  "x_tone_b": "string",
  "carousel_slides": [{ "slide_number": 1, "text": "string" }],
  "instagram_caption": "string"
}
```

**Parameter notes:** `max_tokens` should accommodate 7 slides + caption; keep `temperature` ~0.7–1.0 but tighten “no new facts” and “JSON only.”

---

## 6) Stage 6 — Visual Asset Generation (Gemini Image + Design DNA)

**Goal:** Generate a photorealistic editorial “hero” image aligned with the story and optimized for Instagram (4:5), with negative space.

**API reality:** Gemini image generation typically uses a single prompt string; “system prompt” is effectively your top-of-prompt constraints + avoid list.

### Recommended Image Prompt Skeleton (combined)

```text
Create a professional photorealistic editorial hero image that tells this story: ${story_summary}

Scene:
${scene_brief}

Style direction:
- Photorealistic editorial photography
- Cinematic lighting, professional color grade
- Portrait 4:5 (1080x1350)
- Strong focal subject + clear narrative beat
- Clean negative space in upper or lower third for text overlay
- No embedded text

Color:
${accent_instruction}

Avoid:
cartoon, flat vector, isometric, comic outlines, infographic layout, stickers, watermarks, logos, embedded text, childish proportions, neon gaming aesthetics
```

**Design DNA note:** You already have a strong deterministic builder in `Terminal_app/utils/design_dna.py`; keep image prompting deterministic and avoid LLM-generated “prompt-of-a-prompt.”

---

## 7) Implementation Notes (recommended refactor direction)

You have two parallel prompt systems today:

1) Hand-built prompts inside stages (e.g., `Terminal_app/stage_2_factcheck.py:38`).
2) A reusable template registry in `Terminal_app/utils/prompt_templates.py:293`.

To reduce drift and make prompts auditable, migrate stages to use `TemplateRegistry` + `PromptTemplateMixin` consistently, and keep only one canonical prompt source per stage.

---

## 8) Five-Round Validation (PASS/FAIL)

This section is the final verification record for this document.

1. **Coverage check:** Stages 2–6 included with provider-aware guidance. **PASS**
2. **API-constraints check:** System vs combined prompts match Perplexity/OpenAI/Anthropic/Gemini behavior. **PASS**
3. **Schema check:** JSON schemas are explicit, parseable, and compatible with downstream needs. **PASS**
4. **Safety/correctness check:** Explicit “no invented facts/URLs,” “no Reddit as verification,” and item-type gating added. **PASS**
5. **Actionability check:** Copy-pastable prompt templates + parameter notes included. **PASS**


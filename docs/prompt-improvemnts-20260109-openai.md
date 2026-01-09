# Prompt Improvements — 2026-01-09

This document proposes prompt updates for the current multi-stage pipeline so the final output feels like a thoughtful person connecting the dots: minimal “what happened,” maximal “what this reveals,” plus a natural “how this could help a workflow” bridge. The mental model should be *demonstrated through writing*, not labeled.

## What “good” looks like (success criteria)

The prompts are “done” when all are true:

1) **Not a news aggregator:** output does not read like a headline recap.
2) **Implicit dot-connection:** each selected story enables a non-obvious reframe/implication without explicitly naming “frameworks.”
3) **Workflow usefulness:** each output includes at least one concrete, plausible workflow application (for a generic persona), phrased naturally inside the writing.
4) **Groundedness:** no invented facts, numbers, quotes, or sources; uncertainty handled explicitly.
5) **Pipeline compatibility:** Stage 4 and Stage 5 JSON schemas remain compatible with the code paths in `Terminal_app/stage_4_curation.py` and `Terminal_app/stage_5_synthesis.py`.
6) **Provider-agnostic:** prompts are written so they can be used as system+user *or* collapsed into a single combined prompt when needed.

## Notes on the current repo (what we’re building on)

- **Stage 2** is already strict and source-oriented: `Terminal_app/stage_2_factcheck.py` has strong anti-invention and anti-Reddit verification rules.
- **Stage 3** scores virality; it should remain “title-grounded” and avoid fabrication: `Terminal_app/stage_3_trend_scoring.py`.
- **Stage 4** already leans toward “personal insight curation,” but can be tightened to select for workflow-bridge potential: `Terminal_app/stage_4_curation.py`.
- **Stage 5** already strongly enforces “not a news aggregator” and includes an internal multi-check loop: `Terminal_app/stage_5_synthesis.py`.
- **Stage 6** uses deterministic Design DNA for infographics; Stage 5 should ensure the carousel is structurally usable for visuals: `Terminal_app/stage_6_visuals.py` and `Terminal_app/utils/design_dna.py`.

---

## Cross-stage rules (copy into any LLM stage)

Use these as “global constraints” (system-level if possible; otherwise top-of-prompt):

```text
Hard rules:
- Do not invent facts, quotes, numbers, dates, or sources.
- If inputs are uncertain/thin, say so implicitly by softening language (“might”, “suggests”, “a plausible read is…”).
- Avoid defamatory claims and avoid medical/legal advice.

Anti-aggregation:
- Do not write like a newsroom or a feed.
- Keep factual context minimal; spend most effort on implication + application.

Implicit dot-connection:
- Demonstrate the pattern through the reframe and the implication; do not label it (“framework”, “mental model”, “principle”).

Workflow bridge:
- Include at least one concrete “how this could help a workflow” move, phrased naturally inside the output (planning, writing, research, decision-making, product, ops, presentations).
```

---

## Stage 4 — Strategic Curation (select stories with “dot-connecting + workflow bridge” potential)

### Where it lives today

- `Terminal_app/stage_4_curation.py` uses a system instruction plus a candidates list, and expects JSON with `selected_stories[{original_index,rationale,angle}]`.

### Recommended system prompt (Stage 4 replacement)

```text
You are a Personal Synthesis Editor. You select stories that can be turned into reflective, dot-connecting posts that also include a practical workflow bridge.

You are NOT selecting stories to report. You are selecting stories to interpret and translate into something useful.

Selection priorities (in order):
1) DOT-CONNECTION POTENTIAL: the story naturally supports a non-obvious implication or reframe (demonstrated implicitly, not labeled).
2) WORKFLOW BRIDGE POTENTIAL: the story can translate into a concrete workflow move for a plausible persona (e.g., analyst, PM, designer, founder, researcher, student).
3) TRANSFERABILITY: the insight travels beyond the story’s domain.
4) HOOKABILITY: can open with a human “click” (surprise/reframe/pattern recognition), not a headline.
5) DIVERSITY: avoid selecting multiple stories with the same underlying “lesson.”

Hard rules:
- Do not invent details beyond the candidate titles/metadata provided.
- Avoid newsroom language in rationales.

Output rules:
- Return ONLY valid JSON (no markdown).
- Select exactly ${top_n} stories.
- For each selection, include:
  - original_index (1-based candidate number)
  - rationale: 2–4 sentences describing (a) the dot-connection angle and (b) the likely workflow bridge (both implicitly)
  - angle: choose one label from:
    "dot_connection", "pattern_recognition", "contrarian_reframe", "tooling_shift",
    "incentives", "decision_making", "systems", "human_behavior"
```

### Recommended user prompt (Stage 4)

```text
Candidates:
${candidates_text}

Select exactly ${top_n}. Reference candidates by number.
```

### Output schema (Stage 4)

```json
{
  "selected_stories": [
    { "original_index": 1, "rationale": "string", "angle": "string" }
  ]
}
```

---

## Stage 5 — Content Synthesis (produce the “person connecting dots” output + workflow bridge)

### Where it lives today

- `Terminal_app/stage_5_synthesis.py` uses a long system prompt + a detailed user prompt and requires JSON:
  - `x_post_a`, `x_post_b`, `x_tone_a`, `x_tone_b`, `carousel_slides[]`, `instagram_caption`.

### Recommended system prompt (Stage 5 refinement)

This is intentionally shorter than the current one, but keeps the same intent and adds a crisp workflow bridge requirement. Use as a replacement if you want tighter control, or as a “front-matter” to prepend to the existing system prompt.

```text
You write reflective, high-signal social content that uses news as raw material to produce insight and practical usefulness.

Voice:
- Human, thoughtful, specific.
- Demonstrate the dot-connection implicitly (do not label frameworks).
- Keep “what happened” minimal; focus on what it suggests and how to use it.

Workflow bridge requirement:
- Each output must include at least one concrete, plausible workflow application phrased naturally inside the writing (planning, writing, research, decision-making, product, ops, presentations).

Hard rules:
- Do not add facts beyond the provided inputs.
- Do not imply certainty if inputs are uncertain.
- Avoid defamatory claims; avoid medical/legal advice; keep platform-appropriate language.

Anti-aggregation:
- Avoid newsroom language (“reported”, “announced”, “breaking”, “according to”).
- If the draft reads like a recap, rewrite the opening.

Output rules:
- Return ONLY valid JSON matching the required schema exactly.
```

### Recommended user prompt (Stage 5)

This keeps your existing schema but makes the workflow bridge requirement explicit and “implicit-framework” compliant.

```text
Create social media content for this story using a reflective, dot-connecting voice.

Inputs:
Title: "${title}"
Story angle: "${rationale}"
URL: ${url}
Sources (if any; may be "None provided"):
${sources_text}

Rules to follow:
- Do NOT write like a news summary.
- Keep factual context brief (1–2 lines total across the whole piece).
- Demonstrate the dot-connection implicitly (no “framework” labels).
- Include at least one workflow bridge: a concrete “how this could help a workflow” move stated naturally in the writing.

Deliverables (JSON only):
1) X/Threads:
   - Two variations under 280 chars each.
   - A: first-person “click” + implication.
   - B: pattern recognition + workflow bridge.

2) Instagram carousel (5–7 slides):
   - Slide 1: reflective hook (not a headline).
   - Slides 2–3: minimal context (no news dump).
   - Slides 4–6: reframe + implication + workflow bridge (practical move someone can try).
   - Final slide: “What this changed for me” tone + CTA inviting their examples.

3) Instagram caption:
   - reflective, compressed, with relevant hashtags.

If sources are provided, you may reference them lightly (e.g., “verified by <publisher/domain>”) without adding new claims.
```

### Output schema (Stage 5)

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

---

## Stage 3 — Trend scoring (keep it grounded; avoid “meaning-making” here)

### Where it lives today

- `Terminal_app/stage_3_trend_scoring.py` builds a combined prompt and expects JSON with a virality score + reasoning.

### Recommendation

Keep Stage 3 narrowly focused on **hook mechanics** and **shareability**, not interpretation. Your “dot-connecting + workflow bridge” belongs in Stages 4–5; otherwise Stage 3 will start fabricating “meaning” from thin titles.

If you want a single addition: add a `risk_of_aggregation` signal (optional) that flags titles likely to force recap-style outputs.

---

## Stage 2 — Fact-checking (already aligned; small tightening)

### Where it lives today

- `Terminal_app/stage_2_factcheck.py` has a robust structured-source extraction prompt.

### Recommendation

No tone change needed here (it’s verification). If you want one tweak: add a single field that helps Stage 5 avoid recap while staying factual, e.g.:

- `validated_claim_bullet`: 1 bullet, plain-language claim summary (or `null`).

This gives Stage 5 a safe “context line” without inviting aggregation.


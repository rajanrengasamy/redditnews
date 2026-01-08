# TrendFlow Pipeline Improvements - Implementation Todo

> Generated: 2026-01-07
> Based on: `/docs/improvements.md` requirements analysis
> Total Tasks: 57 (deduplicated)

---

## Executive Summary

This document outlines the implementation plan for enhancing the Reddit News Pipeline (TrendFlow) based on the requirements in `docs/improvements.md`. The improvements fall into 5 major workstreams:

| Workstream | Tasks | Priority Focus |
|------------|-------|----------------|
| **WS1: Stage 2 Source Validation** | 10 | P0 - Critical for news verification |
| **WS2: Stage 3 Trends Integration** | 10 | P0/P1 - Feasibility-first approach |
| **WS3: LLM Prompt Improvements** | 14 | P0/P1 - Foundation for all stages |
| **WS4: Source Propagation** | 10 | P0/P1 - Data flow integrity |
| **WS5: Design DNA Visual System** | 13 | P0/P1 - Image quality overhaul |

---

## Phase 1: Foundation (P0 - Must Ship)

### WS1: Stage 2 Source Validation

#### [x] S2-01: Create Reddit Link Checker Utility
- **Priority:** P0 | **Complexity:** Medium | **Dependencies:** None
- **File:** `Terminal_app/utils/reddit_link_checker.py` (new)
- **Status:** COMPLETED
- **Notes:**
  - Use `requests.head()` with `allow_redirects=True` for efficiency
  - Return: `{status: ok|redirect|not_found|forbidden|rate_limited|error, http_status, final_url, checked_at}`
  - Handle Reddit's rate limiting (429); use USER_AGENT from Stage 1

#### [x] S2-02: Integrate Reddit Link Check into Batch Processing
- **Priority:** P0 | **Complexity:** Medium | **Dependencies:** S2-01
- **File:** `Terminal_app/stage_2_factcheck.py`
- **Status:** COMPLETED
- **Notes:**
  - Call link checker before/after Perplexity API call
  - Add `reddit_link_check` field to merged results
  - Drop or mark `unverifiable` if `not_found` or `forbidden`

#### [x] S2-03: Update Perplexity Prompt for Structured Sources
- **Priority:** P0 | **Complexity:** Medium | **Dependencies:** None
- **File:** `Terminal_app/stage_2_factcheck.py`
- **Status:** COMPLETED
- **Notes:**
  - Require `sources[]` array with: `url`, `title`, `publisher`, `source_type`, `evidence`
  - Add instruction: reject Reddit URLs in `sources[]`
  - Include example JSON schema in prompt

#### [x] S2-07: Update Output Schema with New Fields
- **Priority:** P0 | **Complexity:** Low | **Dependencies:** S2-01 through S2-06
- **File:** `Terminal_app/stage_2_factcheck.py`
- **Status:** COMPLETED
- **Notes:**
  - Add: `reddit_post_url`, `reddit_outbound_url`, `reddit_link_check`, `sources[]`, `perplexity_query`, `perplexity_search_url`
  - Keep `url` as alias of `reddit_post_url` for backward compatibility
  - Preserve existing `perplexity_citations` list

#### [x] S2-08: Implement Verification Acceptance Criteria
- **Priority:** P0 | **Complexity:** Medium | **Dependencies:** S2-02, S2-06
- **File:** `Terminal_app/stage_2_factcheck.py`
- **Status:** COMPLETED
- **Notes:**
  - Create `_validate_acceptance_criteria(item)` method
  - Verify: (a) `reddit_link_check.status` is ok/redirect, (b) at least one non-Reddit source, (c) substantive `perplexity_reason`
  - Downgrade failing items to `unverifiable`

---

### WS2: Stage 3 Trends Integration

#### S3-01: Create pytrends Feasibility Test Module
- **Priority:** P0 | **Complexity:** Medium | **Dependencies:** None
- **File:** `Terminal_app/utils/trends_feasibility_test.py` (new)
- **Notes:**
  - **MUST complete first** - gates all other Trends work
  - Test: (1) no CAPTCHA, (2) returns data for sample keywords, (3) completes <30s for 5 keywords
  - Return: `{feasible: bool, avg_latency_ms: int, error_type: str|null}`

#### S3-02: Implement GoogleTrendsClient Wrapper Class
- **Priority:** P0 | **Complexity:** Medium | **Dependencies:** S3-01 (must confirm feasibility)
- **File:** `Terminal_app/utils/trends_client.py` (new)
- **Notes:**
  - Wrap `pytrends.TrendReq` with config: `timeframe='now 7-d'`, `geo='US'`
  - Add circuit-breaker: after 3 consecutive failures, disable for session
  - Follow `PerplexityClient` pattern from `api_clients.py`

#### S3-07: Implement Graceful Fallback Logic
- **Priority:** P0 | **Complexity:** Medium | **Dependencies:** S3-05
- **File:** `Terminal_app/stage_3_trend_scoring.py`
- **Notes:**
  - Run feasibility probe at stage start
  - If fails, set `trends_enabled = False` and log warning
  - All items must still have `trends` object (even when disabled)

---

### WS3: LLM Prompt Improvements

#### [x] P-01: Create Shared Prompt Template System
- **Priority:** P0 | **Complexity:** Medium | **Dependencies:** None
- **File:** `Terminal_app/utils/prompt_templates.py` (new)
- **Status:** COMPLETED
- **Notes:**
  - `PromptTemplate` base class with `system_prompt`, `user_prompt`, `json_schema`
  - `PromptBuilder` class enforcing standard pattern
  - `render()` method returns `PromptResult(system, user)` with `.combined` and `.as_messages()` helpers
  - Stage-specific templates: `ValidationPromptTemplate`, `ViralityPromptTemplate`, `CurationPromptTemplate`, `SynthesisPromptTemplate`, `ImageGenerationPromptTemplate`
  - `TemplateRegistry` for lookup by stage number
  - `PromptTemplateMixin` for StageBase integration

#### P-02: Implement Strict JSON Output Contract Enforcement
- **Priority:** P0 | **Complexity:** Medium | **Dependencies:** P-01
- **File:** `Terminal_app/utils/stage_base.py`
- **Notes:**
  - Extend `JSONCleanupMixin` with `parse_with_retry(content, max_retries=1)`
  - Add `validate_json_schema(data, required_keys)` method
  - Include in all prompts: "Return ONLY valid JSON. Do not wrap in markdown code blocks."

#### [x] P-03: Refactor Stage 2 Prompts for Source Extraction
- **Priority:** P0 | **Complexity:** High | **Dependencies:** P-01, P-02
- **File:** `Terminal_app/stage_2_factcheck.py`
- **Status:** COMPLETED
- **Notes:**
  - Rewrite `build_validation_prompt()` to require `sources[]` array
  - Add system instruction: "Do NOT mark 'verified' if all citations are Reddit URLs"
  - Include `perplexity_query` and `perplexity_search_url` in schema

#### [x] P-04: Add Reddit-Only Citation Rejection Logic
- **Priority:** P0 | **Complexity:** Low | **Dependencies:** P-03
- **File:** `Terminal_app/stage_2_factcheck.py`
- **Status:** COMPLETED
- **Notes:**
  - Post-process check in `_merge_validation_results()` and `_validate_acceptance_criteria()`
  - Scan for `reddit.com`/`redd.it` domains using `is_reddit_url()` utility
  - Downgrade to `unverifiable` if no non-Reddit sources exist

---

### WS4: Source Propagation

#### [x] SP-01: Define Source Field Schema for Stage 2
- **Priority:** P0 | **Complexity:** Medium | **Dependencies:** None
- **File:** `Terminal_app/stage_2_factcheck.py`, `Terminal_app/utils/source_utils.py`
- **Status:** COMPLETED
- **Notes:**
  - Add: `reddit_post_url`, `reddit_outbound_url`, `sources[]`, `perplexity_search_url`
  - `sources[]` objects: `{url, title, publisher, published_at, source_type, evidence}`
  - Keep `url` as alias for backward compatibility
  - `StructuredSource` TypedDict defined in `source_utils.py`

#### SP-05: Propagate Source Fields Through Stage 5 + Update Prompt
- **Priority:** P0 | **Complexity:** Medium | **Dependencies:** SP-04
- **File:** `Terminal_app/stage_5_synthesis.py`
- **Notes:**
  - Update `_build_social_prompt()` to include `sources[]` data
  - Add "Sources" slide at carousel end (1-3 source domains)
  - Add caption suffix mentioning source domains

#### [x] SP-06: Add Sources Section to Stage 6 Markdown
- **Priority:** P0 | **Complexity:** Medium | **Dependencies:** SP-05
- **File:** `Terminal_app/stage_6_visuals.py`
- **Status:** COMPLETED
- **Notes:**
  - `_build_sources_section(item)` method creates structured Sources section
  - Lists up to 3 `sources[].url` with titles/publishers and source_type
  - Includes `perplexity_search_url` as "Validation" subsection
  - Includes `reddit_post_url` as "Discovery" subsection

---

### WS5: Design DNA Visual System

#### [x] D-01: Create Design DNA Configuration Module
- **Priority:** P0 | **Complexity:** Low | **Dependencies:** None
- **File:** `Terminal_app/utils/design_dna.py` (new)
- **Status:** COMPLETED
- **Notes:**
  - `VisualStyle` enum, `StyleDNA` and `CompositionSettings` frozen dataclasses
  - `AVOID_LIST` tuple with 19 items to exclude
  - Theme-to-accent color mapping

#### [x] D-02: Implement Story-to-Scene Summarization Helper
- **Priority:** P0 | **Complexity:** Medium | **Dependencies:** None
- **File:** `Terminal_app/utils/design_dna.py`
- **Status:** COMPLETED
- **Notes:**
  - `summarize_story_context(title, rationale, carousel_slides)` function
  - Extract core narrative from title, rationale, carousel slides
  - Produce 1-2 sentence summary for image prompt

#### [x] D-03: Rewrite Image Prompt Builder with Design DNA
- **Priority:** P0 | **Complexity:** Medium | **Dependencies:** D-01, D-02
- **File:** `Terminal_app/stage_6_visuals.py`, `Terminal_app/utils/design_dna.py`
- **Status:** COMPLETED
- **Notes:**
  - Replaced "2D flat-vector" prompt with Design DNA template
  - `DesignDNAPromptBuilder.build_prompt()` generates complete prompts
  - Target: "photorealistic editorial, cinematic lighting, professional color grade"

#### [x] D-04: Add Aspect Ratio to Image Generation
- **Priority:** P0 | **Complexity:** Low | **Dependencies:** D-03
- **File:** `Terminal_app/stage_6_visuals.py`
- **Status:** COMPLETED
- **Notes:**
  - `CompositionSettings` defines 4:5 portrait ratio (1080x1350)
  - `prompt_builder.get_dimensions()` returns target size
  - Framing section includes "portrait 4:5" prominently

---

## Phase 2: Quality & Integration (P1)

### WS1: Stage 2 Source Validation (continued)

#### [x] S2-04: Build Perplexity Search URL Generator
- **Priority:** P1 | **Complexity:** Low | **Dependencies:** None
- **File:** `Terminal_app/utils/source_utils.py`
- **Status:** COMPLETED
- **Notes:**
  - Create helper: `build_perplexity_search_url(query) -> str`
  - Store both `perplexity_query` and `perplexity_search_url`

#### [x] S2-05: Extract Reddit Outbound URL from Item
- **Priority:** P1 | **Complexity:** Low | **Dependencies:** None
- **File:** `Terminal_app/utils/source_utils.py`
- **Status:** COMPLETED
- **Notes:**
  - Parse Reddit post JSON to determine if link post vs self-post
  - Add `reddit_outbound_url` field (null for self-posts)

#### [x] S2-06: Implement Sources Deduplication
- **Priority:** P1 | **Complexity:** Medium | **Dependencies:** S2-03
- **File:** `Terminal_app/utils/source_utils.py`
- **Status:** COMPLETED
- **Notes:**
  - Create `deduplicate_sources(raw_citations, structured_sources)` function
  - Remove duplicates, filter Reddit domains, strip tracking params

#### S2-10: Write Unit Tests for Stage 2
- **Priority:** P1 | **Complexity:** Medium | **Dependencies:** S2-01 through S2-08
- **File:** `Terminal_app/tests/test_stage_2.py` (new)
- **Notes:**
  - Test link checker with mock responses
  - Test Perplexity prompt parsing with sample responses
  - Test acceptance criteria validation edge cases

---

### WS2: Stage 3 Trends Integration (continued)

#### S3-03: Implement Keyword Extraction Utility
- **Priority:** P1 | **Complexity:** Medium | **Dependencies:** None
- **File:** `Terminal_app/utils/trends_client.py`
- **Notes:**
  - Extract 1-3 keywords from title (strip stopwords, keep named entities)
  - Prefer primary entity names from `sources[]` if available
  - Never use full Reddit title as keyword

#### S3-04: Implement Momentum Score Calculation
- **Priority:** P1 | **Complexity:** Medium | **Dependencies:** S3-02
- **Notes:**
  - Compare last 2-day avg to first 2-day avg of 7-day window
  - Return: `{momentum_score: 0-100, confidence: high|medium|low, interest_summary: {...}}`

#### S3-05: Extend Stage 3 with Trends Integration
- **Priority:** P0 | **Complexity:** High | **Dependencies:** S3-02, S3-03, S3-04
- **File:** `Terminal_app/stage_3_trend_scoring.py`
- **Notes:**
  - Add `trends_client` and `trends_enabled` flag
  - After Gemini score: extract keywords, call Trends, calculate momentum
  - Store full `trends` object in output

#### S3-06: Implement Composite Scoring Formula
- **Priority:** P1 | **Complexity:** Low | **Dependencies:** S3-05
- **Notes:**
  - If Trends enabled AND confidence != low: `final_score = 0.70 * virality + 0.30 * momentum`
  - Otherwise: `final_score = virality_score`
  - Sort by `final_score` descending

#### S3-10: Create Integration Tests for Trends
- **Priority:** P1 | **Complexity:** Medium | **Dependencies:** All S3 tasks
- **File:** `Terminal_app/tests/test_stage_3_trends.py` (new)
- **Notes:**
  - Test keyword extraction, momentum calculation, composite scoring
  - Mock pytrends to avoid network calls
  - Test graceful fallback scenarios

---

### WS3: LLM Prompt Improvements (continued)

#### P-05: Refactor Stage 3 Prompts for Stable JSON
- **Priority:** P1 | **Complexity:** Medium | **Dependencies:** P-01, P-02
- **File:** `Terminal_app/stage_3_trend_scoring.py`
- **Notes:**
  - Require `virality_score`, `reasoning` (2-3 concrete sentences), `final_score`
  - Add: "Reasoning MUST reference specific elements from title/content"

#### P-06: Refactor Stage 4 Prompts for Editorial Diversity
- **Priority:** P1 | **Complexity:** Medium | **Dependencies:** P-01, P-02
- **File:** `Terminal_app/stage_4_curation.py`
- **Notes:**
  - Add diversity constraint: avoid multiple stories on same topic
  - `rationale` must reference source domains when available
  - Pass `sources[]` to GPT for citation

#### P-07: Refactor Stage 5 to Use Real System Prompt
- **Priority:** P1 | **Complexity:** Low | **Dependencies:** P-01
- **File:** `Terminal_app/stage_5_synthesis.py`
- **Notes:**
  - Use Anthropic API's `system` parameter instead of embedding in user message
  - Extract role definition into separate system prompt constant

#### P-08: Add Sources Slide/Caption Suffix to Stage 5
- **Priority:** P1 | **Complexity:** Medium | **Dependencies:** P-07
- **File:** `Terminal_app/stage_5_synthesis.py`
- **Notes:**
  - Pass `sources[]` data to prompt
  - Require "Sources" final slide in carousel
  - Require "Sources:" suffix in instagram_caption

#### [x] P-09: Implement Design DNA Template for Stage 6
- **Priority:** P1 | **Complexity:** Medium | **Dependencies:** P-01
- **File:** `Terminal_app/stage_6_visuals.py`, `Terminal_app/utils/design_dna.py`
- **Status:** COMPLETED
- **Notes:**
  - Replaced "2D flat-vector infographic" with Design DNA template
  - Template sections: story context, scene brief, style DNA, framing, avoid list
  - `DesignDNAPromptBuilder` class handles template construction

#### [x] P-10: Add Explicit Avoid List to Stage 6
- **Priority:** P1 | **Complexity:** Low | **Dependencies:** P-09
- **File:** `Terminal_app/utils/design_dna.py`
- **Status:** COMPLETED
- **Notes:**
  - `AVOID_LIST` tuple with 19 items including cartoon, flat vector, isometric, etc.
  - Configurable via `DesignDNAPromptBuilder.avoid_list` field

#### P-13: Propagate Source Fields Through Stages 3-6
- **Priority:** P1 | **Complexity:** Low | **Dependencies:** P-03
- **File:** All stage files
- **Notes:**
  - Preserve: `reddit_post_url`, `reddit_outbound_url`, `sources`, `perplexity_search_url`, `perplexity_citations`
  - Add `PROPAGATE_FIELDS` constant and utility method

---

### WS4: Source Propagation (continued)

#### SP-03: Propagate Source Fields Through Stage 3
- **Priority:** P1 | **Complexity:** Low | **Dependencies:** SP-01
- **File:** `Terminal_app/stage_3_trend_scoring.py`
- **Notes:**
  - Verify new fields preserved in `process()` loop
  - No changes needed if existing `.copy()` pattern works

#### SP-04: Propagate Source Fields Through Stage 4
- **Priority:** P1 | **Complexity:** Low | **Dependencies:** SP-03
- **File:** `Terminal_app/stage_4_curation.py`
- **Notes:**
  - Update `_build_candidate_prompt()` to optionally include source domains
  - Verify `rationale` references sources when available

#### SP-07: Distinguish URL Fields in Stage 1
- **Priority:** P1 | **Complexity:** Low | **Dependencies:** None
- **File:** `Terminal_app/stage_1_ingestion.py` (lines 110-118)
- **Notes:**
  - Set `reddit_post_url = url`
  - Keep `url` as alias
  - Add `reddit_outbound_url: null` placeholder

#### SP-08: Create Domain Extraction Helper
- **Priority:** P2 | **Complexity:** Low | **Dependencies:** None
- **File:** `Terminal_app/utils/` (new)
- **Notes:**
  - Extract clean domain from URL (e.g., `techcrunch.com`)
  - Strip tracking params, handle `www.` prefixes
  - Used by Stages 5 and 6 for human-readable sources

#### SP-10: Write Integration Tests for Propagation
- **Priority:** P1 | **Complexity:** Medium | **Dependencies:** SP-01 through SP-06
- **File:** `Terminal_app/tests/test_source_propagation.py` (new)
- **Notes:**
  - Test fixtures with all new source fields
  - Verify fields preserved through all stages
  - Verify markdown output contains Sources section

---

### WS5: Design DNA (continued)

#### [x] D-05: Create Scene Brief Inference Logic
- **Priority:** P1 | **Complexity:** Medium | **Dependencies:** D-02
- **File:** `Terminal_app/utils/design_dna.py`
- **Status:** COMPLETED
- **Notes:**
  - `infer_scene_elements(title, rationale, carousel_text) -> SceneElements`
  - Keyword-based mapping for subject, setting, emotion
  - `SceneElements` dataclass with subject, setting, emotion, action fields

#### [x] D-06: Implement Prompt Template Manager Class
- **Priority:** P1 | **Complexity:** Medium | **Dependencies:** D-01, D-03, D-05
- **File:** `Terminal_app/utils/design_dna.py`
- **Status:** COMPLETED
- **Notes:**
  - `DesignDNAPromptBuilder` dataclass for prompt construction
  - Methods: `build_prompt()`, `get_avoid_list_string()`, `get_aspect_ratio()`, `get_dimensions()`
  - Allows A/B testing via configurable `style`, `composition`, `avoid_list` fields

#### [x] D-07: Add Negative Space Guidance
- **Priority:** P1 | **Complexity:** Low | **Dependencies:** D-03
- **File:** `Terminal_app/utils/design_dna.py`
- **Status:** COMPLETED
- **Notes:**
  - `include_negative_space` flag in DesignDNAPromptBuilder
  - Framing section: "negative space in upper third and lower third for text overlay"
  - Critical for Instagram usability

#### D-08: Implement Visual Acceptance Validator
- **Priority:** P1 | **Complexity:** High | **Dependencies:** D-03, D-04
- **File:** `Terminal_app/stage_6_visuals.py`
- **Notes:**
  - Post-generation check against acceptance criteria
  - Use Gemini Vision to analyze generated image
  - Log validation results in manifest entry

#### D-09: Create Visual Quality Testing Harness
- **Priority:** P1 | **Complexity:** Medium | **Dependencies:** D-03, D-08
- **File:** `Terminal_app/tests/test_visual_quality.py` (new)
- **Notes:**
  - Process 3-5 sample stories
  - Output prompts, images, validation scores
  - Store for visual inspection

---

## Phase 3: Polish & Maintainability (P2)

### Cross-Cutting

#### X-01: Add Schema Version to All Stage Outputs
- **Priority:** P2 | **Complexity:** Low | **Dependencies:** None
- **File:** `Terminal_app/utils/stage_base.py`
- **Notes:**
  - Add `schema_version: "2.0"` to output JSON
  - Enables downstream migration handling
  - Each stage defines `SCHEMA_VERSION` class attribute

#### X-02: Add Debug Mode for Prompt Storage
- **Priority:** P2 | **Complexity:** Low | **Dependencies:** P-01
- **File:** `Terminal_app/utils/stage_base.py`
- **Notes:**
  - Optional `debug_mode` flag stores prompts in output under `_debug_prompts`
  - Helps debug LLM behavior without code inspection

---

### WS2: Stage 3 (continued)

#### S3-08: Update Output Schema and Documentation
- **Priority:** P2 | **Complexity:** Low | **Dependencies:** S3-05, S3-06, S3-07
- **Notes:**
  - Update docstrings for new fields
  - Ensure `3_ranked_trends.json` includes all new fields
  - Add `schema_version` field

#### S3-09: Add Configuration for Trends Parameters
- **Priority:** P2 | **Complexity:** Low | **Dependencies:** S3-05
- **Notes:**
  - Add class constants: `TRENDS_TIMEFRAME`, `TRENDS_GEO`, `TRENDS_WEIGHT`
  - Consider env var `TRENDS_ENABLED=false` to force disable

---

### WS5: Design DNA (continued)

#### D-10: Add Debug Mode for Prompt Logging
- **Priority:** P2 | **Complexity:** Low | **Dependencies:** D-03
- **Notes:**
  - Store `image_prompt` in manifest entry when debug enabled
  - Use env var `DEBUG_PROMPTS=1`

#### D-11: Implement Accent Color Selection
- **Priority:** P2 | **Complexity:** Medium | **Dependencies:** D-01, D-05
- **Notes:**
  - Map story themes to accent colors (AI=blue, biotech=green, controversy=amber)
  - Include in prompt: "neutral tones with {accent_color} accent"

#### D-12: Update Markdown to Note Visual Style
- **Priority:** P2 | **Complexity:** Low | **Dependencies:** D-03
- **Notes:**
  - Add "Visual Style" section documenting Design DNA
  - Include generated prompt if debug mode

#### D-13: Create Prompt Template Version Control
- **Priority:** P2 | **Complexity:** Low | **Dependencies:** D-06
- **Notes:**
  - Add `prompt_template_version` field (e.g., "v1.0")
  - Include in manifest for traceability

---

### WS3: LLM Prompts (continued)

#### P-11: Add Schema Version to Stage Outputs
- **Priority:** P2 | **Complexity:** Low | **Dependencies:** None
- **Notes:**
  - (Merged with X-01)

#### P-12: Add Debug Mode for Prompt Storage
- **Priority:** P2 | **Complexity:** Low | **Dependencies:** P-01
- **Notes:**
  - (Merged with X-02)

#### P-14: Add Sources Section to Markdown Export
- **Priority:** P2 | **Complexity:** Low | **Dependencies:** P-13
- **Notes:**
  - (Merged with SP-06)

---

## Implementation Order

### Recommended Sequence

```
Week 1: Foundation (P0)
├── WS3: P-01, P-02 (Prompt template system - enables all other prompt work)
├── WS1: S2-01, S2-03 (Link checker + prompt rewrite - can parallelize)
├── WS5: D-01, D-02 (Design DNA config + summarizer)
└── WS2: S3-01 (Feasibility test - gates all Trends work)

Week 2: Core Implementation (P0 continued)
├── WS1: S2-02, S2-07, S2-08 (Integration + schema + acceptance)
├── WS3: P-03, P-04 (Stage 2 prompt finalization)
├── WS5: D-03, D-04 (Prompt rewrite + aspect ratio)
└── WS4: SP-01, SP-05, SP-06 (Source propagation core)

Week 3: Integration (P1)
├── WS2: S3-02 through S3-07 (Trends integration - if feasible)
├── WS3: P-05 through P-10 (All remaining prompt refactors)
├── WS4: SP-03, SP-04, SP-07 (Remaining propagation)
└── WS5: D-05, D-06, D-07, D-08 (Quality infrastructure)

Week 4: Testing & Polish (P1/P2)
├── All test tasks: S2-10, S3-10, SP-10, D-09
├── Cross-cutting: X-01, X-02
└── Remaining P2 tasks
```

---

## Dependency Graph (Critical Path)

```
P-01 (Prompt Templates) ────┬──> P-02 (JSON Contract) ──> P-03 (Stage 2 Prompt) ──> P-04 (Rejection)
                            │
                            └──> All other prompt tasks (P-05 through P-10)

S2-01 (Link Checker) ──> S2-02 (Integration) ──> S2-07 (Schema) ──> S2-08 (Acceptance)
                                                       │
                                                       └──> SP-01 (Source Schema) ──> SP-03/04/05/06

D-01 (Config) ──┬──> D-03 (Prompt Rewrite) ──> D-04 (Aspect Ratio)
                │
D-02 (Summary) ─┘

S3-01 (Feasibility) ──> S3-02 (Client) ──> S3-05 (Integration) ──> S3-06/07 (Scoring/Fallback)
```

---

## Files Changed Summary

| File | Workstreams | Change Type |
|------|-------------|-------------|
| `utils/prompt_templates.py` | WS3 | New |
| `utils/design_dna.py` | WS5 | New |
| `utils/reddit_link_checker.py` | WS1 | New |
| `utils/trends_client.py` | WS2 | New |
| `utils/trends_feasibility_test.py` | WS2 | New |
| `utils/stage_base.py` | WS3, X | Modify |
| `utils/json_utils.py` | WS3 | Modify |
| `stage_1_ingestion.py` | WS4 | Modify |
| `stage_2_factcheck.py` | WS1, WS3, WS4 | Heavy Modify |
| `stage_3_trend_scoring.py` | WS2, WS3, WS4 | Heavy Modify |
| `stage_4_curation.py` | WS3, WS4 | Modify |
| `stage_5_synthesis.py` | WS3, WS4 | Modify |
| `stage_6_visuals.py` | WS3, WS4, WS5 | Heavy Modify |
| `tests/*` | All | New |

---

## Risk Considerations

1. **pytrends Reliability (WS2):** Google Trends can rate-limit or require CAPTCHAs. S3-01 feasibility check is critical - if it fails, skip all Trends work.

2. **LLM Output Stability (WS3):** Prompt changes may cause unexpected output format changes. Test each prompt change in isolation before deploying.

3. **Backward Compatibility (WS4):** Existing tools may depend on current schema. Keep `url` as alias, preserve `perplexity_citations`, add `schema_version` for migration detection.

4. **Image Generation Quality (WS5):** Design DNA prompt changes are subjective. Create visual testing harness early (D-09) to validate output quality.

5. **Testing Debt:** Current test coverage is 0/10. Prioritize test tasks to establish testing patterns for future work.

---

## Success Criteria

- [ ] Stage 2 outputs contain `sources[]` with non-Reddit citations for verified items
- [ ] Stage 2 validates Reddit post existence before marking verified
- [ ] Stage 3 includes Google Trends momentum (when feasible) in composite score
- [ ] All LLM prompts use system/user separation with JSON contracts
- [ ] Sources propagate through all stages to final markdown export
- [ ] Generated images are photorealistic editorial style, not cartoon/vector
- [ ] All stages include `schema_version` in output
- [ ] Test coverage exists for critical paths

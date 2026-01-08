# Reddit News Pipeline - Architectural Review

**Project:** TrendFlow / Reddit News Pipeline
**Review Date:** January 7, 2026
**Reviewers:** Automated Analysis (3-Agent Parallel Review)

---

## Executive Summary

The Reddit News Pipeline is a **6-stage state-machine data processing pipeline** that transforms raw Reddit RSS feeds into curated, multi-channel social media content with AI-generated visuals. The architecture emphasizes modularity, cost-efficiency, and checkpoint-based processing.

### Overall Assessment: 6.5/10 - Solid Foundation, Needs Hardening

| Category | Score | Status |
|----------|-------|--------|
| Architecture Design | 8/10 | Well-designed stage pipeline |
| Code Organization | 7/10 | Good structure, repetitive patterns |
| Error Handling | 6/10 | Catches errors, lacks retry logic |
| Logging & Observability | 7/10 | Good coverage, missing metrics |
| Testing | 0/10 | **CRITICAL** - No tests |
| Security | 5/10 | Weak API key handling |
| Performance | 6/10 | Synchronous, fixed delays |
| Documentation | 6/10 | Good high-level, sparse low-level |
| Best Practices | 7/10 | Mostly good, inconsistent |

**Verdict:** The pipeline is **architecturally sound** and demonstrates good separation of concerns. However, it requires significant hardening before production use, particularly in testing, security, and error handling.

---

## 1. Project Purpose & Goals

### What It Does

The pipeline automatically discovers, validates, curates, and synthesizes trending Reddit news into ready-to-publish social media content:

1. **Extract** viral news from 70+ AI/tech subreddits via RSS
2. **Validate** factual accuracy using AI fact-checking (Perplexity)
3. **Score** virality potential using trend analysis (Gemini)
4. **Curate** top 5 stories with strategic rationale (OpenAI GPT-5.2)
5. **Generate** social media content with A/B variations (Claude Sonnet 4.5)
6. **Create** visual assets - hero images/infographics (Gemini Pro Image)

### Target Platforms
- X/Twitter (280-char posts with A/B testing)
- Instagram (carousels + captions with hashtags)
- Threads (cross-platform posts)

---

## 2. Architecture Overview

### Pipeline Data Flow

```
Reddit RSS (70+ subreddits)
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│ STAGE 1: INGESTION (Free)                                     │
│ • Parse subreddit config from markdown                        │
│ • Fetch RSS feeds with rate limiting (2s delay)               │
│ • Filter posts: 24-72h time window                            │
│ Output: 1_raw_feed.json (~50-100 items)                       │
└───────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│ STAGE 2: FACT-CHECK (Perplexity API - sonar model)            │
│ • Batch validation (5 items/batch)                            │
│ • Status: verified | debunked | unverifiable                  │
│ • Keep only "verified" items                                  │
│ Output: 2_validated_facts.json (~15-30 items)                 │
└───────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│ STAGE 3: TREND SCORING (Gemini 3.0 Flash + Thinking)          │
│ • Per-item virality analysis (0-100 score)                    │
│ • Factors: hook strength, emotional engagement, appeal        │
│ • Sort descending by score                                    │
│ Output: 3_ranked_trends.json (~15-30 items, sorted)           │
└───────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│ STAGE 4: CURATION (OpenAI GPT-5.2)                            │
│ • Select exactly top 5 from top 10 candidates                 │
│ • Generate rationale for each selection                       │
│ Output: 4_curated_top5.json (5 items)                         │
└───────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│ STAGE 5: CONTENT SYNTHESIS (Claude Sonnet 4.5)                │
│ • Generate A/B post variations (2 tones per story)            │
│ • Create 5-7 slide carousels (Hook → Narrative → CTA)         │
│ • Write Instagram captions with hashtags                      │
│ Output: 5_social_drafts.json (5 items with social_drafts)     │
└───────────────────────────────────────────────────────────────┘
        │
        ▼
┌───────────────────────────────────────────────────────────────┐
│ STAGE 6: VISUAL ASSETS (Gemini 3.0 Pro Image)                 │
│ • Generate 2D flat-vector infographic hero images             │
│ • Export markdown files per story                             │
│ • Create session folder with README index                     │
│ Output: 6_manifest.json + session_YYYYMMDD_HHMMSS/            │
│         • 5 markdown files                                    │
│         • 5 PNG hero images                                   │
└───────────────────────────────────────────────────────────────┘
```

### Key Architectural Decisions

| Decision | Rationale | Assessment |
|----------|-----------|------------|
| JSON checkpoint system | Enables stage isolation, debugging, cost control | **Excellent** |
| Multi-model orchestration | Right model for each task (cost vs capability) | **Good** |
| Sequential stage execution | Simplifies orchestration, reduces complexity | **Acceptable** |
| File-based state | No database needed, easy versioning | **Good for scale** |
| Markdown output format | Human-readable, CMS-compatible | **Excellent** |

---

## 3. Is This a Good Pipeline?

### Strengths

1. **Modular Stage Design**
   - Each stage is independently executable (`--stage N`)
   - Clear input/output contracts via JSON
   - Easy to debug individual stages without re-running entire pipeline

2. **Cost-Conscious Architecture**
   - Stage 1 is free (RSS scraping)
   - Cheapest models used where possible (Perplexity sonar, Gemini Flash)
   - User can stop after any stage to review before expensive operations

3. **Factuality Filter**
   - Stage 2 removes rumors/hallucinations before downstream processing
   - Reduces wasted API calls on unreliable content

4. **Content Quality**
   - A/B testing variations for posts
   - Multiple tonal options (informative vs provocative)
   - Professional carousel structure (Hook → Value → CTA)

5. **Graceful Degradation**
   - Stages continue processing even if individual items fail
   - Fallback to deterministic selection if AI curation fails

### Weaknesses

1. **No Testing** (Critical)
   - Zero test files in repository
   - No regression protection
   - High risk of silent failures

2. **No Retry Logic**
   - API failures immediately mark items as errors
   - No exponential backoff for rate limits
   - Transient failures not recovered

3. **Security Gaps**
   - API keys loaded without validation
   - No input sanitization for URLs/titles
   - Potential for injection via malicious Reddit post titles

4. **Performance Bottlenecks**
   - Synchronous processing with fixed delays
   - No concurrent API calls
   - Full JSON serialization between stages

---

## 4. Detailed Component Analysis

### Stage 1: Ingestion

**File:** `Terminal_app/stage_1_ingestion.py`

**What It Does Well:**
- Time window filtering (24-72h) prevents stale/future content
- Rate limiting (2s delay) respects Reddit API
- Graceful handling of malformed RSS feeds

**Issues:**
- No caching of RSS responses
- Missing validation of extracted URLs
- Regex for subreddit extraction is brittle:
  ```python
  matches = re.findall(r'r/([A-Za-z0-9_]+)', line)
  ```
  Could match false positives like "user_r/stuff"

**Recommendation:** Add URL validation and improve subreddit regex.

---

### Stage 2: Fact-Check

**File:** `Terminal_app/stage_2_factcheck.py`

**What It Does Well:**
- Batch processing (5 items) for API efficiency
- Low temperature (0.1) for deterministic validation
- Structured output with citations

**Issues:**
- No retry for API failures:
  ```python
  if response.status_code != 200:
      # All items in batch marked as 'api_error'
      for item in items:
          item['validation_status'] = 'api_error'
  ```
- No differentiation between 429 (rate limit) vs 401 (auth) errors
- JSON parse failures store raw error instead of recovering

**Recommendation:** Add retry logic with exponential backoff for 429/503 errors.

---

### Stage 3: Trend Scoring

**File:** `Terminal_app/stage_3_trend_scoring.py`

**What It Does Well:**
- Uses Gemini's thinking mode for deeper analysis
- Clear scoring criteria (hook, emotion, appeal)
- Maintains sort order for downstream stages

**Issues:**
- Per-item API calls (no batching) - expensive for large feeds
- Magic number `thinking_budget = 1024` without explanation
- No caching of identical title scores

**Recommendation:** Consider batching similar items or caching results.

---

### Stage 4: Curation

**File:** `Terminal_app/stage_4_curation.py`

**What It Does Well:**
- Takes safety buffer (top 10 → select 5)
- Generates strategic rationale for selections
- Falls back to score-based selection on failure

**Issues:**
- Single point of failure (one API call for all curation)
- No validation that returned indices match input items
- Hardcoded "top 5" - should be configurable

**Recommendation:** Add validation of AI response and make count configurable.

---

### Stage 5: Content Synthesis

**File:** `Terminal_app/stage_5_synthesis.py`

**What It Does Well:**
- A/B testing with tonal descriptions
- Structured carousel format with narrative arc
- Platform-specific optimization (X char limits, IG hashtags)

**Issues:**
- Inconsistent JSON cleanup vs other stages:
  ```python
  # Uses regex in stage 5
  match = re.search(r'```json(.*?)```', content, re.DOTALL)
  # vs simple replace in other stages
  clean_content = content.replace("```json", "").replace("```", "").strip()
  ```
- No validation of character counts (X posts should be <280)
- Emoji usage not controlled

**Recommendation:** Extract JSON cleanup to shared utility, add post-validation.

---

### Stage 6: Visual Generation

**File:** `Terminal_app/stage_6_visuals.py`

**What It Does Well:**
- Dual output paths (session folder + flat assets)
- Session index README for navigation
- `sanitize_filename()` helper for safe filenames

**Issues:**
- Import inside function (`import shutil`) - should be at top
- No fallback if image generation fails (story still created without image)
- Hardcoded image style prompt - should be configurable

**Recommendation:** Move imports to top, add configurable image style.

---

## 5. Code Quality Issues

### Critical: No Tests (Score: 0/10)

The repository contains **zero test files**. This is the highest priority issue.

**Missing Test Coverage:**
- Unit tests for JSON parsing
- Unit tests for regex-based config loading
- Integration tests for stage chaining
- Mock API tests for each external service

**Recommended Test Structure:**
```
tests/
├── unit/
│   ├── test_config_loader.py
│   ├── test_json_parsing.py
│   └── test_sanitize_filename.py
├── integration/
│   ├── test_stage_1.py
│   ├── test_stage_2.py
│   └── test_full_pipeline.py
└── fixtures/
    ├── sample_raw_feed.json
    └── mock_api_responses/
```

---

### Security Issues (Score: 5/10)

1. **API Key Management**
   ```python
   api_key = os.getenv("PERPLEXITY_API_KEY")  # No validation
   ```
   - No format validation
   - Could log keys in error messages
   - Both `.env` and `projects.env` exist (confusing)

2. **Input Validation Missing**
   ```python
   item = {
       "id": entry.id,      # No validation
       "url": entry.link,   # No URL validation
       "title": entry.title, # No length/content validation
   }
   ```

3. **Potential XSS Vector**
   - Reddit post titles passed directly to social media output
   - Malicious titles could contain injection payloads

**Recommendations:**
- Add pydantic models for input validation
- Mask API keys in logs
- Sanitize all user-generated content before output

---

### Error Handling (Score: 6/10)

**Pattern Found Across All Stages:**
```python
try:
    # API call
except Exception as e:
    logger.error(f"Error: {e}")
    # Continue with degraded state
```

**Issues:**
- Bare `except Exception` catches too much
- No distinction between recoverable and fatal errors
- No retry mechanism for transient failures

**Recommended Pattern:**
```python
from tenacity import retry, stop_after_attempt, wait_exponential

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def call_api_with_retry(payload):
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()
```

---

### Code Duplication (Score: 6/10)

**Repeated Patterns:**

1. **Stage initialization** (appears 6 times):
   ```python
   if not os.path.exists(input_file):
       logger.error(f"Input file not found: {input_file}")
       return
   ```

2. **JSON loading/saving** (appears in all stages):
   ```python
   with open(input_file, 'r', encoding='utf-8') as f:
       items = json.load(f)
   ```

3. **LLM response cleanup** (appears 4 times with variations):
   ```python
   clean_content = content.replace("```json", "").replace("```", "").strip()
   ```

**Recommendation:** Create base class or utility module:
```python
# utils/stage_base.py
class StageBase:
    def load_input(self, path: str) -> List[Dict]:
        ...

    def save_output(self, data: List[Dict], path: str):
        ...

    def clean_llm_json(self, content: str) -> Dict:
        ...
```

---

## 6. Performance Analysis

### Current Performance Profile

| Stage | Blocking Factor | Estimated Time (50 items) |
|-------|-----------------|---------------------------|
| 1 | Network I/O + 2s delays | ~2-3 minutes |
| 2 | API calls (10 batches × 1s) | ~30-60 seconds |
| 3 | API calls (15-30 items × 1s) | ~30-60 seconds |
| 4 | Single API call | ~5-10 seconds |
| 5 | API calls (5 items × 1s) | ~15-30 seconds |
| 6 | Image gen (5 items × 2s) | ~30-60 seconds |
| **Total** | | **~5-8 minutes** |

### Bottlenecks

1. **Synchronous Processing**
   - All API calls are blocking
   - Fixed sleep delays even when API is fast

2. **No Parallelism**
   - Could batch RSS fetches in parallel
   - Could run fact-check batches concurrently

3. **Full Serialization**
   - Each stage writes full JSON to disk
   - No streaming or incremental processing

### Optimization Opportunities

1. **Async I/O** for RSS fetching (Stage 1)
2. **Concurrent API calls** with semaphore for rate limiting
3. **Adaptive delays** based on API response headers
4. **Streaming JSON** for large datasets

---

## 7. Recommendations

### Immediate (Critical)

| Priority | Issue | Action |
|----------|-------|--------|
| P0 | No tests | Add pytest with 80%+ coverage target |
| P0 | API key security | Add validation, masking, single source |
| P1 | No retry logic | Add tenacity for exponential backoff |

### Short-term (High Value)

| Priority | Issue | Action |
|----------|-------|--------|
| P1 | Code duplication | Extract StageBase class |
| P1 | Input validation | Add pydantic models for JSON schemas |
| P2 | Documentation | Add docstrings to all public functions |

### Medium-term (Improvements)

| Priority | Issue | Action |
|----------|-------|--------|
| P2 | Performance | Add async support for I/O-bound stages |
| P2 | Observability | Add metrics (API latency, token usage) |
| P3 | Configuration | Move magic numbers to config file |

---

## 8. Proposed Refactored Structure

```
redditnews/
├── src/
│   ├── __init__.py
│   ├── config/
│   │   ├── __init__.py
│   │   ├── settings.py          # Pydantic settings model
│   │   └── subreddits.py        # Subreddit config loader
│   ├── stages/
│   │   ├── __init__.py
│   │   ├── base.py              # StageBase class
│   │   ├── ingestion.py
│   │   ├── factcheck.py
│   │   ├── scoring.py
│   │   ├── curation.py
│   │   ├── synthesis.py
│   │   └── visuals.py
│   ├── clients/
│   │   ├── __init__.py
│   │   ├── perplexity.py        # Perplexity API client
│   │   ├── gemini.py            # Google Gemini client
│   │   ├── openai_client.py     # OpenAI client
│   │   └── anthropic_client.py  # Anthropic client
│   ├── models/
│   │   ├── __init__.py
│   │   ├── feed_item.py         # Pydantic models for data
│   │   └── social_content.py
│   └── utils/
│       ├── __init__.py
│       ├── json_utils.py        # JSON parsing utilities
│       ├── file_utils.py        # File I/O utilities
│       └── retry.py             # Retry decorators
├── tests/
│   ├── __init__.py
│   ├── unit/
│   ├── integration/
│   └── fixtures/
├── cli.py                       # CLI entry point
├── pyproject.toml               # Project config + dependencies
└── .env.example                 # Environment template
```

---

## 9. Summary

### The Good

- **Well-designed 6-stage architecture** with clear separation of concerns
- **Cost-conscious model selection** (right tool for each job)
- **Checkpoint system** enables debugging and cost control
- **Graceful degradation** keeps pipeline running on partial failures
- **High-quality output format** (markdown + images)

### The Bad

- **Zero test coverage** - critical risk for production use
- **Weak security** - API keys and input validation need work
- **No retry logic** - transient failures not recovered
- **Code duplication** - repeated patterns across stages

### The Verdict

This is a **well-architected pipeline** that demonstrates good software design principles. The stage-based approach with JSON checkpoints is particularly elegant for this use case.

However, it is **not production-ready** without:
1. Comprehensive test suite
2. Proper error handling with retries
3. Security hardening
4. Input validation

**Recommendation:** Invest 2-3 focused sessions on testing and security before deploying to any automated/scheduled execution.

---

## Appendix A: File Reference

| File | Purpose | LOC |
|------|---------|-----|
| `Terminal_app/run.py` | Orchestration | ~200 |
| `Terminal_app/stage_1_ingestion.py` | RSS fetching | ~120 |
| `Terminal_app/stage_2_factcheck.py` | Perplexity validation | ~130 |
| `Terminal_app/stage_3_trend_scoring.py` | Gemini scoring | ~100 |
| `Terminal_app/stage_4_curation.py` | GPT curation | ~100 |
| `Terminal_app/stage_5_synthesis.py` | Claude synthesis | ~110 |
| `Terminal_app/stage_6_visuals.py` | Image gen + export | ~220 |
| `Terminal_app/utils/config_loader.py` | Subreddit parser | ~30 |

## Appendix B: API Dependencies

| Service | Model | Stage | Cost Tier |
|---------|-------|-------|-----------|
| Reddit RSS | N/A | 1 | Free |
| Perplexity | sonar | 2 | Low |
| Google Gemini | 3.0 Flash | 3 | Medium |
| OpenAI | GPT-5.2 | 4 | Medium-High |
| Anthropic | Claude Sonnet 4.5 | 5 | Medium |
| Google Gemini | 3.0 Pro Image | 6 | High |

## Appendix C: Environment Variables

```bash
# Required
PERPLEXITY_API_KEY=pplx-...
GOOGLE_AI_API_KEY=AIzaSy...
OPENAI_API_KEY=sk-proj-...
ANTHROPIC_API_KEY=sk-ant-...

# Optional
YOUTUBE_API_KEY=AIzaSy...  # For future video integration
```

---

*Review generated by 3-agent parallel analysis system*

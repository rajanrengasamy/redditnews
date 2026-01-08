# Project Request: "TrendFlow" - Modular Viral News Synthesis Engine

**Core Philosophy:**
Build a Python-based CLI application that functions as a **state-machine pipeline**. To strictly conserve API credits and allow for debugging, the application must **NOT** run end-to-end by default. Instead, it must execute in discrete stages, where each stage generates a structured JSON artifact. This artifact serves as the immutable input for the next stage.

**Project Structure & Inputs:**
- **Root Directory:** `antiGravity-projects/redditnews/`
- **Source Config:** `docs/subreditlist.md` (or `docs/subreditlist-revised.md` if available).
  - *Note:* The file schema is `## Category` followed by `- r/Subreddit` or `- https://...`.
- **Environment:** `projects.env` (Contains API keys for Perplexity, OpenAI, Anthropic, Google).

## Architectural Requirement: The "Checkpoint" System
The application must accept a CLI argument to determine its entry point.
*Example Usage:* `python run.py --stage [stage_name] --input [path_to_previous_json]`

## The Pipeline Stages

### Stage 1: Ingestion (Free/Low Cost)
- **Input:** `docs/subreditlist.md`
- **Logic:** Parse RSS feeds (handle both reddit.com/r/... and raw RSS URLs).
- **Filter:** Strictly strictly **24h - 72h** window.
- **Output:** `output/1_raw_feed.json`
  - *Schema:* `[{ "id": "uuid", "url": "...", "title": "...", "published_at": "...", "category": "..." }]`

### Stage 2: Fact-Check & Validation (Agent: Perplexity)
- **Input:** `output/1_raw_feed.json`
- **Logic:** Query **Perplexity.ai** to verify factual accuracy. Remove hallucinations/rumors.
- **Output:** `output/2_validated_facts.json`
  - *Schema:* Adds `"validation_status": "verified/debunked"`, `"perplexity_citations": [...]`

### Stage 3: Trend Scoring (Agent: Gemini Flash 3.0 + Google Trends)
- **Input:** `output/2_validated_facts.json`
- **Logic:**
  1. Use **Gemini Flash 3.0** to analyze "Virality Potential" (capitalization, hooks).
  2. Cross-reference keywords with **Google Trends** API for search volume momentum.
- **Output:** `output/3_ranked_trends.json`
  - *Schema:* Adds `"virality_score": 0-100`, `"trend_metrics": {...}`. *Sorted by score.*

### Stage 4: Strategic Curation (Agent: "GPT 5.2 Thinking")
- **Input:** `output/3_ranked_trends.json`
- **Logic:** Act as a "Rationale Engine." Select strictly the **Top 5** stories.
- **Output:** `output/4_curated_top5.json`
  - *Schema:* Top 5 items with `"rationale": "Why this will go viral..."`

### Stage 5: Content Synthesis (Agent: "Claude Sonnet 4.5")
- **Input:** `output/4_curated_top5.json`
- **Logic:** Generate social copy for **X (Twitter), Threads, and Instagram**.
- **Variations Required per Story:**
  1. Single Post (Punchy)
  2. Carousel (5-7 slides narrative)
  3. A/B Testing (Two distinct tonal options for each)
- **Output:** `output/5_social_drafts.json`

### Stage 6: Visual Asset Generation (Agent: Gemini 3.0 Nano Pro)
- **Input:** `output/5_social_drafts.json`
- **Logic:** Read the carousel text/hooks and generate professional infographics adhering to a specific style guide.
- **Output:** `output/6_final_assets/` (Folder containing images) & `output/6_manifest.json`

## Immediate Deliverable
Generate the `main.py` orchestration script that implements this `argparse` logic for stage selection and JSON file handling. Ensure the script can parse the Markdown list format correctly.

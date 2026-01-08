# Reddit News Pipeline Task List

## Phase 0: Project Initialization & Setup
- [x] Create `Terminal_app/` directory and structure <!-- id: 0 -->
- [x] Create `Terminal_app/run.py` entry point (State Machine Skeleton) <!-- id: 1 -->
- [x] Create `Terminal_app/projects.env` (or configure `.env` loading) <!-- id: 2 -->
- [x] Implement Logging & Error Handling <!-- id: 3 -->
- [x] Create utility for loading `docs/subreditlist.md` and extracting subreddits <!-- id: 4 -->

## Phase 1: Ingestion (Stage 1)
- [x] Implement `Terminal_app/stage_1_ingestion.py` <!-- id: 5 -->
- [x] Logic: Convert subreddits to RSS URLs <!-- id: 6 -->
- [x] Logic: Fetch RSS feeds (handle rate limits/errors) <!-- id: 7 -->
- [x] Logic: Filter for 24h-72h window <!-- id: 8 -->
- [x] Logic: Save to `output/1_raw_feed.json` <!-- id: 9 -->
- [x] Test Phase 1 (Data validation) <!-- id: 10 -->

## Phase 2: Fact-Check & Validation (Stage 2)
- [x] Implement `Terminal_app/stage_2_factcheck.py` <!-- id: 11 -->
- [x] Setup Perplexity API Client <!-- id: 12 -->
- [x] Logic: Loop through items in `1_raw_feed.json` <!-- id: 13 -->
- [x] Logic: Query Perplexity for verification <!-- id: 14 -->
- [x] Logic: Filter out debunked/rumor items <!-- id: 15 -->
- [x] Logic: Save to `output/2_validated_facts.json` <!-- id: 16 -->
- [x] Test Phase 2 <!-- id: 17 -->

## Phase 3: Trend Scoring (Stage 3)
- [x] Implement `Terminal_app/stage_3_trend_scoring.py` <!-- id: 18 -->
- [x] Setup Gemini Flash 3.0 Client <!-- id: 19 -->
- [x] Setup Google Trends API Client (or scraping fallback) <!-- id: 20 -->
- [x] Logic: Analyze "Virality Potential" with Gemini <!-- id: 21 -->
- [x] Logic: Check Search Volume with Google Trends <!-- id: 22 -->
- [x] Logic: Calculate composite score and sort <!-- id: 23 -->
- [x] Logic: Save to `output/3_ranked_trends.json` <!-- id: 24 -->
- [ ] Test Phase 3 <!-- id: 25 -->

## Phase 4: Strategic Curation (Stage 4)
- [x] Implement `Terminal_app/stage_4_curation.py` <!-- id: 26 -->
- [x] Setup OpenAI (GPT-5.2/4o) Client <!-- id: 27 -->
- [x] Logic: "Rationale Engine" prompt <!-- id: 28 -->
- [x] Logic: Select Top 5 stories <!-- id: 29 -->
- [x] Logic: Save to `output/4_curated_top5.json` <!-- id: 30 -->
- [ ] Test Phase 4 <!-- id: 31 -->

## Phase 5: Content Synthesis (Stage 5)
- [x] Implement `Terminal_app/stage_5_synthesis.py` <!-- id: 32 -->
- [x] Setup Claude (Sonnet 3.5/4.5) Client <!-- id: 33 -->
- [x] Logic: Generate Social Copy (Post, Carousel, A/B) <!-- id: 34 -->
- [x] Logic: Save to `output/5_social_drafts.json` <!-- id: 35 -->
- [x] Test Phase 5 <!-- id: 36 -->

## Phase 6: Visual Asset Generation (Stage 6)
- [x] Implement `Terminal_app/stage_6_visuals.py` <!-- id: 37 -->
- [x] Setup Gemini 3.0 Nano Pro (or available Image Gen) Client <!-- id: 38 -->
- [x] Logic: Parse carousel text for prompts <!-- id: 39 -->
- [x] Logic: Generate Images <!-- id: 40 -->
- [x] Logic: Save images to `output/6_final_assets/` <!-- id: 41 -->
- [x] Logic: Save manifest to `output/6_manifest.json` <!-- id: 42 -->
- [x] Test Phase 6 <!-- id: 43 -->

## Phase 7: Final Polish
- [x] End-to-End Walkthrough (Manual Triggering) <!-- id: 44 -->
- [x] Final Code Cleanup & Documentation <!-- id: 45 -->

# Reddit News Pipeline - CLI Instructions

This application is a state-machine pipeline that can run **fully automatically** or in discrete stages for debugging.

## Prerequisites

1.  **Python 3.9+**
2.  **API Keys**: Ensure `.env` (or `Terminal_app/projects.env`) contains:
    *   `PERPLEXITY_API_KEY`
    *   `GOOGLE_API_KEY` (or `GOOGLE_AI_API_KEY`)
    *   `OPENAI_API_KEY`
    *   `ANTHROPIC_API_KEY`
3.  **Dependencies**: `pip install -r requirements.txt`

---

## 🚀 Quick Start: Run Full Pipeline Automatically

To run the entire pipeline from start to finish with a single command:

```bash
python3 Terminal_app/run.py --stage all
```

This will:
1.  **Ingest** RSS feeds from `docs/subreditlist.md`
2.  **Validate** facts via Perplexity AI
3.  **Score** trends using Gemini
4.  **Curate** top 5 stories with GPT-5.2
5.  **Synthesize** social media content via Claude Sonnet 4.5
6.  **Generate** visual assets using DALL-E 3

All outputs are saved to the `output/` directory:
*   `1_raw_feed.json`
*   `2_validated_facts.json`
*   `3_ranked_trends.json`
*   `4_curated_top5.json`
*   `5_social_drafts.json`
*   `6_final_assets/` (images)
*   `6_manifest.json`

---

## Manual Stage-by-Stage Execution (Optional)

For debugging or cost control, you can run individual stages:

| Stage | Command |
|-------|---------|
| 1 - Ingestion | `python3 Terminal_app/run.py --stage 1` |
| 2 - Fact-Check | `python3 Terminal_app/run.py --stage 2 --input output/1_raw_feed.json` |
| 3 - Trend Scoring | `python3 Terminal_app/run.py --stage 3 --input output/2_validated_facts.json` |
| 4 - Curation | `python3 Terminal_app/run.py --stage 4 --input output/3_ranked_trends.json` |
| 5 - Synthesis | `python3 Terminal_app/run.py --stage 5 --input output/4_curated_top5.json` |
| 6 - Visuals | `python3 Terminal_app/run.py --stage 6 --input output/5_social_drafts.json` |

---

## Configuration

*   **Subreddits**: Edit `docs/subreditlist.md` to add/remove RSS sources.
*   **Models**: Edit individual stage files in `Terminal_app/` if model IDs change.

import argparse
import sys
import logging
import os
from dotenv import load_dotenv

from utils.api_clients import validate_pipeline_keys, ServiceName

# Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("RedditNewsPipeline")

def load_environment():
    """Load environment variables from projects.env and .env"""
    # Load .env first (default)
    load_dotenv()
    
    # Then load projects.env if it exists (overriding .env if logic dictates, but usually we want to ensure basic env vars are there)
    env_path = os.path.join(os.path.dirname(__file__), 'projects.env')
    if os.path.exists(env_path):
        load_dotenv(env_path, override=True) # strict override? Or just load?
        logger.info(f"Loaded environment from {env_path}")
    
    logger.info("Environment variables loaded")

def validate_required_keys(stages: list[int] = None) -> bool:
    """
    Validate API keys are present before running pipeline.

    Args:
        stages: List of stage numbers to validate (None = all stages)

    Returns:
        True if all required keys are present, False otherwise
    """
    # Map stage numbers to required services
    stage_services = {
        2: ServiceName.PERPLEXITY,
        3: ServiceName.GEMINI,
        4: ServiceName.OPENAI,
        5: ServiceName.ANTHROPIC,
        6: ServiceName.GEMINI,
    }

    # Determine which stages to check
    if stages is None:
        stages_to_check = list(stage_services.keys())
    else:
        stages_to_check = [s for s in stages if s in stage_services]

    # Get unique services needed
    services_needed = list(set(stage_services[s] for s in stages_to_check))

    valid, missing = validate_pipeline_keys(services_needed)

    if not valid:
        logger.error("=" * 50)
        logger.error("MISSING API KEYS - Pipeline cannot proceed")
        logger.error("=" * 50)
        for service, key_name in missing.items():
            logger.error(f"  • {service}: Set environment variable {key_name}")
        logger.error("")
        logger.error("Add missing keys to your .env or projects.env file")
        logger.error("=" * 50)
        return False

    logger.info("✓ All required API keys validated")
    return True


def run_full_pipeline():
    """Run the entire pipeline end-to-end automatically."""
    # Validate all API keys upfront (fail-fast)
    if not validate_required_keys():
        return False

    base_dir = os.path.dirname(os.path.dirname(__file__))
    output_dir = os.path.join(base_dir, 'output')

    # Stage 1: Ingestion
    logger.info("=" * 50)
    logger.info("STAGE 1: Ingestion")
    logger.info("=" * 50)
    from stage_1_ingestion import run_stage_1
    run_stage_1()
    stage_1_output = os.path.join(output_dir, '1_raw_feed.json')
    if not os.path.exists(stage_1_output):
        logger.error("Stage 1 failed to produce output.")
        return False
    logger.info(f"Stage 1 complete: {stage_1_output}")
    
    # Stage 2: Fact-Check
    logger.info("=" * 50)
    logger.info("STAGE 2: Fact-Check & Validation")
    logger.info("=" * 50)
    from stage_2_factcheck import run_stage_2
    run_stage_2(stage_1_output)
    stage_2_output = os.path.join(output_dir, '2_validated_facts.json')
    if not os.path.exists(stage_2_output):
        logger.error("Stage 2 failed to produce output.")
        return False
    logger.info(f"Stage 2 complete: {stage_2_output}")
    
    # Stage 3: Trend Scoring
    logger.info("=" * 50)
    logger.info("STAGE 3: Trend Scoring")
    logger.info("=" * 50)
    from stage_3_trend_scoring import run_stage_3
    run_stage_3(stage_2_output)
    stage_3_output = os.path.join(output_dir, '3_ranked_trends.json')
    if not os.path.exists(stage_3_output):
        logger.error("Stage 3 failed to produce output.")
        return False
    logger.info(f"Stage 3 complete: {stage_3_output}")
    
    # Stage 4: Strategic Curation
    logger.info("=" * 50)
    logger.info("STAGE 4: Strategic Curation")
    logger.info("=" * 50)
    from stage_4_curation import run_stage_4
    run_stage_4(stage_3_output)
    stage_4_output = os.path.join(output_dir, '4_curated_top5.json')
    if not os.path.exists(stage_4_output):
        logger.error("Stage 4 failed to produce output.")
        return False
    logger.info(f"Stage 4 complete: {stage_4_output}")
    
    # Stage 5: Content Synthesis
    logger.info("=" * 50)
    logger.info("STAGE 5: Content Synthesis")
    logger.info("=" * 50)
    from stage_5_synthesis import run_stage_5
    run_stage_5(stage_4_output)
    stage_5_output = os.path.join(output_dir, '5_social_drafts.json')
    if not os.path.exists(stage_5_output):
        logger.error("Stage 5 failed to produce output.")
        return False
    logger.info(f"Stage 5 complete: {stage_5_output}")
    
    # Stage 6: Visual Asset Generation
    logger.info("=" * 50)
    logger.info("STAGE 6: Visual Asset Generation")
    logger.info("=" * 50)
    from stage_6_visuals import run_stage_6
    run_stage_6(stage_5_output)
    stage_6_manifest = os.path.join(output_dir, '6_manifest.json')
    if not os.path.exists(stage_6_manifest):
        logger.error("Stage 6 failed to produce output.")
        return False
    logger.info(f"Stage 6 complete: {stage_6_manifest}")

    # Stage 7: Carousel Image Generation
    logger.info("=" * 50)
    logger.info("STAGE 7: Carousel Image Generation")
    logger.info("=" * 50)
    from stage_7_carousel import run_stage_7
    # Find the session folder from Stage 6 manifest
    import json
    with open(stage_6_manifest, 'r') as f:
        manifest = json.load(f)
    if manifest and 'session_image_path' in manifest[0]:
        # Extract session folder from first item's session_image_path
        session_dir = os.path.dirname(os.path.dirname(manifest[0]['session_image_path']))
    else:
        session_dir = None
    run_stage_7(stage_5_output, session_dir=session_dir)
    stage_7_manifest = os.path.join(output_dir, '7_carousel_manifest.json')
    # Stage 7 is non-critical, so we don't fail if it doesn't produce output
    if os.path.exists(stage_7_manifest):
        logger.info(f"Stage 7 complete: {stage_7_manifest}")
    else:
        logger.warning("Stage 7 did not produce manifest (check session folder)")

    logger.info("=" * 50)
    logger.info("PIPELINE COMPLETE!")
    logger.info("=" * 50)
    logger.info(f"All outputs saved to: {output_dir}")
    return True

def main():
    parser = argparse.ArgumentParser(description="Reddit News State-Machine Pipeline")
    parser.add_argument("--stage", type=str, required=True,
                        help="Stage to execute: all (full pipeline), 1-7 (individual stages)")
    parser.add_argument("--input", type=str, required=False,
                        help="Path to input JSON artifact (required for stages 2-7 when run individually)")
    parser.add_argument("--session", type=str, required=False,
                        help="Path to existing session folder (for Stage 7 to output alongside Stage 6 assets)")
    
    args = parser.parse_args()
    
    load_environment()
    
    logger.info(f"Starting Pipeline Stage: {args.stage}")
    
    try:
        if args.stage == "all":
            success = run_full_pipeline()
            if not success:
                sys.exit(1)
        elif args.stage == "1":
            # Stage 1 has no API dependencies
            from stage_1_ingestion import run_stage_1
            run_stage_1()
        elif args.stage == "2":
            if not args.input:
                logger.error("--input is required for Stage 2")
                sys.exit(1)
            if not validate_required_keys([2]):
                sys.exit(1)
            from stage_2_factcheck import run_stage_2
            run_stage_2(args.input)
        elif args.stage == "3":
            if not args.input:
                logger.error("--input is required for Stage 3")
                sys.exit(1)
            if not validate_required_keys([3]):
                sys.exit(1)
            from stage_3_trend_scoring import run_stage_3
            run_stage_3(args.input)
        elif args.stage == "4":
            if not args.input:
                logger.error("--input is required for Stage 4")
                sys.exit(1)
            if not validate_required_keys([4]):
                sys.exit(1)
            from stage_4_curation import run_stage_4
            run_stage_4(args.input)
        elif args.stage == "5":
            if not args.input:
                logger.error("--input is required for Stage 5")
                sys.exit(1)
            if not validate_required_keys([5]):
                sys.exit(1)
            from stage_5_synthesis import run_stage_5
            run_stage_5(args.input)
        elif args.stage == "6":
            if not args.input:
                logger.error("--input is required for Stage 6")
                sys.exit(1)
            if not validate_required_keys([6]):
                sys.exit(1)
            from stage_6_visuals import run_stage_6
            run_stage_6(args.input)
        elif args.stage == "7":
            if not args.input:
                logger.error("--input is required for Stage 7 (path to 5_social_drafts.json)")
                sys.exit(1)
            # Stage 7 has no API dependencies (local rendering only)
            from stage_7_carousel import run_stage_7
            run_stage_7(args.input, session_dir=args.session)
        else:
            logger.error(f"Unknown stage: {args.stage}")
            sys.exit(1)
            
    except Exception as e:
        logger.exception(f"Pipeline failed at Stage {args.stage}")
        sys.exit(1)

if __name__ == "__main__":
    main()

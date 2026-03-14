#!/usr/bin/env python3
"""
demo_run.py — Run Task 1 + Task 2 end-to-end against real AWS services.

Prerequisites:
    1. A valid .env file with AWS credentials (see .env.example)
    2. AWS IAM user/role with permissions for S3, Textract, and Bedrock
    3. pip install -r requirements.txt
    4. Sample files to process (resume PDF/image + job description PDF/image)

Usage:
    # Full pipeline: Task 1 (OCR) → Task 2 (extraction)
    python demo_run.py --resume ./samples/resume.pdf --job-desc ./samples/jd.png

    # Task 1 only (OCR + text cleaning)
    python demo_run.py --resume ./samples/resume.pdf --job-desc ./samples/jd.png --step 1

    # Task 2 only (skip OCR, provide raw text files instead)
    python demo_run.py --resume-text ./samples/resume.txt --jd-text ./samples/jd.txt --step 2

    # Save output to file
    python demo_run.py --resume ./samples/resume.pdf --job-desc ./samples/jd.png --output result.json

    # Verbose logging
    python demo_run.py --resume ./samples/resume.pdf --job-desc ./samples/jd.png -v
"""

import argparse
import json
import logging
import sys
from pathlib import Path

from config.settings import config
from ocr_pipeline.pipeline import OCRPipeline
from ocr_pipeline.models import FileType
from extraction_pipeline.graph import run_extraction
from extraction_pipeline.llm_client import BedrockClient


def setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s | %(name)-35s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
    )
    # Quiet down noisy libraries unless in verbose mode
    if not verbose:
        logging.getLogger("botocore").setLevel(logging.WARNING)
        logging.getLogger("urllib3").setLevel(logging.WARNING)


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Task 1: File Storage + OCR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def run_task1(resume_path: str, job_desc_path: str) -> dict:
    """
    Run the OCR pipeline on a resume + job description pair.

    Returns a dict with 'resume_text' and 'job_description_text'.
    """
    print("\n" + "=" * 70)
    print("  TASK 1: File Storage + OCR Pipeline")
    print("=" * 70)

    pipeline = OCRPipeline()
    pipeline.initialize()

    print(f"\n  Resume file:  {resume_path}")
    print(f"  JD file:      {job_desc_path}")
    print(f"  S3 bucket:    {config.s3.bucket_name}")
    print(f"  AWS region:   {config.aws.region}")
    print("-" * 70)

    result = pipeline.process_pair(resume_path, job_desc_path)

    # Print Task 1 summary
    print("\n  [Resume OCR Result]")
    if result.resume_output:
        r = result.resume_output
        print(f"    File ID:     {r.file_id}")
        print(f"    Status:      {r.status}")
        print(f"    Pages:       {r.page_count}")
        print(f"    Words:       {r.word_count}")
        print(f"    Confidence:  {r.confidence:.1f}%")
        print(f"    S3 key:      {r.s3_key}")
        if r.error:
            print(f"    ERROR:       {r.error}")
        print(f"\n    --- Cleaned text (first 400 chars) ---")
        print(f"    {r.cleaned_text[:400]}...")

    print("\n  [Job Description OCR Result]")
    if result.job_description_output:
        j = result.job_description_output
        print(f"    File ID:     {j.file_id}")
        print(f"    Status:      {j.status}")
        print(f"    Pages:       {j.page_count}")
        print(f"    Words:       {j.word_count}")
        print(f"    Confidence:  {j.confidence:.1f}%")
        print(f"    S3 key:      {j.s3_key}")
        if j.error:
            print(f"    ERROR:       {j.error}")
        print(f"\n    --- Cleaned text (first 400 chars) ---")
        print(f"    {j.cleaned_text[:400]}...")

    print("-" * 70)
    print(f"  Session ID: {result.session_id}")

    return {
        "session_id": result.session_id,
        "resume_text": result.resume_text,
        "job_description_text": result.job_description_text,
        "task1_output": result.to_dict(),
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  Task 2: LangGraph/LangChain Extraction
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def run_task2(resume_text: str, job_description_text: str) -> dict:
    """
    Run the extraction pipeline on cleaned text.

    Returns the full ExtractionState as a dict.
    """
    print("\n" + "=" * 70)
    print("  TASK 2: LangGraph Extraction Pipeline")
    print("=" * 70)

    print(f"\n  Bedrock model:  {config.bedrock.model_id}")
    print(f"  Temperature:    {config.bedrock.temperature}")
    print(f"  Max tokens:     {config.bedrock.max_tokens}")
    print(f"  Resume length:  {len(resume_text)} chars")
    print(f"  JD length:      {len(job_description_text)} chars")
    print("-" * 70)

    print("\n  Running LangGraph extraction (JD + resume in parallel)...")
    result = run_extraction(
        resume_text=resume_text,
        job_description_text=job_description_text,
    )

    print(f"\n  Status: {result.status}")

    # Print Job Requirements
    if result.job_requirements:
        jr = result.job_requirements
        print("\n  [Job Requirements]")
        print(f"    Title:          {jr.job_title}")
        print(f"    Company:        {jr.company_name}")
        print(f"    Location:       {jr.location}")
        print(f"    Experience:     {jr.years_experience_required}+ years")
        print(f"    Type:           {jr.employment_type}")
        print(f"    Salary:         {jr.salary_range}")
        print(f"    Required skills ({len(jr.required_skills)}):")
        for skill in jr.required_skills:
            print(f"      - {skill}")
        print(f"    Preferred skills ({len(jr.preferred_skills)}):")
        for skill in jr.preferred_skills:
            print(f"      - {skill}")
        print(f"    Tools & technologies ({len(jr.tools_and_technologies)}):")
        for tool in jr.tools_and_technologies:
            print(f"      - {tool}")
        print(f"    Education requirements:")
        for edu in jr.education_requirements:
            print(f"      - {edu}")
        print(f"    Key responsibilities ({len(jr.key_responsibilities)}):")
        for resp in jr.key_responsibilities:
            print(f"      - {resp}")

    # Print Candidate Profile
    if result.candidate_profile:
        cp = result.candidate_profile
        print("\n  [Candidate Profile]")
        print(f"    Name:           {cp.candidate_name}")
        print(f"    Contact:        {cp.contact_info}")
        print(f"    Total exp:      {cp.total_years_experience} years")
        print(f"    Summary:        {cp.resume_experience_summary[:200]}...")
        print(f"    Skills ({len(cp.resume_skills)}):")
        for skill in cp.resume_skills:
            print(f"      - {skill}")
        print(f"    Experience ({len(cp.resume_experience)} roles):")
        for exp in cp.resume_experience:
            print(f"      {exp.title} @ {exp.company} ({exp.duration})")
            for h in exp.highlights:
                print(f"        - {h}")
        print(f"    Projects ({len(cp.resume_projects)}):")
        for proj in cp.resume_projects:
            print(f"      {proj.name}: {proj.description}")
            print(f"        Tech: {', '.join(proj.technologies)}")
        print(f"    Education:")
        for edu in cp.education:
            print(f"      - {edu}")
        print(f"    Certifications:")
        for cert in cp.certifications:
            print(f"      - {cert}")

    if result.errors:
        print(f"\n  Errors ({len(result.errors)}):")
        for err in result.errors:
            print(f"    - {err}")

    print("-" * 70)

    return result.model_dump()


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
#  CLI
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def main():
    parser = argparse.ArgumentParser(
        description="Demo: Run Task 1 + Task 2 against real AWS services",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Full pipeline (OCR → extraction)
  python demo_run.py --resume resume.pdf --job-desc jd.png

  # Task 1 only
  python demo_run.py --resume resume.pdf --job-desc jd.png --step 1

  # Task 2 only (provide pre-extracted text files)
  python demo_run.py --resume-text resume.txt --jd-text jd.txt --step 2

  # Save JSON output
  python demo_run.py --resume resume.pdf --job-desc jd.png -o result.json
        """,
    )

    # Task 1 inputs (file paths for OCR)
    parser.add_argument(
        "--resume", "-r",
        help="Path to resume file (PDF or image) for OCR",
    )
    parser.add_argument(
        "--job-desc", "-j",
        help="Path to job description file (PDF or image) for OCR",
    )

    # Task 2 inputs (pre-extracted text, skip OCR)
    parser.add_argument(
        "--resume-text",
        help="Path to a .txt file with pre-extracted resume text (skips OCR)",
    )
    parser.add_argument(
        "--jd-text",
        help="Path to a .txt file with pre-extracted JD text (skips OCR)",
    )

    # Control
    parser.add_argument(
        "--step", type=int, choices=[1, 2],
        help="Run only Task 1 or Task 2 (default: both)",
    )
    parser.add_argument(
        "--output", "-o",
        help="Save full JSON output to this file",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true",
        help="Enable debug logging",
    )

    args = parser.parse_args()
    setup_logging(args.verbose)

    # ── Validate arguments ─────────────────────────────────────────────
    run_step1 = args.step is None or args.step == 1
    run_step2 = args.step is None or args.step == 2

    if run_step1 and (not args.resume or not args.job_desc):
        parser.error(
            "Task 1 requires --resume and --job-desc. "
            "Or use --step 2 with --resume-text and --jd-text to skip OCR."
        )

    if args.step == 2 and (not args.resume_text or not args.jd_text):
        parser.error(
            "Task 2 standalone requires --resume-text and --jd-text "
            "(plain text files)."
        )

    # Validate file paths exist
    for path_arg, label in [
        (args.resume, "Resume file"),
        (args.job_desc, "Job description file"),
        (args.resume_text, "Resume text file"),
        (args.jd_text, "JD text file"),
    ]:
        if path_arg and not Path(path_arg).exists():
            parser.error(f"{label} not found: {path_arg}")

    # ── Run pipelines ──────────────────────────────────────────────────
    full_output = {}

    # Task 1
    if run_step1:
        task1_result = run_task1(args.resume, args.job_desc)
        full_output["task1"] = task1_result
        resume_text = task1_result["resume_text"]
        jd_text = task1_result["job_description_text"]
    else:
        # Load pre-extracted text for Task 2
        resume_text = Path(args.resume_text).read_text(encoding="utf-8")
        jd_text = Path(args.jd_text).read_text(encoding="utf-8")
        print(f"\n  Loaded resume text: {len(resume_text)} chars from {args.resume_text}")
        print(f"  Loaded JD text:     {len(jd_text)} chars from {args.jd_text}")

    # Task 2
    if run_step2:
        if not resume_text.strip() or not jd_text.strip():
            print("\n  WARNING: One or both texts are empty. Task 2 will be partial.")
        task2_result = run_task2(resume_text, jd_text)
        full_output["task2"] = task2_result

    # ── Final output ───────────────────────────────────────────────────
    print("\n" + "=" * 70)
    print("  COMPLETE")
    print("=" * 70)

    if args.output:
        output_path = Path(args.output)
        output_path.write_text(
            json.dumps(full_output, indent=2, default=str),
            encoding="utf-8",
        )
        print(f"\n  Full JSON output saved to: {output_path.resolve()}")
    else:
        print("\n  Tip: Use --output result.json to save the full output")

    print()


if __name__ == "__main__":
    main()
"""LLM-generated written analysis of a skin assessment report, via the Claude API."""

import json

import anthropic
from flask import current_app

MODEL = "claude-opus-4-8"

SYSTEM_PROMPT = (
    "You are a dermatology assistant summarizing an automated skin-image analysis "
    "for the person who took the photos. You are given the pipeline's stage-by-stage "
    "output and the final per-metric scores (0-100, higher = more of that concern). "
    "Write a short, plain-language analysis: 1) a one-paragraph overall summary, "
    "2) the metric(s) that stand out and why, 3) 3-5 practical, general skincare "
    "suggestions. Do not diagnose conditions or recommend medications. Keep it under "
    "250 words, no markdown headers."
)


def generate_ai_analysis(report_data):
    """report_data: dict with overall_skin_health_score, metrics, stage_details."""
    client = anthropic.Anthropic(api_key=current_app.config["ANTHROPIC_API_KEY"])

    payload = {
        "overall_skin_health_score": report_data.get("overall_skin_health_score"),
        "metrics": report_data.get("metrics"),
        "stage_details": report_data.get("stage_details"),
    }

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": json.dumps(payload)}],
    )
    return next(block.text for block in response.content if block.type == "text")

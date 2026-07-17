"""LLM-generated written analysis of a skin assessment report via OpenRouter."""

import json
from urllib import error, request

from flask import current_app

DEFAULT_MODEL = "openai/gpt-5.1"
DEFAULT_BASE_URL = "https://openrouter.ai/api/v1"

SYSTEM_PROMPT = (
    "You are a skincare treatment and recommendation assistant for a clinical-style "
    "skin assessment report. You are given the pipeline's scores and intake summary. "
    "Return ONLY valid JSON with these keys: summary_title, score_interpretation, "
    "key_concerns, morning_routine, evening_routine, night_routine, recommendations, "
    "weekly_treatments, "
    "needs_doctor_review, doctor_review_reason, safety_note. "
    "score_interpretation should explain the report score in simple language and mention "
    "whether the skin looks good, moderate, or needs attention. "
    "key_concerns must be a list of 2-4 short strings. "
    "morning_routine, evening_routine, and night_routine must each be a list of 2-4 "
    "short, practical steps personalized to the image-derived metrics and intake summary. "
    "Keep remedies gentle and low-risk, such as cleansing, moisturizing, sun protection, "
    "hydration, and avoiding known triggers. recommendations must be a list of 3-5 "
    "additional personalized skincare and lifestyle recommendations. weekly_treatments must "
    "be a list of only 1-3 treatments that the person should do once or twice per week based "
    "on their skin scores and intake profile; it is NOT a seven-day schedule. Every treatment "
    "object must have treatment, frequency, reason, and steps keys. frequency must say either "
    "Once weekly or Twice weekly, and steps must contain 1-3 gentle actions. Do not suggest "
    "exfoliation more than twice weekly, do not combine irritating treatments, and do not "
    "recommend unsafe home remedies. "
    "needs_doctor_review must be a JSON boolean and should be true "
    "when the overall health score is 30 or lower, any metric is severe, or the supplied "
    "data suggests persistent, painful, spreading, infected, bleeding, or sudden symptoms. "
    "doctor_review_reason must briefly explain why review is advised, or be an empty string. "
    "safety_note must be one short sentence encouraging dermatology review if symptoms worsen or persist. "
    "Do not diagnose disease, do not prescribe medication, and do not mention unsupported medical certainty."
)


def _extract_text(content):
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict) and item.get("type") == "text":
                parts.append(item.get("text", ""))
        return "".join(parts)
    if isinstance(content, dict) and content.get("type") == "text":
        return content.get("text", "")
    return ""


def generate_ai_analysis(report_data):
    """Generate a treatment and recommendation summary from report data."""
    api_key = current_app.config.get("OPENROUTER_API_KEY")
    if not api_key:
        raise RuntimeError("OpenRouter is not configured on this server")

    base_url = current_app.config.get("OPENROUTER_BASE_URL", DEFAULT_BASE_URL).rstrip("/")
    model = current_app.config.get("OPENROUTER_MODEL", DEFAULT_MODEL)

    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps({
                "overall_skin_health_score": report_data.get("overall_skin_health_score"),
                "metrics": report_data.get("metrics"),
                "stage_details": report_data.get("stage_details"),
                "intake_summary": report_data.get("intake_summary"),
                "username": report_data.get("username"),
                "status": report_data.get("status"),
            })},
        ],
        "max_tokens": 1800,
        "temperature": 0.3,
    }

    req = request.Request(
        f"{base_url}/chat/completions",
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": current_app.config.get("OPENROUTER_SITE_URL", "http://127.0.0.1:5000"),
            "X-Title": current_app.config.get("OPENROUTER_APP_NAME", "SkinSync AI"),
        },
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=60) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"OpenRouter request failed ({exc.code}): {detail}") from exc
    except error.URLError as exc:
        raise RuntimeError(f"OpenRouter request failed: {exc.reason}") from exc

    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("OpenRouter returned no choices")

    message = choices[0].get("message") or {}
    text = _extract_text(message.get("content"))
    if text:
        text = text.strip()
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return json.dumps(parsed, ensure_ascii=False)
        except json.JSONDecodeError:
            pass
        return text

    raise RuntimeError("OpenRouter returned no text output")

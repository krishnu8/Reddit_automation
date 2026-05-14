"""
AI Lead Analyzer.

Uses llama3 (via Ollama) to evaluate scraped Reddit posts and
return structured lead-quality assessments. Stores raw AI
responses in the audit trail for debugging.
"""

from __future__ import annotations

import json
from typing import Any

from loguru import logger

from app.ai import ollama_client
from app.ai.prompts import LEAD_ANALYSIS_SYSTEM, LEAD_ANALYSIS_PROMPT
from app.database import db
from app.config import ollama_cfg


async def analyze_lead(lead: dict[str, Any]) -> dict[str, Any]:
    """
    Analyze a single lead using llama3.

    Parameters
    ----------
    lead : dict
        A row from the ``leads`` table (must include id, username,
        title, body, subreddit).

    Returns
    -------
    dict
        Parsed analysis with keys: lead_quality, urgency,
        project_type, recommended_action, reply, etc.
    """
    prompt = LEAD_ANALYSIS_PROMPT.format(
        subreddit=lead.get("subreddit", ""),
        title=lead.get("title", ""),
        body=lead.get("body", "")[:2000],  # cap body length
        username=lead.get("username", ""),
    )

    # Use timed variant for audit trail
    analysis, raw_response, processing_ms = await ollama_client.generate_json_timed(
        prompt,
        model=ollama_cfg.model_slow,  # always use llama3 for analysis
        system=LEAD_ANALYSIS_SYSTEM,
        temperature=0.3,
    )

    # Normalise / validate fields
    result = _normalise_analysis(analysis)

    # Persist the analysis result to the database
    lead_id = lead.get("id")
    if lead_id:
        await db.update_lead_analysis(
            lead_id=lead_id,
            lead_quality=result["lead_quality"],
            urgency=result["urgency"],
            project_type=result["project_type"],
            recommended_action=result["recommended_action"],
            ai_reply=result["reply"],
            budget_estimate=result["budget_estimate"],
            emotional_tone=result["emotional_tone"],
            recommended_price=result["recommended_price"],
        )

        # Log raw AI response for audit
        await db.log_ai_analysis(
            lead_id=lead_id,
            model_used=ollama_cfg.model_slow,
            raw_response=raw_response,
            parsed_json=json.dumps(analysis),
            processing_time_ms=processing_ms,
        )

    logger.info(
        "Analyzed lead #{} — quality={}, action={}, emotion={}",
        lead_id,
        result["lead_quality"],
        result["recommended_action"],
        result["emotional_tone"],
    )
    return result


async def analyze_batch(leads: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Analyze a batch of leads sequentially (to avoid overloading Ollama)."""
    results: list[dict[str, Any]] = []
    for lead in leads:
        try:
            result = await analyze_lead(lead)
            results.append(result)
        except Exception as exc:
            logger.error("Error analyzing lead #{}: {}", lead.get("id"), exc)
            results.append(_default_analysis())
    return results


def _normalise_analysis(raw: dict[str, Any]) -> dict[str, Any]:
    """Ensure all expected keys are present with valid types."""
    # Score normalization: 1-10 → 0-100
    score = raw.get("lead_score", raw.get("lead_quality", 0))
    if isinstance(score, str):
        try:
            score = int(score)
        except ValueError:
            score = 0

    # If already 0-100 scale, keep; otherwise multiply by 10
    quality = score if score > 10 else score * 10
    quality = max(0, min(100, quality))

    # Determine action
    is_client = raw.get("is_potential_client", False)
    if is_client and quality >= 70:
        action = "dm"
    elif quality >= 70:
        action = "dm"
    else:
        action = "skip"

    urgency = str(raw.get("urgency", "low")).lower()
    if urgency not in ("low", "medium", "high"):
        urgency = "low"

    budget_estimate = str(raw.get("budget_estimate", "unknown")).lower()
    if budget_estimate not in ("low", "medium", "high", "unknown"):
        budget_estimate = "unknown"

    emotional_tone = str(raw.get("emotional_tone", "neutral")).lower()

    return {
        "lead_quality": quality,
        "urgency": urgency,
        "project_type": str(raw.get("service_type", raw.get("project_type", "other"))),
        "recommended_action": action,
        "reply": str(raw.get("personalized_pitch", raw.get("reply", ""))),
        "budget_estimate": budget_estimate,
        "emotional_tone": emotional_tone,
        "recommended_price": str(raw.get("recommended_price", "")),
        "followup_strategy": str(raw.get("followup_strategy", "")),
        "reasoning": str(raw.get("reasoning", "")),
    }


def _default_analysis() -> dict[str, Any]:
    """Fallback analysis when AI call fails."""
    return {
        "lead_quality": 0,
        "urgency": "low",
        "project_type": "unknown",
        "recommended_action": "skip",
        "reply": "",
        "budget_estimate": "unknown",
        "emotional_tone": "neutral",
        "recommended_price": "",
        "followup_strategy": "",
        "reasoning": "Analysis failed",
    }

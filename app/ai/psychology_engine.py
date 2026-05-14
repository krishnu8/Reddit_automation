"""
AI Psychology Engine.

Detects emotional state, personality style, and communication
preferences of Reddit users to adapt outreach and conversation tone.
"""

from __future__ import annotations

from typing import Any

from loguru import logger

from app.ai import ollama_client
from app.ai.prompts import PSYCHOLOGY_SYSTEM, PSYCHOLOGY_PROMPT
from app.config import ollama_cfg


async def analyze_psychology(
    message: str,
    context: str = "",
) -> dict[str, Any]:
    """
    Analyze the emotional state and personality of a user
    based on their message content.

    Parameters
    ----------
    message : str
        The user's message or post content.
    context : str
        Additional context (conversation history, post title, etc.)

    Returns
    -------
    dict
        Psychology profile with emotions, personality, and tone recommendations.
    """
    prompt = PSYCHOLOGY_PROMPT.format(
        message=message[:1500],
        context=context[:500],
    )

    try:
        result = await ollama_client.generate_json(
            prompt,
            model=ollama_cfg.model_fast,  # Use phi3 for speed
            system=PSYCHOLOGY_SYSTEM,
            temperature=0.3,
        )

        profile = _normalise_psychology(result)
        logger.debug(
            "Psychology analysis: emotion={}, style={}, trust={}",
            profile["primary_emotion"],
            profile["personality_style"],
            profile["trust_level"],
        )
        return profile

    except Exception as exc:
        logger.error("Psychology analysis failed: {}", exc)
        return _default_psychology()


def get_adapted_tone(psychology: dict[str, Any]) -> str:
    """
    Based on psychology profile, return tone guidance for the AI.
    """
    emotion = psychology.get("primary_emotion", "neutral")
    style = psychology.get("personality_style", "neutral")
    trust = psychology.get("trust_level", "medium")

    tone_map = {
        "frustrated": "Be empathetic and solution-focused. Acknowledge their frustration. Show you understand their pain. Don't be overly cheerful.",
        "urgent": "Be direct and action-oriented. Show you can move fast. Emphasize quick turnaround and reliability.",
        "confused": "Be patient and educational. Explain things simply. Offer to guide them through the process.",
        "overwhelmed": "Be reassuring and calm. Break things down. Show you can handle the complexity for them.",
        "fearful": "Build trust with specifics. Mention past work. Offer guarantees or phased approach. Address risk directly.",
        "excited": "Match their energy. Be enthusiastic about their project. Move quickly toward agreement.",
        "cautious": "Be transparent about process and pricing. Offer references. Don't push too hard. Give them space.",
        "neutral": "Be professional, friendly, and helpful. Focus on value and expertise.",
    }

    base_tone = tone_map.get(emotion, tone_map["neutral"])

    # Adjust for personality style
    if style == "analytical":
        base_tone += " Provide data, specifics, and detailed breakdowns."
    elif style == "expressive":
        base_tone += " Be conversational and share your enthusiasm."
    elif style == "driver":
        base_tone += " Be concise and results-focused. Get to the point quickly."
    elif style == "amiable":
        base_tone += " Be warm and build personal connection first."

    # Adjust for trust level
    if trust == "low":
        base_tone += " Extra focus on building credibility. Mention specifics about past work."

    return base_tone


def _normalise_psychology(raw: dict[str, Any]) -> dict[str, Any]:
    """Ensure all expected keys are present."""
    valid_emotions = {"frustrated", "urgent", "confused", "overwhelmed",
                      "neutral", "excited", "cautious", "fearful"}
    valid_styles = {"analytical", "expressive", "driver", "amiable"}
    valid_trust = {"low", "medium", "high"}

    primary = str(raw.get("primary_emotion", "neutral")).lower()
    if primary not in valid_emotions:
        primary = "neutral"

    secondary = str(raw.get("secondary_emotion", "none")).lower()
    if secondary not in valid_emotions and secondary != "none":
        secondary = "none"

    style = str(raw.get("personality_style", "neutral")).lower()
    if style not in valid_styles:
        style = "amiable"

    trust = str(raw.get("trust_level", "medium")).lower()
    if trust not in valid_trust:
        trust = "medium"

    pain_points = raw.get("pain_points", [])
    if not isinstance(pain_points, list):
        pain_points = []

    return {
        "primary_emotion": primary,
        "secondary_emotion": secondary,
        "personality_style": style,
        "communication_preference": str(raw.get("communication_preference", "casual")),
        "pain_points": pain_points,
        "trust_level": trust,
        "recommended_tone": str(raw.get("recommended_tone", "")),
    }


def _default_psychology() -> dict[str, Any]:
    """Fallback psychology profile."""
    return {
        "primary_emotion": "neutral",
        "secondary_emotion": "none",
        "personality_style": "amiable",
        "communication_preference": "casual",
        "pain_points": [],
        "trust_level": "medium",
        "recommended_tone": "Be professional, friendly, and helpful.",
    }

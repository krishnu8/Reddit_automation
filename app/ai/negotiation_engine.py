"""
AI Negotiation Engine.

Handles pricing negotiations intelligently — defends pricing,
avoids desperation, reduces scope instead of price, and
preserves profitability.
"""

from __future__ import annotations

from typing import Any, Optional

from loguru import logger

from app.ai import ollama_client
from app.ai.prompts import NEGOTIATION_SYSTEM, NEGOTIATION_PROMPT
from app.config import ollama_cfg, PRICING


def get_pricing(service_type: str) -> dict[str, int]:
    """Get pricing for a service type."""
    # Normalize service type
    normalized = service_type.lower().replace(" ", "_").replace("-", "_")

    # Try direct match
    if normalized in PRICING:
        return PRICING[normalized]

    # Try mapping common names
    mapping = {
        "website": "website",
        "web": "website",
        "site": "website",
        "ui": "uiux",
        "ux": "uiux",
        "uiux": "uiux",
        "ui/ux": "uiux",
        "design": "uiux",
        "seo": "seo",
        "search engine": "seo",
        "automation": "automation",
        "ai": "automation",
        "ai_automation": "automation",
        "webapp": "webapp",
        "web_app": "webapp",
        "app": "webapp",
        "dashboard": "dashboard",
        "admin": "dashboard",
        "panel": "dashboard",
        "ecommerce": "ecommerce",
        "e_commerce": "ecommerce",
        "shopify": "ecommerce",
        "store": "ecommerce",
        "saas": "saas",
        "mvp": "saas",
        "landing": "landing_page",
        "landing_page": "landing_page",
        "api": "api_integration",
        "api_integration": "api_integration",
        "integration": "api_integration",
        "wordpress": "website",
        "crm": "webapp",
    }

    for key, val in mapping.items():
        if key in normalized:
            return PRICING[val]

    return PRICING["other"]


def evaluate_offer(
    service_type: str,
    client_offer: float,
) -> dict[str, Any]:
    """
    Evaluate a client's price offer against our pricing structure.

    Returns assessment with recommended response strategy.
    """
    pricing = get_pricing(service_type)

    if client_offer >= pricing["preferred_min"]:
        return {
            "verdict": "accept",
            "message": "Good offer — within preferred range",
            "suggested_response": "accept_gracefully",
            "can_accept": True,
        }
    elif client_offer >= pricing["hard_min"]:
        return {
            "verdict": "negotiate",
            "message": "Below preferred but above minimum — negotiate scope",
            "suggested_response": "reduce_scope",
            "can_accept": True,
        }
    else:
        return {
            "verdict": "decline",
            "message": f"Below hard minimum of ${pricing['hard_min']}",
            "suggested_response": "explain_value",
            "can_accept": False,
        }


async def generate_negotiation_reply(
    service_type: str,
    client_budget: str,
    concern: str,
    context: str = "",
) -> str:
    """
    Generate an intelligent negotiation response.
    """
    pricing = get_pricing(service_type)

    prompt = NEGOTIATION_PROMPT.format(
        service_type=service_type,
        our_price=f"${pricing['start']}-${pricing['preferred_max']}",
        hard_min=f"${pricing['hard_min']}",
        client_budget=client_budget,
        concern=concern,
        context=context[:500],
    )

    reply = await ollama_client.generate_text(
        prompt,
        model=ollama_cfg.model_slow,
        system=NEGOTIATION_SYSTEM,
        temperature=0.7,
    )

    logger.info("Generated negotiation reply for {} service", service_type)
    return reply


def get_scope_reduction_options(service_type: str) -> list[str]:
    """
    Return scope reduction options for when a client's budget is low.
    """
    reductions = {
        "website": [
            "Start with a 3-page site instead of 5+",
            "Use a template-based approach instead of custom design",
            "Skip animations and advanced interactions",
            "Handle content/copy themselves",
            "Phase 1: core pages, Phase 2: blog/extras",
        ],
        "webapp": [
            "Build MVP with core features only",
            "Skip admin panel in Phase 1",
            "Use simpler authentication",
            "Reduce number of user roles",
            "Skip email notifications initially",
        ],
        "ecommerce": [
            "Start with fewer product categories",
            "Use standard Shopify theme with customization",
            "Skip custom checkout flow",
            "Phase 1: store setup, Phase 2: analytics",
        ],
        "uiux": [
            "Design key pages only (home, product, checkout)",
            "Skip mobile-specific designs initially",
            "Provide wireframes instead of full mockups",
            "Reduce revision rounds",
        ],
        "seo": [
            "Focus on on-page SEO only",
            "Audit + recommendations without implementation",
            "Target fewer keywords initially",
            "Skip content creation",
        ],
        "automation": [
            "Automate the single most impactful workflow first",
            "Use simpler triggers/conditions",
            "Skip error handling edge cases initially",
            "Phase 1: core automation, Phase 2: monitoring",
        ],
    }

    normalized = service_type.lower()
    for key, options in reductions.items():
        if key in normalized:
            return options

    return [
        "Reduce feature count to core essentials",
        "Phase the delivery into multiple stages",
        "Use simpler technical approach",
        "Skip nice-to-have features",
    ]

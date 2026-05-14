"""
AI Conversation Agent.

Manages multi-turn conversations with potential clients using
llama3 (complex) and phi3 (simple) through Ollama.

Each conversation has full memory: project details, budget,
tech stack, negotiation stage, personality style, objections,
and message history are stored in SQLite and injected into
every prompt.
"""

from __future__ import annotations

from typing import Any, Optional

from loguru import logger

from app.ai import ollama_client
from app.ai.prompts import (
    CONVERSATION_SYSTEM,
    CONVERSATION_REPLY_PROMPT,
    QUICK_REPLY_SYSTEM,
    QUICK_REPLY_PROMPT,
    FOLLOWUP_SYSTEM,
    FOLLOWUP_PROMPT,
    CLASSIFY_MESSAGE_SYSTEM,
    CLASSIFY_MESSAGE_PROMPT,
)
from app.ai.psychology_engine import analyze_psychology, get_adapted_tone
from app.ai.negotiation_engine import generate_negotiation_reply
from app.config import ollama_cfg
from app.database import db


async def generate_reply(
    username: str,
    latest_message: str,
    *,
    lead_id: Optional[int] = None,
) -> str:
    """
    Generate a context-aware reply to a user's message.

    Automatically loads conversation history from the database,
    analyzes user psychology, and chooses the appropriate model.
    """
    # Get or create conversation record
    conv_id = await db.get_or_create_conversation(username, lead_id)
    conv = await db.get_conversation(conv_id)
    messages = await db.get_messages(conv_id, limit=20)

    # Store the incoming user message
    await db.add_message(conv_id, role="user", content=latest_message)

    # Analyze user psychology for tone adaptation
    context = f"Project: {conv['project_details']}" if conv else ""
    psychology = await analyze_psychology(latest_message, context)

    # Update conversation personality if detected
    if psychology.get("personality_style"):
        await db.update_conversation_details(
            conv_id,
            personality_style=psychology["personality_style"],
        )

    # Build conversation history string
    history_lines: list[str] = []
    for msg in messages:
        prefix = "You" if msg["role"] == "agent" else f"u/{username}"
        history_lines.append(f"{prefix}: {msg['content']}")
    conversation_history = "\n".join(history_lines[-10:]) or "(first message)"

    # Check if this is a negotiation message
    is_negotiation = any(kw in latest_message.lower() for kw in [
        "budget", "price", "cost", "expensive", "cheaper", "discount",
        "afford", "too much", "lower", "deal", "$",
    ])

    # Decide model complexity
    is_complex = (
        len(latest_message) > 150
        or len(messages) > 3
        or is_negotiation
        or any(kw in latest_message.lower() for kw in [
            "timeline", "scope", "features", "technical",
            "requirements", "proposal", "estimate", "contract",
        ])
    )

    if is_negotiation and conv:
        # Use negotiation engine for pricing discussions
        await db.update_conversation_details(
            conv_id, negotiation_stage="negotiating"
        )
        reply = await generate_negotiation_reply(
            service_type=conv.get("project_details", "website"),
            client_budget=latest_message,
            concern=latest_message,
            context=conversation_history,
        )
    elif is_complex:
        # Use llama3 for nuanced, context-heavy replies
        tone_guidance = get_adapted_tone(psychology)
        prompt = CONVERSATION_REPLY_PROMPT.format(
            username=username,
            project_details=conv["project_details"] if conv else "",
            budget=conv["budget"] if conv else "",
            tech_stack=conv["tech_stack"] if conv else "",
            negotiation_stage=conv["negotiation_stage"] if conv else "initial",
            personality_style=conv["personality_style"] if conv else "neutral",
            objections=conv["objections"] if conv else "",
            conversation_history=conversation_history,
            latest_message=latest_message,
        )
        # Inject tone guidance into system prompt
        system = CONVERSATION_SYSTEM + f"\n\nTONE GUIDANCE: {tone_guidance}"
        reply = await ollama_client.generate_text(
            prompt,
            model=ollama_cfg.model_slow,
            system=system,
            temperature=0.7,
        )
    else:
        # Use phi3 for quick, simple responses
        prompt = QUICK_REPLY_PROMPT.format(message=latest_message)
        reply = await ollama_client.generate_text(
            prompt,
            model=ollama_cfg.model_fast,
            system=QUICK_REPLY_SYSTEM,
            temperature=0.7,
        )

    # Store the agent's reply
    await db.add_message(conv_id, role="agent", content=reply)

    logger.info(
        "Generated reply for u/{} (model={}, conv=#{})",
        username,
        ollama_cfg.model_slow if is_complex else ollama_cfg.model_fast,
        conv_id,
    )
    return reply


async def generate_initial_reply(
    username: str,
    post_title: str,
    post_body: str,
    ai_reply_suggestion: str,
    *,
    lead_id: Optional[int] = None,
) -> str:
    """
    Generate the very first outreach reply to a lead.

    If the AI analyzer already provided a suggestion, refine it.
    Otherwise generate one from scratch.
    """
    conv_id = await db.get_or_create_conversation(username, lead_id)

    if ai_reply_suggestion:
        # The analyzer already drafted something — use it
        reply = ai_reply_suggestion
    else:
        prompt = CONVERSATION_REPLY_PROMPT.format(
            username=username,
            project_details=post_title,
            budget="",
            tech_stack="",
            negotiation_stage="initial",
            personality_style="neutral",
            objections="",
            conversation_history="(first contact)",
            latest_message=f"{post_title}\n\n{post_body[:1000]}",
        )
        reply = await ollama_client.generate_text(
            prompt,
            model=ollama_cfg.model_slow,
            system=CONVERSATION_SYSTEM,
            temperature=0.7,
        )

    # Store as the first agent message
    await db.add_message(conv_id, role="agent", content=reply, sent_via="dm")

    # Update conversation project details
    await db.update_conversation_details(
        conv_id, project_details=post_title
    )

    logger.info("Generated initial reply for u/{}", username)
    return reply


async def generate_followup(
    username: str,
    days_ago: int = 3,
) -> str:
    """Generate a follow-up message for a stale conversation."""
    conv = await db.get_conversation_by_username(username)
    if not conv:
        return ""

    conv_id = conv["id"]
    messages = await db.get_messages(conv_id, limit=10)
    summary_lines = [
        f"{'You' if m['role'] == 'agent' else 'Client'}: {m['content'][:100]}"
        for m in messages[-5:]
    ]

    prompt = FOLLOWUP_PROMPT.format(
        username=username,
        project_details=conv.get("project_details", ""),
        days_ago=days_ago,
        personality_style=conv.get("personality_style", "neutral"),
        conversation_summary="\n".join(summary_lines) or "No prior messages",
    )

    reply = await ollama_client.generate_text(
        prompt,
        model=ollama_cfg.model_slow,
        system=FOLLOWUP_SYSTEM,
        temperature=0.7,
    )

    await db.add_message(conv_id, role="agent", content=reply, sent_via="dm")
    logger.info("Generated follow-up for u/{}", username)
    return reply


async def classify_message(message: str) -> str:
    """
    Classify an incoming message using the fast model.

    Returns one of: interested, question, negotiation,
    rejection, spam, other.
    """
    prompt = CLASSIFY_MESSAGE_PROMPT.format(message=message[:500])
    result = await ollama_client.fast_completion(
        prompt, system=CLASSIFY_MESSAGE_SYSTEM, temperature=0.1
    )
    classification = result.strip().lower().split()[0] if result.strip() else "other"

    valid = {"interested", "question", "negotiation", "rejection", "spam", "other"}
    if classification not in valid:
        classification = "other"

    logger.debug("Message classified as: {}", classification)
    return classification


async def extract_project_details(
    conversation_id: int,
) -> dict[str, str]:
    """
    Scan conversation messages and extract project details,
    budget, and tech stack using the slow model.
    """
    messages = await db.get_messages(conversation_id, limit=30)
    full_text = "\n".join(
        f"{'Client' if m['role'] == 'user' else 'You'}: {m['content']}"
        for m in messages
    )

    prompt = f"""Extract project details from this conversation:

{full_text}

Return ONLY this JSON:
{{
  "project_details": "<what the client wants to build>",
  "budget": "<any budget mentioned, or 'unknown'>",
  "tech_stack": "<any technologies mentioned, or 'unknown'>",
  "negotiation_stage": "<initial/discussing/negotiating/agreed/closed>",
  "objections": "<any objections or concerns raised>"
}}"""

    result = await ollama_client.generate_json(
        prompt, model=ollama_cfg.model_slow, temperature=0.2
    )

    details = {
        "project_details": str(result.get("project_details", "")),
        "budget": str(result.get("budget", "unknown")),
        "tech_stack": str(result.get("tech_stack", "unknown")),
    }

    # Persist extracted details
    await db.update_conversation_details(
        conversation_id,
        project_details=details["project_details"],
        budget=details["budget"],
        tech_stack=details["tech_stack"],
        negotiation_stage=str(result.get("negotiation_stage", "initial")),
        objections=str(result.get("objections", "")),
    )

    return details

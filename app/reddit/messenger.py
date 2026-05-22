"""
Reddit Messenger.

Handles sending replies, chat messages, and follow-ups through
the browser with human-like behaviour, rate limiting, and
outreach logging.

Note: Reddit deprecated PMs in favour of Chat. All "DM" functions
now send via Reddit Chat.
"""

from __future__ import annotations

from typing import Any, Optional

from loguru import logger

from app.database import db
from app.reddit.reddit_browser import reddit_browser
from app.automation.humanizer import humanizer
from app.ai.conversation_agent import generate_initial_reply, generate_reply


async def reply_to_lead(lead: dict[str, Any]) -> bool:
    """
    Send a comment reply to a Reddit lead post.

    1. Check rate limits
    2. Generate (or use pre-generated) AI reply
    3. Navigate to the post
    4. Post the comment
    5. Record in database + outreach log

    Returns True on success.
    """
    # Rate-limit check
    if not await humanizer.can_send_reply():
        logger.info("Skipping reply — rate limit reached")
        return False

    if await humanizer.already_replied_to(lead["post_url"]):
        logger.info("Already replied to {}", lead["post_url"])
        return False

    # Generate reply
    reply_text = lead.get("ai_reply", "")
    if not reply_text:
        reply_text = await generate_initial_reply(
            username=lead["username"],
            post_title=lead["title"],
            post_body=lead["body"],
            ai_reply_suggestion="",
            lead_id=lead.get("id"),
        )

    if not reply_text:
        logger.warning("No reply generated for lead #{}", lead.get("id"))
        return False

    # Check message uniqueness
    if not humanizer.is_message_unique(reply_text):
        logger.warning("Reply too similar to recent messages — skipping")
        return False

    # Human-like delay before replying
    await humanizer.long_delay("composing reply")

    # Navigate and post
    await reddit_browser.goto_post(lead["post_url"])
    await humanizer.short_delay("reading post")

    success = await reddit_browser.post_comment(reply_text)

    if success:
        lead_id = lead.get("id")
        if lead_id:
            await db.mark_lead_replied(lead_id)
        humanizer.record_message(reply_text)
        logger.info("✅ Replied to lead #{} by u/{}", lead_id, lead["username"])
    else:
        logger.warning("❌ Failed to post comment on lead #{}", lead.get("id"))

    # Log outreach attempt
    await db.log_outreach(
        lead_id=lead.get("id"),
        username=lead["username"],
        channel="comment",
        message_preview=reply_text[:200],
        success=success,
        error_message="" if success else "Failed to post comment",
    )

    await humanizer.enforce_cooldown()
    return success


async def dm_lead(lead: dict[str, Any], message: Optional[str] = None) -> bool:
    """
    Send a Chat message to a lead's author.

    Uses Reddit Chat (PMs are deprecated).
    Returns True on success.
    """
    if not await humanizer.can_send_dm():
        logger.info("Skipping DM — daily limit reached")
        return False

    # Generate DM text if not provided
    if not message:
        message = await generate_initial_reply(
            username=lead["username"],
            post_title=lead["title"],
            post_body=lead["body"],
            ai_reply_suggestion=lead.get("ai_reply", ""),
            lead_id=lead.get("id"),
        )

    if not message:
        return False

    # Check uniqueness
    if not humanizer.is_message_unique(message):
        logger.warning("DM too similar to recent messages — regenerating")
        # Try to generate a fresh message
        message = await generate_initial_reply(
            username=lead["username"],
            post_title=lead["title"],
            post_body=lead["body"],
            ai_reply_suggestion="",  # Force fresh generation
            lead_id=lead.get("id"),
        )
        if not message or not humanizer.is_message_unique(message):
            logger.warning("Could not generate unique message — skipping")
            return False

    await humanizer.long_delay("preparing DM")

    subject = f"Re: {lead['title'][:50]}" if lead.get("title") else "Hey!"
    success = await reddit_browser.send_dm(lead["username"], subject, message)

    if success:
        lead_id = lead.get("id")
        if lead_id:
            await db.mark_lead_replied(lead_id)

        # Record in conversation
        conv_id = await db.get_or_create_conversation(
            lead["username"], lead.get("id")
        )
        await db.add_message(conv_id, "agent", message, sent_via="dm")
        humanizer.record_message(message)

        logger.info("✅ DM sent to u/{}", lead["username"])
    else:
        logger.warning("❌ Failed to DM u/{}", lead["username"])

    # Log outreach attempt
    await db.log_outreach(
        lead_id=lead.get("id"),
        username=lead["username"],
        channel="dm",
        message_preview=message[:200] if message else "",
        success=success,
        error_message="" if success else "Failed to send DM",
    )

    await humanizer.enforce_cooldown()
    return success


async def reply_to_message(
    username: str,
    incoming_message: str,
    lead_id: Optional[int] = None,
) -> Optional[str]:
    """
    Generate and return a reply to an incoming message.
    """
    if not await humanizer.can_send_reply():
        return None

    reply = await generate_reply(
        username=username,
        latest_message=incoming_message,
        lead_id=lead_id,
    )

    logger.info("Generated reply for u/{}: {}...", username, reply[:80])
    return reply


async def send_followup(
    username: str,
    message: str,
) -> bool:
    """Send a follow-up chat message to a user."""
    if not await humanizer.can_send_dm():
        return False

    await humanizer.long_delay("follow-up")
    success = await reddit_browser.send_dm(username, "Following up", message)

    if success:
        conv_id = await db.get_or_create_conversation(username)
        await db.add_message(conv_id, "agent", message, sent_via="dm")
        humanizer.record_message(message)
        logger.info("✅ Follow-up sent to u/{}", username)

    # Log outreach
    await db.log_outreach(
        lead_id=None,
        username=username,
        channel="dm_followup",
        message_preview=message[:200],
        success=success,
        error_message="" if success else "Failed to send follow-up",
    )

    return success


async def process_inbox() -> list[dict[str, str]]:
    """
    Check inbox for new messages and generate replies.
    Returns list of {username, incoming, reply} dicts.
    """
    inbox = await reddit_browser.check_inbox()
    results: list[dict[str, str]] = []

    for msg in inbox:
        username = msg.get("author", "")
        body = msg.get("body", "")
        if not username or not body:
            continue

        reply = await reply_to_message(username, body)
        if reply:
            results.append({
                "username": username,
                "incoming": body,
                "reply": reply,
            })

        await humanizer.short_delay("processing inbox")

    return results

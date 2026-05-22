"""
Async Task Manager — Fully Autonomous Mode.

Runs continuous loops:
  1. Search Reddit globally + subreddits for leads
  2. Analyze leads with AI
  3. Automatically DM post authors (or queue for approval)
  4. Monitor inbox for replies
  5. Reply to conversations automatically
  6. Process follow-ups
  7. Track everything in the database

Supports auto-send toggle and manual approval mode.
"""

from __future__ import annotations

import asyncio
from typing import Any, Optional

from loguru import logger

from app.config import scan_cfg, rate_limit_cfg, lead_cfg, auto_send_cfg
from app.database import db
from app.reddit.lead_scraper import run_full_scan, quick_scan
from app.reddit.messenger import (
    reply_to_lead,
    dm_lead,
    send_followup,
    process_inbox,
)
from app.ai.ai_analyzer import analyze_batch
from app.ai.conversation_agent import generate_followup, generate_reply
from app.automation.humanizer import humanizer


class TaskManager:
    """Fully autonomous agent with optional manual approval mode."""

    def __init__(self) -> None:
        self._running: bool = False
        self._paused: bool = False
        self._tasks: list[asyncio.Task[Any]] = []
        self._browser_lock = asyncio.Lock()
        self._auto_send: bool = auto_send_cfg.auto_send_enabled
        self._live_logs: list[dict[str, str]] = []  # Recent log entries

    # ── Control ─────────────────────────────────────────────────

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def is_paused(self) -> bool:
        return self._paused

    @property
    def auto_send(self) -> bool:
        return self._auto_send

    @auto_send.setter
    def auto_send(self, value: bool) -> None:
        self._auto_send = value
        logger.info("Auto-send mode: {}", "ON" if value else "OFF")

    @property
    def live_logs(self) -> list[dict[str, str]]:
        return self._live_logs[-50:]  # Return last 50

    def add_log(self, level: str, message: str) -> None:
        """Add a log entry for the dashboard."""
        from datetime import datetime, timezone
        self._live_logs.append({
            "time": datetime.now(timezone.utc).strftime("%H:%M:%S"),
            "level": level,
            "message": message,
        })
        # Keep only last 100
        if len(self._live_logs) > 100:
            self._live_logs = self._live_logs[-100:]

    async def start(self) -> None:
        """Start all autonomous background loops."""
        if self._running:
            logger.warning("Task manager already running")
            return

        self._running = True
        self._paused = False
        humanizer.reset_session()

        self._tasks = [
            asyncio.create_task(self._main_loop(), name="main_loop"),
            asyncio.create_task(self._inbox_loop(), name="inbox_loop"),
            asyncio.create_task(self._followup_loop(), name="followup_loop"),
        ]

        self.add_log("INFO", "🤖 Autonomous agent started")
        logger.info("🤖 Autonomous agent started — {} tasks", len(self._tasks))

    async def stop(self) -> None:
        """Cancel all running tasks."""
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        self._tasks.clear()
        self.add_log("INFO", "Agent stopped")
        logger.info("Agent stopped")

    def pause(self) -> None:
        """Pause the agent (loops continue but skip work)."""
        self._paused = True
        self.add_log("INFO", "⏸️ Agent paused")
        logger.info("Agent paused")

    def resume(self) -> None:
        """Resume the agent."""
        self._paused = False
        self.add_log("INFO", "▶️ Agent resumed")
        logger.info("Agent resumed")

    # ── Main Loop: Search → Analyze → DM ───────────────────────

    async def _main_loop(self) -> None:
        """
        The core automation loop:
        1. Search Reddit globally + subreddits for leads
        2. Analyze them with AI
        3. DM high-quality leads (auto or queue for approval)
        """
        while self._running:
            if self._paused:
                await asyncio.sleep(5)
                continue

            async with self._browser_lock:
                try:
                    # Step 1: Search Reddit
                    self.add_log("INFO", "🔍 Searching Reddit for leads…")
                    logger.info("🔍 Searching Reddit for leads…")
                    leads = await quick_scan()
                    self.add_log("INFO", f"🔍 Found {len(leads)} new leads")
                    logger.info("🔍 Found {} leads", len(leads))

                    # Step 2: Analyze unprocessed leads
                    new_leads = await db.get_new_leads()
                    if new_leads:
                        self.add_log("INFO", f"🧠 Analyzing {len(new_leads)} leads…")
                        logger.info("🧠 Analyzing {} new leads…", len(new_leads))
                        results = await analyze_batch(new_leads)

                        # Step 3: Handle high-quality leads
                        for lead, analysis in zip(new_leads, results):
                            if (
                                analysis["lead_quality"] >= lead_cfg.min_lead_quality
                                and analysis["recommended_action"] in ("reply", "dm")
                                and lead.get("username")
                            ):
                                if self._auto_send:
                                    # Auto-send mode: DM immediately
                                    self.add_log(
                                        "INFO",
                                        f"📨 Auto-messaging u/{lead['username']} "
                                        f"(quality={analysis['lead_quality']})"
                                    )

                                    if not await humanizer.can_send_dm():
                                        self.add_log("WARN", "Daily DM limit reached")
                                        break

                                    success = await dm_lead(
                                        {**lead, **analysis},
                                        analysis.get("reply", ""),
                                    )
                                    if success:
                                        self.add_log("OK", f"✅ DM sent to u/{lead['username']}")
                                    else:
                                        self.add_log("ERR", f"❌ Failed DM to u/{lead['username']}")

                                    await humanizer.long_delay("between DMs")
                                else:
                                    # Manual mode: queue for approval
                                    self.add_log(
                                        "INFO",
                                        f"📋 Queued u/{lead['username']} for approval "
                                        f"(quality={analysis['lead_quality']})"
                                    )

                except Exception as exc:
                    err_str = str(exc).lower()
                    self.add_log("ERR", f"Main loop error: {exc}")
                    logger.error("Main loop error: {}", exc)
                    
                    if "target closed" in err_str or "browser has been closed" in err_str or "playwright" in err_str:
                        self.add_log("WARN", "🔄 Browser crashed. Attempting recovery...")
                        logger.warning("Browser crashed. Attempting recovery...")
                        from app.reddit.reddit_browser import reddit_browser
                        try:
                            await reddit_browser.close()
                        except:
                            pass
                        try:
                            await reddit_browser.launch()
                            self.add_log("INFO", "✅ Browser recovered successfully.")
                            logger.info("Browser recovered successfully.")
                        except Exception as relaunch_exc:
                            self.add_log("ERR", f"Recovery failed: {relaunch_exc}")
                            logger.error("Recovery failed: {}", relaunch_exc)

            # Wait before next scan cycle
            wait_minutes = scan_cfg.scan_interval_minutes
            self.add_log("INFO", f"💤 Sleeping {wait_minutes}min before next scan")
            logger.info("💤 Sleeping {} minutes before next scan…", wait_minutes)
            await asyncio.sleep(wait_minutes * 60)

    # ── Inbox Loop: Monitor & Auto-Reply ───────────────────────

    async def _inbox_loop(self) -> None:
        """Check inbox for replies and automatically respond."""
        await asyncio.sleep(60)  # Wait for initial scan

        while self._running:
            if self._paused:
                await asyncio.sleep(5)
                continue

            async with self._browser_lock:
                try:
                    self.add_log("INFO", "📬 Checking inbox…")
                    logger.info("📬 Checking inbox for replies…")
                    inbox_results = await process_inbox()

                    for r in inbox_results:
                        username = r["username"]
                        incoming = r["incoming"]
                        reply_text = r["reply"]

                        self.add_log("INFO", f"📬 u/{username} replied: \"{incoming[:60]}\"")
                        logger.info("📬 u/{} replied: \"{}\"", username, incoming[:80])

                        if self._auto_send:
                            if await humanizer.can_send_reply():
                                await humanizer.medium_delay("composing reply")
                                success = await send_followup(username, reply_text)
                                if success:
                                    self.add_log("OK", f"✅ Reply sent to u/{username}")
                                else:
                                    self.add_log("ERR", f"❌ Failed reply to u/{username}")
                        else:
                            self.add_log("INFO", f"📋 Reply queued for u/{username} (manual mode)")

                except Exception as exc:
                    self.add_log("ERR", f"Inbox loop error: {exc}")
                    logger.error("Inbox loop error: {}", exc)

            await asyncio.sleep(scan_cfg.message_poll_interval_seconds)

    # ── Follow-up Loop ─────────────────────────────────────────

    async def _followup_loop(self) -> None:
        """Process scheduled follow-ups automatically."""
        await asyncio.sleep(120)  # stagger start

        while self._running:
            if self._paused:
                await asyncio.sleep(5)
                continue

            try:
                pending = await db.get_pending_followups()
                for fu in pending:
                    async with self._browser_lock:
                        try:
                            username = fu["username"]
                            message = fu.get("message", "")
                            if not message:
                                message = await generate_followup(username)

                            if message and await humanizer.can_send_dm():
                                if self._auto_send:
                                    await humanizer.long_delay("follow-up")
                                    success = await send_followup(username, message)
                                    if success:
                                        self.add_log("OK", f"✅ Follow-up sent to u/{username}")
                                else:
                                    self.add_log("INFO", f"📋 Follow-up queued for u/{username}")

                            await db.complete_followup(fu["id"])
                        except Exception as exc:
                            self.add_log("ERR", f"Follow-up error: {exc}")
                            logger.error("Follow-up error #{}: {}", fu["id"], exc)
            except Exception as exc:
                logger.error("Followup loop error: {}", exc)

            await asyncio.sleep(300)

    # ── Manual triggers ────────────────────────────────────────

    async def trigger_scan(self) -> int:
        """Trigger a quick scan manually."""
        self.add_log("INFO", "🔍 Manual scan triggered")
        leads = await quick_scan()
        return len(leads)

    async def trigger_full_scan(self) -> int:
        """Trigger a full scan manually."""
        self.add_log("INFO", "🔍 Manual full scan triggered")
        leads = await run_full_scan()
        return len(leads)

    async def send_approved_leads(self) -> int:
        """Send DMs to all approved-but-unsent leads."""
        approved = await db.get_approved_pending_leads()
        sent = 0
        for lead in approved:
            if not await humanizer.can_send_dm():
                break
            success = await dm_lead(lead, lead.get("ai_reply", ""))
            if success:
                sent += 1
            await humanizer.long_delay("between approved DMs")
        self.add_log("INFO", f"📨 Sent {sent}/{len(approved)} approved leads")
        return sent


# Module-level singleton
task_manager = TaskManager()

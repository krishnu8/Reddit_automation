"""
Human-like behaviour simulation.

Provides delays, typing simulation, mouse movement, scrolling,
cooldown management, and anti-spam protection to make the
agent's Reddit activity look natural.
"""

from __future__ import annotations

import asyncio
import random
import math
from datetime import datetime, timezone
from typing import Any

from loguru import logger

from app.config import timing_cfg, rate_limit_cfg
from app.database import db


class Humanizer:
    """Simulates natural human browsing and typing patterns."""

    def __init__(self) -> None:
        self._last_action_time: float = 0
        self._actions_this_session: int = 0
        self._messages_sent: list[str] = []  # Track sent messages for uniqueness

    # ── Random delays ───────────────────────────────────────────

    async def random_delay(
        self,
        min_seconds: float | None = None,
        max_seconds: float | None = None,
        label: str = "action",
    ) -> None:
        """Sleep for a random duration within the configured range."""
        lo = min_seconds if min_seconds is not None else timing_cfg.reply_delay_min
        hi = max_seconds if max_seconds is not None else timing_cfg.reply_delay_max
        delay = random.uniform(lo, hi)
        logger.debug("Humanizer: waiting {:.1f}s before {}", delay, label)
        await asyncio.sleep(delay)
        self._last_action_time = asyncio.get_event_loop().time()
        self._actions_this_session += 1

    async def short_delay(self, label: str = "browse") -> None:
        """A brief 2-8 second pause (simulates reading / scrolling)."""
        await self.random_delay(2, 8, label)

    async def medium_delay(self, label: str = "think") -> None:
        """A moderate 10-30 second pause (simulates thinking)."""
        await self.random_delay(10, 30, label)

    async def long_delay(self, label: str = "compose") -> None:
        """A long pause using the configured reply delay range."""
        await self.random_delay(label=label)

    async def micro_delay(self, label: str = "hover") -> None:
        """A very brief 0.5-2 second pause (simulates hover/glance)."""
        await self.random_delay(0.5, 2, label)

    async def reading_delay(self, text_length: int = 500) -> None:
        """Simulate time to read text — longer text = longer delay."""
        # Average reading speed: ~250 words/min, ~5 chars/word
        words = text_length / 5
        minutes = words / 250
        seconds = max(3, min(30, minutes * 60))
        jitter = random.uniform(0.8, 1.3)
        await asyncio.sleep(seconds * jitter)

    # ── Mouse movement simulation ──────────────────────────────

    async def simulate_mouse_movement(self, page: Any) -> None:
        """
        Simulate natural mouse movement across the page.
        Uses Bezier-like curves for realistic paths.
        """
        try:
            viewport = page.viewport_size
            if not viewport:
                return

            width = viewport["width"]
            height = viewport["height"]

            # Generate 2-4 random waypoints
            num_moves = random.randint(2, 4)
            for _ in range(num_moves):
                target_x = random.randint(100, width - 100)
                target_y = random.randint(100, height - 100)

                # Move with slight curve (multiple small steps)
                steps = random.randint(5, 15)
                for step in range(steps):
                    progress = step / steps
                    # Add slight wobble
                    wobble_x = random.randint(-3, 3)
                    wobble_y = random.randint(-3, 3)
                    x = int(target_x * progress + wobble_x)
                    y = int(target_y * progress + wobble_y)
                    await page.mouse.move(x, y)
                    await asyncio.sleep(random.uniform(0.01, 0.05))

                # Random pause at destination
                await asyncio.sleep(random.uniform(0.2, 0.8))

        except Exception as exc:
            logger.debug("Mouse simulation error: {}", exc)

    # ── Scroll simulation ──────────────────────────────────────

    async def simulate_scroll(self, page: Any, direction: str = "down") -> None:
        """Simulate natural scrolling behaviour."""
        try:
            num_scrolls = random.randint(2, 5)
            for _ in range(num_scrolls):
                delta = random.randint(100, 400)
                if direction == "up":
                    delta = -delta

                await page.mouse.wheel(0, delta)
                await asyncio.sleep(random.uniform(0.3, 1.2))

                # Occasionally pause longer (reading)
                if random.random() < 0.3:
                    await asyncio.sleep(random.uniform(1, 3))
        except Exception as exc:
            logger.debug("Scroll simulation error: {}", exc)

    # ── Typing simulation ──────────────────────────────────────

    async def simulate_typing(self, page: Any, text: str) -> None:
        """
        Type text character-by-character with natural timing.
        Includes occasional pauses, speed variations, and
        simulated typos (corrected).
        """
        for i, char in enumerate(text):
            # Base delay between keystrokes
            delay = random.uniform(
                timing_cfg.typing_delay_min,
                timing_cfg.typing_delay_max,
            )

            # Occasionally type faster in bursts
            if random.random() < 0.2:
                delay *= 0.5

            # Pause longer at sentence boundaries
            if char in ".!?\n":
                delay += random.uniform(0.3, 0.8)

            # Pause at commas
            if char == ",":
                delay += random.uniform(0.1, 0.3)

            # Occasional thinking pause mid-word
            if random.random() < 0.05 and char == " ":
                await asyncio.sleep(random.uniform(0.5, 2.0))

            await page.keyboard.type(char, delay=int(delay * 1000))

        logger.debug("Typed {} chars with humanized timing", len(text))

    # ── Cooldown / rate-limit checks ───────────────────────────

    async def can_send_dm(self) -> bool:
        """Return True if we haven't exceeded daily DM limits."""
        count = await db.count_replies_today()
        allowed = count < rate_limit_cfg.max_dms_per_day
        if not allowed:
            logger.warning(
                "DM limit reached: {}/{} today", count, rate_limit_cfg.max_dms_per_day
            )
        return allowed

    async def can_send_reply(self) -> bool:
        """Return True if we haven't exceeded hourly reply limits."""
        count = await db.count_messages_last_hour()
        allowed = count < rate_limit_cfg.max_replies_per_hour
        if not allowed:
            logger.warning(
                "Reply rate limit: {}/{} this hour",
                count,
                rate_limit_cfg.max_replies_per_hour,
            )
        return allowed

    async def enforce_cooldown(self) -> None:
        """
        Wait if we're acting too fast.
        Adds an extra random delay proportional to how many
        actions we've taken this session.
        """
        if self._actions_this_session > 5:
            extra = random.uniform(30, 120)
            logger.info(
                "Cooldown: {} actions this session, extra {:.0f}s pause",
                self._actions_this_session,
                extra,
            )
            await asyncio.sleep(extra)

    # ── Anti-duplicate helpers ─────────────────────────────────

    @staticmethod
    async def already_replied_to(post_url: str) -> bool:
        """Check if we've already replied to a specific post."""
        from app.database import db as _db
        cursor = await _db.conn.execute(
            "SELECT status FROM leads WHERE post_url = ?", (post_url,)
        )
        row = await cursor.fetchone()
        if row and row["status"] == "replied":
            return True
        return False

    def is_message_unique(self, message: str) -> bool:
        """Check if a message is sufficiently different from recent ones."""
        if not self._messages_sent:
            return True

        # Simple similarity check — compare first 50 chars
        prefix = message[:50].lower()
        for sent in self._messages_sent[-10:]:  # Check last 10
            if sent[:50].lower() == prefix:
                return False

        return True

    def record_message(self, message: str) -> None:
        """Record a sent message for uniqueness tracking."""
        self._messages_sent.append(message)
        # Keep only last 50
        if len(self._messages_sent) > 50:
            self._messages_sent = self._messages_sent[-50:]

    # ── Session stats ──────────────────────────────────────────

    def reset_session(self) -> None:
        """Reset the per-session action counter."""
        self._actions_this_session = 0
        logger.debug("Humanizer session counters reset")


# Module-level singleton
humanizer = Humanizer()

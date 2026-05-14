"""
SQLite database layer using aiosqlite.

Tables:
  - leads             : scraped Reddit leads
  - conversations     : per-user conversation tracking
  - messages          : individual messages in a conversation
  - followups         : scheduled follow-up actions
  - settings          : key-value application settings
  - outreach_logs     : log of every outreach attempt
  - subreddit_scans   : history of subreddit/keyword scans
  - ai_analysis       : raw AI analysis results for auditing
"""

from __future__ import annotations

import aiosqlite
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from loguru import logger

from app.config import db_cfg


# ── Schema ──────────────────────────────────────────────────────

_SCHEMA = """
CREATE TABLE IF NOT EXISTS leads (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    username            TEXT    NOT NULL,
    title               TEXT    NOT NULL DEFAULT '',
    body                TEXT    NOT NULL DEFAULT '',
    subreddit           TEXT    NOT NULL DEFAULT '',
    post_url            TEXT    NOT NULL DEFAULT '' UNIQUE,
    lead_quality        INTEGER NOT NULL DEFAULT 0,
    urgency             TEXT    NOT NULL DEFAULT 'unknown',
    project_type        TEXT    NOT NULL DEFAULT 'unknown',
    budget_estimate     TEXT    NOT NULL DEFAULT 'unknown',
    emotional_tone      TEXT    NOT NULL DEFAULT 'neutral',
    recommended_action  TEXT    NOT NULL DEFAULT 'none',
    recommended_price   TEXT    NOT NULL DEFAULT '',
    ai_reply            TEXT    NOT NULL DEFAULT '',
    status              TEXT    NOT NULL DEFAULT 'new',
    scraped_at          TEXT    NOT NULL DEFAULT (datetime('now')),
    analyzed_at         TEXT,
    replied_at          TEXT,
    approved            INTEGER NOT NULL DEFAULT 0,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS conversations (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    username            TEXT    NOT NULL UNIQUE,
    project_details     TEXT    NOT NULL DEFAULT '',
    budget              TEXT    NOT NULL DEFAULT '',
    tech_stack          TEXT    NOT NULL DEFAULT '',
    negotiation_stage   TEXT    NOT NULL DEFAULT 'initial',
    personality_style   TEXT    NOT NULL DEFAULT 'neutral',
    objections          TEXT    NOT NULL DEFAULT '',
    followup_timing     TEXT    NOT NULL DEFAULT '',
    status              TEXT    NOT NULL DEFAULT 'active',
    lead_id             INTEGER,
    started_at          TEXT    NOT NULL DEFAULT (datetime('now')),
    last_message_at     TEXT,
    FOREIGN KEY (lead_id) REFERENCES leads(id)
);

CREATE TABLE IF NOT EXISTS messages (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id     INTEGER NOT NULL,
    role                TEXT    NOT NULL CHECK(role IN ('user', 'agent', 'system')),
    content             TEXT    NOT NULL,
    sent_via            TEXT    NOT NULL DEFAULT 'comment',
    created_at          TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

CREATE TABLE IF NOT EXISTS followups (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id     INTEGER NOT NULL,
    scheduled_at        TEXT    NOT NULL,
    message             TEXT    NOT NULL DEFAULT '',
    status              TEXT    NOT NULL DEFAULT 'pending',
    completed_at        TEXT,
    FOREIGN KEY (conversation_id) REFERENCES conversations(id)
);

CREATE TABLE IF NOT EXISTS settings (
    key     TEXT PRIMARY KEY,
    value   TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS outreach_logs (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id             INTEGER,
    username            TEXT    NOT NULL,
    channel             TEXT    NOT NULL DEFAULT 'dm',
    message_preview     TEXT    NOT NULL DEFAULT '',
    success             INTEGER NOT NULL DEFAULT 0,
    error_message       TEXT    NOT NULL DEFAULT '',
    created_at          TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (lead_id) REFERENCES leads(id)
);

CREATE TABLE IF NOT EXISTS subreddit_scans (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    subreddit           TEXT    NOT NULL DEFAULT '',
    keyword             TEXT    NOT NULL DEFAULT '',
    search_type         TEXT    NOT NULL DEFAULT 'global',
    posts_found         INTEGER NOT NULL DEFAULT 0,
    leads_saved         INTEGER NOT NULL DEFAULT 0,
    scanned_at          TEXT    NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS ai_analysis (
    id                  INTEGER PRIMARY KEY AUTOINCREMENT,
    lead_id             INTEGER NOT NULL,
    model_used          TEXT    NOT NULL DEFAULT '',
    raw_response        TEXT    NOT NULL DEFAULT '',
    parsed_json         TEXT    NOT NULL DEFAULT '',
    processing_time_ms  INTEGER NOT NULL DEFAULT 0,
    created_at          TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (lead_id) REFERENCES leads(id)
);

CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
CREATE INDEX IF NOT EXISTS idx_leads_username ON leads(username);
CREATE INDEX IF NOT EXISTS idx_leads_quality ON leads(lead_quality);
CREATE INDEX IF NOT EXISTS idx_conversations_username ON conversations(username);
CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(conversation_id);
CREATE INDEX IF NOT EXISTS idx_followups_status ON followups(status);
CREATE INDEX IF NOT EXISTS idx_outreach_logs_lead ON outreach_logs(lead_id);
CREATE INDEX IF NOT EXISTS idx_subreddit_scans_time ON subreddit_scans(scanned_at);
CREATE INDEX IF NOT EXISTS idx_ai_analysis_lead ON ai_analysis(lead_id);
"""


class Database:
    """Async SQLite wrapper for the Reddit AI agent."""

    def __init__(self, db_path: Optional[Path] = None) -> None:
        self.db_path = db_path or db_cfg.absolute_path
        self._conn: Optional[aiosqlite.Connection] = None

    # ── Connection lifecycle ────────────────────────────────────

    async def connect(self) -> None:
        """Open the database and apply the schema."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = await aiosqlite.connect(str(self.db_path))
        self._conn.row_factory = aiosqlite.Row
        await self._conn.executescript(_SCHEMA)
        await self._conn.commit()
        logger.info("Database connected at {}", self.db_path)

    async def close(self) -> None:
        """Close the database connection."""
        if self._conn:
            await self._conn.close()
            self._conn = None
            logger.info("Database connection closed")

    @property
    def conn(self) -> aiosqlite.Connection:
        if self._conn is None:
            raise RuntimeError("Database not connected — call await db.connect() first")
        return self._conn

    # ── Lead operations ─────────────────────────────────────────

    async def insert_lead(
        self,
        username: str,
        title: str,
        body: str,
        subreddit: str,
        post_url: str,
    ) -> Optional[int]:
        """Insert a new lead. Returns the row id or None if duplicate."""
        try:
            cursor = await self.conn.execute(
                """
                INSERT OR IGNORE INTO leads (username, title, body, subreddit, post_url)
                VALUES (?, ?, ?, ?, ?)
                """,
                (username, title, body, subreddit, post_url),
            )
            await self.conn.commit()
            if cursor.rowcount == 0:
                return None  # duplicate post_url
            logger.debug("Inserted lead: {} — {}", username, title[:60])
            return cursor.lastrowid
        except Exception as exc:
            logger.error("Failed to insert lead: {}", exc)
            return None

    async def update_lead_analysis(
        self,
        lead_id: int,
        lead_quality: int,
        urgency: str,
        project_type: str,
        recommended_action: str,
        ai_reply: str,
        budget_estimate: str = "unknown",
        emotional_tone: str = "neutral",
        recommended_price: str = "",
    ) -> None:
        """Store the AI analysis result for a lead."""
        now = datetime.now(timezone.utc).isoformat()
        await self.conn.execute(
            """
            UPDATE leads
            SET lead_quality = ?, urgency = ?, project_type = ?,
                recommended_action = ?, ai_reply = ?,
                budget_estimate = ?, emotional_tone = ?,
                recommended_price = ?,
                analyzed_at = ?, status = 'analyzed'
            WHERE id = ?
            """,
            (lead_quality, urgency, project_type, recommended_action,
             ai_reply, budget_estimate, emotional_tone,
             recommended_price, now, lead_id),
        )
        await self.conn.commit()

    async def mark_lead_replied(self, lead_id: int) -> None:
        """Mark a lead as replied."""
        now = datetime.now(timezone.utc).isoformat()
        await self.conn.execute(
            "UPDATE leads SET status = 'replied', replied_at = ? WHERE id = ?",
            (now, lead_id),
        )
        await self.conn.commit()

    async def approve_lead(self, lead_id: int) -> None:
        """Approve a lead for outreach."""
        await self.conn.execute(
            "UPDATE leads SET approved = 1 WHERE id = ?",
            (lead_id,),
        )
        await self.conn.commit()

    async def update_lead_reply(self, lead_id: int, ai_reply: str) -> None:
        """Update the AI reply for a lead (for manual edits)."""
        await self.conn.execute(
            "UPDATE leads SET ai_reply = ? WHERE id = ?",
            (ai_reply, lead_id),
        )
        await self.conn.commit()

    async def get_new_leads(self) -> list[dict[str, Any]]:
        """Return all leads with status 'new'."""
        cursor = await self.conn.execute(
            "SELECT * FROM leads WHERE status = 'new' ORDER BY created_at DESC"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get_analyzed_leads(self, min_quality: int = 0) -> list[dict[str, Any]]:
        """Return analyzed leads above a quality threshold."""
        cursor = await self.conn.execute(
            """
            SELECT * FROM leads
            WHERE status = 'analyzed' AND lead_quality >= ?
            ORDER BY lead_quality DESC
            """,
            (min_quality,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get_approved_pending_leads(self) -> list[dict[str, Any]]:
        """Return leads that are approved but not yet messaged."""
        cursor = await self.conn.execute(
            """
            SELECT * FROM leads
            WHERE status = 'analyzed' AND approved = 1
            ORDER BY lead_quality DESC
            """
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get_all_leads(self, limit: int = 100) -> list[dict[str, Any]]:
        """Return the most recent leads."""
        cursor = await self.conn.execute(
            "SELECT * FROM leads ORDER BY created_at DESC LIMIT ?", (limit,)
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def get_lead_by_id(self, lead_id: int) -> Optional[dict[str, Any]]:
        """Return a single lead by its id."""
        cursor = await self.conn.execute("SELECT * FROM leads WHERE id = ?", (lead_id,))
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_lead_stats(self) -> dict[str, int]:
        """Return aggregate lead counts grouped by status."""
        cursor = await self.conn.execute(
            "SELECT status, COUNT(*) as cnt FROM leads GROUP BY status"
        )
        rows = await cursor.fetchall()
        return {r["status"]: r["cnt"] for r in rows}

    # ── Conversation operations ─────────────────────────────────

    async def get_or_create_conversation(
        self, username: str, lead_id: Optional[int] = None
    ) -> int:
        """Return existing conversation id or create a new one."""
        cursor = await self.conn.execute(
            "SELECT id FROM conversations WHERE username = ?", (username,)
        )
        row = await cursor.fetchone()
        if row:
            return row["id"]

        cursor = await self.conn.execute(
            "INSERT INTO conversations (username, lead_id) VALUES (?, ?)",
            (username, lead_id),
        )
        await self.conn.commit()
        logger.info("Created conversation for user: {}", username)
        return cursor.lastrowid  # type: ignore[return-value]

    async def update_conversation_details(
        self,
        conversation_id: int,
        project_details: Optional[str] = None,
        budget: Optional[str] = None,
        tech_stack: Optional[str] = None,
        status: Optional[str] = None,
        negotiation_stage: Optional[str] = None,
        personality_style: Optional[str] = None,
        objections: Optional[str] = None,
    ) -> None:
        """Update project metadata on a conversation."""
        fields: list[str] = []
        values: list[Any] = []
        mapping = {
            "project_details": project_details,
            "budget": budget,
            "tech_stack": tech_stack,
            "status": status,
            "negotiation_stage": negotiation_stage,
            "personality_style": personality_style,
            "objections": objections,
        }
        for col, val in mapping.items():
            if val is not None:
                fields.append(f"{col} = ?")
                values.append(val)
        if not fields:
            return
        values.append(conversation_id)
        await self.conn.execute(
            f"UPDATE conversations SET {', '.join(fields)} WHERE id = ?", values
        )
        await self.conn.commit()

    async def get_conversation(self, conversation_id: int) -> Optional[dict[str, Any]]:
        """Return a conversation row."""
        cursor = await self.conn.execute(
            "SELECT * FROM conversations WHERE id = ?", (conversation_id,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_conversation_by_username(self, username: str) -> Optional[dict[str, Any]]:
        """Return a conversation by Reddit username."""
        cursor = await self.conn.execute(
            "SELECT * FROM conversations WHERE username = ?", (username,)
        )
        row = await cursor.fetchone()
        return dict(row) if row else None

    async def get_all_conversations(self) -> list[dict[str, Any]]:
        """Return all conversations ordered by most recently active."""
        cursor = await self.conn.execute(
            "SELECT * FROM conversations ORDER BY last_message_at DESC NULLS LAST"
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    # ── Message operations ──────────────────────────────────────

    async def add_message(
        self,
        conversation_id: int,
        role: str,
        content: str,
        sent_via: str = "comment",
    ) -> int:
        """Insert a message and update conversation timestamp."""
        now = datetime.now(timezone.utc).isoformat()
        cursor = await self.conn.execute(
            """
            INSERT INTO messages (conversation_id, role, content, sent_via, created_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (conversation_id, role, content, sent_via, now),
        )
        await self.conn.execute(
            "UPDATE conversations SET last_message_at = ? WHERE id = ?",
            (now, conversation_id),
        )
        await self.conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    async def get_messages(
        self, conversation_id: int, limit: int = 50
    ) -> list[dict[str, Any]]:
        """Return messages for a conversation, oldest first."""
        cursor = await self.conn.execute(
            """
            SELECT * FROM messages
            WHERE conversation_id = ?
            ORDER BY created_at ASC
            LIMIT ?
            """,
            (conversation_id, limit),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    # ── Follow-up operations ────────────────────────────────────

    async def schedule_followup(
        self, conversation_id: int, scheduled_at: str, message: str = ""
    ) -> int:
        """Create a pending follow-up."""
        cursor = await self.conn.execute(
            """
            INSERT INTO followups (conversation_id, scheduled_at, message)
            VALUES (?, ?, ?)
            """,
            (conversation_id, scheduled_at, message),
        )
        await self.conn.commit()
        return cursor.lastrowid  # type: ignore[return-value]

    async def get_pending_followups(self) -> list[dict[str, Any]]:
        """Return follow-ups that are due."""
        now = datetime.now(timezone.utc).isoformat()
        cursor = await self.conn.execute(
            """
            SELECT f.*, c.username
            FROM followups f
            JOIN conversations c ON c.id = f.conversation_id
            WHERE f.status = 'pending' AND f.scheduled_at <= ?
            ORDER BY f.scheduled_at ASC
            """,
            (now,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    async def complete_followup(self, followup_id: int) -> None:
        """Mark a follow-up as completed."""
        now = datetime.now(timezone.utc).isoformat()
        await self.conn.execute(
            "UPDATE followups SET status = 'completed', completed_at = ? WHERE id = ?",
            (now, followup_id),
        )
        await self.conn.commit()

    # ── Outreach log operations ─────────────────────────────────

    async def log_outreach(
        self,
        lead_id: Optional[int],
        username: str,
        channel: str,
        message_preview: str,
        success: bool,
        error_message: str = "",
    ) -> None:
        """Log an outreach attempt."""
        await self.conn.execute(
            """
            INSERT INTO outreach_logs
                (lead_id, username, channel, message_preview, success, error_message)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (lead_id, username, channel, message_preview[:200],
             1 if success else 0, error_message),
        )
        await self.conn.commit()

    async def get_outreach_logs(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return recent outreach logs."""
        cursor = await self.conn.execute(
            "SELECT * FROM outreach_logs ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    # ── Scan history ────────────────────────────────────────────

    async def log_scan(
        self,
        subreddit: str,
        keyword: str,
        search_type: str,
        posts_found: int,
        leads_saved: int,
    ) -> None:
        """Log a subreddit/keyword scan."""
        await self.conn.execute(
            """
            INSERT INTO subreddit_scans
                (subreddit, keyword, search_type, posts_found, leads_saved)
            VALUES (?, ?, ?, ?, ?)
            """,
            (subreddit, keyword, search_type, posts_found, leads_saved),
        )
        await self.conn.commit()

    async def get_scan_history(self, limit: int = 30) -> list[dict[str, Any]]:
        """Return recent scan history."""
        cursor = await self.conn.execute(
            "SELECT * FROM subreddit_scans ORDER BY scanned_at DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [dict(r) for r in rows]

    # ── AI analysis audit trail ─────────────────────────────────

    async def log_ai_analysis(
        self,
        lead_id: int,
        model_used: str,
        raw_response: str,
        parsed_json: str,
        processing_time_ms: int,
    ) -> None:
        """Store raw AI analysis for auditing."""
        await self.conn.execute(
            """
            INSERT INTO ai_analysis
                (lead_id, model_used, raw_response, parsed_json, processing_time_ms)
            VALUES (?, ?, ?, ?, ?)
            """,
            (lead_id, model_used, raw_response, parsed_json, processing_time_ms),
        )
        await self.conn.commit()

    # ── Settings operations ─────────────────────────────────────

    async def get_setting(self, key: str, default: str = "") -> str:
        cursor = await self.conn.execute(
            "SELECT value FROM settings WHERE key = ?", (key,)
        )
        row = await cursor.fetchone()
        return row["value"] if row else default

    async def set_setting(self, key: str, value: str) -> None:
        await self.conn.execute(
            "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
            (key, value),
        )
        await self.conn.commit()

    # ── Rate-limit helpers ──────────────────────────────────────

    async def count_replies_today(self) -> int:
        """Count how many leads were replied to today (UTC)."""
        cursor = await self.conn.execute(
            """
            SELECT COUNT(*) as cnt FROM leads
            WHERE replied_at IS NOT NULL
              AND date(replied_at) = date('now')
            """
        )
        row = await cursor.fetchone()
        return row["cnt"] if row else 0

    async def count_messages_last_hour(self) -> int:
        """Count agent messages sent in the last 60 minutes."""
        cursor = await self.conn.execute(
            """
            SELECT COUNT(*) as cnt FROM messages
            WHERE role = 'agent'
              AND created_at >= datetime('now', '-1 hour')
            """
        )
        row = await cursor.fetchone()
        return row["cnt"] if row else 0

    async def get_outreach_stats(self) -> dict[str, Any]:
        """Return outreach statistics."""
        cursor = await self.conn.execute(
            """
            SELECT
                COUNT(*) as total,
                SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as successful,
                SUM(CASE WHEN success = 0 THEN 1 ELSE 0 END) as failed
            FROM outreach_logs
            """
        )
        row = await cursor.fetchone()
        return {
            "total": row["total"] or 0,
            "successful": row["successful"] or 0,
            "failed": row["failed"] or 0,
        }


# ── Module-level singleton ──────────────────────────────────────

db = Database()

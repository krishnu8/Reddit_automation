"""
Reddit AI Lead Generation Agent — Main Entry Point.

Boots up:
  1. Logger
  2. Database
  3. Browser (Playwright + Chrome)
  4. Dashboard (FastAPI on background thread)
  5. Task Manager (async loops)

Usage:
    python -m app.main            # full agent + dashboard
    python -m app.main --dashboard-only   # dashboard without browser
"""

from __future__ import annotations

import argparse
import asyncio
import signal
import sys
import threading

import uvicorn
from loguru import logger

from app.utils.logger import setup_logger
from app.config import dashboard_cfg
from app.database import db
from app.reddit.reddit_browser import reddit_browser
from app.automation.task_manager import task_manager
from app.dashboard.routes import app as fastapi_app
from app.ai.ollama_client import check_health as ollama_health


# ── Graceful shutdown ───────────────────────────────────────────

_shutdown_event = asyncio.Event()


def _signal_handler(sig: int, frame: object) -> None:
    logger.info("Received signal {} — shutting down…", sig)
    _shutdown_event.set()


# ── Dashboard server (runs in a background thread) ─────────────

def _run_dashboard() -> None:
    uvicorn.run(
        fastapi_app,
        host=dashboard_cfg.dashboard_host,
        port=dashboard_cfg.dashboard_port,
        log_level="warning",
    )


# ── Main async entry point ─────────────────────────────────────

async def run_agent(*, dashboard_only: bool = False) -> None:
    # 1. Initialise logger
    setup_logger()
    logger.info("=" * 60)
    logger.info("  Reddit AI Lead Generation Agent")
    logger.info("=" * 60)

    # 2. Connect database
    await db.connect()
    logger.info("Database ready")

    # 3. Check Ollama connectivity
    ollama_ok = await ollama_health()
    if ollama_ok:
        logger.info("✅ Ollama is reachable")
    else:
        logger.warning("⚠️  Ollama is NOT reachable — make sure Ollama is running")

    # 4. Launch dashboard
    dash_thread = threading.Thread(target=_run_dashboard, daemon=True)
    dash_thread.start()
    logger.info(
        "🌐 Dashboard at http://{}:{}",
        dashboard_cfg.dashboard_host, dashboard_cfg.dashboard_port,
    )

    if dashboard_only:
        logger.info("Running in dashboard-only mode")
        try:
            while not _shutdown_event.is_set():
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            await db.close()
        return

    # 5. Launch browser
    try:
        await reddit_browser.launch()
    except Exception as exc:
        logger.error("Failed to launch browser: {}", exc)
        logger.info("Running dashboard-only. Fix browser and restart.")
        try:
            while not _shutdown_event.is_set():
                await asyncio.sleep(1)
        except asyncio.CancelledError:
            pass
        finally:
            await db.close()
        return

    # 6. Check Reddit login
    logged_in = await reddit_browser.is_logged_in()
    if logged_in:
        logger.info("✅ Reddit session is logged in")
    else:
        logger.warning("⚠️  Not logged into Reddit — log in manually then restart")

    # 7. Start task manager
    await task_manager.start()
    logger.info("🚀 Agent running! Press Ctrl+C to stop.")

    # 8. Wait for shutdown
    try:
        while not _shutdown_event.is_set():
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    finally:
        logger.info("Shutting down…")
        await task_manager.stop()
        await reddit_browser.close()
        await db.close()
        logger.info("Goodbye! 👋")


def main() -> None:
    parser = argparse.ArgumentParser(description="Reddit AI Lead Generation Agent")
    parser.add_argument("--dashboard-only", action="store_true",
                        help="Start only the dashboard (no browser)")
    args = parser.parse_args()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    try:
        asyncio.run(run_agent(dashboard_only=args.dashboard_only))
    except KeyboardInterrupt:
        print("\nInterrupted — exiting.")
        sys.exit(0)


if __name__ == "__main__":
    main()

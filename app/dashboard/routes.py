"""
FastAPI Dashboard for the Reddit AI Agent.

Provides a web-based control panel with:
  - Lead overview & statistics
  - Conversation viewer
  - Approval system with Approve / DM / Reinstate per lead
  - Auto-send toggle
  - Live logs
  - Agent pause/resume
  - Outreach analytics
"""

from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from loguru import logger

from app.database import db
from app.automation.task_manager import task_manager
from app.ai.ollama_client import check_health as ollama_health
from app.dashboard.templates import render_dashboard


# ── FastAPI app ─────────────────────────────────────────────────

app = FastAPI(title="Reddit AI Agent", docs_url="/docs")


# ── Dashboard Route ─────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def dashboard_home():
    """Render the main dashboard."""
    leads = await db.get_all_leads(limit=100)
    stats = await db.get_lead_stats()
    conversations = await db.get_all_conversations()
    ollama_ok = await ollama_health()
    outreach_stats = await db.get_outreach_stats()

    html = render_dashboard(
        leads=leads,
        stats=stats,
        conversations=conversations,
        agent_running=task_manager.is_running and not task_manager.is_paused,
        ollama_ok=ollama_ok,
        auto_send=task_manager.auto_send,
        logs=task_manager.live_logs,
        outreach_stats=outreach_stats,
    )
    return HTMLResponse(content=html)


# ── Control API endpoints ──────────────────────────────────────

@app.get("/api/toggle-auto-send")
async def toggle_auto_send():
    """Toggle auto-send mode."""
    task_manager.auto_send = not task_manager.auto_send
    return RedirectResponse(url="/", status_code=303)


@app.get("/api/trigger-scan")
async def trigger_scan():
    """Trigger a manual scan."""
    try:
        count = await task_manager.trigger_scan()
        return RedirectResponse(url="/", status_code=303)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/send-approved")
async def send_approved():
    """Send DMs to all approved leads."""
    try:
        count = await task_manager.send_approved_leads()
        return RedirectResponse(url="/", status_code=303)
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@app.get("/api/pause-agent")
async def pause_agent():
    """Pause the agent."""
    task_manager.pause()
    return RedirectResponse(url="/", status_code=303)


@app.get("/api/resume-agent")
async def resume_agent():
    """Resume the agent."""
    task_manager.resume()
    return RedirectResponse(url="/", status_code=303)


@app.get("/api/leads/{lead_id}/approve")
async def approve_lead(lead_id: int):
    """Approve a lead for outreach."""
    await db.approve_lead(lead_id)
    return RedirectResponse(url="/", status_code=303)


@app.get("/api/leads/{lead_id}/dm")
async def dm_lead_now(lead_id: int):
    """Approve and immediately queue a DM to a lead."""
    lead = await db.get_lead_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    # Mark as approved
    await db.approve_lead(lead_id)

    # Schedule the DM via the task manager in background
    import asyncio
    from app.reddit.messenger import dm_lead as _dm_lead

    async def _send():
        try:
            success = await _dm_lead(lead, lead.get("ai_reply", ""))
            task_manager.add_log(
                "OK" if success else "ERR",
                f"{'✅' if success else '❌'} Manual DM to u/{lead['username']}"
            )
        except Exception as exc:
            task_manager.add_log("ERR", f"Manual DM failed: {exc}")

    asyncio.create_task(_send())
    return RedirectResponse(url="/", status_code=303)


@app.get("/api/leads/{lead_id}/reinstate")
async def reinstate_lead(lead_id: int):
    """Reset a lead back to 'analyzed' so it can be re-approved/re-messaged."""
    await db.reinstate_lead(lead_id)
    return RedirectResponse(url="/", status_code=303)


# ── Read-only API endpoints ─────────────────────────────────────

@app.get("/api/leads")
async def api_get_leads():
    return await db.get_all_leads(limit=200)


@app.get("/api/leads/{lead_id}")
async def api_get_lead(lead_id: int):
    lead = await db.get_lead_by_id(lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")
    return lead


@app.get("/api/conversations")
async def api_get_conversations():
    return await db.get_all_conversations()


@app.get("/api/conversations/{conv_id}/messages")
async def api_get_messages(conv_id: int):
    messages = await db.get_messages(conv_id, limit=100)
    if not messages:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return messages


@app.get("/api/stats")
async def api_stats():
    stats = await db.get_lead_stats()
    outreach = await db.get_outreach_stats()
    return {
        "lead_stats": stats,
        "outreach_stats": outreach,
        "total_conversations": len(await db.get_all_conversations()),
        "agent_running": task_manager.is_running,
        "auto_send": task_manager.auto_send,
    }


@app.get("/api/outreach-logs")
async def api_outreach_logs():
    return await db.get_outreach_logs(limit=50)


@app.get("/api/scan-history")
async def api_scan_history():
    return await db.get_scan_history(limit=30)


@app.get("/api/health")
async def api_health():
    ollama_ok = await ollama_health()
    return {
        "status": "ok",
        "ollama": ollama_ok,
        "agent_running": task_manager.is_running,
        "auto_send": task_manager.auto_send,
    }

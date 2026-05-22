# Reddit AI Lead Generation Agent - Architecture Report

## 1. Current Architecture Overview

The system is a fully autonomous, local-only Python AI agent that scans Reddit for freelance leads, analyzes them using local Ollama models (Llama3/Phi3), and engages qualified leads via DMs and comments.

**Core Components:**
- **Task Manager (`app/automation/task_manager.py`)**: The orchestrator running asynchronous loops for scanning, inbox monitoring, and follow-ups.
- **Reddit Browser (`app/reddit/reddit_browser.py`)**: Uses Playwright with a persistent Chrome profile to navigate Reddit, scrape data, and send messages without API limitations.
- **AI Pipelines (`app/ai/`)**:
  - `ai_analyzer.py`: Qualifies leads based on post content.
  - `conversation_agent.py`: Generates context-aware replies using conversation memory.
  - `psychology_engine.py`: Analyzes user emotions and adapts agent tone.
  - `negotiation_engine.py`: Defends pricing and handles scope reduction.
  - `ollama_client.py`: Async client with retries and JSON extraction.
- **Database (`app/database.py`)**: SQLite (via `aiosqlite`) storing leads, conversations, messages, follow-ups, and logs.
- **Dashboard (`app/dashboard/`)**: FastAPI + HTML/CSS rendering for monitoring and manual control.
- **Humanizer (`app/automation/humanizer.py`)**: Simulates human behavior (typing, delays, scrolling) and manages rate limits.

## 2. Identified Weaknesses & Scalability Issues

- **AI Lead Scoring**: The current `LEAD_ANALYSIS_PROMPT` is somewhat simplistic. It lacks deep analysis of `business_intent`, `startup_intent`, `technical_complexity`, and `hiring_probability` as requested in the requirements.
- **Browser Crash Recovery**: While there is error catching for Playwright actions, the `task_manager.py` does not currently detect if the browser process completely crashes and needs to be relaunched mid-execution.
- **Database Schema Completeness**: The `leads` table is missing specific qualification metric columns (e.g., `business_intent`, `hiring_probability`).
- **Inbox Event Transparency**: While conversations are tracked, explicit unread inbox event monitoring and visualization in the dashboard can be improved for better AI decision transparency.
- **Error Recovery**: If Ollama goes down temporarily, the task manager logs an error but could implement a backoff-and-pause mechanism to avoid wasting API calls.

## 3. Missing Systems & Next Steps

- **Advanced Lead Qualification Engine**: Expand `ai_analyzer.py` and `prompts.py` to extract all required metrics (urgency, business seriousness, budget likelihood, conversion probability).
- **Database Migrations**: Update `database.py` schema to support the new metrics and ensure backwards compatibility (e.g., adding columns via `ALTER TABLE`).
- **Resilience Engine**: Implement Playwright/Browser crash recovery within the main loops.
- **Dashboard Enhancements**: Expose AI decision transparency (raw JSON analysis, detailed metrics) in the UI.

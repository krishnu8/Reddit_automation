# Reddit AI Lead Generation Agent - Execution Plan

## PHASE 1: Critical Fixes & Database Schema
1. Update `app/database.py` to include new columns in the `leads` table for advanced qualification metrics (business intent, startup intent, technical complexity, etc.).
2. Implement schema auto-migration using `ALTER TABLE` if columns do not exist.
3. Update `app/automation/task_manager.py` to handle browser crashes (catch `TargetClosedError` or `Error` and restart the `reddit_browser` instance).

## PHASE 2: AI Improvements & Deep Lead Qualification
1. Rewrite `LEAD_ANALYSIS_PROMPT` in `app/ai/prompts.py` to mandate the analysis of business seriousness, startup intent, urgency, technical complexity, hiring probability, budget likelihood, and long-term client potential.
2. Update `app/ai/ai_analyzer.py` to parse these new JSON fields.
3. Ensure the lead score (0-100) mathematically weighs these advanced metrics rather than relying purely on the LLM's arbitrary guess.

## PHASE 3: Conversation Intelligence
1. Enhance `app/ai/conversation_agent.py` to utilize the new lead metrics when generating the initial reply.
2. Ensure `negotiation_engine.py` is firmly integrated and never goes below the hard minimums.

## PHASE 4: Scaling + Optimization
1. Enhance `app/automation/humanizer.py` to implement more robust anti-spam (e.g., adaptive pacing based on Reddit response times).
2. Refine the Playwright `reddit_browser.py` logic to handle modern Reddit Chat interface changes safely.

## PHASE 5: Production Hardening
1. Update `app/dashboard/routes.py` and `app/dashboard/templates.py` to display the newly collected AI metrics and provide deep AI decision transparency.
2. Complete end-to-end testing of the fully autonomous loop.

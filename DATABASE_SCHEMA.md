# Database Schema Overview

The database uses SQLite (via `aiosqlite`).

## Tables

### `leads`
Stores scraped Reddit posts and their AI qualification scores.
**Core Columns:** `id`, `username`, `title`, `body`, `subreddit`, `post_url`, `status`, `created_at`
**AI Metrics (Updated):** `lead_quality`, `urgency`, `project_type`, `budget_estimate`, `emotional_tone`, `recommended_action`, `recommended_price`, `ai_reply`, `business_intent`, `startup_intent`, `technical_complexity`, `hiring_probability`, `long_term_client_potential`

### `conversations`
Tracks the context and state of an ongoing discussion with a lead.
**Core Columns:** `id`, `username`, `lead_id`, `status`, `last_message_at`
**Context Memory:** `project_details`, `budget`, `tech_stack`, `negotiation_stage`, `personality_style`, `objections`, `followup_timing`

### `messages`
Stores individual chat/comment messages within a conversation for memory retrieval.
**Columns:** `id`, `conversation_id`, `role` (user/agent), `content`, `sent_via`, `created_at`

### `followups`
Queue for scheduled automated follow-up messages.
**Columns:** `id`, `conversation_id`, `scheduled_at`, `message`, `status`

### `outreach_logs`
Audit log of every DM or comment attempt.
**Columns:** `id`, `lead_id`, `username`, `channel`, `message_preview`, `success`, `error_message`

### `subreddit_scans`
Analytics for which subreddits/keywords are yielding leads.
**Columns:** `id`, `subreddit`, `keyword`, `search_type`, `posts_found`, `leads_saved`

### `ai_analysis`
Raw JSON and processing time logs for auditing model performance.
**Columns:** `id`, `lead_id`, `model_used`, `raw_response`, `parsed_json`, `processing_time_ms`

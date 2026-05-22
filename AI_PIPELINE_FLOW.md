# AI Pipeline Flow

The agent utilizes a dual-model approach using local Ollama endpoints to balance deep reasoning with high-speed execution.

## 1. Lead Qualification Pipeline (Model: `llama3` - Slow/Deep)
- **Trigger:** New lead saved to DB by scraper.
- **Prompt:** `LEAD_ANALYSIS_PROMPT`
- **Goal:** Analyze the post for business intent, startup intent, technical complexity, urgency, and budget likelihood.
- **Output:** Structured JSON with a 1-100 `lead_quality` score, recommended action, and a drafted personalized reply.
- **Fallback:** Retries up to 3 times, extracts JSON from markdown blocks if raw format fails.

## 2. Psychology & Tone Pipeline (Model: `phi3` - Fast)
- **Trigger:** Incoming user message.
- **Prompt:** `PSYCHOLOGY_PROMPT`
- **Goal:** Detect primary/secondary emotion, personality style (analytical, expressive, etc.), and trust level.
- **Output:** JSON guiding the agent's tone for the next reply.

## 3. Conversation Generation Pipeline (Model: `llama3` or `phi3`)
- **Trigger:** Incoming user message.
- **Routing:** 
  - If message is complex, >150 chars, or mentions negotiation/pricing keywords -> Route to **Llama3**.
  - If message is simple/short -> Route to **Phi3**.
- **Context Injection:** The prompt receives the last 10 messages, project details, budget, tech stack, negotiation stage, and psychology tone guidance.
- **Output:** Raw text reply.

## 4. Negotiation Engine Pipeline (Model: `llama3` - Slow/Deep)
- **Trigger:** Client negotiates price.
- **Logic:** Engine checks `PRICING` limits in `config.py`. If below hard minimum, suggests scope reduction.
- **Prompt:** `NEGOTIATION_PROMPT`
- **Output:** Firm but polite defense of pricing or alternative phased approach.

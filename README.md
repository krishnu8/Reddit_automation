# Reddit AI Lead Generation Agent 🤖

A fully autonomous, local-only Python AI agent that continuously monitors Reddit for freelance opportunities, qualifies leads using local LLMs (Ollama), and executes personalized, human-like outreach via direct messages and comments.

## ✨ Features

- **Local-First Architecture:** 100% offline AI processing. No OpenAI, no cloud APIs.
- **Intelligent Lead Qualification:** Uses `llama3` for deep analysis of posts to filter out noise and find high-intent buyers.
- **Psychology & Negotiation Engine:** Adapts communication tone based on the user's emotional state (frustrated, urgent, confused) and negotiates pricing intelligently without dropping below minimum thresholds.
- **Human-like Browser Automation:** Built on Playwright with a `Humanizer` module that simulates natural typing, mouse movements, scrolling, and reading delays to avoid detection.
- **Persistent Sessions:** Reuses your existing Chrome profile, bypassing login hurdles.
- **Stateful Conversation Memory:** Maintains full context of multi-turn conversations in SQLite.
- **Premium Dashboard:** Real-time FastAPI dashboard with a dark-glassmorphism UI for monitoring leads, logs, and approving outreach.
- **Autonomous & Manual Modes:** Run fully automatically, or queue high-quality leads for manual review and approval before sending.

## 🚀 Getting Started

### Prerequisites

1. **Python 3.12+**
2. **Google Chrome** installed.
3. **Ollama** installed and running locally.
4. Pull the required local models:
   ```bash
   ollama run llama3
   ollama run phi3
   ```

### Installation

1. Install the dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Install Playwright browsers:
   ```bash
   playwright install
   ```

### Configuration

Edit the `.env` file in the root directory. Crucially, ensure the `CHROME_PROFILE_PATH` points to your active Chrome profile that is logged into Reddit.

```ini
# .env example
CHROME_PROFILE_PATH=C:\Users\YourUser\AppData\Local\Google\Chrome\User Data\Profile 1
AUTO_SEND_ENABLED=true
```
*Note: To find your Chrome profile path, type `chrome://version` in Chrome and look for "Profile Path".*

### Running the Agent

**Important:** Close ALL Chrome windows before starting the agent, as Playwright needs exclusive access to copy the profile.

To start the full agent (browser automation + AI + dashboard):
```bash
py -m app.main
```

To start **only the dashboard** (useful for reviewing leads without running the browser automation):
```bash
py -m app.main --dashboard-only
```

Once running, access the dashboard at: [http://127.0.0.1:8080](http://127.0.0.1:8080)

## 🏗️ Architecture

- `app/main.py`: Entry point and process manager.
- `app/ai/`: Local LLM integration.
  - `ollama_client.py`: Async client for Ollama.
  - `ai_analyzer.py`: Initial lead scoring and intent extraction.
  - `conversation_agent.py`: Multi-turn stateful conversational logic.
  - `psychology_engine.py`: Tone and emotion detection.
  - `negotiation_engine.py`: Pricing and scope reduction logic.
- `app/reddit/`: Playwright automation.
  - `reddit_browser.py`: Core browser control and data extraction.
  - `lead_scraper.py`: Global keyword and subreddit scanning.
  - `messenger.py`: Comment and DM execution.
- `app/automation/`:
  - `task_manager.py`: The main loop orchestrating scans, analysis, and replies.
  - `humanizer.py`: Anti-detection mechanisms (typing delays, mouse movement).
- `app/dashboard/`: FastAPI web interface and UI templates.

## ⚠️ Disclaimer

Automated scraping and messaging on Reddit violates their Terms of Service. This project implements extensive humanization and rate-limiting to mitigate risks, but your account may still be banned. Use responsibly, ideally with a dedicated outreach account.

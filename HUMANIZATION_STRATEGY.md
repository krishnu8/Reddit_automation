# Humanization Strategy

The goal of the Reddit agent is to be indistinguishable from a human freelancer. Anti-automation systems and human skepticism are the primary obstacles.

## 1. Timing & Delays (`humanizer.py`)
- **Reading Delays:** Calculated based on the length of the post body (average 250 WPM) + randomized jitter.
- **Micro-Delays:** 0.5s - 2s delays between distinct actions (like clicking a chat box before typing).
- **Thinking Delays:** 10s - 30s before generating complex replies or transitioning between subreddits.

## 2. Browser Fingerprint (`reddit_browser.py`)
- Uses a persistent, pre-authenticated Chrome profile (`AgentProfile` copy) so login cookies match a real user session.
- Playwright arguments (`--disable-blink-features=AutomationControlled`) to strip basic headless fingerprints.

## 3. Physical Emulation
- **Typing Simulation:** Types character by character with delays (0.05s-0.15s). Pauses longer on punctuation (.,!?) and occasionally simulates mid-word thinking pauses.
- **Scroll Simulation:** Random delta scrolls down/up with reading pauses in between.
- **Mouse Movement:** Bezier-like curve generation moving the mouse to random coordinates on the screen while pages load.

## 4. Anti-Spam & Rate Limiting
- **Daily Limits:** Enforces strict limits (e.g., max 20 DMs/day) to prevent account bans.
- **Cooldowns:** If the agent performs >5 actions in a single session rapidly, it enforces an extended 30-120s cooldown to break robotic cadence.
- **Uniqueness Check:** Maintains a local memory of the last 50 sent messages. Rejects sending messages with the exact same starting 50 characters to prevent copy-paste spamming.

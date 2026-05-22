# Conversation Memory Flow

The agent maintains long-term memory for every lead it interacts with, enabling context-aware follow-ups and negotiations without hallucination.

## Data Storage
- SQLite database (`app.db`) maintains `conversations` and `messages`.
- `conversations` table acts as the structured memory state for a user.
- `messages` table acts as the raw transcript.

## The Flow
1. **Initial Contact:** Agent scrapes a post and sends a DM. A new `conversation` record is created, seeded with the post's title as `project_details`. The DM is logged as the first `message` (Role: agent).
2. **Incoming Message:** The inbox scanner detects a reply. It associates the message with the existing `conversation` via the Reddit username.
3. **Psychology Analysis:** The raw message is sent to `phi3` to update the user's `personality_style` in the `conversation` table.
4. **Memory Retrieval:** When generating the next reply, the agent fetches:
   - The `project_details`, `budget`, `tech_stack`, and `negotiation_stage`.
   - The last 10-20 messages from the transcript.
5. **Context Injection:** All retrieved memory is injected into the prompt for `llama3`.
6. **State Update:** Periodically, the agent runs `extract_project_details` on the transcript to update the structured memory fields (budget, tech stack, objections) if new information was revealed.

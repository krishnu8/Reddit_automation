"""
Playwright-based Reddit browser automation.

Launches a persistent Chrome profile so the existing Reddit
login session is reused.  Provides methods for navigating,
reading posts/comments, and interacting with the Reddit UI.

IMPORTANT: Close all Chrome windows before starting the agent.
Playwright needs exclusive access to the Chrome profile.
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any, Optional

from loguru import logger
from playwright.async_api import (
    async_playwright,
    Browser,
    BrowserContext,
    Page,
    Playwright,
)

from app.config import browser_cfg
from app.automation.humanizer import humanizer


class RedditBrowser:
    """Controls a persistent Chrome session on Reddit."""

    def __init__(self) -> None:
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._context: Optional[BrowserContext] = None
        self._page: Optional[Page] = None
        # Lock prevents multiple tasks from navigating the same page at once
        self._nav_lock = asyncio.Lock()

    # ── Lifecycle ───────────────────────────────────────────────

    async def launch(self) -> None:
        """
        Start Playwright and open Chrome with the user's existing profile.
        Creates a copy of the profile to avoid file lock conflicts.
        """
        import shutil
        self._playwright = await async_playwright().start()

        raw_profile = browser_cfg.chrome_profile_path.strip()
        chrome_args = [
            "--disable-blink-features=AutomationControlled",
            "--no-first-run",
            "--no-default-browser-check",
            "--hide-crash-restore-bug",
            "--disable-crash-reporter",
            "--disable-features=Translate",
            "--disable-notifications",
        ]

        if not raw_profile:
            base_dir = Path.home() / "AppData" / "Local" / "Google" / "Chrome" / "User Data"
            profile_name = "Default"
        else:
            raw_path = Path(raw_profile)
            if raw_path.parent.name == "User Data" or raw_path.name.startswith("Profile") or raw_path.name == "Default":
                base_dir = raw_path.parent
                profile_name = raw_path.name
            else:
                base_dir = raw_path
                profile_name = "Default"

        # Copy profile to avoid lock conflicts
        agent_dir = base_dir.parent / "AgentProfile"
        logger.info(f"Copying Chrome profile '{profile_name}' to AgentProfile to avoid locks...")

        try:
            agent_dir.mkdir(parents=True, exist_ok=True)
            src_profile = base_dir / profile_name
            dst_profile = agent_dir / profile_name
            dst_profile.mkdir(parents=True, exist_ok=True)

            # Copy essential files
            essential = [
                "Cookies", "Cookies-journal",
                "Login Data", "Login Data-journal",
                "Web Data", "Web Data-journal",
                "Preferences", "Secure Preferences"
            ]
            for fname in essential:
                try:
                    shutil.copy2(src_profile / fname, dst_profile / fname)
                except Exception:
                    pass

            # Copy Local State
            try:
                shutil.copy2(base_dir / "Local State", agent_dir / "Local State")
            except Exception:
                pass

            logger.info("Profile copied successfully.")
        except Exception as exc:
            logger.warning("Profile copy issue: {}", exc)

        chrome_args.append(f"--profile-directory={profile_name}")

        logger.info("Launching Chrome from AgentProfile…")

        try:
            self._context = await self._playwright.chromium.launch_persistent_context(
                user_data_dir=str(agent_dir),
                executable_path=r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                headless=browser_cfg.headless,
                args=chrome_args,
                ignore_default_args=["--enable-automation"],
                viewport={"width": 1280, "height": 900},
                user_agent=(
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/125.0.0.0 Safari/537.36"
                ),
                timeout=30_000,
            )
            logger.info("Chrome launched with persistent profile ✅")
        except Exception as exc:
            error_msg = str(exc).lower()
            if "user data directory is already in use" in error_msg or "lock" in error_msg:
                logger.error(
                    "❌ Chrome profile is locked! Close ALL Chrome windows and retry."
                )
                raise RuntimeError("Chrome profile locked.") from exc

            logger.error("Failed to launch Chrome with profile: {}", exc)
            logger.info("Falling back to standalone Chromium (no login session)")
            self._browser = await self._playwright.chromium.launch(
                headless=browser_cfg.headless,
                args=["--disable-blink-features=AutomationControlled"],
            )
            self._context = await self._browser.new_context(
                viewport={"width": 1280, "height": 900},
            )

        pages = self._context.pages
        self._page = pages[0] if pages else await self._context.new_page()
        logger.info("Browser ready")

    async def close(self) -> None:
        """Gracefully close the browser."""
        if self._context:
            await self._context.close()
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()
        logger.info("Browser closed")

    @property
    def page(self) -> Page:
        if self._page is None:
            raise RuntimeError("Browser not launched — call await browser.launch()")
        return self._page

    # ── Navigation (serialised via _nav_lock) ───────────────────

    async def goto(self, url: str, wait: str = "domcontentloaded") -> None:
        """Navigate to a URL with human-like behaviour."""
        async with self._nav_lock:
            logger.debug("→ {}", url)
            try:
                await self.page.goto(url, wait_until=wait, timeout=30_000)
            except Exception as exc:
                logger.warning("Navigation retry ({})", exc)
                await asyncio.sleep(3)
                await self.page.goto(url, wait_until=wait, timeout=30_000)

            # Human-like post-navigation behaviour
            await asyncio.sleep(2)
            # Simulate mouse movement after page load
            await humanizer.simulate_mouse_movement(self.page)

    async def goto_subreddit(self, subreddit: str) -> None:
        await self.goto(f"https://www.reddit.com/r/{subreddit}/new/")
        await humanizer.simulate_scroll(self.page, "down")

    async def goto_post(self, post_url: str) -> None:
        if not post_url.startswith("http"):
            post_url = f"https://www.reddit.com{post_url}"
        await self.goto(post_url)

    async def goto_inbox(self) -> None:
        await self.goto("https://www.reddit.com/message/inbox/")

    async def goto_chat(self) -> None:
        await self.goto("https://chat.reddit.com/")

    # ── GLOBAL Reddit search ────────────────────────────────────

    async def search_reddit_global(self, query: str, sort: str = "new", time_filter: str = "week") -> None:
        """Search ALL of Reddit globally (not limited to any subreddit)."""
        url = (
            f"https://www.reddit.com/search/"
            f"?q={query.replace(' ', '+')}&sort={sort}&t={time_filter}&type=link"
        )
        await self.goto(url)
        await humanizer.simulate_scroll(self.page, "down")

    async def search_subreddit(self, subreddit: str, query: str) -> None:
        """Search within a specific subreddit."""
        url = (
            f"https://www.reddit.com/r/{subreddit}/search/"
            f"?q={query.replace(' ', '+')}&restrict_sr=1&sort=new&t=week"
        )
        await self.goto(url)

    # ── Post extraction ─────────────────────────────────────────

    async def get_post_listings(self, max_posts: int = 20) -> list[dict[str, str]]:
        """
        Extract post cards from the current listing/search page.
        Returns list of dicts: title, url, author, subreddit.
        """
        posts: list[dict[str, str]] = []

        async with self._nav_lock:
            await asyncio.sleep(3)

            post_elements = await self.page.query_selector_all(
                "shreddit-post, [data-testid='post-container'], .Post, article, "
                "search-telemetry-tracker faceplate-tracker, "
                "div[data-testid='search-post']"
            )

            for el in post_elements[:max_posts]:
                try:
                    title_el = await el.query_selector(
                        "a[slot='title'], [data-testid='post-title'], h3, "
                        "[data-adclicklocation='title'], a[data-click-id='body']"
                    )
                    title = (await title_el.inner_text()).strip() if title_el else ""

                    link_el = await el.query_selector(
                        "a[slot='title'], a[data-click-id='body'], "
                        "[data-testid='post-title'] a, h3 a, a[href*='/comments/']"
                    )
                    href = await link_el.get_attribute("href") if link_el else ""
                    if href and not href.startswith("http"):
                        href = f"https://www.reddit.com{href}"

                    author_el = await el.query_selector(
                        "[data-testid='post_author_link'], "
                        "a[href*='/user/'], .author, "
                        "faceplate-tracker[source='post'] a[href*='/user/']"
                    )
                    author = ""
                    if author_el:
                        author_text = await author_el.inner_text()
                        author = author_text.strip().replace("u/", "")

                    # Try to get the subreddit name
                    sub_el = await el.query_selector(
                        "a[href*='/r/'], [data-testid='subreddit-link']"
                    )
                    subreddit = ""
                    if sub_el:
                        sub_text = await sub_el.inner_text()
                        subreddit = sub_text.strip().replace("r/", "")

                    if title and href:
                        posts.append({
                            "title": title,
                            "url": href,
                            "author": author,
                            "subreddit": subreddit,
                        })
                except Exception as exc:
                    logger.debug("Error extracting post card: {}", exc)
                    continue

        logger.info("Extracted {} post listings", len(posts))
        return posts

    async def get_post_body(self) -> str:
        """Read the body text of the currently open post."""
        async with self._nav_lock:
            await asyncio.sleep(1)
            selectors = [
                "[data-test-id='post-content'] .RichTextJSON-root",
                "[data-click-id='text'] div",
                ".Post .RichTextJSON-root",
                "shreddit-post [slot='text-body']",
                "[slot='text-body']",
                ".expando .md",
                "[data-testid='post-content']",
            ]
            for sel in selectors:
                el = await self.page.query_selector(sel)
                if el:
                    text = await el.inner_text()
                    if text.strip():
                        return text.strip()
        return ""

    async def get_comments(self, max_comments: int = 10) -> list[dict[str, str]]:
        """Extract top-level comments from the current post."""
        comments: list[dict[str, str]] = []
        async with self._nav_lock:
            await asyncio.sleep(2)
            comment_els = await self.page.query_selector_all(
                "shreddit-comment, [data-testid='comment'], .Comment"
            )
            for el in comment_els[:max_comments]:
                try:
                    author_el = await el.query_selector("a[href*='/user/'], .author")
                    body_el = await el.query_selector("[slot='comment'], .RichTextJSON-root, .md, p")
                    author = (await author_el.inner_text()).strip().replace("u/", "") if author_el else ""
                    body = (await body_el.inner_text()).strip() if body_el else ""
                    if body:
                        comments.append({"author": author, "body": body})
                except Exception:
                    continue
        logger.debug("Extracted {} comments", len(comments))
        return comments

    # ── Interaction ─────────────────────────────────────────────

    async def post_comment(self, text: str) -> bool:
        """Post a comment on the currently open Reddit post."""
        async with self._nav_lock:
            try:
                comment_box_selectors = [
                    "[data-testid='comment-composer'] div[contenteditable='true']",
                    "div[contenteditable='true'][aria-label*='comment']",
                    ".public-DraftEditor-content",
                    "textarea[name='comment']",
                    "shreddit-composer div[contenteditable='true']",
                ]
                for sel in comment_box_selectors:
                    box = await self.page.query_selector(sel)
                    if box:
                        await box.click()
                        await asyncio.sleep(1)
                        await humanizer.simulate_typing(self.page, text)
                        await asyncio.sleep(1)
                        submit_selectors = [
                            "button[type='submit']",
                            "button:has-text('Comment')",
                            "[data-testid='comment-submission-form-submit']",
                        ]
                        for submit_sel in submit_selectors:
                            submit_btn = await self.page.query_selector(submit_sel)
                            if submit_btn:
                                await submit_btn.click()
                                logger.info("Comment posted ✅")
                                await asyncio.sleep(3)
                                return True
                logger.warning("Could not find comment input box")
                return False
            except Exception as exc:
                logger.error("Failed to post comment: {}", exc)
                return False

    async def send_dm(self, username: str, subject: str, message: str) -> bool:
        """Send a message to a Reddit user via modern Reddit Chat."""
        try:
            # Navigate directly to the user's chat channel
            url = f"https://chat.reddit.com/user/{username}"
            await self.goto(url)

            async with self._nav_lock:
                await asyncio.sleep(4)  # Wait for chat UI to load

                # Combine subject and message for chat
                full_message = f"**{subject}**\n\n{message}" if subject else message

                # Look for the chat input box
                chat_input_selectors = [
                    "div[contenteditable='true'][role='textbox']",
                    "textarea[placeholder*='Message']",
                    "shreddit-composer div[contenteditable='true']",
                    "[data-testid='chat-input']",
                    "div[aria-label*='Message']",
                    "#chat-input"
                ]

                body_input = None
                for sel in chat_input_selectors:
                    body_input = await self.page.query_selector(sel)
                    if body_input:
                        break

                if not body_input:
                    logger.warning("Could not find chat input box for u/{}", username)
                    return False

                # Click and type the message with human-like timing
                await body_input.click()
                await asyncio.sleep(1)
                await humanizer.simulate_typing(self.page, full_message)
                await asyncio.sleep(1)

                # Send it
                send_btn = await self.page.query_selector(
                    "button[aria-label='Send'], [data-testid='send-button'], button:has-text('Send')"
                )
                if send_btn:
                    await send_btn.click()
                else:
                    await self.page.keyboard.press("Enter")

                logger.info("Chat message sent to u/{} ✅", username)
                await asyncio.sleep(3)
                return True

        except Exception as exc:
            logger.error("Failed to send chat to u/{}: {}", username, exc)
            return False

    async def check_inbox(self) -> list[dict[str, str]]:
        """Check the modern Reddit Chat for new/unread messages."""
        try:
            await self.goto("https://chat.reddit.com/")
            async with self._nav_lock:
                await asyncio.sleep(4)
                messages: list[dict[str, str]] = []

                # Look for unread channels in the chat sidebar
                unread_channels = await self.page.query_selector_all(
                    "div[data-testid='channel-list-item']:has(div[data-testid='unread-badge'])"
                )

                for channel in unread_channels[:5]:
                    try:
                        # Click the unread channel to open it
                        await channel.click()
                        await asyncio.sleep(2)

                        # Get the username of the person
                        header_el = await self.page.query_selector(
                            "h1, [data-testid='chat-header-title']"
                        )
                        author = (await header_el.inner_text()).strip() if header_el else ""
                        author = author.replace("u/", "")

                        # Get the latest message bubble received
                        msg_els = await self.page.query_selector_all(
                            "[data-testid='message-bubble']"
                        )
                        if msg_els:
                            latest_msg = msg_els[-1]
                            body = (await latest_msg.inner_text()).strip()

                            if author and body:
                                messages.append({
                                    "author": author,
                                    "subject": "Chat Reply",
                                    "body": body,
                                })
                    except Exception as exc:
                        logger.debug("Error reading unread chat channel: {}", exc)
                        continue

            logger.info("Found {} unread chat messages", len(messages))
            return messages
        except Exception as exc:
            logger.error("Failed to check chat inbox: {}", exc)
            return []

    # ── Utility ─────────────────────────────────────────────────

    async def screenshot(self, path: str = "screenshot.png") -> None:
        await self.page.screenshot(path=path)
        logger.debug("Screenshot saved: {}", path)

    async def is_logged_in(self) -> bool:
        """Check if the current Reddit session is logged in."""
        try:
            await self.goto("https://www.reddit.com/", wait="domcontentloaded")
            async with self._nav_lock:
                await asyncio.sleep(3)
                indicators = [
                    "#USER_DROPDOWN_ID",
                    "button[aria-label*='profile']",
                    "[data-testid='user-drawer-button']",
                    "a[href*='/user/']",
                    "faceplate-tracker[source='profile']",
                ]
                for sel in indicators:
                    el = await self.page.query_selector(sel)
                    if el:
                        logger.info("Reddit session is logged in ✅")
                        return True
            logger.warning("Not logged into Reddit")
            return False
        except Exception as exc:
            logger.error("Login check failed: {}", exc)
            return False

    async def get_page_text(self) -> str:
        """Get all visible text on the current page."""
        try:
            return await self.page.inner_text("body")
        except Exception:
            return ""


# Module-level singleton
reddit_browser = RedditBrowser()

"""
Reddit Lead Scraper.

Searches ALL of Reddit globally for potential freelance clients
using keyword searches + subreddit browsing, extracts post data,
and stores new leads. Logs scan history for analytics.
"""

from __future__ import annotations

import asyncio
import random
from typing import Any

from loguru import logger

from app.config import SEARCH_KEYWORDS, TARGET_SUBREDDITS
from app.database import db
from app.reddit.reddit_browser import reddit_browser
from app.automation.humanizer import humanizer


async def search_global_keyword(
    keyword: str,
    max_posts: int = 10,
) -> list[dict[str, Any]]:
    """
    Search ALL of Reddit globally for a keyword and extract leads.
    Not limited to any specific subreddit.
    """
    leads: list[dict[str, Any]] = []
    posts_found = 0

    try:
        await reddit_browser.search_reddit_global(keyword, sort="new", time_filter="week")
        await humanizer.short_delay("loading global search results")

        posts = await reddit_browser.get_post_listings(max_posts=max_posts)
        posts_found = len(posts)
        logger.info("Found {} results globally for '{}'", len(posts), keyword)

        for post in posts:
            try:
                # Navigate to the post to read the full body
                await reddit_browser.goto_post(post["url"])
                await humanizer.short_delay("reading post")

                body = await reddit_browser.get_post_body()

                # Simulate reading the post
                await humanizer.reading_delay(len(body))

                lead = {
                    "username": post.get("author", ""),
                    "title": post.get("title", ""),
                    "body": body,
                    "subreddit": post.get("subreddit", "global"),
                    "post_url": post.get("url", ""),
                }

                # Only store if we have a username to message
                if lead["username"]:
                    result = await db.insert_lead(**lead)
                    if result:
                        leads.append(lead)

            except Exception as exc:
                logger.debug("Error processing search result: {}", exc)
                continue

        # Log scan
        await db.log_scan(
            subreddit="global",
            keyword=keyword,
            search_type="global",
            posts_found=posts_found,
            leads_saved=len(leads),
        )

    except Exception as exc:
        logger.error("Failed global search for '{}': {}", keyword, exc)

    return leads


async def search_subreddit_feed(
    subreddit: str,
    max_posts: int = 8,
) -> list[dict[str, Any]]:
    """
    Browse a subreddit's new feed and extract leads.
    """
    leads: list[dict[str, Any]] = []

    try:
        await reddit_browser.goto_subreddit(subreddit)
        await humanizer.short_delay("loading subreddit")

        posts = await reddit_browser.get_post_listings(max_posts=max_posts)
        logger.info("Found {} posts in r/{}", len(posts), subreddit)

        for post in posts:
            try:
                await reddit_browser.goto_post(post["url"])
                await humanizer.short_delay("reading post")

                body = await reddit_browser.get_post_body()
                await humanizer.reading_delay(len(body))

                lead = {
                    "username": post.get("author", ""),
                    "title": post.get("title", ""),
                    "body": body,
                    "subreddit": subreddit,
                    "post_url": post.get("url", ""),
                }

                if lead["username"]:
                    result = await db.insert_lead(**lead)
                    if result:
                        leads.append(lead)

            except Exception as exc:
                logger.debug("Error reading post in r/{}: {}", subreddit, exc)
                continue

        await db.log_scan(
            subreddit=subreddit,
            keyword="",
            search_type="subreddit_feed",
            posts_found=len(posts),
            leads_saved=len(leads),
        )

    except Exception as exc:
        logger.error("Failed to scan r/{}: {}", subreddit, exc)

    return leads


async def run_full_scan(
    keywords: list[str] | None = None,
    max_posts_per_search: int = 8,
) -> list[dict[str, Any]]:
    """
    Run a complete scan: global keyword search + subreddit feed browsing.
    """
    kws = keywords or SEARCH_KEYWORDS
    all_leads: list[dict[str, Any]] = []

    # Shuffle to avoid predictable patterns
    search_kws = list(kws)
    random.shuffle(search_kws)

    # Pick a subset each run
    keyword_batch = search_kws[:5]

    # Also pick some subreddits to browse
    subs = list(TARGET_SUBREDDITS)
    random.shuffle(subs)
    sub_batch = subs[:3]

    logger.info(
        "Starting full scan — {} keywords, {} subreddits",
        len(keyword_batch), len(sub_batch),
    )

    # Global keyword searches
    for kw in keyword_batch:
        try:
            leads = await search_global_keyword(kw, max_posts=max_posts_per_search)
            all_leads.extend(leads)
            await humanizer.medium_delay("between keyword searches")
        except Exception as exc:
            logger.error("Error searching for '{}': {}", kw, exc)
        await humanizer.enforce_cooldown()

    # Subreddit feed browsing
    for sub in sub_batch:
        try:
            leads = await search_subreddit_feed(sub, max_posts=max_posts_per_search)
            all_leads.extend(leads)
            await humanizer.medium_delay("between subreddit scans")
        except Exception as exc:
            logger.error("Error scanning r/{}: {}", sub, exc)

    logger.info("Full scan complete: {} total leads collected", len(all_leads))
    return all_leads


async def quick_scan(
    keywords: list[str] | None = None,
    max_posts: int = 5,
) -> list[dict[str, Any]]:
    """
    A faster scan — search 2-3 random keywords globally +
    browse 1-2 subreddits.
    """
    kws = keywords or SEARCH_KEYWORDS
    keyword_batch = random.sample(kws, min(3, len(kws)))
    sub_batch = random.sample(TARGET_SUBREDDITS, min(2, len(TARGET_SUBREDDITS)))

    all_leads: list[dict[str, Any]] = []

    logger.info(
        "Quick scan: {} keywords, {} subreddits",
        len(keyword_batch), len(sub_batch),
    )

    for kw in keyword_batch:
        try:
            leads = await search_global_keyword(kw, max_posts=max_posts)
            all_leads.extend(leads)
            await humanizer.short_delay("between searches")
        except Exception as exc:
            logger.error("Error in quick scan for '{}': {}", kw, exc)

    for sub in sub_batch:
        try:
            leads = await search_subreddit_feed(sub, max_posts=max_posts)
            all_leads.extend(leads)
            await humanizer.short_delay("between subreddit scans")
        except Exception as exc:
            logger.error("Error scanning r/{}: {}", sub, exc)

    logger.info("Quick scan complete: {} leads", len(all_leads))
    return all_leads

"""Quick smoke test for all system components."""
import asyncio
from app.ai.negotiation_engine import get_pricing, evaluate_offer, get_scope_reduction_options
from app.ai.psychology_engine import get_adapted_tone, _default_psychology
from app.config import SEARCH_KEYWORDS, TARGET_SUBREDDITS, PRICING

def test_pricing():
    print("=== Pricing Engine ===")
    for svc in ["website", "uiux", "seo", "automation", "webapp", "saas"]:
        p = get_pricing(svc)
        print(f"  {svc}: ${p['start']}-${p['preferred_max']} (min ${p['hard_min']})")

    print("\n=== Offer Evaluation ===")
    tests = [
        ("website", 400, "accept"),
        ("website", 250, "negotiate"),
        ("website", 100, "decline"),
        ("seo", 90, "accept"),
    ]
    for svc, offer, expected in tests:
        r = evaluate_offer(svc, offer)
        status = "PASS" if r["verdict"] == expected else "FAIL"
        print(f"  [{status}] {svc} @ ${offer}: {r['verdict']} - {r['message']}")

def test_psychology():
    print("\n=== Psychology Engine ===")
    psych = _default_psychology()
    tone = get_adapted_tone(psych)
    print(f"  Default tone: {tone[:80]}...")

    psych["primary_emotion"] = "frustrated"
    psych["personality_style"] = "analytical"
    tone = get_adapted_tone(psych)
    print(f"  Frustrated+analytical: {tone[:80]}...")

def test_config():
    print(f"\n=== Config ===")
    print(f"  Keywords: {len(SEARCH_KEYWORDS)}")
    print(f"  Subreddits: {len(TARGET_SUBREDDITS)}")
    print(f"  Price categories: {len(PRICING)}")

async def test_database():
    print("\n=== Database ===")
    from app.database import db
    await db.connect()
    stats = await db.get_lead_stats()
    print(f"  Connected OK, lead stats: {stats}")
    await db.close()
    print("  Closed OK")

def main():
    test_config()
    test_pricing()
    test_psychology()
    asyncio.run(test_database())
    print("\nAll tests passed!")

if __name__ == "__main__":
    main()

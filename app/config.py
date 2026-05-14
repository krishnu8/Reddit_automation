"""
Centralized configuration for the Reddit AI Agent.

Loads all settings from .env file and provides validated
configuration objects used throughout the application.
"""

from pathlib import Path
from pydantic_settings import BaseSettings
from pydantic import Field


# Project root directory (parent of /app)
PROJECT_ROOT = Path(__file__).resolve().parent.parent


class OllamaSettings(BaseSettings):
    """Ollama local AI model configuration."""
    model_slow: str = Field(default="llama3", alias="MODEL_SLOW")
    model_fast: str = Field(default="phi3", alias="MODEL_FAST")
    ollama_url: str = Field(
        default="http://localhost:11434/api/generate",
        alias="OLLAMA_URL",
    )

    model_config = {"env_file": PROJECT_ROOT / ".env", "extra": "ignore"}


class BrowserSettings(BaseSettings):
    """Playwright browser configuration."""
    headless: bool = Field(default=False, alias="HEADLESS")
    chrome_profile_path: str = Field(default="", alias="CHROME_PROFILE_PATH")

    model_config = {"env_file": PROJECT_ROOT / ".env", "extra": "ignore"}


class RateLimitSettings(BaseSettings):
    """Rate limiting to avoid spam-like behaviour."""
    max_dms_per_day: int = Field(default=20, alias="MAX_DMS_PER_DAY")
    max_replies_per_hour: int = Field(default=5, alias="MAX_REPLIES_PER_HOUR")
    max_scans_per_hour: int = Field(default=10, alias="MAX_SCANS_PER_HOUR")

    model_config = {"env_file": PROJECT_ROOT / ".env", "extra": "ignore"}


class TimingSettings(BaseSettings):
    """Human-like delay configuration."""
    reply_delay_min: int = Field(default=20, alias="REPLY_DELAY_MIN")
    reply_delay_max: int = Field(default=90, alias="REPLY_DELAY_MAX")
    typing_delay_min: float = Field(default=0.05, alias="TYPING_DELAY_MIN")
    typing_delay_max: float = Field(default=0.15, alias="TYPING_DELAY_MAX")

    model_config = {"env_file": PROJECT_ROOT / ".env", "extra": "ignore"}


class ScanSettings(BaseSettings):
    """Scanning and polling intervals."""
    scan_interval_minutes: int = Field(default=30, alias="SCAN_INTERVAL_MINUTES")
    message_poll_interval_seconds: int = Field(
        default=60, alias="MESSAGE_POLL_INTERVAL_SECONDS"
    )

    model_config = {"env_file": PROJECT_ROOT / ".env", "extra": "ignore"}


class DashboardSettings(BaseSettings):
    """Dashboard web server configuration."""
    dashboard_host: str = Field(default="127.0.0.1", alias="DASHBOARD_HOST")
    dashboard_port: int = Field(default=8080, alias="DASHBOARD_PORT")
    dashboard_secret_key: str = Field(
        default="change-this-to-a-random-secret-key",
        alias="DASHBOARD_SECRET_KEY",
    )

    model_config = {"env_file": PROJECT_ROOT / ".env", "extra": "ignore"}


class DatabaseSettings(BaseSettings):
    """Database path configuration."""
    database_path: str = Field(default="app/storage/app.db", alias="DATABASE_PATH")

    model_config = {"env_file": PROJECT_ROOT / ".env", "extra": "ignore"}

    @property
    def absolute_path(self) -> Path:
        """Return the absolute path to the database file."""
        db_path = Path(self.database_path)
        if db_path.is_absolute():
            return db_path
        return PROJECT_ROOT / db_path


class LogSettings(BaseSettings):
    """Logging configuration."""
    log_level: str = Field(default="DEBUG", alias="LOG_LEVEL")
    log_file: str = Field(default="app/storage/agent.log", alias="LOG_FILE")

    model_config = {"env_file": PROJECT_ROOT / ".env", "extra": "ignore"}

    @property
    def absolute_log_path(self) -> Path:
        log_path = Path(self.log_file)
        if log_path.is_absolute():
            return log_path
        return PROJECT_ROOT / log_path


class LeadSettings(BaseSettings):
    """Lead scoring configuration."""
    min_lead_quality: int = Field(default=70, alias="MIN_LEAD_QUALITY")

    model_config = {"env_file": PROJECT_ROOT / ".env", "extra": "ignore"}


class AutoSendSettings(BaseSettings):
    """Auto-send toggle — controls whether DMs are sent automatically."""
    auto_send_enabled: bool = Field(default=True, alias="AUTO_SEND_ENABLED")

    model_config = {"env_file": PROJECT_ROOT / ".env", "extra": "ignore"}


# ── Target subreddits ───────────────────────────────────────────

TARGET_SUBREDDITS: list[str] = [
    "forhire",
    "freelance_forhire",
    "webdev",
    "Entrepreneur",
    "startups",
    "smallbusiness",
    "slavelabour",
    "seo",
    "UI_Design",
    "web_design",
    "shopify",
    "wordpress",
    "SaaS",
    "artificial",
    "ecommerce",
    "agency",
    "digitalnomad",
    "programming",
    "business",
    "sideproject",
]

# ── Search keywords (direct, indirect, problem-based) ───────────

SEARCH_KEYWORDS_DIRECT: list[str] = [
    "hiring developer",
    "hiring web developer",
    "need website",
    "looking for freelancer",
    "need UI designer",
    "need UX designer",
    "need automation",
    "need SEO help",
    "freelance developer",
    "need landing page",
    "need web app",
    "startup needs developer",
    "need MVP",
    "need dashboard",
    "need redesign",
    "need Shopify developer",
    "need WordPress developer",
    "need AI automation",
    "need API integration",
    "looking for someone to build",
    "need programmer",
    "developer wanted",
    "looking for technical partner",
]

SEARCH_KEYWORDS_INDIRECT: list[str] = [
    "website too slow",
    "how much does website cost",
    "need help scaling",
    "repetitive manual task",
    "losing traffic",
    "startup tech issue",
    "need recommendation",
    "how do I build",
    "who can create",
    "can someone help me",
    "best way to automate",
    "website cost",
    "need help with website",
    "my business needs",
    "how much for a website",
]

SEARCH_KEYWORDS_PROBLEMS: list[str] = [
    "bad conversion rate",
    "SEO issue",
    "slow website",
    "workflow problem",
    "customer management issue",
    "dashboard problem",
    "ecommerce slow",
    "website broken",
    "need CRM",
    "admin panel issue",
]

# Combined master list
SEARCH_KEYWORDS: list[str] = (
    SEARCH_KEYWORDS_DIRECT
    + SEARCH_KEYWORDS_INDIRECT
    + SEARCH_KEYWORDS_PROBLEMS
)

# ── Pricing configuration ──────────────────────────────────────

PRICING = {
    "website": {"start": 300, "preferred_min": 300, "preferred_max": 800, "hard_min": 230},
    "uiux": {"start": 80, "preferred_min": 80, "preferred_max": 200, "hard_min": 60},
    "seo": {"start": 80, "preferred_min": 80, "preferred_max": 150, "hard_min": 60},
    "automation": {"start": 150, "preferred_min": 150, "preferred_max": 500, "hard_min": 120},
    "webapp": {"start": 400, "preferred_min": 400, "preferred_max": 1500, "hard_min": 300},
    "dashboard": {"start": 300, "preferred_min": 300, "preferred_max": 800, "hard_min": 230},
    "ecommerce": {"start": 350, "preferred_min": 350, "preferred_max": 1000, "hard_min": 280},
    "saas": {"start": 500, "preferred_min": 500, "preferred_max": 2000, "hard_min": 400},
    "landing_page": {"start": 150, "preferred_min": 150, "preferred_max": 400, "hard_min": 120},
    "api_integration": {"start": 200, "preferred_min": 200, "preferred_max": 600, "hard_min": 150},
    "other": {"start": 200, "preferred_min": 200, "preferred_max": 600, "hard_min": 150},
}


# ── Singleton config instances ──────────────────────────────────

ollama_cfg = OllamaSettings()
browser_cfg = BrowserSettings()
rate_limit_cfg = RateLimitSettings()
timing_cfg = TimingSettings()
scan_cfg = ScanSettings()
dashboard_cfg = DashboardSettings()
db_cfg = DatabaseSettings()
log_cfg = LogSettings()
lead_cfg = LeadSettings()
auto_send_cfg = AutoSendSettings()

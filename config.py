"""Winslow scraper configuration."""
import os
from dataclasses import dataclass, field
from dotenv import load_dotenv

load_dotenv()


@dataclass
class Config:
    BRAND_NAME: str = "Winslow"
    SOURCE: str = "scraper-winslow"
    BRAND_COLUMN: str = "Winslow"
    SECOND_HAND: bool = False
    LANDING_PAGE: str = "https://winslowla.com/"

    CATEGORY_URLS: list[str] = field(default_factory=lambda: [
        "https://winslowla.com/collections/hoodies",
        "https://winslowla.com/collections/tees",
        "https://winslowla.com/collections/sweaters",
        "https://winslowla.com/collections/outerwear",
        "https://winslowla.com/collections/sweatpants",
        "https://winslowla.com/collections/hats",
    ])

    CATEGORY_DISPLAY: dict[str, str] = field(default_factory=lambda: {
        "hoodies": "Hoodies",
        "tees": "Tees",
        "sweaters": "Sweaters",
        "outerwear": "Outerwear",
        "sweatpants": "Sweatpants",
        "hats": "Hats",
    })

    SUPABASE_URL: str = field(default_factory=lambda: os.getenv("SUPABASE_URL", ""))
    SUPABASE_KEY: str = field(default_factory=lambda: os.getenv("SUPABASE_KEY", ""))

    EMBEDDING_MODEL: str = "google/siglip-base-patch16-384"
    EMBEDDING_DIM: int = 768
    EMBEDDING_VERSION: int = 2
    RATE_LIMIT_DELAY: float = 1.0
    BATCH_SIZE: int = 5
    STALE_MISS_THRESHOLD: int = 2
    REQUEST_TIMEOUT: int = 30
    USER_AGENT: str = (
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
    )


cfg = Config()

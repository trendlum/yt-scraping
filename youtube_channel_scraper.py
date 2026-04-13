from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SRC_PATH = ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from yt_insights.cli import build_argument_parser, main
from yt_insights.config import load_dotenv
from yt_insights.exceptions import SupabaseAPIError, YouTubeAPIError
from yt_insights.services.scraper import scrape_and_store_channels, scrape_channel_latest_videos

__all__ = [
    "YouTubeAPIError",
    "SupabaseAPIError",
    "load_dotenv",
    "build_argument_parser",
    "scrape_channel_latest_videos",
    "scrape_and_store_channels",
    "main",
]


if __name__ == "__main__":
    raise SystemExit(main())

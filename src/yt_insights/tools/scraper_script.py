from ..cli import build_argument_parser, main
from ..config import load_dotenv
from ..exceptions import SupabaseAPIError, YouTubeAPIError
from ..services.scraper import scrape_and_store_channels, scrape_channel_latest_videos

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

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parent
SRC_PATH = ROOT / "src"
if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))

from yt_insights.tools.transcript_backfill_script import *  # noqa: F403

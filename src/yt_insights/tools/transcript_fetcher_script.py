from ..transcript_cli import build_argument_parser, fetch_transcript, get_video_id, main, save_to_json

__all__ = [
    "build_argument_parser",
    "fetch_transcript",
    "get_video_id",
    "main",
    "save_to_json",
]


if __name__ == "__main__":
    raise SystemExit(main())

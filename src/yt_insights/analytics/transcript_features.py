from __future__ import annotations

import logging
from dataclasses import dataclass

import requests

from ..clients.http import build_retry_session
from ..constants import DEFAULT_TIMEOUT
from ..models import VideoFeatureRecord
from ..transcript_cli import (
    TranscriptDependencyError,
    TranscriptIpBlockedError,
    TranscriptNetworkError,
    TranscriptNotAvailableError,
    TranscriptRequestBlockedError,
    VideoUnplayableError,
    VideoUnavailableError,
    fetch_transcript,
    create_youtube_transcript_api,
)


LOGGER = logging.getLogger(__name__)


@dataclass(slots=True)
class TranscriptFeatures:
    status: str
    language: str | None
    is_auto_generated: bool | None
    transcript_text: str | None


class TranscriptFeatureExtractor:
    def __init__(
        self,
        *,
        timeout: int = DEFAULT_TIMEOUT,
        session: requests.Session | None = None,
    ) -> None:
        self.timeout = timeout
        self.session = session or build_retry_session()

    def extract_from_video_id(self, video_id: str) -> TranscriptFeatures:
        try:
            youtube_api = create_youtube_transcript_api(self.session)
            result = fetch_transcript(video_id, api=youtube_api)
        except TranscriptNotAvailableError:
            return TranscriptFeatures(
                status="no_captions",
                language=None,
                is_auto_generated=None,
                transcript_text=None,
            )
        except VideoUnavailableError:
            return TranscriptFeatures(
                status="video_unavailable",
                language=None,
                is_auto_generated=None,
                transcript_text=None,
            )
        except VideoUnplayableError as exc:
            LOGGER.warning("Transcript video unplayable for %s: %s", video_id, exc)
            return TranscriptFeatures(
                status="video_unplayable",
                language=None,
                is_auto_generated=None,
                transcript_text=None,
            )
        except TranscriptRequestBlockedError as exc:
            LOGGER.warning("Transcript request blocked for %s: %s", video_id, exc)
            return TranscriptFeatures(
                status="request_blocked",
                language=None,
                is_auto_generated=None,
                transcript_text=None,
            )
        except TranscriptIpBlockedError as exc:
            LOGGER.warning("Transcript IP blocked for %s: %s", video_id, exc)
            return TranscriptFeatures(
                status="ip_blocked",
                language=None,
                is_auto_generated=None,
                transcript_text=None,
            )
        except TranscriptDependencyError as exc:
            LOGGER.warning("Transcript dependency missing for %s: %s", video_id, exc)
            return TranscriptFeatures(
                status="dependency_missing",
                language=None,
                is_auto_generated=None,
                transcript_text=None,
            )
        except TranscriptNetworkError as exc:
            LOGGER.warning("Transcript fetch failed for %s: %s", video_id, exc)
            return TranscriptFeatures(
                status="download_failed",
                language=None,
                is_auto_generated=None,
                transcript_text=None,
            )

        return TranscriptFeatures(
            status="complete",
            language=result.language_code,
            is_auto_generated=result.is_generated,
            transcript_text=result.full_text,
        )


def enrich_transcript_features(
    feature_record: VideoFeatureRecord,
    extractor: TranscriptFeatureExtractor,
) -> VideoFeatureRecord:
    features = extractor.extract_from_video_id(feature_record.video_id)
    feature_record.transcript_status = features.status
    feature_record.transcript_language = features.language
    feature_record.transcript_is_auto_generated = features.is_auto_generated
    feature_record.transcript_text = features.transcript_text
    return feature_record

"""Haystack component that fetches YouTube transcripts as Documents."""

from __future__ import annotations

import logging
from collections.abc import Mapping
from typing import Any

from haystack import Document, component, default_from_dict, default_to_dict
from haystack.utils import Secret, deserialize_secrets_inplace

from getyoutubetranscript import Client, GetYouTubeTranscriptError, to_timed_text

logger = logging.getLogger(__name__)


@component
class GetYouTubeTranscriptFetcher:
    """Fetch the transcripts of YouTube videos and return one Document per video.

    Uses the GetYouTubeTranscript API (https://getyoutubetranscript.com). Reads the API key
    from the ``GETYOUTUBETRANSCRIPT_API_KEY`` environment variable by default.

    ```python
    from haystack_integrations.components.fetchers.getyoutubetranscript import GetYouTubeTranscriptFetcher

    fetcher = GetYouTubeTranscriptFetcher(timestamps=True)
    documents = fetcher.run(videos=["https://youtu.be/jNQXAC9IVRw"])["documents"]
    ```

    ``content`` is the transcript (``[m:ss]`` lines when ``timestamps=True``). ``meta`` has
    ``url``, ``video_id``, ``title``, ``author_name``, ``language_code`` and ``word_count``,
    plus ``segments`` when ``timestamps=True``.
    """

    def __init__(
        self,
        api_key: Secret = Secret.from_env_var("GETYOUTUBETRANSCRIPT_API_KEY"),  # noqa: B008 (Haystack convention; Secret is immutable)
        language: str | None = None,
        timestamps: bool = False,
        raise_on_failure: bool = True,
    ) -> None:
        """
        :param api_key: GetYouTubeTranscript API key.
        :param language: Caption language code, e.g. "en". Defaults to the API default.
        :param timestamps: Return ``[m:ss]`` lines and per-line ``segments`` in meta.
        :param raise_on_failure: Raise on the first failed video. If False, failures are logged
            and skipped, and the other videos are still returned.
        """
        self.api_key = api_key
        self.language = language
        self.timestamps = timestamps
        self.raise_on_failure = raise_on_failure
        self._client: Client | None = None

    def warm_up(self) -> None:
        if self._client is None:
            self._client = Client(api_key=self.api_key.resolve_value() or "")

    def to_dict(self) -> dict[str, Any]:
        return default_to_dict(
            self,
            api_key=self.api_key.to_dict(),
            language=self.language,
            timestamps=self.timestamps,
            raise_on_failure=self.raise_on_failure,
        )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GetYouTubeTranscriptFetcher:
        deserialize_secrets_inplace(data["init_parameters"], keys=["api_key"])
        return default_from_dict(cls, data)

    @component.output_types(documents=list[Document])
    def run(self, videos: list[str]) -> dict[str, list[Document]]:
        """
        :param videos: YouTube video URLs or 11-character video IDs.
        :returns: ``{"documents": [...]}``, one Document per video that succeeded.
        """
        self.warm_up()
        assert self._client is not None
        documents = []
        for video in videos:
            try:
                result = self._client.get_transcript(video, language=self.language, timestamps=self.timestamps)
            except GetYouTubeTranscriptError as e:
                if self.raise_on_failure:
                    raise
                logger.warning("Skipping %s: %s (%s)", video, e.message, e.code)
                continue
            documents.append(self._to_document(result))
        return {"documents": documents}

    def _to_document(self, result: Mapping[str, Any]) -> Document:
        timed = self.timestamps and bool(result.get("segments"))
        meta = {
            "url": f"https://www.youtube.com/watch?v={result['video_id']}",
            "video_id": result["video_id"],
            "title": result.get("title", ""),
            "author_name": result.get("author_name", ""),
            "language_code": result.get("language_code", ""),
            "word_count": result.get("word_count", 0),
        }
        if timed:
            meta["segments"] = result["segments"]
        return Document(content=to_timed_text(result) if timed else result.get("transcript", ""), meta=meta)

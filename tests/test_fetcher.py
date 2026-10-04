from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from getyoutubetranscript import GetYouTubeTranscriptError
from haystack import Pipeline
from haystack.utils import Secret

from haystack_integrations.components.fetchers.getyoutubetranscript import GetYouTubeTranscriptFetcher

RESULT = {
    "video_id": "jNQXAC9IVRw",
    "language_code": "en",
    "title": "Me at the zoo",
    "author_name": "jawed",
    "transcript": "All right, so here we are",
    "word_count": 6,
    "segments": [{"start": 61.0, "duration": 2.0, "text": "All right, so here we are"}],
}


def _fetcher(**kwargs) -> tuple[GetYouTubeTranscriptFetcher, MagicMock]:
    fetcher = GetYouTubeTranscriptFetcher(api_key=Secret.from_token("test-key"), **kwargs)
    client = MagicMock()
    client.get_transcript.return_value = RESULT
    fetcher._client = client
    return fetcher, client


def test_one_document_per_video():
    fetcher, client = _fetcher(language="en")
    docs = fetcher.run(videos=["a", "b"])["documents"]
    assert len(docs) == 2
    assert client.get_transcript.call_args.kwargs == {"language": "en", "timestamps": False}
    assert docs[0].content == "All right, so here we are"
    assert docs[0].meta == {
        "url": "https://www.youtube.com/watch?v=jNQXAC9IVRw",
        "video_id": "jNQXAC9IVRw",
        "title": "Me at the zoo",
        "author_name": "jawed",
        "language_code": "en",
        "word_count": 6,
    }


def test_timestamps():
    fetcher, _ = _fetcher(timestamps=True)
    doc = fetcher.run(videos=["a"])["documents"][0]
    assert doc.content == "[1:01] All right, so here we are"
    assert doc.meta["segments"] == RESULT["segments"]


def test_failures_raise_by_default_or_are_skipped():
    error = GetYouTubeTranscriptError("NOT_FOUND", "No transcript for this video.", 404)
    fetcher, client = _fetcher()
    client.get_transcript.side_effect = [error, RESULT]
    with pytest.raises(GetYouTubeTranscriptError):
        fetcher.run(videos=["bad", "good"])

    fetcher, client = _fetcher(raise_on_failure=False)
    client.get_transcript.side_effect = [error, RESULT]
    assert [d.meta["video_id"] for d in fetcher.run(videos=["bad", "good"])["documents"]] == ["jNQXAC9IVRw"]


def test_serialization_round_trip_keeps_env_secret(monkeypatch):
    monkeypatch.setenv("GETYOUTUBETRANSCRIPT_API_KEY", "env-key")
    fetcher = GetYouTubeTranscriptFetcher(language="es", timestamps=True, raise_on_failure=False)
    data = fetcher.to_dict()
    assert data["init_parameters"]["api_key"] == {
        "type": "env_var",
        "env_vars": ["GETYOUTUBETRANSCRIPT_API_KEY"],
        "strict": True,
    }
    restored = GetYouTubeTranscriptFetcher.from_dict(data)
    assert (restored.language, restored.timestamps, restored.raise_on_failure) == ("es", True, False)
    assert restored.api_key.resolve_value() == "env-key"


def test_works_in_a_pipeline():
    fetcher, _ = _fetcher()
    pipeline = Pipeline()
    pipeline.add_component("fetcher", fetcher)
    assert len(pipeline.run({"fetcher": {"videos": ["a"]}})["fetcher"]["documents"]) == 1

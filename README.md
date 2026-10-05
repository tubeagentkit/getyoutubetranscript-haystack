# getyoutubetranscript-haystack

A [Haystack](https://haystack.deepset.ai) component that fetches YouTube video transcripts as `Document`s, powered by the [GetYouTubeTranscript](https://getyoutubetranscript.com) API. Use it in RAG pipelines, or wrap it as a tool for Haystack agents.

The API fetches transcripts on its own servers, so it works from cloud servers without proxies, and without `RequestBlocked` / `IpBlocked` errors.

## Install

```bash
pip install getyoutubetranscript-haystack
```

Get an API key at [getyoutubetranscript.com/developers](https://getyoutubetranscript.com/developers) (free tier included):

```bash
export GETYOUTUBETRANSCRIPT_API_KEY=sk_live_...
```

## Usage

```python
from haystack_integrations.components.fetchers.getyoutubetranscript import GetYouTubeTranscriptFetcher

fetcher = GetYouTubeTranscriptFetcher()
documents = fetcher.run(videos=["https://youtu.be/jNQXAC9IVRw", "5e37ZT3SQbk"])["documents"]

print(documents[0].meta)
# {'url': 'https://www.youtube.com/watch?v=jNQXAC9IVRw', 'video_id': 'jNQXAC9IVRw', 'title': 'Me at the zoo',
#  'author_name': 'jawed', 'language_code': 'en', 'word_count': 39}
```

One `Document` per video. Parameters:

| Parameter | Default | Description |
| --- | --- | --- |
| `api_key` | `Secret.from_env_var("GETYOUTUBETRANSCRIPT_API_KEY")` | API key |
| `language` | `None` | Caption language code, e.g. `"en"` |
| `timestamps` | `False` | `content` becomes `[m:ss]` lines, and `meta["segments"]` holds `{start, duration, text}` per caption line |
| `raise_on_failure` | `True` | If `False`, videos that fail (no captions, invalid ID) are logged and skipped |

### In a RAG pipeline

```python
from haystack import Pipeline
from haystack.components.preprocessors import DocumentSplitter
from haystack.components.writers import DocumentWriter
from haystack.document_stores.in_memory import InMemoryDocumentStore
from haystack_integrations.components.fetchers.getyoutubetranscript import GetYouTubeTranscriptFetcher

store = InMemoryDocumentStore()
indexing = Pipeline()
indexing.add_component("fetcher", GetYouTubeTranscriptFetcher())
indexing.add_component("splitter", DocumentSplitter(split_by="word", split_length=200))
indexing.add_component("writer", DocumentWriter(document_store=store))
indexing.connect("fetcher.documents", "splitter.documents")
indexing.connect("splitter.documents", "writer.documents")

indexing.run({"fetcher": {"videos": ["https://youtu.be/5e37ZT3SQbk"]}})
```

### As an agent tool

```python
from haystack.tools import ComponentTool
from haystack_integrations.components.fetchers.getyoutubetranscript import GetYouTubeTranscriptFetcher

youtube_tool = ComponentTool(
    component=GetYouTubeTranscriptFetcher(timestamps=True),
    name="youtube_transcript",
    description="Get the transcripts of YouTube videos from their URLs or IDs.",
)
```

The component serializes with `to_dict()` / `from_dict()`, keeping the key as an environment variable reference, so pipelines can be saved as YAML.

## Pricing

Each transcript uses one credit from your GetYouTubeTranscript account. Failed requests are not charged.

## Links

- [GetYouTubeTranscript API docs](https://getyoutubetranscript.com/docs)
- [Python SDK](https://pypi.org/project/getyoutubetranscript/) (this package is built on it)
- [License: MIT](LICENSE)

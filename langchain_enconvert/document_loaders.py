"""EnConvert document loader for LangChain."""

from __future__ import annotations

import json
import os
import time
from typing import Iterator, List, Optional

import requests
from enconvert import Enconvert
from langchain_core.document_loaders import BaseLoader
from langchain_core.documents import Document


class EnconvertLoader(BaseLoader):
    """Load web pages or a whole site into LangChain Documents via EnConvert.

    Pass ``urls=`` to perceive pages into clean-markdown Documents (each carrying
    a ``render_quality`` score), or ``ingest_url=`` to crawl a site into
    RAG-ready chunk Documents.
    """

    def __init__(
        self,
        urls: Optional[List[str]] = None,
        *,
        ingest_url: Optional[str] = None,
        mode: str = "sitemap",
        max_pages: int = 50,
        api_key: Optional[str] = None,
        base_url: str = "https://api.enconvert.com",
        poll_interval: float = 5.0,
    ) -> None:
        self.urls = urls
        self.ingest_url = ingest_url
        self.mode = mode
        self.max_pages = max_pages
        self.base_url = base_url
        self.poll_interval = poll_interval
        self._api_key = api_key or os.environ.get("ENCONVERT_API_KEY", "")

    def lazy_load(self) -> Iterator[Document]:
        if not self._api_key:
            raise ValueError(
                "EnConvert api_key is missing. Pass api_key= or set $ENCONVERT_API_KEY "
                "(a private key starting with sk_)."
            )
        client = Enconvert(api_key=self._api_key, base_url=self.base_url)
        if self.urls:
            for url in self.urls:
                op = client.v2.perceive_direct(url, outputs=["markdown"])
                yield Document(
                    page_content=op.content.decode("utf-8", "replace"),
                    metadata={"source": url, "render_quality": op.render_quality},
                )
        elif self.ingest_url:
            yield from _ingest(
                client, self.ingest_url, self.mode, self.max_pages, self.poll_interval
            )
        else:
            raise ValueError("Provide urls=[...] or ingest_url=...")


def _ingest(
    client: Enconvert,
    url: str,
    mode: str,
    max_pages: int,
    poll_interval: float,
) -> Iterator[Document]:
    job = client.v2.ingest(mode=mode, url=url, max_pages=max_pages)
    while True:
        status = client.v2.get_ingest_job(job.job_id)
        if status.status in ("completed", "failed", "cancelled"):
            break
        time.sleep(poll_interval)
    if status.status != "completed":
        raise RuntimeError(f"EnConvert ingest job {job.job_id} ended: {status.status}")
    resp = requests.get(status.output_url, timeout=120)
    resp.raise_for_status()
    yield from _chunks_to_documents(resp.text)


def _chunks_to_documents(jsonl_text: str) -> Iterator[Document]:
    """Map an EnConvert ingest JSONL (one chunk per line) to LangChain Documents.

    Schema-agnostic: text comes from ``content`` (or ``text``); the rest becomes
    metadata, with ``source`` set from the chunk's URL for LangChain provenance.
    """
    for line in jsonl_text.splitlines():
        line = line.strip()
        if not line:
            continue
        chunk = json.loads(line)
        text = chunk.pop("content", None) or chunk.pop("text", "")
        src = chunk.get("source_url") or chunk.get("url")
        if src and "source" not in chunk:
            chunk["source"] = src
        yield Document(page_content=text, metadata=chunk)


if __name__ == "__main__":
    sample = (
        '{"content": "hello", "source_url": "https://x.com", "chunk_index": 0}\n'
        "\n"
        '{"text": "world", "title": "W"}'
    )
    out = list(_chunks_to_documents(sample))
    assert len(out) == 2, out
    assert out[0].page_content == "hello" and out[0].metadata["source"] == "https://x.com"
    assert out[1].page_content == "world" and out[1].metadata["title"] == "W"
    print("ok")

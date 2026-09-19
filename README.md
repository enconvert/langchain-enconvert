# EnConvert loader for LangChain

`langchain-enconvert` turns web pages and whole sites into LangChain `Document`s through
[EnConvert](https://www.enconvert.com). Every perceived page carries a `render_quality` score (0.0-1.0)
in its metadata, so a blocked or empty page comes back flagged rather than trusted.

## Install

```bash
pip install langchain-enconvert
```

## Use

```python
from langchain_enconvert import EnconvertLoader

# A few URLs into clean-markdown Documents:
docs = EnconvertLoader(urls=["https://example.com", "https://example.com/pricing"]).load()

# Or a whole site into RAG-ready chunk Documents:
docs = EnconvertLoader(ingest_url="https://docs.example.com", mode="sitemap", max_pages=100).load()
```

- **URLs** are perceived into markdown; metadata carries `source` and `render_quality`.
- **`ingest_url`** crawls the site (async; the loader polls to completion), then returns one Document per
  chunk, each carrying the chunk's own metadata (`source`, title, etc.).
- `.lazy_load()` streams Documents one at a time.

Auth: a **private** key (`sk_...`) from your [dashboard](https://www.enconvert.com/dashboard/api-keys).
Public `pk_` keys are rejected. The key is read from `api_key=` or `$ENCONVERT_API_KEY`.

## Licence

[MIT](LICENSE)

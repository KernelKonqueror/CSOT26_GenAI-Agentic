# Lesson 3: arXiv Paper Search & Read

Week 2 used the AlphaXiv MCP server for papers. Week 3 replaces that with the Hugging Face Papers API. You are free to interact with the API or use their MCP.

---

## What HF Papers actually indexes

**This does not search all of arXiv.** It searches papers indexed on [huggingface.co/papers](https://huggingface.co/papers) — a large subset of ML/CS arXiv papers that have Hub pages (linked from model cards, Daily Papers submissions, etc.).

If a paper returns 404, it isn't indexed yet. Fall back to `web_search` + `web_fetch` on `arxiv.org/abs/...`.

For most ML research questions, the index is big enough. When it isn't, your web tools still work.

---

## Two tools

| Tool | API | Purpose |
|---|---|---|
| `paper_search` | `GET /api/papers/search?q=...` | Find papers by keyword (hybrid semantic + full-text) |
| `read_paper` | `GET /api/papers/{id}` + `GET /papers/{id}.md` | Metadata + markdown content |

Base URL: `https://huggingface.co`

---

## paper_search


Return **small** dicts per paper — title, ID, snippet. The model calls `read_paper` when it needs full text.

---

## read_paper

### Normalize the arxiv ID first

Users and search results may pass URLs. Strip prefixes before calling the API:
The `.md` endpoint uses arXiv HTML when available. Not every paper has it — abstract fallback is normal.

---

## When to use which tool

| Question | Tool |
|---|---|
| "What papers exist on RLHF?" | `paper_search` |
| "Read the FlashAttention paper" | `paper_search` → `read_paper` |
| "What did OpenAI announce yesterday?" | `web_search` (not papers) |
| "Paper not on HF — get it from arXiv" | `web_fetch("https://arxiv.org/abs/...")` |

Add this routing table to your system prompt or `AGENTS.md`.

---

## Typical agent flow

```
User: "Summarise the main ideas in the FlashAttention paper"

1. paper_search("FlashAttention")
   → arxiv_id: 2205.14135, title: FlashAttention...

2. read_paper("2205.14135")
   → markdown content (truncated)

3. Synthesise answer with citation: [FlashAttention](https://arxiv.org/abs/2205.14135)

4. Optionally write_file("notes/flash-attention.md", ...)
```

---

## If facing rate limits, use HF_TOKEN

Public read endpoints work without authentication. An optional `HF_TOKEN` (get this from your user settings) in `.env` helps with rate limits during heavy use.

---

## Things to Think About

- **404 on read:** the paper exists on arXiv but isn't on HF yet. Teach the model to fall back to web fetch.

- **Truncation:** a paper can be 50k+ tokens. Always cap `content` before returning.

- **Version suffixes:** `2305.18290v2` — HF usually accepts both forms; pick one normalization strategy and stick to it.

- **Response shape variance:** search results may wrap paper data in a `"paper"` key or not. Handle both when parsing JSON.

---

## Further Reading

- **HF Papers API** — <https://huggingface.co/docs/hub/en/paper-pages>

**Next:** wire `paper_search` and `read_paper` into your [Research Desk project](../README.md#project-research-desk).

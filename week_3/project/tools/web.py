"""
Web search and fetch tools — carry forward from Week 2.

Implement or copy from your week_2/project/:
  - web_search(query) — Serper
  - web_fetch(url) — requests + trafilatura/markdownify
"""

# TODO: copy from Week 2 project

import os
import re
import requests
import trafilatura
from markdownify import markdownify

def web_search(query: str, limit: int = 5) -> list[dict]:
    key = os.environ.get("SERPER_API_KEY")
    if not key:
        return [{"title": "Error", "link": "", "snippet": "SERPER_API_KEY is not set."}]
    
    try:
        resp = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": key, "Content-Type": "application/json"},
            json={"q": query, "num": limit},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        res = []
        for item in data.get("organic", []):
            res.append({
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
            })
        return res
    except Exception as e:
        return [{"title": "Error", "link": "", "snippet": f"Search failed: {str(e)}"}]


def web_fetch(url: str) -> str:
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ResearchBot/1.0)"}
    try:
        resp = requests.get(url, headers=headers, allow_redirects=True, timeout=10)
        resp.raise_for_status()
        html = resp.text
        
        text = trafilatura.extract(html, include_comments=False, include_tables=True)
        if not text:
            text = markdownify(html, heading_style="ATX", strip=["script", "style", "nav", "footer"])
            text = re.sub(r'\n{3,}', '\n\n', text).strip()
        
        limit_chars = 8000
        if len(text) > limit_chars:
            text = text[:limit_chars] + "\n\n[...truncated]"
        return text
    except Exception as e:
        return f"Error fetching URL: {str(e)}"

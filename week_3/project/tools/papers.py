"""
Paper search and read tools — Hugging Face Papers API (arXiv index).

Implement:
  - paper_search(query, limit) -> {papers: [{arxiv_id, title, abstract, url}, ...]}
  - read_paper(arxiv_id) -> {title, abstract, content, url, ...}

API docs: week_3/3_paper_tools.md
"""

import re
import requests

def normalize_arxiv_id(aid: str) -> str:
    aid = aid.strip()
    
    m = re.search(r'(\d{4}\.\d{4,5})(?:v\d+)?', aid)
    if m:
        return m.group(1)
        
    m = re.search(r'([a-zA-Z\-]+(?:\.[a-zA-Z\-]+)?/\d{7})(?:v\d+)?', aid)
    if m:
        return m.group(1)
        
    return re.sub(r'v\d+$', '', aid)


def paper_search(query: str, limit: int = 5) -> dict:
    url = "https://huggingface.co/api/papers/search"
    try:
        r = requests.get(url, params={"q": query}, timeout=10)
        if r.status_code != 200:
            return {"error": f"search failed: HTTP {r.status_code}"}
        
        data = r.json()
        papers = []
        
        results = []
        if isinstance(data, list):
            results = data
        elif isinstance(data, dict) and "papers" in data:
            results = data["papers"]
            
        for item in results:
            if len(papers) >= limit:
                break
                
            p = item.get("paper", item) if isinstance(item, dict) else {}
            if not p:
                continue
                
            arxiv_id = p.get("id", "")
            title = p.get("title", "")
            summary = p.get("summary", "")
            
            if arxiv_id:
                papers.append({
                    "arxiv_id": arxiv_id,
                    "title": title,
                    "abstract": summary,
                    "url": f"https://arxiv.org/abs/{arxiv_id}"
                })
                
        return {"papers": papers}
    except Exception as e:
        return {"error": f"search failed: {str(e)}"}


def read_paper(arxiv_id: str) -> dict:
    clean_id = normalize_arxiv_id(arxiv_id)
    meta_url = f"https://huggingface.co/api/papers/{clean_id}"
    try:
        r_meta = requests.get(meta_url, timeout=10)
        if r_meta.status_code == 404:
            return {"error": f"paper {clean_id} not found on HF"}
        elif r_meta.status_code != 200:
            return {"error": f"failed to get meta: HTTP {r_meta.status_code}"}
            
        m_data = r_meta.json()
        title = m_data.get("title", "")
        abstract = m_data.get("summary", "")
        
        md_url = f"https://huggingface.co/papers/{clean_id}.md"
        r_md = requests.get(md_url, timeout=10)
        
        if r_md.status_code == 200:
            content = r_md.text
            max_len = 16000
            if len(content) > max_len:
                content = content[:max_len] + "\n\n[...truncated]"
        else:
            content = f"Markdown not available. Abstract:\n\n{abstract}"
            
        return {
            "arxiv_id": clean_id,
            "title": title,
            "abstract": abstract,
            "content": content,
            "url": f"https://arxiv.org/abs/{clean_id}"
        }
    except Exception as e:
        return {"error": f"failed to read: {str(e)}"}
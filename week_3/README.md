---
track: "genai"
week: 3
---

# Week 3: Agent Memory & Persistent Sessions

## Objective

Last week you built a research agent that searches the web and reads pages. It forgot everything when you closed the terminal.

This week you give it a past. Conversations save to disk and resume later. Project rules live in `AGENTS.md`. Research notes land in files the agent writes itself. You add **arXiv paper search and read tools** via the Hugging Face Papers API — replacing Week 2's AlphaXiv MCP with code you own. And you wrap everything in an **agent class** with no UI inside it, so the same brain runs in a REPL, a one-shot CLI command, or the Textual TUI you built in Week 2.

By the end you'll have **Research Desk**: a full research agent that searches the web *and* academic papers, reads primary sources, picks up where you left off, and saves findings to `notes/`.

---

## What You'll Learn and Build

1. **Persistent Sessions**
   - Save conversation history to disk as JSON
   - List, load, and resume sessions by ID
   - Episodic memory: "last Tuesday we researched transformer attention"

2. **AGENTS.md — Procedural Memory**
   - Load project rules from `AGENTS.md` into the system prompt on startup
   - Same pattern OpenCode, Cursor, and Claude Code use

3. **arXiv Paper Tools (required)**
   - `paper_search` — Hugging Face Papers API (`/api/papers/search`)
   - `read_paper` — metadata + markdown content (`/api/papers/{id}` + `.md`)
   - Replaces AlphaXiv MCP from Week 2 — hand-written, no MCP

4. **File Tools (OpenCode-style)**
   - Sandboxed `read_file` with `start_line`, `read_lines`, line numbers, and `has_more`
   - `edit_file` — line-level replace, delete, append with diff preview in the response
   - `write_file`, `list_files`
   - Structured `{"content": ...}` / `{"error": ...}` returns

5. **Agent class hierarchy** — `Agent` (brain) → `REPLAgent` (terminal) / `TUIAgent` (Textual)
   - All loop logic, tools, and session I/O on `Agent`
   - Subclasses only add `run()` and optional `_emit()` hooks
   - Three entry points: `REPLAgent.run_once()`, `REPLAgent.run()`, `TUIAgent.run()`

---

## Setup

Reuse Week 2 dependencies — nothing new required:

```bash
uv add openai python-dotenv requests markdownify trafilatura textual
```

Your `.env` should still have `OPENROUTER_API_KEY` and `SERPER_API_KEY`.

Optional: `HF_TOKEN` improves rate limits on Hugging Face API calls. Not required for paper search/read.

---

## Lessons

Three lessons, two builds, one project.

| Lesson | Topic |
|---|---|
| [1_memory.md](1_memory.md) | Sessions on disk, AGENTS.md, CoALA memory types |
| [2_agent_class.md](2_agent_class.md) | File tools + the detached agent class pattern |
| [3_paper_tools.md](3_paper_tools.md) | `paper_search` and `read_paper` via HF Papers API |

---


## Project: Research Desk

Your Week 2 Perplexity clone, upgraded into a research agent with memory and papers.

### What it does

A research agent that:

1. **Searches the web** (Serper) and **reads** pages — Week 2 web tools
2. **Searches papers** (`paper_search`) and **reads** them (`read_paper`) — **required**, HF Papers API
3. **Saves** findings to `notes/` via `write_file` — build a research archive over time
4. **Resumes** past investigations — load a session, continue the thread
5. **Follows** rules in `AGENTS.md` — citation style, when to use papers vs web
6. **Runs three ways:**
   - `python agent.py` — interactive REPL
   - `python agent.py "What is Q-learning?"` — single question, print answer, exit
   - `python agent.py --tui` — Week 2 Textual UI wrapping the same `ResearchAgent` class

Get the agent class, paper tools, and one-shot CLI working **before** wiring the TUI.

### Suggested layout

```
week_3/project/
  agent.py       # Agent, REPLAgent, main() — no Textual imports
  tui.py         # TUIAgent(Agent): Textual App
  tools/
    web.py       # web_search, web_fetch (from Week 2)
    papers.py    # paper_search, read_paper (required — Lesson 3)
    files.py     # read_file, write_file, list_files, edit_file
  .agent/sessions/
  notes/
  AGENTS.md
```

Why split code into files? It makes components easier to test and explore (as a new developer on a codebase).

### SUBMISSION.md

What you built and why, your own voice.

### Getting started

1. Build 1 — session save/load + `AGENTS.md` loader
2. Build 2 — `Agent` + `REPLAgent` with file tools
3. Implement `tools/papers.py` — `paper_search` + `read_paper` ([Lesson 3](3_paper_tools.md))
4. Copy Week 2 web tools into `tools/web.py`, register all tools on `Agent`
5. One-shot CLI: `python agent.py "Summarise the FlashAttention paper"`
6. REPL: `python agent.py`
7. `TUIAgent` in `tui.py` — inherits from `Agent`, overrides `_emit()` for tool log

---

## Bonus Challenges

- **`/sessions` REPL command** — list sessions and `/resume <id>` to switch
- **Auto-title** — after the first exchange, ask the model for a 5-word session title
- **Read the Opencode architecture** and add something inspired from it. Could be a small element or detail, doesn't matter.
---

## Resources

- **CoALA paper** — <https://arxiv.org/abs/2309.02427>
- **OpenCode architecture** — <https://opencode-ai-opencode.mintlify.app/core-concepts/architecture>

---

## Submission Checklist

All project code in `week_3/project/`.

**Packaging:**
- [ ] `requirements.txt` and `.env.example` exist; no real keys in source

**Functionality:**
- [ ] `Agent` base class holds loop, tools, sessions — no Textual imports in `agent.py`
- [ ] `REPLAgent(Agent)` — REPL + one-shot CLI
- [ ] `TUIAgent(Agent)` in `tui.py` — inherits `chat()`, adds Textual UI only
- [ ] `python agent.py "question"` runs one research query and prints the answer
- [ ] `python agent.py` starts an interactive REPL
- [ ] `python agent.py --tui` launches the Textual UI
- [ ] Sessions persist to disk and can be resumed
- [ ] Agent loads and follows `AGENTS.md`
- [ ] **`paper_search` finds papers via Hugging Face Papers API**
- [ ] **`read_paper` returns paper content (markdown or abstract) by arxiv_id**
- [ ] **`read_file` supports `start_line` and `read_lines`, returns line numbers and `has_more`**
- [ ] **`edit_file` supports replace, delete, and append with diff preview in the response**
- [ ] Agent can search the web, read pages, and write or edit research notes in `notes/`
- [ ] Agent uses paper tools for academic questions (not just web search)

**Writeup:**
- [ ] `SUBMISSION.md` in your own words

Submission instructions will be posted separately.

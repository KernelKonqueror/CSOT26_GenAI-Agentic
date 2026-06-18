# Submission: Research Desk (Week 3)

This is the submission for **Research Desk** (Week 3), a research assistant that queries the web, searches academic papers, and handles file notes. 

Compared to Week 2 (which used AlphaXiv MCP), this version implements our own paper tools, adds sandboxed file management, implements persistent sessions on disk, parses custom rules from `AGENTS.md` into the system prompt, and separates the agent logic into a clean class structure.

---

## Architecture & Layout

The project separates the core agent logic (brain) from the interface layers (REPL/TUI) so that the brain runs the same way regardless of the UI.

```
week_3/project/
  agent.py       # Core Agent, REPLAgent, and main() entrypoint
  tui.py         # TUIAgent(Agent, App) for the full Textual UI
  AGENTS.md      # Citation and operation rules
  tools/
    web.py       # web_search (Serper) and web_fetch (Trafilatura/Markdownify)
    papers.py    # paper_search and read_paper (Hugging Face Papers API)
    files.py     # Sandboxed file operations (read_file, write_file, edit_file, list_files)
  .agent/
    sessions/    # Saved conversation JSON files
  notes/         # Output directory for research notes written by the agent
```

### Class Structure
1. **`Agent` (Base)**: Handles the API client, system prompt assembly, agent loop logic, session saving/loading, and tool routing.
2. **`REPLAgent(Agent)`**: Runs the terminal-based interactive input loop, handles one-shot command-line queries, and supports commands like `/sessions` and `/resume`.
3. **`TUIAgent(Agent, App)`**: The Textual UI application that inherits from both our `Agent` brain and Textual's `App` to provide a full-screen view.

---

## Features Implemented

### 1. Persistent Sessions
* Saves conversation history automatically to `.agent/sessions/{session_id}.json` after every turn.
* **Auto-Titling (Bonus)**: On starting a new session, a fast background API call takes the first user question and summarizes it into a title (max 5 words) to replace "Untitled".
* **Interactive Commands (Bonus)**: You can run `/sessions` in the terminal to view saved sessions or `/resume <session_id>` to reload a past conversation.

### 2. Procedural Memory (`AGENTS.md`)
* The agent reads the rules inside `AGENTS.md` dynamically at startup and appends them to the system prompt to enforce rules for formatting, tool choices, and sandboxing.

### 3. arXiv Paper Tools
* **`paper_search`**: Queries Hugging Face's paper search API to find matching papers (returns arXiv ID, abstract, title, and URL).
* **`read_paper`**: Normalizes input arXiv IDs by stripping URL prefixes and **removing arXiv version suffixes** (e.g. `2307.08691v2` $\rightarrow$ `2307.08691`) to prevent 404/401 API errors, then retrieves metadata and full markdown.

### 4. Sandboxed File Tools
* **Path Safety**: All inputs are checked using `os.path.abspath` to guarantee they don't escape `WORKSPACE_ROOT`.
* **`read_file`**: Returns lines prefixed with line numbers for easy editing. Supports pagination via `start_line` and `read_lines` parameters.
* **`edit_file`**: Handles line-level `replace`, `delete`, and `append` operations, and returns a unified diff to verify the edit.
* **`list_files`**: Lists files in the sandbox directory matching a glob pattern (e.g. `notes/*.md`).

### 5. Web Tools
* **`web_search`**: Searches the web using the Serper API.
* **`web_fetch`**: Grabs HTML content, cleans it up using `trafilatura` (with a fallback to `markdownify`), and truncates the content to prevent blowing up context limits.

---

## Setup & Running Instructions

API keys go inside `week_3/project/.env`:
```bash
GEMINI_API_KEY=your-gemini-key
SERPER_API_KEY=your-serper-key
# Or use OpenRouter:
OPENROUTER_API_KEY=your-openrouter-key
```

Run using the `genaivenv` virtual environment:

### Interactive REPL
```bash
/home/ppisgr8/genaivenv/bin/python3 agent.py
```

### One-Shot Research CLI
```bash
/home/ppisgr8/genaivenv/bin/python3 agent.py "Summarise the FlashAttention paper"
```

### Full-Screen Textual TUI
```bash
/home/ppisgr8/genaivenv/bin/python3 agent.py --tui
```
*TUI Shortcuts*: `Ctrl+Q` to Quit, `Ctrl+L` to Clear Panels, `Ctrl+K` to Reset History, `Ctrl+S` to Save Chat Log.

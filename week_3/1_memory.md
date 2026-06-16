# Lesson 1: Sessions, AGENTS.md & Memory

## The Problem

Your Week 2 agent was amnesiac. Close the terminal and the research vanishes — sources found, pages read, threads of thought, all gone.

Production agents don't work this way. OpenCode saves conversations to SQLite. Cursor remembers your project rules from `.cursor/rules`. Claude Code reads `CLAUDE.md` every session. This week you build the file-based version yourself.

---

## Three Memory Types That Matter Here

The [CoALA framework](https://arxiv.org/abs/2309.02427) describes four memory types. For a research agent, three are enough:

| Type | What it stores | Your implementation |
|---|---|---|
| **Working** | Current conversation | `messages` list in memory |
| **Procedural** | How the agent should behave | `AGENTS.md` → system prompt |
| **Episodic** | Past sessions | JSON files in `.agent/sessions/` |

Semantic memory (stable facts like "user prefers APA citations") can live inside `AGENTS.md` or as a `preferences` block in the session file. Keep it simple this week — don't build a separate facts database unless you want the bonus.

---

## Sessions on Disk

Each conversation gets an ID and a JSON file:

```
.agent/
  sessions/
    a3f8c2.json
    b71e04.json
  AGENTS.md          # optional; can also live at project root
notes/
  quantum-computing.md
  attention-mechanisms.md
```

You can use [nanoid](https://pypi.org/project/nanoid/) to generate the IDs.


Session file shape:

```json
{
  "id": "a3f8c2",
  "title": "Quantum error correction",
  "created_at": "2025-06-10T14:30:00",
  "updated_at": "2025-06-12T09:15:00",
  "messages": [
    {"role": "system", "content": "..."},
    {"role": "user", "content": "What is surface code?" },
    {"role": "assistant", "content": "Surface code is..."}
  ]
}
```

Save after every turn. Load on startup or when the user resumes.

Working with APIs, you should already be familiar with JSON. If not, here are some resources:
- https://stackoverflow.blog/2022/06/02/a-beginners-guide-to-json-the-data-format-for-the-internet/
- https://realpython.com/python-json/

**Go work through Build 1 now.**

---

## AGENTS.md — Procedural Memory

A markdown file at the project root (or `.agent/AGENTS.md`) that the agent reads every session. You write it; the agent follows it.

```markdown
# Research Desk Rules

## Citations
- Always include source URLs inline: [title](url)
- Prefer primary sources and official docs over blog posts

## Notes
- Save long findings to notes/ as markdown files
- Filename: lowercase, hyphens, topic-based (e.g. notes/transformer-attention.md)

## Search
- Use paper_search + read_paper for ML/academic questions
- Use web_search + web_fetch for news, blogs, and docs
- Search before fetching — don't fetch URLs blindly
- Truncate fetched pages; quote only what's relevant
```

Load it into the system prompt:

```python
def build_system_prompt() -> str:
    parts = [BASE_PROMPT]
    for path in ("AGENTS.md", ".agent/AGENTS.md"):
        if os.path.isfile(path):
            parts.append(f"## Project rules\n{open(path).read()}")
            break
    return "\n\n".join(parts)
```

This is exactly how OpenCode's `ContextPaths` work — files injected into context before the agent runs. No embedding, no framework. Just read the file and prepend.

---

## Resuming a Session

```
$ python agent.py
Research Desk [session a3f8c2: Quantum error correction]
> Tell me more about the surface code threshold

$ python agent.py --session b71e04
Resumed: Attention mechanisms in ViTs
>
```

The agent loads `messages` from disk, appends the new user turn, runs the loop, saves back. Working memory *is* the saved conversation — no separate sync step.

For long sessions, the context window will eventually fill up. Week 5 touches compaction; this week, if a session gets too long, start a new one and reference the old notes on disk.

---

## Research Notes as Episodic Memory

When the agent writes `notes/transformer-attention.md`, that file outlives the session. Next time:

```
> What did we find out about transformer attention last week?
```

The agent can `list_files("notes/")` and `read_file("notes/transformer-attention.md")`. Files on disk *are* memory — the agent reads them on demand via tools (Lesson 2).

Week 2's bonus `save_research_note` tool becomes a first-class part of the project this week.

---

## Things to Think About

- **When to save:** after every turn is simplest. Partial saves on crash are a bonus problem.

- **Session titles:** "Untitled" is fine for Build 1. Auto-generating a title from the first question is a nice bonus.

- **What goes in messages:** save the full API message list including tool calls and tool results — that's what you need to resume exactly.

- **AGENTS.md vs system prompt in code:** rules the *user* should edit live in `AGENTS.md`. Rules the *developer* owns (iteration cap, tool list) stay in code.

---

## Further Reading

- **CoALA paper** — <https://arxiv.org/abs/2309.02427>
- **OpenCode context files** — <https://opencode-ai-opencode.mintlify.app/core-concepts/architecture>

**Next:** [2_agent_class.md](2_agent_class.md)

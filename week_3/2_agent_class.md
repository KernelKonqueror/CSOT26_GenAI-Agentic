# Lesson 2: File Tools & the Agent Class

## File Tools — OpenCode Style

Week 2 Build 1 had naive `read_file` / `write_file` — no sandbox, no line numbers, inconsistent errors. That works for a toy demo. It breaks the moment the model reads `/etc/passwd` or dumps a 10,000-line file into context.

[OpenCode](https://github.com/opencode-ai/opencode), Cursor, Claude Code, etc. converged on a small set of file-tool conventions. They're boring on purpose. Boring tools are tools the model uses correctly.

Put implementations in `tools/files.py`. The agent class imports them.

---

### Why OpenCode structures tools this way

Coding agents don't get a filesystem API — they get **tool calls**. Every design choice below is about making those calls predictable for the model and safe for you.

| Convention | What it means | Why it exists |
|---|---|---|
| **Sandbox** (`WORKSPACE_ROOT`) | Paths can't escape the project folder | Stops the model (or a malicious prompt) from reading secrets or wiping system files |
| **Line numbers in `read_file`** | `"  42\| def foo():"` | Model cites exact lines; `edit_file` targets those same numbers |
| **`start_line` + `read_lines`** | Paginated reads | Large files without blowing the context window |
| **Truncation** | Cap output at ~12k chars | Safety net even when `read_lines` is too generous |
| **Structured returns** | Always `{content}` or `{error}` | Model learns to retry on `"error"`, not crash on a Python traceback |
| **`list_files` before `read_file`** | Glob/navigation tool | Model explores unknown repos instead of guessing paths |
| **`edit_file` with diff preview** | Line delete / replace / append | Surgical edits; return what changed so the model (and you) can verify |
| **Separate tools** | Not one mega `"file"` tool | Smaller schemas → model picks the right action more often |

OpenCode's production `edit` tool uses **find-and-replace strings** (Week 5). Week 3 uses **line-based** `edit_file` instead — it pairs directly with numbered `read_file` output and is easier to implement correctly.

---

### Disadvantages of simple read/write tools

**Truncation cuts off content.** Mitigation: pass `start_line` and `read_lines` to read a window (e.g. lines 100–149), check `has_more` in the response, then read the next chunk.

**Line edits can target wrong lines.** The model misreads line numbers or edits before re-reading. Mitigation: `read_file` immediately before `edit_file`; return a diff preview in the edit result so mistakes are visible in the tool log.

**`write_file` still overwrites whole files.** Use `write_file` for new notes; use `edit_file` to update existing ones. Restrict destructive edits to `notes/` in `AGENTS.md` until Week 5 adds confirmation gates.

**Structured errors can be ignored.** The model sometimes apologises instead of retrying. Mitigation: good tool descriptions + system prompt ("on error, try a different path or tool").

---

### resolve_path — the sandbox

Every path must resolve inside `WORKSPACE_ROOT` (from `.env`, default `"."`).

```
resolve_path(path):
    full = absolute path joining WORKSPACE_ROOT + path
    if full escapes WORKSPACE_ROOT:
        raise error "Path escapes workspace"
    return full
```

---

### read_file — line numbers, pagination, truncation

Either read the whole file, or read a **window** of lines. Always prefix output with line numbers so the model can pass them to `edit_file`.

Parameters:

| Param | Default | Meaning |
|---|---|---|
| `start_line` | `1` | First line to read (1-indexed) |
| `read_lines` | `200` | How many lines to return |

But how does the model know how many lines there are in the file? Something to think about...

Maybe you can add some metadata too?

**Workflow:** `read_file("notes/foo.md", start_line=50, read_lines=30)` → edit lines 55–58 → `read_file` again to verify.

---

### edit_file — line delete, replace, append

OpenCode returns a **preview of what changed** after an edit so the agent can self-correct. Do the same: include a short `diff` or `-`/`+` snippet in the return value.

One tool, three operations (enum in schema):

| Operation | Needs | Effect |
|---|---|---|
| **`replace`** | `start_line`, `end_line`, `content` | Lines `start_line..end_line` (inclusive) replaced by `content` (split on newlines) |
| **`delete`** | `start_line`, `end_line` | Remove lines `start_line..end_line` (inclusive) |
| **`append`** | `start_line`, `content` | Insert `content` lines **after** `start_line` (`0` = before line 1) |

---

### write_file — create or overwrite

Should be self-explanatory

---

### list_files — glob

Read about [glob patterns](https://www.malikbrowne.com/blog/a-beginners-guide-glob-patterns/) (they are a unix staple) and [how to use them in Python](https://realpython.com/ref/stdlib/glob/) 

**Go work through Build 2 file-tool stubs after reading the class hierarchy below.**

---

## The Agent Class Hierarchy

The biggest design mistake in agent projects: loop logic, tools, and Textual code in one file. When something breaks, you can't tell if it's the model, a tool, or the UI thread.

This is where 2 OOPS concepts: abstraction and inheritance come in (I hope you remember week 1).

**Refactor your week 2 agent to use three classes:**

```
Agent          ← brain: loop, tools, sessions, chat()
├── REPLAgent  ← terminal: input loop + one-shot CLI
└── TUIAgent   ← Textual: full-screen UI (lives in tui.py)
```

| Class | Owns | Does not own |
|---|---|---|
| **`Agent`** | `chat()`, `_run_loop()`, `dispatch()`, session I/O, tool registry | `input()`, `print()`, Textual |
| **`REPLAgent`** | `run()` REPL loop | Agent loop logic |
| **`TUIAgent`** | Textual layout, key bindings, background workers | Tool dispatch, API calls |

Subclasses inherit every method from `Agent`. They only add **how the user talks to the agent**.

**Rule:** `agent.py` defines `Agent` and `REPLAgent`. No Textual imports in `agent.py`. `TUIAgent` lives in `tui.py`.

---

## Entry point — `main()` dispatches to the right subclass by [parsing CLI arguments](https://www.geeksforgeeks.org/python/command-line-arguments-in-python/).

Test in this order:

1. `python agent.py "Summarise the FlashAttention paper"` — `run_once`
2. `python agent.py` — `REPLAgent.run`
3. `python agent.py --tui` — `TUIAgent.run`

---

## Why inheritance?

You might ask: why not `REPLAgent(agent: Agent)` holding an agent instance?

Inheritance works better when:

- REPL and TUI need the **same overrides** (`_emit`, maybe `_title()`)
- There's one agent identity per session — the UI *is* the agent from the user's perspective
- `TUIAgent.chat()` and `REPLAgent.chat()` must behave identically (they're the same method)

Composition is fine if you need multiple agents in one UI. For Research Desk — one session, one agent — inheritance keeps the call chain flat.

**Don't over-inherit.** If a subclass reimplements `_run_loop()`, you've gone wrong. Only override presentation hooks and `run()`.

---

## Registering All Project Tools

In the project, register **eight** tools on `Agent`:

| Tool | Module | From |
|---|---|---|
| `web_search`, `web_fetch` | `tools/web.py` | Week 2 |
| `paper_search`, `read_paper` | `tools/papers.py` | Lesson 3 |
| `read_file`, `write_file`, `list_files`, `edit_file` | `tools/files.py` | Build 2 |

Wire them into `TOOLS` (OpenAI format) and route in `Agent.dispatch()` by name.

**Week 3 replaces AlphaXiv MCP** with hand-written paper tools. Do not use AlphaXiv in the Week 3 project.

Suggested tool routing — put this in your system prompt or `AGENTS.md`:

| Question type | Tool |
|---|---|
| ML paper / literature | `paper_search` → `read_paper` |
| Current events, blogs, docs | `web_search` → `web_fetch` |
| Save new notes | `write_file("notes/...")` |
| Update existing notes | `read_file` → `edit_file` |
| Recall past work | `list_files("notes/")` → `read_file` |

Write tool **descriptions** carefully — the model chooses tools based on them. See Week 2 Lesson 1 for JSON Schema format.

Implement paper tools in [Lesson 3](3_paper_tools.md) before wiring the full project.

---

## Things to Think About

- **Where does session logic live?** On `Agent`, not in `main()`. Subclasses only implement `run()`.

- **Override `_emit`, not `_run_loop`.** If TUI needs tool logging, override the hook — don't duplicate the loop.

- **Tool results in saved sessions:** when you resume, the model sees the full tool history. That's correct — it's how it knows what it already fetched.

- **WORKSPACE_ROOT:** set via `.env` so the agent can't wander outside the project folder.

- **Thread safety (TUI):** disable input until `chat()` returns — Week 2 already did this.

---

## Further Reading

- **OpenCode tool system** — read, write, list in the architecture docs
- **Week 2 `build2_sdk_tools.py`** — the loop you're now moving into a class

**Next:** the [Research Desk project](../README.md#project-research-desk) — implement [paper tools](3_paper_tools.md) in `tools/papers.py`.

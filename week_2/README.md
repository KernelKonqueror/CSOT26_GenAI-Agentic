---
track: "genai"
week: 2
---

# Week 2: Tools, Agents, and TUIs

## Objective

Last week you built a chatbot that holds a conversation. This week you give it hands.

A tool is a Python function the model can *request* to call. An agent is a loop around tool calls: the model asks, you run, you feed back the result, the model decides what to do next. Once you've built this loop from scratch, you'll see it everywhere.

By the end of the week you'll have a research agent with a full-screen terminal UI that can search the web, read pages, and synthesise information across multiple sources, in a loop you wrote yourself.

---

## What You'll Learn and Build

1. **Tool Calling**
   - Write tool schemas (JSON Schema) that the model uses to decide *when* and *how* to call a function
   - Parse a custom text-based tool-call format by hand (so the SDK magic isn't magic)
   - Implement the full round-trip: tool call → dispatch → tool result → continue
   - Use the OpenAI SDK's `tools=` parameter and `tool_calls` response field
   - Build a clean tool dispatcher and the agent loop with an iteration cap

2. **Web Tools**
   - Fetch URLs with `requests`, convert HTML to clean text
   - Use `serper.dev` to search the web programmatically
   - Understand `llms.txt`, the convention AI agents use to navigate websites efficiently

3. **Model Context Protocol (MCP)**
   - Why a standard protocol for tools matters
   - How to write and connect an MCP server in Python
   - How to use an online MCP server (like AlphaXiv) with the OpenAI SDK

4. **Terminal User Interfaces with Textual**
   - Build full-screen apps with panels, input boxes, and key bindings
   - Keep the UI responsive while an API call is running

---

## Setup

Install new dependencies:

```bash
uv add openai python-dotenv requests markdownify trafilatura textual
```

Or with pip:

```bash
pip install openai python-dotenv requests markdownify trafilatura textual
```

**Serper** (web search): 2,500 free queries/month:
1. Sign up at <https://serper.dev>
2. Copy your API key
3. Add to your `.env`: `SERPER_API_KEY=your_key_here`

Your `.env` should now look like:

```
OPENROUTER_API_KEY=sk-or-v1-...
SERPER_API_KEY=...
```

---

## Lessons

Work through these in order. Each lesson covers one topic in depth with code examples and things to think about.

| Lesson | Topic |
|---|---|
| [1_tools.md](1_tools.md) | Tool schemas, the agent loop, and the full round-trip |
| [2_web_tools.md](2_web_tools.md) | Web fetch, HTML to markdown, llms.txt, Serper |
| [3_mcp.md](3_mcp.md) | Model Context Protocol: what it is and how to use it |
| [4_tui.md](4_tui.md) | Building terminal UIs with Textual |

---

## Builds

Three focused builds, each implementing one piece of the week's content. Complete these before starting the project.

### Build 1: Custom Tool Parser [`builds/build1_custom_tools.py`](builds/build1_custom_tools.py)

Implement a tool-calling agent **without** the SDK's built-in support. The model is prompted to emit tool calls wrapped in `<tool_call>` XML tags. You parse them with a regex, run the function, and inject the result back as a `<tool_response>`.

The tools are `read_file` and `write_file` — simple, deterministic, no API keys needed.

This build exists to make the mechanics concrete. When Build 2 "just works", you'll know exactly why.

**Implement:**
- `parse_tool_call(response_text)`: extract name + args from the model's output
- `dispatch(name, arguments)`: route to the right function and return a JSON string
- `read_file(path)` and `write_file(path, content)`: the actual tool functions
- `run_agent(user_message)`: the full back-and-forth loop

### Build 2: SDK Tool Calling [`builds/build2_sdk_tools.py`](builds/build2_sdk_tools.py)

Same two tools, same loop, but using the OpenAI SDK's native `tools=` parameter and `tool_calls` response field. Compare how much cleaner this is versus Build 1, and understand what the SDK is doing for you.

**Implement:**
- `get_weather(city, unit)` and `calculate(expression)`
- `dispatch(tool_call)`: parse `tool_call.function.arguments` (a JSON string) and call the right function
- `run_agent(user_message)`: the canonical agent loop with `finish_reason == "tool_calls"` detection

### Build 3: TUI Chatbot [`builds/build3_tui.py`](builds/build3_tui.py)

Take your Week 1 multi-turn chatbot and wrap it in a Textual full-screen UI. The chat logic is the same; you're just changing how the user interacts with it.

**Implement:**
- `call_model(messages)` and `trim_history(messages, max_turns)`: reuse from Week 1
- `on_input_submitted`: handle user input, run API call in a background worker
- `_get_response`: fetch model reply and update the UI safely from a thread
- `action_clear_display` and `action_clear_history`: the key binding actions

**Required key bindings:**
- `Ctrl+L`: clear the displayed log (history unchanged)
- `Ctrl+K`: clear history and display (fresh start)
- `Ctrl+Q`: quit

---

## Project: Build your own Perplexity

[Perplexity](https://www.perplexity.ai) is an AI-powered research tool (we got Pro free for a year lol). You ask it a question, it searches the web, reads the relevant pages, and synthesises a cited answer. This week you build your own version of that, from scratch, running entirely in your terminal.

### What it does

The user types a research question. The agent:
1. Searches the web for relevant results using Serper
2. Reads one or more pages in full using `requests`
3. Searches for relevant academic papers using the AlphaXiv MCP server (`discover_papers` and `get_paper_content`)
4. Synthesises the information into a clear, sourced answer
5. All of this in a Textual TUI the user can interact with

Setting up the AlphaXiv MCP server: see the docs at <https://www.alphaxiv.org/docs/mcp>. Read Lesson 3 for how to connect an online MCP server to an OpenAI SDK agent loop.

### SUBMISSION.md

Write a short document (300–600 words) covering:
- What you built and how the agent loop works in your implementation
- One design decision you made and why (e.g. how you truncate fetched pages, how you handle errors, what system prompt you wrote)
- Something that surprised you or didn't work the way you expected
- Anything you'd improve given more time

Write it in your own words. This is assessed; a generic AI-generated summary scores poorly.

### Getting started

The project scaffold is in [`project/`](project/). `agent.py` currently makes a single API call. Evolve it step by step:

1. Get the base call working
2. Add `web_search` and `web_fetch` as standalone functions and wire up the agent loop
3. Test the loop works from the command line
4. Connect the AlphaXiv MCP server and add `discover_papers` and `get_paper_content` to the loop
5. Play around with the system prompt and tool descriptions to produce good results.
6. Build the Textual TUI around the working agent

Don't skip step 4. A TUI built around a broken agent is much harder to debug.

---

## Bonus Challenges

If you finish early and want to go deeper:

- **Split-panel TUI**: add a second panel (distinct from the chat log) that shows each tool call and its result as it happens
- **Streaming**: display the model's response token-by-token using `stream=True`, updating the chat panel as tokens arrive
- **`save_research_note` tool**: let the model save findings to a markdown file in a `notes/` folder; useful for multi-session research
- **Error recovery**: handle network timeouts, HTTP errors, and empty search results gracefully, feeding structured error messages back to the model instead of crashing

---

## Resources

- **OpenAI Function Calling Guide**: <https://platform.openai.com/docs/guides/function-calling>
- **ReAct: Synergizing Reasoning and Acting** (the paper behind the agent loop pattern): <https://arxiv.org/abs/2210.03629>
- **llms.txt spec**: <https://llmstxt.org/>
- **Serper API reference**: <https://serper.dev/api-reference>
- **requests docs**: <https://requests.readthedocs.io/>
- **trafilatura**: <https://trafilatura.readthedocs.io/>
- **Textual docs**: <https://textual.textualize.io/>
- **Textual widget gallery**: <https://textual.textualize.io/widget_gallery/>
- **AlphaXiv MCP**: <https://www.alphaxiv.org/docs/mcp>
- **MCP Python SDK**: <https://github.com/modelcontextprotocol/python-sdk>

---

## Submission Checklist

All project code must live in the `week_2/project/` folder. Before you submit, go through every item:

**Packaging:**
- [ ] `requirements.txt` exists and lists all external packages
- [ ] `.env.example` exists with placeholder values (no real keys)
- [ ] `.env` is in `.gitignore`
- [ ] No API key in any source file

**Functionality:**
- [ ] The agent can search the web and read pages to answer a question
- [ ] The agent connects to the AlphaXiv MCP server and can search for papers (`discover_papers`) and read them (`get_paper_content`)
- [ ] The agent uses a loop — it keeps calling tools until it has enough to answer
- [ ] The TUI launches and you can have a conversation with the agent
- [ ] There are keyboard shortcuts to clear the chat and to quit

**Writeup:**
- [ ] `SUBMISSION.md` exists and is written in your own words

Submission instructions will be posted separately.

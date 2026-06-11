# Week 2 Submission

## What I Built

I built a full-screen terminal-based research assistant named **ResearchBot** (located in `week_2/project/agent.py`) using **Textual** and the OpenAI-compatible SDK (configured to use Gemini or OpenRouter). The bot serves as a custom "Perplexity-like" research engine, allowing users to input complex research questions and watch the agent dynamically search the web, fetch pages, query scientific paper databases, and compile a cited final response.

## How the Agent Loop Works

The core of the application is an asynchronous agent loop (`run_research_agent`):
1. **Tool Discovery**: Upon startup, the agent establishes a connection to the **AlphaXiv MCP server** over Server-Sent Events (SSE). It lists the tools offered by the MCP server (`discover_papers` and `get_paper_content`), dynamically builds their OpenAI function schemas, merges them with local tools (`web_search` via Serper and `web_fetch`), and compiles the complete tool list.
2. **Reasoning Loop**: The loop executes for a maximum of 10 iterations. At each turn, it sends the conversation history (system prompt, user messages, and previous tool/response context) to the Gemini model.
3. **Execution & Dispatch**: If the model emits tool requests:
   - The loop catches them and routes them: local tools are run immediately; MCP tools are forwarded to the AlphaXiv session.
   - Events (tool name, parameters, status, and bytes returned) are logged in real-time to the TUI's **Tool Activity Log** panel.
   - The results are injected back into the message log with the `tool` role, and the loop repeats.
4. **Final Synthesized Answer**: Once the model returns `finish_reason == "stop"` (or does not request tools), the loop terminates and returning the model's markdown response containing synthesized facts and citations, which is then displayed in the **Chat Log** panel.

## Key Design Decisions

- **Two-Panel TUI Layout**: I split the Textual interface into a **Chat Panel** (65% width) and a **Tool Activity Log** (35% width). This prevents cluttering the main conversation with raw tool outputs while providing transparency into what queries the agent is running and what resources it is reading.
- **Robust Web Fetching with Trafilatura Fallback**: The `web_fetch` tool first attempts to use `trafilatura` to extract only the main article content (filtering out ads, navigation links, and footers). If that fails, it falls back to a generalized `markdownify` parsing and truncates the result to 8,000 characters to prevent token bloat.
- **Graceful MCP Connection Fallback**: If the AlphaXiv MCP server is unavailable or fails to initialize, the agent catches the error, logs a warning in the tool panel, and seamlessly transitions to a fallback loop (limited to 5 iterations) using only local web search/fetch tools, ensuring the bot remains usable.
- **Background Worker Threads**: Because API calls and web requests are blocking, the agent loop runs under Textual's worker thread system (`run_worker(..., thread=True)`). Updates to the UI are safely dispatched from the background thread via `self.call_from_thread`.
- **Keyboard Shortcuts**: In addition to `Ctrl+L` (clear log), `Ctrl+K` (clear history + log), and `Ctrl+Q` (quit), I implemented a custom `Ctrl+S` key binding to export the complete conversation transcript to a timestamped local file (`research_log_<timestamp>.txt`) for future reference.

## What Surprised Me and Challenges Faced

- **The Power of Model Context Protocol (MCP)**: I was surprised by how clean and standard the MCP interface is. Once connected, listing and invoking tools on a remote server requires no hardcoded schemas or custom HTTP code; it is completely driven by the protocol metadata.
- **TUI Thread Safety**: Initially, updating the RichLog panel directly from the asynchronous agent worker would trigger race conditions or freeze the Textual event loop. Learning to correctly dispatch UI calls from threads with `call_from_thread` was a key learning curve.

## Future Improvements

If given more time, I would:
1. Implement token-by-token streaming in the RichLog panel using `stream=True`.
2. Add a persistent research notebook tool (`save_research_note`) allowing the agent to write its compiled findings to markdown files under a dedicated folder.
3. Enhance the web-fetching tool to parse `llms.txt` of websites before crawling them to find cleaner entry points.

## Completed Builds and Files

- `builds/build1_custom_tools.py`: Completed custom regex-based `<tool_call>`/`<tool_response>` parser and loop.
- `builds/build2_sdk_tools.py`: Completed native OpenAI tool calling with `calculate` and `get_weather`.
- `builds/build3_tui.py`: Completed Textual TUI for a multi-turn chat assistant with key bindings.
- `project/agent.py`: Fully functional Perplexity-style terminal researcher integrating Serper, Trafilatura, AlphaXiv MCP, and a responsive Textual UI.

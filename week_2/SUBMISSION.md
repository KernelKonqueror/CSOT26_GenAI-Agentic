# Week 2 Submission

## What I Built

A terminal-based research assistant named **ResearchBot** (inside `week_2/project/agent.py`) built using Textual for the TUI and the OpenAI SDK connected to Gemini/OpenRouter. It works like Perplexity where you ask a research query and it automatically searches the web, fetches pages, looks up papers on AlphaXiv, and synthesizes a final cited response.


## How It Works

The core agent loop runs in `run_research_agent` for a maximum of 10 turns. First, it connects to the AlphaXiv MCP server (uses an API key via SSE if you have one, otherwise it handles OAuth client credentials flow and stores tokens in `.alphaxiv_tokens.json`). It dynamically pulls the MCP tool definitions, blends them with local search tools (`web_search` via Serper and `web_fetch`), and gives them to the model.

At each step, the model either returns a final answer or requests tools. If it wants tools, we execute them (local tools run locally, MCP ones get forwarded to the remote server), log the action in the side panel so the user knows what's happening, append the results to history, and query the model again. Once the model stops calling tools or we hit the 10-turn cap, it stops and prints the markdown response.


## Decisions I Made 

- **Two-Panel TUI Layout with `RichLog`**: 
  - **The Decision**: I split the screen into a main chat panel (65% width) and a tool activity panel (35% width) using Textual's `RichLog` widget.
  - **Why `RichLog`**: Raw tool outputs (like search results or fetched pages) are extremely large and messy. Placing them in a dedicated `RichLog` widget on the side keeps the main conversation clean while still displaying the agent's step-by-step thinking process.
  - **Features**: `RichLog` allows for rich markup formatting (e.g., color-coding system messages like `[bold blue]System:[/bold blue]`), automatic text-wrapping, and independent scrolling of logs without cluttering the console.

- **Trafilatura with Fallback & Truncation**: For fetching webpages, I used `trafilatura` because it extracts the main article text and drops ads/headers/footers. If that fails, it falls back to `markdownify`. I also limited the text to 8,000 characters so large pages don't eat up the entire prompt token limit.

- **Graceful MCP Fallback**: If the AlphaXiv MCP server is down or throws an auth error, instead of crashing the program, the code catches the error and runs a fallback loop (limited to 5 turns) using only local web search and fetch tools.

- **Implementation of Multithreading**:
  - **The Problem**: Web scraping and API calls are network processes that take time. Since Textual runs on the main thread, executing these operations directly would freeze the entire window, preventing the user from scrolling or even exiting the app.
  - **The Solution**: I implemented multithreading by running the agent loop inside Textual's worker system (`run_worker(..., thread=True)`).
  - **The Segregation & Safety**:
    - UI elements (widgets like `RichLog`) are not thread-safe. If a background thread tries to edit a widget directly (e.g., calling `log.write("Searching...")` from a thread), it can cause race conditions, print out-of-order logs, or crash the terminal display.
    - `self.call_from_thread` acts as a bridge. Instead of the background thread modifying the widget directly, it sends a message/callback to the main UI thread.
    - main UI thread then safely performs the actual update on the next tick of the event loop, avoiding any threading conflicts.


## What I Learned

- **From Build 1 (Custom Tool Parser)**: I learned the raw mechanics of an agent loop by hand-writing XML tags (`<tool_call>`) and regex parsing JSON arguments. It made me realize that agent loop is just a back-and-forth cycle of matching patterns and feeding the output back as a message.
- **From Build 2 (SDK Tool Calling)**: I saw how much cleaner and more reliable it is to use native OpenAI function schemas. The model is trained to output clean JSON directly, saving us from writing regex wrappers, and handling multiple tools at the same time becomes way easier.
- **From Build 3 (TUI Chatbot)**: I learned how to build a basic TUI with Textual using widgets like `RichLog` for scrollable text output, and bind custom keyboard shortcuts. Crucially, I learned that blocking API calls will lock the terminal unless run inside `run_worker(thread=True)` and updated via thread-safe callbacks to the UI elements.
- **From the Main Project**: MCP (Model Context Protocol) is awesome because once connected, you don't need to manually define tool schemas or write HTTP requests for them; it handles the protocol metadata automatically. I also learned how to handle OAuth client credentials.


## WSL2 OAuth Challenges & Solutions

While setting up OAuth authentication (e.g., for the AlphaXiv flow) within WSL2, we run into environment-specific network and GUI limitations:
- **Headless Browser Launch Failure**:
  - **Issue**: Standard libraries like Python's `webbrowser.open()` try to open native Linux browsers. Since WSL2 runs headlessly without a Linux desktop environment, this fails or hangs.
  - **Fix**: Implemented a fallback that prints the OAuth link directly to the terminal so the user can copy/paste it. Alternatively, users can install the `wslu` utility package and set `export BROWSER=wslview` in their shell configuration to bridge WSL2 browser commands to the host Windows browser.
- **Callback Resolution Mismatch (`localhost` routing)**:
  - **Issue**: The redirect callback routes back to `http://localhost:8765/callback`. The Windows browser sometimes fails to route `localhost` to the separate virtual network interface of the WSL2 VM.
  - **Fix**: Configure `.wslconfig` on the Windows host to use `networkingMode=mirrored` so Windows and WSL2 share the same loopback interface, or bind the callback listener to `0.0.0.0` and configure an SSH/port forwarding tunnel.


## Files

- `builds/build1_custom_tools.py` - Custom XML-tag tool parser (`<tool_call>`) and agent loop.
- `builds/build2_sdk_tools.py` - Native OpenAI SDK tool calling using functions like `get_weather`.
- `builds/build3_tui.py` - Basic multi-turn chat UI with Textual using key bindings.
- `project/agent.py` - The complete Perplexity-like research assistant with Serper, Trafilatura, and AlphaXiv MCP.


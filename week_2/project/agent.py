"""
ResearchBot: Week 2 Project Starter
======================================
This file currently makes a basic single-turn call to OpenRouter.
Your job is to evolve it into a full research agent with:
  - Web search and web fetch tools (using OpenAI SDK tool calling)
  - An agent loop that iterates until the model stops requesting tools
  - A Textual TUI with a chat panel and a tool activity log
  - Keyboard shortcuts: Ctrl+L (clear display), Ctrl+K (clear history), Ctrl+Q (quit),
    and at least one more of your choice

Start by getting this file working, then add tools, then add the TUI.
Don't try to build everything at once.
"""

import os
import sys
import time
import json
import re
import asyncio
import requests
import httpx
import webbrowser
from urllib.parse import parse_qs, urlparse
from markdownify import markdownify
import trafilatura
from openai import OpenAI
from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.sse import sse_client
from mcp.client.auth import OAuthClientProvider, TokenStorage
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken
from rich.markdown import Markdown
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Input, RichLog
from textual.containers import Horizontal, Vertical

load_dotenv()

# Check which API key is available and configure client
if os.environ.get("OPENROUTER_API_KEY"):
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ["OPENROUTER_API_KEY"],
    )
    MODEL = "google/gemini-2.5-flash"
else:
    client = OpenAI(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        api_key=os.environ.get("GEMINI_API_KEY", ""),
    )
    MODEL = "gemini-2.5-flash"


def call_model(prompt: str) -> str:
    response = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.choices[0].message.content


# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def web_search(query: str, num_results: int = 5) -> list[dict]:
    """Search the web using Serper API and return titles, links, and snippets."""
    serper_key = os.environ.get("SERPER_API_KEY")
    if not serper_key:
        return [{"title": "Error", "link": "", "snippet": "SERPER_API_KEY is not set."}]
    
    try:
        response = requests.post(
            "https://google.serper.dev/search",
            headers={"X-API-KEY": serper_key, "Content-Type": "application/json"},
            json={"q": query, "num": num_results},
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        results = []
        for item in data.get("organic", []):
            results.append({
                "title": item.get("title", ""),
                "link": item.get("link", ""),
                "snippet": item.get("snippet", ""),
            })
        return results
    except Exception as e:
        return [{"title": "Error", "link": "", "snippet": f"Search failed: {str(e)}"}]


def web_fetch(url: str) -> str:
    """Fetch raw HTML content from a URL and extract clean markdown or text."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; ResearchBot/1.0)"}
    try:
        response = requests.get(url, headers=headers, allow_redirects=True, timeout=10)
        response.raise_for_status()
        html = response.text
        
        # Try using trafilatura for article extraction first
        text = trafilatura.extract(html, include_comments=False, include_tables=True)
        if not text:
            # Fallback to markdownify if trafilatura fails to extract
            text = markdownify(html, heading_style="ATX", strip=["script", "style", "nav", "footer"])
            text = re.sub(r'\n{3,}', '\n\n', text).strip()
        
        # Truncate content to save tokens
        MAX_CHARS = 8000
        if len(text) > MAX_CHARS:
            text = text[:MAX_CHARS] + "\n\n[...truncated]"
        return text
    except Exception as e:
        return f"Error fetching URL: {str(e)}"


# Define standard tool schemas for local tools
LOCAL_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "Search the web for current information. Use this when the user asks "
                "about recent events, specific facts, or anything you are uncertain about. "
                "Returns a list of search results with titles, URLs, and snippets."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query. Be specific and targeted.",
                    }
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": (
                "Fetch and read the full content of a web page. Use this after web_search "
                "to read a specific result in detail. Prefer this for documentation, articles, "
                "and pages where the snippet is not enough."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The full URL to fetch, including https://",
                    }
                },
                "required": ["url"],
            },
        },
    },
]

# ---------------------------------------------------------------------------
# History Trimming
# ---------------------------------------------------------------------------

def trim_history(messages: list[dict], max_turns: int) -> list[dict]:
    """Keep the system message and only the last `max_turns` user/assistant pairs."""
    system_message = None
    chat_history = []
    for msg in messages:
        if msg["role"] == "system":
            system_message = msg
        else:
            chat_history.append(msg)
            
    max_messages = max_turns * 2
    if len(chat_history) > max_messages:
        chat_history = chat_history[-max_messages:]
        
    if system_message:
        return [system_message] + chat_history
    return chat_history


# ---------------------------------------------------------------------------
# AlphaXiv OAuth Helper & Token Storage
# ---------------------------------------------------------------------------

class FileTokenStorage(TokenStorage):
    def __init__(self, token_path: str):
        self.token_path = token_path
        self.tokens: OAuthToken | None = None
        self.client_info: OAuthClientInformationFull | None = None
        if os.path.exists(self.token_path):
            try:
                data = json.loads(open(self.token_path).read())
                if data.get("tokens"):
                    self.tokens = OAuthToken(**data["tokens"])
                if data.get("client_info"):
                    self.client_info = OAuthClientInformationFull(**data["client_info"])
            except Exception:
                pass

    def _save(self):
        data = {}
        if self.tokens:
            data["tokens"] = self.tokens.model_dump(mode="json")
        if self.client_info:
            data["client_info"] = self.client_info.model_dump(mode="json")
        open(self.token_path, "w").write(json.dumps(data, indent=2))

    async def get_tokens(self) -> OAuthToken | None:
        return self.tokens

    async def set_tokens(self, tokens: OAuthToken) -> None:
        self.tokens = tokens
        self._save()

    async def get_client_info(self) -> OAuthClientInformationFull | None:
        return self.client_info

    async def set_client_info(self, client_info: OAuthClientInformationFull) -> None:
        self.client_info = client_info
        self._save()


async def open_browser(auth_url: str) -> None:
    print(f"Opening browser for login...\nIf it doesn't open: {auth_url}\n")
    webbrowser.open(auth_url)


async def wait_for_callback() -> tuple[str, str | None]:
    from http.server import BaseHTTPRequestHandler, HTTPServer

    code = state = None

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            nonlocal code, state
            params = parse_qs(urlparse(self.path).query)
            code = params.get("code", [None])[0]
            state = params.get("state", [None])[0]
            self.send_response(200)
            self.send_header("Content-Type", "text/html")
            self.end_headers()
            self.wfile.write(b"<h1>Authorized. You can close this tab.</h1>")

        def log_message(self, *args):
            pass

    print("Waiting for callback on http://localhost:8765/callback ...")
    server = HTTPServer(("localhost", 8765), Handler)
    server.timeout = 120
    server.handle_request()
    server.server_close()

    if not code:
        raise RuntimeError("OAuth callback received no authorization code.")
    return code, state


# ---------------------------------------------------------------------------
# Research Agent Loop
# ---------------------------------------------------------------------------

async def run_research_agent(user_message: str, history: list[dict], log_callback=None) -> str:
    """Run the main agent reasoning/action loop with tool call capabilities."""
    mcp_url = "https://api.alphaxiv.org/mcp/v1"
    
    messages = history.copy()
    if not any(msg["role"] == "system" for msg in messages):
        messages.insert(0, {
            "role": "system",
            "content": (
                "You are an expert AI Research Assistant. You have access to web search, "
                "web fetch, and AlphaXiv tools for discovering and analyzing scientific papers. "
                "Synthesize information thoroughly, cite your sources, and be precise."
            )
        })
    messages.append({"role": "user", "content": user_message})

    if log_callback:
        log_callback("[bold blue]System:[/bold blue] Connecting to AlphaXiv MCP server...")

    script_dir = os.path.dirname(os.path.abspath(__file__))
    token_path = os.path.join(script_dir, ".alphaxiv_tokens.json")
    storage = FileTokenStorage(token_path)
    api_key = os.environ.get("ALPHAXIV_API_KEY")

    try:
        if api_key:
            headers = {"Authorization": f"Bearer {api_key}"}
            mcp_connect = sse_client(mcp_url, headers=headers)
        else:
            auth = OAuthClientProvider(
                server_url=mcp_url,
                client_metadata=OAuthClientMetadata(
                    client_name="AlphaXiv Search CLI",
                    redirect_uris=["http://localhost:8765/callback"],
                    grant_types=["authorization_code", "refresh_token"],
                    response_types=["code"],
                    scope="read",
                ),
                storage=storage,
                redirect_handler=open_browser,
                callback_handler=wait_for_callback,
            )
            http_client = httpx.AsyncClient(auth=auth, follow_redirects=True, timeout=60)
            mcp_connect = streamable_http_client(mcp_url, http_client=http_client)

        async with mcp_connect as transport:
            if api_key:
                read, write = transport
            else:
                read, write, _ = transport

            async with ClientSession(read, write) as session:
                await session.initialize()
                if log_callback:
                    log_callback("[bold green]System:[/bold green] Connected to AlphaXiv MCP server successfully!")

                # 1. Discover tools from the MCP server
                mcp_tools = await session.list_tools()
                
                # 2. Convert MCP tool definitions to OpenAI format
                openai_tools = list(LOCAL_TOOLS)
                mcp_tool_names = set()
                for tool in mcp_tools.tools:
                    openai_tools.append({
                        "type": "function",
                        "function": {
                            "name": tool.name,
                            "description": tool.description,
                            "parameters": tool.inputSchema,
                        },
                    })
                    mcp_tool_names.add(tool.name)

                # 3. Agent loop
                MAX_ITERATIONS = 10
                for iteration in range(MAX_ITERATIONS):
                    if log_callback:
                        log_callback(f"[bold yellow]System:[/bold yellow] Querying model (iteration {iteration + 1})...")

                    response = client.chat.completions.create(
                        model=MODEL,
                        messages=messages,
                        tools=openai_tools,
                    )
                    
                    message = response.choices[0].message
                    finish_reason = response.choices[0].finish_reason

                    if finish_reason == "stop" or not message.tool_calls:
                        if log_callback:
                            log_callback("[bold green]System:[/bold green] Model finished reasoning.")
                        return message.content or ""

                    # 4. For each tool call, delegate to the MCP server or local tool registry
                    messages.append(message)
                    for tool_call in message.tool_calls:
                        name = tool_call.function.name
                        args = json.loads(tool_call.function.arguments)
                        
                        if log_callback:
                            log_callback(f"[bold magenta]Tool Call:[/bold magenta] {name}({args})")

                        # Dispatch tool execution
                        if name == "web_search":
                            result = web_search(**args)
                            content = json.dumps(result)
                        elif name == "web_fetch":
                            content = web_fetch(**args)
                        elif name in mcp_tool_names:
                            # Forward tool call to MCP server
                            mcp_result = await session.call_tool(name, args)
                            content = mcp_result.content[0].text if mcp_result.content else ""
                        else:
                            content = f"Error: Unknown tool {name}"

                        if log_callback:
                            log_callback(f"[dim]  → Finished {name} ({len(content)} chars returned)[/dim]")

                        messages.append({
                            "role": "tool",
                            "tool_call_id": tool_call.id,
                            "name": name,
                            "content": content,
                        })

                    await asyncio.sleep(1)

                return "[Agent stopped: Hit max iteration limit without a final answer]"

    except Exception as e:
        # Fallback to local tools only if MCP server fails or is unauthorized
        if log_callback:
            log_callback(f"[bold red]MCP Connection Failed:[/bold red] {str(e)}")
            log_callback("[bold yellow]System:[/bold yellow] Running agent in fallback mode (Web tools only)...")
        
        MAX_FALLBACK_ITERATIONS = 5
        for iteration in range(MAX_FALLBACK_ITERATIONS):
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=LOCAL_TOOLS,
            )
            message = response.choices[0].message
            finish_reason = response.choices[0].finish_reason

            if finish_reason == "stop" or not message.tool_calls:
                return message.content or ""

            messages.append(message)
            for tool_call in message.tool_calls:
                name = tool_call.function.name
                args = json.loads(tool_call.function.arguments)
                
                if log_callback:
                    log_callback(f"[bold magenta]Tool Call (Fallback):[/bold magenta] {name}({args})")

                if name == "web_search":
                    result = web_search(**args)
                    content = json.dumps(result)
                elif name == "web_fetch":
                    content = web_fetch(**args)
                else:
                    content = f"Error: Tool {name} not available in fallback mode."

                if log_callback:
                    log_callback(f"[dim]  → Finished {name} ({len(content)} chars returned)[/dim]")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": name,
                    "content": content,
                })
            await asyncio.sleep(1)
            
        return "[Agent stopped: Hit max fallback iterations without a final answer]"


# ---------------------------------------------------------------------------
# TUI Application
# ---------------------------------------------------------------------------

class ResearchApp(App):
    """A full-screen TUI for the Research Agent."""

    TITLE = "alphaXiv & Web Research Assistant"
    SUB_TITLE = f"Model: {MODEL}"
    CSS = """
    Screen {
        layout: vertical;
    }
    
    Horizontal {
        height: 1fr;
    }

    #chat-panel {
        width: 65%;
        border: solid $primary;
        padding: 0 1;
    }

    #tool-panel {
        width: 35%;
        border: solid $warning;
        padding: 0 1;
    }

    #query-input {
        dock: bottom;
        height: 3;
    }

    CommandPalette {
        background: rgba(0, 0, 0, 0.85);
        align: center middle;
    }

    CommandInput {
        background: #1e1e1e;
        color: white;
        border: tall $primary;
    }

    CommandList {
        background: #1e1e1e;
        color: white;
        border: solid $primary;
    }

    CommandList > .option-list--option {
        color: white;
    }

    CommandList > .option-list--option-highlighted {
        background: $primary;
        color: white;
        text-style: bold;
    }

    CommandList > .option-list--option-hover {
        background: #333;
        color: white;
    }

    .command-palette--help-text {
        color: #888888;
    }

    .command-palette--highlight {
        color: #ff00ff;
        text-style: bold;
    }
    """

    COMMAND_PALETTE_BINDING = "ctrl+p"

    BINDINGS = [
        Binding("ctrl+l", "clear_display", "Clear display"),
        Binding("ctrl+k", "clear_history", "Clear history"),
        Binding("ctrl+s", "save_history", "Save chat"),
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+p", "command_palette", "Command Palette"),
    ]

    def __init__(self):
        super().__init__()
        self.messages: list[dict] = [
            {
                "role": "system",
                "content": (
                    "You are an expert AI Research Assistant. You have access to web search, "
                    "web fetch, and AlphaXiv tools for discovering and analyzing scientific papers. "
                    "Synthesize information thoroughly, cite your sources, and be precise."
                )
            }
        ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal():
            yield RichLog(id="chat-panel", wrap=True, markup=True, highlight=True)
            yield RichLog(id="tool-panel", wrap=True, markup=True, highlight=True)
        yield Input(placeholder="Ask a research question...", id="query-input")
        yield Footer()

    def on_mount(self) -> None:
        chat_log = self.query_one("#chat-panel", RichLog)
        tool_log = self.query_one("#tool-panel", RichLog)
        
        chat_log.write("[bold green]Welcome to ResearchBot![/bold green] Ask any scientific or web research question.\n")
        chat_log.write("[dim]Shortcuts: Ctrl+Q (quit), Ctrl+L (clear screen), Ctrl+K (fresh start), Ctrl+S (save research log)[/dim]\n\n")
        
        tool_log.write("[bold yellow]Tool Activity Log[/bold yellow]\n")
        tool_log.write("[dim]System notifications and tool invocations will appear here...[/dim]\n\n")
        
        self.query_one("#query-input").focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Called when the user submits input."""
        user_text = event.value.strip()
        if not user_text:
            return

        event.input.clear()

        chat_log = self.query_one("#chat-panel", RichLog)
        chat_log.write(f"[bold cyan][You][/bold cyan] {user_text}\n")

        # Update sub_title
        self.sub_title = "Researching..."

        # Run the agent loop in a background thread so TUI doesn't freeze
        self.run_worker(self._run_agent_task(user_text), thread=True)

    async def _run_agent_task(self, query: str) -> None:
        chat_log = self.query_one("#chat-panel", RichLog)
        tool_log = self.query_one("#tool-panel", RichLog)

        def log_callback(msg):
            self.call_from_thread(tool_log.write, msg)

        try:
            # Run the async agent loop
            reply = await run_research_agent(query, self.messages, log_callback)
            
            # Save the query/reply in message history
            self.messages.append({"role": "user", "content": query})
            self.messages.append({"role": "assistant", "content": reply})
            self.messages = trim_history(self.messages, 20)

            def update_ui(bot_reply):
                chat_log.write("[bold green][Agent][/bold green]")
                chat_log.write(Markdown(bot_reply))
                chat_log.write("\n")
                self.sub_title = f"Model: {MODEL}"

            self.call_from_thread(update_ui, reply)
            
        except Exception as e:
            def handle_error(err_msg):
                chat_log.write(f"[bold red]Error:[/bold red] {err_msg}\n")
                self.sub_title = f"Model: {MODEL}"
            self.call_from_thread(handle_error, str(e))

    # -----------------------------------------------------------------------
    # Actions (bound to keyboard shortcuts)
    # -----------------------------------------------------------------------

    def action_clear_display(self) -> None:
        """Clear the visible log panels."""
        self.query_one("#chat-panel", RichLog).clear()
        self.query_one("#tool-panel", RichLog).clear()

    def action_clear_history(self) -> None:
        """Reset conversation history and clear displays."""
        self.messages = [
            {
                "role": "system",
                "content": (
                    "You are an expert AI Research Assistant. You have access to web search, "
                    "web fetch, and AlphaXiv tools for discovering and analyzing scientific papers. "
                    "Synthesize information thoroughly, cite your sources, and be precise."
                )
            }
        ]
        self.query_one("#chat-panel", RichLog).clear()
        self.query_one("#tool-panel", RichLog).clear()
        self.query_one("#chat-panel", RichLog).write("[bold green]History reset. Ready for new research.[/bold green]\n\n")

    def action_save_history(self) -> None:
        """Save the conversation history to a text file."""
        try:
            filename = f"research_log_{int(time.time())}.txt"
            with open(filename, "w") as f:
                for msg in self.messages:
                    role = msg["role"].upper()
                    content = msg.get("content", "")
                    if not content and "tool_calls" in msg:
                        content = str(msg["tool_calls"])
                    f.write(f"[{role}]: {content}\n\n")
            self.query_one("#chat-panel", RichLog).write(f"[bold yellow]System:[/bold yellow] Chat history saved to {filename}\n")
        except Exception as e:
            self.query_one("#chat-panel", RichLog).write(f"[bold red]Error saving history:[/bold red] {str(e)}\n")


if __name__ == "__main__":
    # If standard run, start the TUI App
    ResearchApp().run()

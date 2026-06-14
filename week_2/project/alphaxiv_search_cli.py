"""
Search AlphaXiv research papers from the command line.

Usage:
    python alphaxiv_search_cli.py "attention mechanism"
    python alphaxiv_search_cli.py "transformers" --keywords self-attention --difficulty 7 --limit 5
    python alphaxiv_search_cli.py "query" --reauth   # force new OAuth login
"""

import argparse
import asyncio
import json
import os
import sys
import textwrap
import traceback
import webbrowser
from urllib.parse import parse_qs, urlparse

import httpx
from mcp import ClientSession
from mcp.client.auth import OAuthClientProvider, TokenStorage
from mcp.client.streamable_http import streamable_http_client
from mcp.shared.auth import OAuthClientInformationFull, OAuthClientMetadata, OAuthToken

ALPHAXIV_MCP_URL = "https://api.alphaxiv.org/mcp/v1"
REDIRECT_URI = "http://localhost:8765/callback"
TOKEN_FILE = ".alphaxiv_tokens.json"


# --- Token storage ---
# The MCP SDK calls these methods to persist OAuth tokens between runs.

class FileTokenStorage(TokenStorage):
    def __init__(self):
        self.tokens: OAuthToken | None = None
        self.client_info: OAuthClientInformationFull | None = None
        if os.path.exists(TOKEN_FILE):
            try:
                data = json.loads(open(TOKEN_FILE).read())
                if data.get("tokens"):
                    self.tokens = OAuthToken(**data["tokens"])
                if data.get("client_info"):
                    self.client_info = OAuthClientInformationFull(**data["client_info"])
            except Exception:
                pass

    def _save(self):
        # mode="json" converts Pydantic types like AnyUrl to plain strings
        data = {}
        if self.tokens:
            data["tokens"] = self.tokens.model_dump(mode="json")
        if self.client_info:
            data["client_info"] = self.client_info.model_dump(mode="json")
        open(TOKEN_FILE, "w").write(json.dumps(data, indent=2))

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


# --- OAuth browser flow ---
# The MCP SDK calls redirect_handler with the auth URL, then callback_handler
# once the user has authorized and the browser is redirected to localhost.

EXPECTED_STATE = None


def is_wsl() -> bool:
    try:
        with open("/proc/version", "r") as f:
            content = f.read().lower()
            return "microsoft" in content or "wsl" in content
    except Exception:
        return False


def is_wsl_interop_working() -> bool:
    import shutil
    import subprocess
    if not shutil.which("cmd.exe"):
        return False
    try:
        res = subprocess.run(["cmd.exe", "/c", "exit"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=1)
        return res.returncode == 0
    except Exception:
        return False


async def open_browser(auth_url: str) -> None:
    global EXPECTED_STATE
    try:
        parsed = urlparse(auth_url)
        params = parse_qs(parsed.query)
        EXPECTED_STATE = params.get("state", [None])[0]
    except Exception:
        pass
    print(f"Opening browser for login...\nIf it doesn't open, copy and paste this URL into your browser:\n{auth_url}\n")
    
    if is_wsl():
        if is_wsl_interop_working():
            try:
                import subprocess
                subprocess.Popen(["cmd.exe", "/c", "start", "", auth_url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass
        else:
            print("Note: WSL Windows interoperability is disabled. Please copy the link above manually.")
    elif os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
        try:
            webbrowser.open(auth_url)
        except Exception:
            pass


async def wait_for_callback() -> tuple[str, str | None]:
    import threading
    from http.server import BaseHTTPRequestHandler, HTTPServer

    code = None
    state = None
    event = asyncio.Event()
    loop = asyncio.get_running_loop()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            nonlocal code, state
            parsed_url = urlparse(self.path)
            if parsed_url.path == "/callback":
                params = parse_qs(parsed_url.query)
                code = params.get("code", [None])[0]
                state = params.get("state", [None])[0]
                
                self.send_response(200)
                self.send_header("Content-Type", "text/html")
                self.end_headers()
                self.wfile.write(b"<h1>Authorized. You can close this tab.</h1>")
                loop.call_soon_threadsafe(event.set)
            else:
                self.send_response(404)
                self.end_headers()

        def log_message(self, *args):
            pass  # silence request logs

    # Start the HTTP server on a separate thread to avoid blocking the event loop
    server = HTTPServer(("localhost", 8765), Handler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()

    print(f"Waiting for callback on {REDIRECT_URI} ...")
    print("If you are on a remote server/headless environment, please authorize using the link above,")
    print("then copy the redirect URL (starting with http://localhost:8765/callback) or the code, and paste it here:")

    async def get_user_input():
        try:
            user_input = await asyncio.to_thread(input, "Enter code or redirect URL: ")
            user_input = user_input.strip()
            if not user_input:
                return
            
            parsed = urlparse(user_input)
            params = parse_qs(parsed.query) if parsed.query else parse_qs(parsed.path)
            
            nonlocal code, state
            parsed_code = params.get("code", [None])[0]
            parsed_state = params.get("state", [None])[0]
            
            if parsed_code:
                code = parsed_code
                state = parsed_state or EXPECTED_STATE
            else:
                # Fallback: treat the entire input as the raw code
                code = user_input
                state = EXPECTED_STATE
            
            loop.call_soon_threadsafe(event.set)
        except Exception:
            pass

    input_task = asyncio.create_task(get_user_input())

    try:
        # Wait up to 120 seconds for login to complete
        await asyncio.wait_for(event.wait(), timeout=120)
    except asyncio.TimeoutError:
        print("\nLogin timeout exceeded.")
    finally:
        server.shutdown()
        server.server_close()
        input_task.cancel()

    if not code:
        raise RuntimeError("OAuth callback received no authorization code.")
    
    return code, state


# --- Output ---

def print_papers(text: str, limit: int | None) -> None:
    # Papers in the response are separated by blank lines
    papers_found = 0
    current: list[str] = []

    def flush():
        nonlocal papers_found, current
        if not current:
            return
        papers_found += 1
        if not limit or papers_found <= limit:
            print("─" * 60)
            for line in current:
                print(textwrap.fill(line, 78, subsequent_indent="  ") if line.strip() else "")
        current.clear()

    for line in text.splitlines():
        if not line.strip() and current:
            flush()
        else:
            current.append(line)
    flush()

    if limit and papers_found > limit:
        print(f"\n... {papers_found - limit} more result(s) omitted")
    print("─" * 60)
    print(f"\n{papers_found} paper(s) found")


# --- Main ---

async def search(query: str, keywords: list[str] | None, difficulty: int, limit: int | None, verbose: bool):
    storage = FileTokenStorage()

    if storage.tokens:
        print("Using saved login (--reauth to reset)")
    else:
        print("No saved login found. Starting OAuth...")

    # OAuthClientProvider handles the full OAuth 2.0 authorization code flow.
    # It auto-refreshes tokens and persists them via the storage object.
    auth = OAuthClientProvider(
        server_url=ALPHAXIV_MCP_URL,
        client_metadata=OAuthClientMetadata(
            client_name="AlphaXiv Search CLI",
            redirect_uris=[REDIRECT_URI],
            grant_types=["authorization_code", "refresh_token"],
            response_types=["code"],
            scope="read",
        ),
        storage=storage,
        redirect_handler=open_browser,
        callback_handler=wait_for_callback,
    )

    # AlphaXiv uses Streamable HTTP transport (MCP 2025-03-26 spec):
    # POST to send requests, GET for SSE stream, DELETE to end session.
    effective_keywords = keywords or query.split()[:4]
    args = {
        "question": query,
        "keywords": effective_keywords,
        "difficulty": difficulty,
    }

    try:
        async with httpx.AsyncClient(auth=auth, follow_redirects=True, timeout=60) as http:
            async with streamable_http_client(ALPHAXIV_MCP_URL, http_client=http) as (read, write, _):
                async with ClientSession(read, write) as session:
                    await session.initialize()
                    print(f'\nSearching: "{query}"')
                    print(f"Keywords: {', '.join(effective_keywords)}  |  Difficulty: {difficulty}/10\n")
                    result = await session.call_tool("discover_papers", arguments=args)
                    for content in result.content:
                        if content.type == "text":
                            print_papers(content.text, limit)
                            return
                    print("No results returned.")

    except Exception as e:
        # Unwrap Python 3.11+ ExceptionGroup from asyncio TaskGroup
        err = e.exceptions[0] if hasattr(e, "exceptions") else e
        print(f"\nError: {err}", file=sys.stderr)
        if verbose:
            traceback.print_exception(type(err), err, err.__traceback__)
        else:
            print("Run with --verbose for full traceback.", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(description="Search AlphaXiv research papers")
    parser.add_argument("query", help="Natural language search query")
    parser.add_argument("--keywords", action="append", help="Extra keywords (repeatable)")
    parser.add_argument("--difficulty", type=int, default=5, help="Search depth 1-10 (default: 5)")
    parser.add_argument("--limit", type=int, help="Max papers to show")
    parser.add_argument("--reauth", action="store_true", help="Delete saved tokens and re-login")
    parser.add_argument("--verbose", action="store_true", help="Print full error tracebacks")
    args = parser.parse_args()

    if args.reauth and os.path.exists(TOKEN_FILE):
        os.remove(TOKEN_FILE)
        print("Saved tokens removed.")

    try:
        asyncio.run(search(args.query, args.keywords, args.difficulty, args.limit, args.verbose))
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(0)


if __name__ == "__main__":
    main()

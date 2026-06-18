"""
Research Desk — Week 3 Project
===============================
Class hierarchy:
  Agent       — brain: chat(), _run_loop(), dispatch(), sessions
  REPLAgent   — terminal REPL + one-shot CLI
  TUIAgent    — Textual UI (in tui.py)

Usage:
  python agent.py                              # REPLAgent.run()
  python agent.py "What is quantum computing?" # REPLAgent.run_once()
  python agent.py --tui                        # TUIAgent.run()
  python agent.py --session abc123 "continue"
"""

import os
import sys
import json
import uuid
import re
import argparse
from datetime import datetime, timezone
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()
if not os.environ.get("OPENROUTER_API_KEY") and not os.environ.get("GEMINI_API_KEY"):
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
if not os.environ.get("OPENROUTER_API_KEY") and not os.environ.get("GEMINI_API_KEY"):
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

openrouter_client = None
gemini_client = None

if os.environ.get("OPENROUTER_API_KEY"):
    openrouter_client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=os.environ["OPENROUTER_API_KEY"],
    )

if os.environ.get("GEMINI_API_KEY"):
    gemini_client = OpenAI(
        base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
        api_key=os.environ["GEMINI_API_KEY"],
    )

if not openrouter_client and not gemini_client:
    print("ERROR: No API key found. Set OPENROUTER_API_KEY or GEMINI_API_KEY in your .env file.")
    sys.exit(1)

WORKSPACE_ROOT = os.path.abspath(os.environ.get("WORKSPACE_ROOT", "."))
MAX_ITERATIONS = 10
SESSIONS_DIR = os.path.join(WORKSPACE_ROOT, ".agent/sessions")
BASE_PROMPT = """You are Research Desk, a professional AI research agent.
You help users research complex topics by searching the web, reading academic papers, and taking detailed research notes.

Use your tools to find accurate, up-to-date information. Cite your sources with inline links.
For academic or machine learning queries, prioritize searching arXiv/Hugging Face papers first.
Save your findings to notes in the 'notes/' directory using write_file and edit_file."""

if openrouter_client:
    MODEL = os.environ.get("OPENROUTER_MODEL", "google/gemini-2.5-flash")
else:
    MODEL = "gemini-2.5-flash"


# --- Session Management Functions ---

def generate_session_id() -> str:
    return uuid.uuid4().hex[:8]


def create_session(workspace: str, session_id: str | None = None) -> str:
    sessions_path = os.path.join(workspace, ".agent/sessions")
    os.makedirs(sessions_path, exist_ok=True)
    
    if not session_id:
        session_id = generate_session_id()
        
    path = os.path.join(sessions_path, f"{session_id}.json")
    if not os.path.exists(path):
        now_str = datetime.now(timezone.utc).isoformat()
        data = {
            "id": session_id,
            "title": "Untitled",
            "created_at": now_str,
            "updated_at": now_str,
            "messages": []
        }
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
            
    return session_id


def save_session(workspace: str, session_id: str, messages: list, title: str = "Untitled") -> None:
    sessions_path = os.path.join(workspace, ".agent/sessions")
    os.makedirs(sessions_path, exist_ok=True)
    path = os.path.join(sessions_path, f"{session_id}.json")
    
    created_at = datetime.now(timezone.utc).isoformat()
    if os.path.exists(path):
        try:
            with open(path, 'r', encoding='utf-8') as f:
                old_data = json.load(f)
                created_at = old_data.get("created_at", created_at)
                if title == "Untitled":
                    title = old_data.get("title", "Untitled")
        except Exception:
            pass
            
    now_str = datetime.now(timezone.utc).isoformat()
    data = {
        "id": session_id,
        "title": title,
        "created_at": created_at,
        "updated_at": now_str,
        "messages": messages
    }
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2)


def load_session(workspace: str, session_id: str) -> dict:
    sessions_path = os.path.join(workspace, ".agent/sessions")
    path = os.path.join(sessions_path, f"{session_id}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Session {session_id} not found.")
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def list_sessions(workspace: str) -> list[dict]:
    sessions_path = os.path.join(workspace, ".agent/sessions")
    os.makedirs(sessions_path, exist_ok=True)
    sessions = []
    for fn in os.listdir(sessions_path):
        if fn.endswith(".json"):
            path = os.path.join(sessions_path, fn)
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    sessions.append({
                        "id": data.get("id"),
                        "title": data.get("title", "Untitled"),
                        "updated_at": data.get("updated_at", "")
                    })
            except Exception:
                pass
    sessions.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
    return sessions


def build_system_prompt(workspace: str) -> str:
    parts = [BASE_PROMPT]
    for filename in ("AGENTS.md", ".agent/AGENTS.md"):
        path = os.path.join(workspace, filename)
        if os.path.isfile(path):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    parts.append(f"## Project rules\n{f.read()}")
                break
            except Exception:
                pass
    return "\n\n".join(parts)


def generate_title(first_question: str, first_answer: str) -> str:
    try:
        prompt = (
            f"Based on the following user question and assistant answer, write a concise title of at most 5 words.\n\n"
            f"Question: {first_question}\n"
            f"Answer: {first_answer[:100]}...\n\n"
            f"Title:"
        )
        messages = [
            {"role": "system", "content": "You are a helpful assistant. You must return ONLY the plain text of the title, with absolutely no quotes, markdown, punctuation, lists, formatting, or introductory text. Do not explain anything."},
            {"role": "user", "content": prompt}
        ]
        
        if openrouter_client:
            model_name = os.environ.get("OPENROUTER_MODEL", "google/gemini-2.5-flash")
            res = openrouter_client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.3
            )
        elif gemini_client:
            res = gemini_client.chat.completions.create(
                model="gemini-2.5-flash",
                messages=messages,
                temperature=0.3
            )
        else:
            return "Untitled"
            
        title = res.choices[0].message.content.strip()
        title = re.sub(r'["\']', '', title)
        return title[:50]
    except Exception:
        return "Untitled"


# --- OpenAI/OpenRouter Tool Schema Declarations ---

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "Search the web for current information, news, blogs, and docs.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query. Be specific and targeted."
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "web_fetch",
            "description": "Fetch and read the full content of a web page.",
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "The full URL to fetch, including https://"
                    }
                },
                "required": ["url"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "paper_search",
            "description": "Search for academic and ML papers indexed on Hugging Face Papers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search keywords (e.g. 'transformer attention' or title/author)."
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of papers to return (default 5).",
                        "default": 5
                    }
                },
                "required": ["query"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_paper",
            "description": "Retrieve metadata and full markdown content/abstract of a paper by arXiv ID.",
            "parameters": {
                "type": "object",
                "properties": {
                    "arxiv_id": {
                        "type": "string",
                        "description": "The arXiv ID (e.g., '2307.08691' or a URL containing it)."
                    }
                },
                "required": ["arxiv_id"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a window of lines from a file with line numbers. Use this before edit_file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to the file inside workspace."
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "First line to read (1-indexed, default 1)."
                    },
                    "read_lines": {
                        "type": "integer",
                        "description": "Number of lines to read (default 200)."
                    }
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create a new file or overwrite an existing file in the workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to write the file to (e.g. 'notes/topic.md')."
                    },
                    "content": {
                        "type": "string",
                        "description": "Full text content of the file."
                    }
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Perform line-level replace, delete, or append operations on a file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Relative path to the file to edit."
                    },
                    "operation": {
                        "type": "string",
                        "enum": ["replace", "delete", "append"],
                        "description": "Operation type: 'replace' lines start_line..end_line; 'delete' lines start_line..end_line; 'append' content after start_line (0 = before line 1)."
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "Line number to start the operation at (1-indexed, or 0 for append-before-line-1)."
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "Line number to end the operation at (inclusive, required for replace/delete)."
                    },
                    "content": {
                        "type": "string",
                        "description": "Content to insert or replace with (required for replace/append)."
                    }
                },
                "required": ["path", "operation", "start_line"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files matching a pattern in a workspace directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path to list files from (default '.')."
                    },
                    "pattern": {
                        "type": "string",
                        "description": "Glob pattern (default '*')."
                    }
                }
            }
        }
    }
]


# --- Agent Base Class (Brain) ---

class Agent:
    def __init__(self, workspace: str = ".", session_id: str | None = None):
        self.workspace = os.path.abspath(workspace)
        os.environ["WORKSPACE_ROOT"] = self.workspace
        os.makedirs(os.path.join(self.workspace, "notes"), exist_ok=True)
        
        if session_id:
            self.session_id = session_id
            try:
                session_data = load_session(self.workspace, session_id)
                self.messages = session_data.get("messages", [])
                self.title = session_data.get("title", "Untitled")
            except FileNotFoundError:
                self.session_id = create_session(self.workspace, session_id)
                self.messages = []
                self.title = "Untitled"
        else:
            self.session_id = create_session(self.workspace)
            self.messages = []
            self.title = "Untitled"
            
        sys_prompt = build_system_prompt(self.workspace)
        if not self.messages or self.messages[0].get("role") != "system":
            self.messages.insert(0, {"role": "system", "content": sys_prompt})
        else:
            self.messages[0] = {"role": "system", "content": sys_prompt}

    def chat(self, user_message: str) -> str:
        self.messages.append({"role": "user", "content": user_message})
        response = self._run_loop()
        
        non_system_msgs = [m for m in self.messages if m.get("role") != "system"]
        if (self.title == "Untitled" or not self.title) and len(non_system_msgs) >= 2:
            user_q = ""
            for m in non_system_msgs:
                if m.get("role") == "user":
                    user_q = m.get("content", "")
                    break
            self.title = generate_title(user_q, response)
            
        save_session(self.workspace, self.session_id, self.messages, self.title)
        return response

    def run_once(self, prompt: str) -> str:
        return self.chat(prompt)

    def _run_loop(self) -> str:
        iterations = 0
        while iterations < MAX_ITERATIONS:
            iterations += 1
            try:
                if openrouter_client:
                    model_name = os.environ.get("OPENROUTER_MODEL", "google/gemini-2.5-flash")
                    res = openrouter_client.chat.completions.create(
                        model=model_name,
                        messages=self.messages,
                        tools=TOOLS,
                        tool_choice="auto"
                    )
                elif gemini_client:
                    res = gemini_client.chat.completions.create(
                        model="gemini-2.5-flash",
                        messages=self.messages,
                        tools=TOOLS,
                        tool_choice="auto"
                    )
                else:
                    raise RuntimeError("No active API client configured.")
            except Exception as e:
                err_msg = f"API Error: {str(e)}"
                self.messages.append({"role": "assistant", "content": err_msg})
                return err_msg
                
            choice = res.choices[0]
            message = choice.message
            
            msg_dict = {"role": "assistant"}
            if message.content:
                msg_dict["content"] = message.content
            if message.tool_calls:
                msg_dict["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments
                        }
                    }
                    for tc in message.tool_calls
                ]
            
            self.messages.append(msg_dict)
            
            if not message.tool_calls:
                return message.content or ""
                
            for tool_call in message.tool_calls:
                self._emit("tool_call", name=tool_call.function.name, arguments=tool_call.function.arguments)
                result_str = self.dispatch(tool_call)
                
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "name": tool_call.function.name,
                    "content": result_str
                })
                
        limit_msg = f"Max iterations ({MAX_ITERATIONS}) reached."
        self.messages.append({"role": "assistant", "content": limit_msg})
        return limit_msg

    def dispatch(self, tool_call) -> str:
        name = tool_call.function.name
        try:
            args = json.loads(tool_call.function.arguments)
        except Exception as e:
            return json.dumps({"error": f"Failed to parse arguments: {str(e)}"})
            
        os.environ["WORKSPACE_ROOT"] = self.workspace
        
        from tools.web import web_search, web_fetch
        from tools.papers import paper_search, read_paper
        from tools.files import read_file, write_file, edit_file, list_files
        
        try:
            if name == "web_search":
                res = web_search(args.get("query"))
            elif name == "web_fetch":
                res = web_fetch(args.get("url"))
            elif name == "paper_search":
                res = paper_search(args.get("query"), limit=args.get("limit", 5))
            elif name == "read_paper":
                res = read_paper(args.get("arxiv_id"))
            elif name == "read_file":
                res = read_file(
                    path=args.get("path"),
                    start_line=args.get("start_line", 1),
                    read_lines=args.get("read_lines", 200)
                )
            elif name == "write_file":
                res = write_file(path=args.get("path"), content=args.get("content"))
            elif name == "edit_file":
                end_line = args.get("end_line")
                if end_line is not None:
                    end_line = int(end_line)
                res = edit_file(
                    path=args.get("path"),
                    operation=args.get("operation"),
                    start_line=int(args.get("start_line")),
                    end_line=end_line,
                    content=args.get("content")
                )
            elif name == "list_files":
                res = list_files(path=args.get("path", "."), pattern=args.get("pattern", "*"))
            else:
                res = {"error": f"Unknown tool: {name}"}
        except Exception as e:
            res = {"error": f"Exception executing tool {name}: {str(e)}"}
            
        return json.dumps(res)

    def _emit(self, event: str, **data) -> None:
        pass


# --- REPLAgent (Terminal UI) ---

class REPLAgent(Agent):
    def run(self) -> None:
        print(f"==================================================")
        print(f"Research Desk [Session: {self.session_id} - {self.title}]")
        print(f"--------------------------------------------------")
        print(f"Type your research question, or use commands:")
        print(f"  /sessions           - List available sessions")
        print(f"  /resume <session_id>- Resume a session")
        print(f"  /quit or /exit      - Exit the program")
        print(f"==================================================")
        
        while True:
            try:
                user_input = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
                
            if not user_input:
                continue
                
            if user_input in ("/quit", "/exit"):
                break
                
            if user_input == "/sessions":
                sessions = list_sessions(self.workspace)
                if not sessions:
                    print("No saved sessions found.")
                else:
                    print("\nSaved Sessions:")
                    for s in sessions:
                        print(f"  - {s['id']}: {s['title']} (updated {s['updated_at']})")
                    print()
                continue
                
            if user_input.startswith("/resume "):
                parts = user_input.split(maxsplit=1)
                if len(parts) < 2:
                    print("Usage: /resume <session_id>")
                    continue
                target_id = parts[1].strip()
                try:
                    self.__init__(workspace=self.workspace, session_id=target_id)
                    print(f"\nResumed session {target_id}: '{self.title}'\n")
                except Exception as e:
                    print(f"Failed to resume session: {str(e)}")
                continue
                
            print("\nThinking...")
            reply = self.chat(user_input)
            print(f"\n[Agent]\n{reply}\n")

    def _emit(self, event: str, **data) -> None:
        if event == "tool_call":
            print(f"  [tool] Running: {data.get('name')} with {data.get('arguments')}", file=sys.stderr)


# --- Main CLI Entrypoint ---

def main():
    parser = argparse.ArgumentParser(description="Research Desk Agent")
    parser.add_argument(
        "--session",
        type=str,
        default=None,
        help="Session ID to load or resume"
    )
    parser.add_argument(
        "--tui",
        action="store_true",
        help="Launch the Textual TUI"
    )
    parser.add_argument(
        "query",
        nargs="*",
        help="One-shot research query to run"
    )
    args = parser.parse_args()
    
    if args.tui:
        try:
            from tui import TUIAgent
            tui_agent = TUIAgent(workspace=".", session_id=args.session)
            tui_agent.run()
        except ImportError as e:
            print(f"Error loading Textual TUI: {e}", file=sys.stderr)
            sys.exit(1)
        return

    agent = REPLAgent(workspace=".", session_id=args.session)
    
    if args.query:
        query_str = " ".join(args.query)
        print(f"One-shot Researching: {query_str}")
        print("Thinking...")
        reply = agent.run_once(query_str)
        print(f"\n[Agent]\n{reply}")
        return
        
    agent.run()


if __name__ == "__main__":
    main()
"""
Build 2: Agent + REPLAgent
===========================
Agent = brain (loop, tools, sessions). REPLAgent = terminal UI.

Before running:
  mkdir -p notes

Tasks:
  1. Agent — chat(), run_once(), _run_loop(), dispatch(), _emit(), session I/O
  2. REPLAgent(Agent) — run() interactive loop
  3. resolve_path, read_file, write_file, list_files, edit_file
  4. main() — one-shot: python build2_agent_class.py "hello"

TUIAgent comes in the project (tui.py). No Textual imports here.
"""

import os
import sys
import json
import glob as glob_module
import difflib
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

WORKSPACE_ROOT = os.path.abspath(os.environ.get("WORKSPACE_ROOT", "."))
MAX_ITERATIONS = 10
MAX_READ_CHARS = 12_000
BASE_PROMPT = "You are Research Desk, a helpful research assistant."

# Check which API key is available and configure client
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
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", "..", ".env"))
    load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))
    
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

if openrouter_client:
    MODEL = os.environ.get("OPENROUTER_MODEL", "google/gemini-2.5-flash")
    client = openrouter_client
else:
    MODEL = "gemini-2.5-flash"
    client = gemini_client


# --- File tools ---

def resolve_path(path: str) -> str:
    ws = os.path.abspath(os.environ.get("WORKSPACE_ROOT", "."))
    p = path.lstrip('/')
    full_path = os.path.abspath(os.path.join(ws, p))
    if not full_path.startswith(ws):
        raise ValueError(f"escapes workspace: {path}")
    return full_path


def read_file(path: str, start_line: int = 1, read_lines: int = 200) -> dict:
    try:
        filepath = resolve_path(path)
        if not os.path.exists(filepath):
            return {"error": f"File not found: {path}"}
        if os.path.isdir(filepath):
            return {"error": f"Path is a directory: {path}"}
            
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
            
        num_lines = len(lines)
        start = max(0, start_line - 1)
        end = min(num_lines, start + read_lines)
        
        lines_window = lines[start:end]
        out = []
        for idx, line in enumerate(lines_window):
            line_num = start + idx + 1
            out.append(f"{line_num}| {line}")
            
        content = "".join(out)
        has_more = end < num_lines
        
        return {
            "content": content,
            "has_more": has_more,
            "total_lines": num_lines,
            "start_line": start + 1,
            "end_line": end
        }
    except Exception as e:
        return {"error": str(e)}


def write_file(path: str, content: str) -> dict:
    try:
        fpath = resolve_path(path)
        os.makedirs(os.path.dirname(fpath), exist_ok=True)
        with open(fpath, 'w', encoding='utf-8') as f:
            f.write(content)
        return {"status": "success", "path": path}
    except Exception as e:
        return {"error": str(e)}


def edit_file(
    path: str,
    operation: str,
    start_line: int,
    end_line: int | None = None,
    content: str | None = None,
) -> dict:
    try:
        fpath = resolve_path(path)
        if not os.path.exists(fpath):
            return {"error": f"File not found: {path}"}
            
        with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
            
        old_lines = list(lines)
        
        if operation == "replace":
            if end_line is None or content is None:
                return {"error": "replace operation requires end_line and content"}
            start = max(0, start_line - 1)
            end = min(len(lines), end_line)
            new_lines = [line + '\n' for line in content.splitlines()] if content else []
            lines[start:end] = new_lines
            
        elif operation == "delete":
            if end_line is None:
                return {"error": "delete operation requires end_line"}
            start = max(0, start_line - 1)
            end = min(len(lines), end_line)
            del lines[start:end]
            
        elif operation == "append":
            if content is None:
                return {"error": "append operation requires content"}
            start = max(0, start_line)
            new_lines = [line + '\n' for line in content.splitlines()] if content else []
            lines[start:start] = new_lines
            
        else:
            return {"error": f"Unknown operation: {operation}"}
            
        with open(fpath, 'w', encoding='utf-8') as f:
            f.writelines(lines)
            
        diff_lines = list(difflib.unified_diff(
            old_lines,
            lines,
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            n=3
        ))
        diff_str = "".join(diff_lines)
        
        return {
            "status": "success",
            "path": path,
            "diff": diff_str if diff_str else "No changes made."
        }
    except Exception as e:
        return {"error": str(e)}


def list_files(path: str = ".", pattern: str = "*") -> dict:
    try:
        ws = os.path.abspath(os.environ.get("WORKSPACE_ROOT", "."))
        target_dir = resolve_path(path)
        
        if not os.path.exists(target_dir):
            return {"error": f"Directory not found: {path}"}
        if not os.path.isdir(target_dir):
            return {"error": f"Path is not a directory: {path}"}
            
        pat = os.path.join(target_dir, pattern)
        recursive = "**" in pattern
        matches = glob_module.glob(pat, recursive=recursive)
        
        results = []
        for p in matches:
            abs_p = os.path.abspath(p)
            if not abs_p.startswith(ws):
                continue
            rel_p = os.path.relpath(abs_p, ws)
            is_dir = os.path.isdir(abs_p)
            results.append({
                "path": rel_p,
                "type": "directory" if is_dir else "file",
                "size": os.path.getsize(abs_p) if not is_dir else None
            })
            
        results.sort(key=lambda x: x["path"])
        return {"files": results}
    except Exception as e:
        return {"error": str(e)}


TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "Read a window of lines from a file with line numbers.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "start_line": {"type": "integer"},
                    "read_lines": {"type": "integer"}
                },
                "required": ["path"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "Create a new file or overwrite an existing file.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "content": {"type": "string"}
                },
                "required": ["path", "content"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "Perform line-level replace, delete, or append operations.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "operation": {"type": "string", "enum": ["replace", "delete", "append"]},
                    "start_line": {"type": "integer"},
                    "end_line": {"type": "integer"},
                    "content": {"type": "string"}
                },
                "required": ["path", "operation", "start_line"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": "List files matching a pattern in a directory.",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string"},
                    "pattern": {"type": "string"}
                }
            }
        }
    }
]


class Agent:
    def __init__(self, workspace: str = ".", session_id: str | None = None):
        self.workspace = os.path.abspath(workspace)
        os.environ["WORKSPACE_ROOT"] = self.workspace
        
        from build1_sessions import create_session, load_session
        
        if session_id:
            self.session_id = session_id
            try:
                session_data = load_session(session_id)
                self.messages = session_data.get("messages", [])
            except FileNotFoundError:
                self.session_id = create_session()
                self.messages = []
        else:
            self.session_id = create_session()
            self.messages = []
            
        sys_prompt = build_system_prompt()
        if not self.messages or self.messages[0].get("role") != "system":
            self.messages.insert(0, {"role": "system", "content": sys_prompt})
        else:
            self.messages[0] = {"role": "system", "content": sys_prompt}

    def chat(self, user_message: str) -> str:
        self.messages.append({"role": "user", "content": user_message})
        response = self._run_loop()
        
        from build1_sessions import save_session
        save_session(self.session_id, self.messages, title="Untitled")
        return response

    def run_once(self, prompt: str) -> str:
        return self.chat(prompt)

    def _run_loop(self) -> str:
        iterations = 0
        while iterations < MAX_ITERATIONS:
            iterations += 1
            try:
                res = client.chat.completions.create(
                    model=MODEL,
                    messages=self.messages,
                    tools=TOOLS,
                    tool_choice="auto"
                )
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
            
        try:
            if name == "read_file":
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


class REPLAgent(Agent):
    def run(self) -> None:
        print(f"Research Desk [{self.session_id}] — /quit to exit")
        while True:
            try:
                user_input = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break
            if not user_input or user_input in ("/quit", "/exit"):
                break
            print(self.chat(user_input))
            print()

    def _emit(self, event: str, **data) -> None:
        if event == "tool_call":
            print(f"  [tool] {data.get('name')}", file=sys.stderr)


def build_system_prompt() -> str:
    parts = [BASE_PROMPT]
    for path in ("AGENTS.md", ".agent/AGENTS.md"):
        found_path = None
        if os.path.isfile(path):
            found_path = path
        elif os.path.isfile(os.path.join("..", path)):
            found_path = os.path.join("..", path)
        elif os.path.isfile(os.path.join("../project", path)):
            found_path = os.path.join("../project", path)
            
        if found_path:
            try:
                with open(found_path, 'r', encoding='utf-8') as f:
                    parts.append(f"## Project rules\n{f.read()}")
                break
            except Exception:
                pass
    return "\n\n".join(parts)


def main():
    agent = REPLAgent()
    if len(sys.argv) > 1:
        print(agent.run_once(" ".join(sys.argv[1:])))
        return
    agent.run()


if __name__ == "__main__":
    main()

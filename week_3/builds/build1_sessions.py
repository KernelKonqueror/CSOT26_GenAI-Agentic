"""
Build 1: Session Store
========================
Save and resume conversations on disk. Load AGENTS.md into the system prompt.

Tasks:
  1. create_session() -> session_id
  2. save_session(session_id, messages, title?)
  3. load_session(session_id) -> {id, title, messages, ...}
  4. list_sessions() -> [{id, title, updated_at}, ...]
  5. build_system_prompt() -> base + AGENTS.md contents

Run twice: save a session in run 1, load it in run 2 and confirm messages restored.
"""

import json
import os
import uuid
from datetime import datetime, timezone

SESSIONS_DIR = ".agent/sessions"
AGENTS_PATHS = ("AGENTS.md", ".agent/AGENTS.md")

BASE_PROMPT = "You are Research Desk, a helpful research assistant."


def create_session() -> str:
    """Return a new 8-char hex session ID."""
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    session_id = uuid.uuid4().hex[:8]
    path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
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


def save_session(session_id: str, messages: list, title: str = "Untitled") -> None:
    """Write session JSON to .agent/sessions/{id}.json"""
    path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
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


def load_session(session_id: str) -> dict:
    """Load and return session dict including messages list."""
    path = os.path.join(SESSIONS_DIR, f"{session_id}.json")
    if not os.path.exists(path):
        raise FileNotFoundError(f"Session {session_id} not found.")
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)


def list_sessions() -> list[dict]:
    """Return sessions sorted by updated_at descending."""
    os.makedirs(SESSIONS_DIR, exist_ok=True)
    sessions = []
    for fn in os.listdir(SESSIONS_DIR):
        if fn.endswith(".json"):
            path = os.path.join(SESSIONS_DIR, fn)
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


def build_system_prompt() -> str:
    """Base prompt + AGENTS.md if it exists."""
    parts = [BASE_PROMPT]
    for path in AGENTS_PATHS:
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


if __name__ == "__main__":
    sid = create_session()
    messages = [
        {"role": "system", "content": build_system_prompt()},
        {"role": "user", "content": "What is a surface code?"},
        {"role": "assistant", "content": "A surface code is a type of quantum error correcting code."},
    ]
    save_session(sid, messages, title="Quantum error correction")
    print(f"Saved session: {sid}")
    print(f"All sessions: {list_sessions()}")
    print(f"Loaded: {load_session(sid)['title']}")

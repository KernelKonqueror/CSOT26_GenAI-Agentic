"""
Sandboxed file tools — see week_3/2_agent_class.md

Implement:
  - resolve_path
  - read_file(path, start_line=1, read_lines=200)  — numbered lines, has_more
  - write_file(path, content)
  - edit_file(path, operation, start_line, end_line?, content?)  — replace | delete | append
  - list_files(path, pattern)
"""

import os
import glob as glob_module
import difflib

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
            return {"error": f"not found: {path}"}
        if os.path.isdir(filepath):
            return {"error": f"is directory: {path}"}
            
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
            return {"error": f"file not found: {path}"}
            
        with open(fpath, 'r', encoding='utf-8', errors='replace') as f:
            lines = f.readlines()
            
        old_lines = list(lines)
        
        if operation == "replace":
            if end_line is None or content is None:
                return {"error": "replace needs end_line and content"}
            start = max(0, start_line - 1)
            end = min(len(lines), end_line)
            new_lines = [line + '\n' for line in content.splitlines()] if content else []
            lines[start:end] = new_lines
            
        elif operation == "delete":
            if end_line is None:
                return {"error": "delete needs end_line"}
            start = max(0, start_line - 1)
            end = min(len(lines), end_line)
            del lines[start:end]
            
        elif operation == "append":
            if content is None:
                return {"error": "append needs content"}
            start = max(0, start_line)
            new_lines = [line + '\n' for line in content.splitlines()] if content else []
            lines[start:start] = new_lines
            
        else:
            return {"error": f"unknown operation: {operation}"}
            
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
            return {"error": f"dir not found: {path}"}
        if not os.path.isdir(target_dir):
            return {"error": f"not a dir: {path}"}
            
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

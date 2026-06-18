"""
TUIAgent — full-screen Textual UI inheriting from Agent.

Usage:
  python agent.py --tui

Tasks:
  1. class TUIAgent(Agent) — override _emit() for tool log panel
  2. class ResearchDeskApp(App) — layout, input, key bindings
  3. on_input_submitted -> worker -> self.chat() (inherited from Agent)
  4. Ctrl+L / Ctrl+K / Ctrl+Q from Week 2
"""

import sys
import os
import time
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Input, RichLog
from textual.containers import Horizontal
from rich.markdown import Markdown
from agent import Agent

class TUIAgent(Agent, App):
    CSS = """
    Screen {
        background: #0f172a;
    }
    Header {
        background: #1e293b;
        color: #38bdf8;
        text-style: bold;
    }
    Footer {
        background: #1e293b;
        color: #94a3b8;
    }
    #chat-panel {
        width: 60%;
        height: 100%;
        background: #0f172a;
        border-right: tall #1e293b;
        padding: 1;
    }
    #tool-panel {
        width: 40%;
        height: 100%;
        background: #0b0f19;
        padding: 1;
    }
    #query-input {
        background: #1e293b;
        color: #f8fafc;
        border: tall #38bdf8;
    }
    """

    BINDINGS = [
        Binding("ctrl+l", "clear_display", "Clear display"),
        Binding("ctrl+k", "clear_history", "Clear history"),
        Binding("ctrl+s", "save_session_log", "Save Log"),
        Binding("ctrl+q", "quit", "Quit"),
    ]

    def __init__(self, workspace: str = ".", session_id: str | None = None):
        Agent.__init__(self, workspace, session_id)
        App.__init__(self)
        
    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal():
            yield RichLog(id="chat-panel", wrap=True, markup=True, highlight=True)
            yield RichLog(id="tool-panel", wrap=True, markup=True, highlight=True)
        yield Input(placeholder="Ask a research question...", id="query-input")
        yield Footer()

    def on_mount(self) -> None:
        self.title = "Research Desk"
        self.sub_title = f"Session: {self.session_id} - {self.title}"
        
        chat_panel = self.query_one("#chat-panel", RichLog)
        tool_panel = self.query_one("#tool-panel", RichLog)
        
        chat_panel.write("[bold green]Welcome to Research Desk TUI![/bold green] Ask any scientific or web research question.\n")
        chat_panel.write("[dim]Shortcuts: Ctrl+Q (quit), Ctrl+L (clear screen), Ctrl+K (clear history), Ctrl+S (save log)[/dim]\n\n")
        
        tool_panel.write("[bold yellow]Tool Activity Log[/bold yellow]\n")
        tool_panel.write("[dim]System notifications and tool invocations will appear here...[/dim]\n\n")
        
        for msg in self.messages[1:]:
            role = msg.get("role")
            content = msg.get("content", "")
            if role == "user":
                chat_panel.write(f"[bold cyan][You][/bold cyan] {content}\n")
            elif role == "assistant" and content:
                chat_panel.write("[bold green][Agent][/bold green]")
                chat_panel.write(Markdown(content))
                chat_panel.write("\n")
                
        self.query_one("#query-input").focus()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        text = event.value.strip()
        if not text:
            return
            
        event.input.clear()
        
        chat_panel = self.query_one("#chat-panel", RichLog)
        chat_panel.write(f"[bold cyan][You][/bold cyan] {text}\n")
        
        self.sub_title = "Researching..."
        event.input.disabled = True
        
        self.run_worker(self._run_agent_task(text), thread=True)

    async def _run_agent_task(self, query: str) -> None:
        chat_panel = self.query_one("#chat-panel", RichLog)
        inp = self.query_one("#query-input", Input)
        
        try:
            reply = self.chat(query)
            
            def update_ui():
                chat_panel.write("[bold green][Agent][/bold green]")
                chat_panel.write(Markdown(reply))
                chat_panel.write("\n")
                self.sub_title = f"Session: {self.session_id} - {self.title}"
                inp.disabled = False
                inp.focus()
                
            self.call_from_thread(update_ui)
        except Exception as e:
            def handle_error(err_msg):
                chat_panel.write(f"[bold red]Error:[/bold red] {err_msg}\n")
                self.sub_title = f"Session: {self.session_id} - {self.title}"
                inp.disabled = False
                inp.focus()
            self.call_from_thread(handle_error, str(e))

    def _emit(self, event: str, **data) -> None:
        if event == "tool_call":
            tool_name = data.get("name")
            tool_args = data.get("arguments")
            msg = f"[bold yellow]Tool Call:[/bold yellow] [green]{tool_name}[/green] with {tool_args}\n"
            try:
                tool_panel = self.query_one("#tool-panel", RichLog)
                self.call_from_thread(tool_panel.write, msg)
            except Exception:
                pass

    def action_clear_display(self) -> None:
        self.query_one("#chat-panel", RichLog).clear()
        self.query_one("#tool-panel", RichLog).clear()

    def action_clear_history(self) -> None:
        if self.messages:
            self.messages = [self.messages[0]]
        else:
            from agent import build_system_prompt
            self.messages = [{"role": "system", "content": build_system_prompt(self.workspace)}]
            
        from agent import save_session
        save_session(self.workspace, self.session_id, self.messages, self.title)
        
        self.action_clear_display()
        chat_panel = self.query_one("#chat-panel", RichLog)
        chat_panel.write("[bold green]History reset. Ready for new research.[/bold green]\n\n")

    def action_save_session_log(self) -> None:
        try:
            filename = f"research_log_{self.session_id}_{int(time.time())}.txt"
            filepath = os.path.join(self.workspace, filename)
            with open(filepath, "w", encoding='utf-8') as f:
                for msg in self.messages:
                    role = msg["role"].upper()
                    content = msg.get("content", "")
                    if not content and "tool_calls" in msg:
                        content = str(msg["tool_calls"])
                    f.write(f"[{role}]: {content}\n\n")
            chat_panel = self.query_one("#chat-panel", RichLog)
            chat_panel.write(f"[bold yellow]System:[/bold yellow] Chat history saved to {filename}\n")
        except Exception as e:
            chat_panel = self.query_one("#chat-panel", RichLog)
            chat_panel.write(f"[bold red]Error saving history:[/bold red] {str(e)}\n")
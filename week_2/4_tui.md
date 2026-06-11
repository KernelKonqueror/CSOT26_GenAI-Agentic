# Lesson 4: Terminal User Interfaces with Textual

## Why a TUI?

A TUI (Terminal User Interface) is a full-screen application that runs inside your terminal. Unlike a stream of `print()` calls, a TUI has persistent, independently-updating panels: a sidebar for tool logs, a chat area for conversation, a status bar showing token counts.

For an agent that calls tools, a TUI transforms a wall of text into something legible: you can watch the search happen in one panel while the response builds in another.

**Textual** is the Python library for building TUIs. It uses a React-like component model (compose → render → handle events) and comes with a rich set of built-in widgets.

```bash
pip install textual
```

---

## Core Concepts

### App

Every Textual application is a subclass of `App`. You override `compose()` to define the layout, and `on_mount()` for setup:

```python
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, Input, RichLog

class ChatApp(App):
    CSS = """
    Screen {
        layout: vertical;
    }
    RichLog {
        border: solid green;
        height: 1fr;
    }
    Input {
        dock: bottom;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        yield RichLog(id="log", wrap=True, markup=True)
        yield Input(placeholder="Type a message...")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#log", RichLog).write("[bold green]Chat started.[/bold green]")

if __name__ == "__main__":
    ChatApp().run()
```

Run this and you get a full-screen app with a header, a scrollable log, and an input at the bottom.

### Widgets

The key built-in widgets:

| Widget | Purpose |
|---|---|
| `Header` | Top bar with app title |
| `Footer` | Bottom bar showing key bindings |
| `RichLog` | Scrollable text area, supports Rich markup |
| `Input` | Single-line text input |
| `Static` | Non-interactive text block |
| `Horizontal` / `Vertical` | Layout containers |
| `ScrollableContainer` | Container with scrollbar |

### CSS Layouts

Textual uses a CSS-like syntax for layout. The key properties:

```css
/* Full height, scrollable */
RichLog {
    height: 1fr;   /* "fraction", takes remaining space */
}

/* Fixed height at bottom */
Input {
    dock: bottom;
    height: 3;
}

/* Side by side */
Screen {
    layout: horizontal;
}

#left-panel {
    width: 2fr;    /* 2/3 of width */
}

#right-panel {
    width: 1fr;    /* 1/3 of width */
    border: solid yellow;
}
```

---

## Handling Events

### Input submission

When the user presses Enter in an Input widget, Textual fires `Input.Submitted`:

```python
def on_input_submitted(self, event: Input.Submitted) -> None:
    user_text = event.value.strip()
    if not user_text:
        return
    
    log = self.query_one("#log", RichLog)
    log.write(f"[bold blue]You:[/bold blue] {user_text}")
    
    event.input.clear()   # clear the input box
    
    self.call_later(self.respond, user_text)   # async-safe way to trigger work
```

### Key bindings

The `BINDINGS` class variable registers keyboard shortcuts. They automatically appear in the Footer:

```python
from textual.binding import Binding

class ChatApp(App):
    BINDINGS = [
        Binding("ctrl+c", "clear_chat", "Clear"),
        Binding("ctrl+q", "quit", "Quit"),
        Binding("ctrl+e", "export", "Export"),
    ]

    def action_clear_chat(self) -> None:
        self.query_one("#log", RichLog).clear()

    def action_export(self) -> None:
        # save conversation to file
        ...
```

The naming convention: `Binding("ctrl+x", "do_thing", "Label")` → method `action_do_thing`.

---

## Running Async Work

Textual is async-native, but blocking calls (like an API call) freeze the UI. Use `run_worker` to push work to a background thread:

```python
from textual.worker import Worker

def on_input_submitted(self, event: Input.Submitted) -> None:
    user_text = event.value.strip()
    if not user_text:
        return
    event.input.clear()
    self.run_worker(self.call_agent(user_text), thread=True)

async def call_agent(self, user_text: str) -> None:
    log = self.query_one("#log", RichLog)
    self.call_from_thread(log.write, f"[bold blue]You:[/bold blue] {user_text}")
    
    # this blocks; run_worker(thread=True) keeps UI alive
    response = run_agent_loop(user_text)      # your synchronous agent code
    
    self.call_from_thread(log.write, f"[bold green]Agent:[/bold green] {response}")
```

The key rule: **never `await` or block on the main thread**. Anything that takes time goes in a worker.

---

## A Split-Panel Layout

For an agent that calls tools, a two-panel layout is natural: conversation on the left, tool call log on the right:

```python
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.widgets import Header, Footer, Input, RichLog
from textual.containers import Horizontal, Vertical

class AgentApp(App):
    CSS = """
    Horizontal {
        height: 1fr;
    }
    #chat-panel {
        width: 65%;
        border: solid $primary;
    }
    #tool-panel {
        width: 35%;
        border: solid $warning;
    }
    Input {
        dock: bottom;
        height: 3;
    }
    """

    BINDINGS = [
        Binding("ctrl+l", "clear_chat", "Clear"),
        Binding("ctrl+q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Horizontal():
            yield RichLog(id="chat-panel", wrap=True, markup=True)
            yield RichLog(id="tool-panel", wrap=True, markup=True)
        yield Input(placeholder="Ask anything...")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#chat-panel").write("[bold]Chat[/bold]\n")
        self.query_one("#tool-panel").write("[bold]Tool Log[/bold]\n")

    def action_clear_chat(self) -> None:
        self.query_one("#chat-panel", RichLog).clear()
        self.query_one("#tool-panel", RichLog).clear()
```

---

## Rich Markup

`RichLog` supports Rich's markup syntax for styled output:

```python
log.write("[bold green]Agent:[/bold green] Here is what I found...")
log.write("[bold yellow]TOOL CALL:[/bold yellow] web_search('OpenAI DevDay 2024')")
log.write("[dim]  → 5 results returned[/dim]")
log.write("[red]ERROR:[/red] Request timed out")
```

Full markup reference: <https://rich.readthedocs.io/en/stable/markup.html>

---

## Things to Think About

- **Blocking vs. streaming.** The approach above waits for the full agent response before showing anything. How would you show the model's output token-by-token (streaming) in the TUI? What changes?

- **State.** Where do you store the conversation history, as an instance variable on the App? What happens if the user clears the chat: should the history clear too, or just the display?

- **Error display.** If the API call fails, where does the error appear? In the chat panel, in the tool panel, or in a modal? What makes sense for the user?

---

## Resources

- **Textual documentation**  
  <https://textual.textualize.io/>
- **Textual widget gallery**: every built-in widget with examples  
  <https://textual.textualize.io/widget_gallery/>
- **Textual tutorial: building a todo app**  
  <https://textual.textualize.io/tutorial/>
- **Rich markup reference**  
  <https://rich.readthedocs.io/en/stable/markup.html>
- **Textual CSS reference**  
  <https://textual.textualize.io/css_types/>

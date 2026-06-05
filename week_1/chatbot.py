import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


class ChatAgent:
    """A simple multi-turn chatbot that works with any OpenAI-compatible API."""

    def __init__(self, model="gemini-2.5-flash", system_prompt="You are a helpful assistant.",
                 max_turns=5, compaction_strategy="summarize", stream=True,
                 base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
                 api_key=None):

        self.model = model
        self.system_prompt = system_prompt
        self.max_turns = max_turns
        self.compaction_strategy = compaction_strategy
        self.stream = stream

        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("GEMINI_API_KEY not found. Set it in .env file.")

        self.client = OpenAI(base_url=base_url, api_key=self.api_key)

        self.history = []
        self.summary = None
        self.last_usage = None

    def call_model(self, prompt):
        """Single call to the model, doesn't touch history."""
        response = self.client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": self.system_prompt},
                {"role": "user", "content": prompt}
            ]
        )
        if response.usage:
            self.last_usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
        return response.choices[0].message.content

    def _build_messages(self):
        """Put together the messages list for the API call."""
        msgs = [{"role": "system", "content": self.system_prompt}]
        # if we have a summary from compacted turns, include it
        if self.summary:
            msgs.append({"role": "system",
                         "content": f"Summary of earlier conversation: {self.summary}"})
        msgs.extend(self.history)
        return msgs

    def chat(self, user_input):
        """Send a message and get a response. Handles streaming if enabled."""
        self.history.append({"role": "user", "content": user_input})
        messages = self._build_messages()

        if self.stream:
            # return a generator that yields chunks
            def stream_response():
                resp = self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    stream=True
                )
                chunks = []
                for chunk in resp:
                    if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                        text = chunk.choices[0].delta.content
                        chunks.append(text)
                        yield text

                    # try to grab usage info if available
                    if getattr(chunk, "usage", None):
                        self.last_usage = {
                            "prompt_tokens": chunk.usage.prompt_tokens,
                            "completion_tokens": chunk.usage.completion_tokens,
                            "total_tokens": chunk.usage.total_tokens
                        }

                full_reply = "".join(chunks)
                self.history.append({"role": "assistant", "content": full_reply})
                self._maybe_compact()

            return stream_response()
        else:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=messages
            )
            reply = resp.choices[0].message.content
            if resp.usage:
                self.last_usage = {
                    "prompt_tokens": resp.usage.prompt_tokens,
                    "completion_tokens": resp.usage.completion_tokens,
                    "total_tokens": resp.usage.total_tokens
                }
            self.history.append({"role": "assistant", "content": reply})
            self._maybe_compact()
            return reply

    def _maybe_compact(self):
        """Check if we have too many turns and compact if needed."""
        num_turns = len(self.history) // 2
        if num_turns > self.max_turns:
            overflow = num_turns - self.max_turns
            self._compact(overflow)

    def _compact(self, num_turns_to_remove=None):
        """Remove oldest turns. Either drop them or summarize first."""
        total_turns = len(self.history) // 2
        if total_turns == 0:
            return
        if num_turns_to_remove is None:
            num_turns_to_remove = max(total_turns - 1, 0)

        msgs_to_remove = self.history[:num_turns_to_remove * 2]
        self.history = self.history[num_turns_to_remove * 2:]

        if self.compaction_strategy == "drop":
            return

        # summarize the removed messages
        text = ""
        if self.summary:
            text += f"Previous context: {self.summary}\n\n"
        for m in msgs_to_remove:
            label = "User" if m["role"] == "user" else "Assistant"
            text += f"{label}: {m['content']}\n"

        try:
            resp = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "Summarize this conversation in under 100 words. Keep all important facts."},
                    {"role": "user", "content": text}
                ]
            )
            self.summary = resp.choices[0].message.content.strip()
        except Exception:
            if not self.summary:
                self.summary = "Earlier conversation was summarized."

    def reset(self):
        """Wipe everything - history and summary."""
        self.history = []
        self.summary = None
        self.last_usage = None


# ---- CLI part ----

MODELS = {
    "1": ("Gemini 2.5 Flash", "gemini-2.5-flash"),
    "2": ("Gemini 2.5 Pro", "gemini-2.5-pro"),
    "3": ("Gemini 2.0 Flash", "gemini-2.0-flash"),
    "4": ("Gemini 2.0 Flash Lite", "gemini-2.0-flash-lite"),
}


def run_chatbot():
    print("=== CSOT GenAI Week 1 Chatbot ===\n")

    # model selection
    print("Pick a model:")
    for k, (name, _) in MODELS.items():
        print(f"  [{k}] {name}")
    print("  [5] Custom model")

    choice = input("Choice (default 1): ").strip() or "1"

    if choice in MODELS:
        model_name, model_id = MODELS[choice]
    elif choice == "5":
        model_id = input("Enter model id: ").strip()
        model_name = model_id
    else:
        print("Invalid, using Gemini 2.5 Flash")
        model_name, model_id = MODELS["1"]

    # config
    mt = input("Max turns before compaction (default 5): ").strip()
    max_turns = int(mt) if mt.isdigit() else 5

    strat = input("Compaction: [1] Summarize [2] Drop (default 1): ").strip()
    strategy = "drop" if strat == "2" else "summarize"

    st = input("Streaming? [Y/n]: ").strip().lower()
    stream = st != "n"

    print(f"\nUsing {model_name}, max_turns={max_turns}, strategy={strategy}, stream={stream}")

    try:
        agent = ChatAgent(model=model_id, max_turns=max_turns,
                          compaction_strategy=strategy, stream=stream)
    except ValueError as e:
        print(f"Error: {e}")
        return

    print("Type 'exit' to quit, '/help' for commands.\n")

    while True:
        try:
            user_input = input("[YOU] > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nBye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ("exit", "quit"):
            print("Bye!")
            break

        # handle commands
        if user_input.startswith("/"):
            cmd = user_input.split()[0].lower()

            if cmd == "/reset":
                agent.reset()
                print("History cleared.\n")
            elif cmd == "/tokens":
                if agent.last_usage:
                    u = agent.last_usage
                    print(f"Prompt: {u['prompt_tokens']}, Completion: {u['completion_tokens']}, Total: {u['total_tokens']}\n")
                else:
                    print("No usage data yet.\n")
            elif cmd == "/compact":
                agent._compact()
                print(f"Compacted. Summary: {agent.summary}\n")
            elif cmd == "/history":
                print(f"Summary: {agent.summary}")
                print(f"Active messages: {len(agent.history)} ({len(agent.history)//2} turns)")
                for i, m in enumerate(agent.history):
                    print(f"  {i+1}. {m['role'].upper()}: {m['content'][:80]}...")
                print()
            elif cmd == "/help":
                print("Commands: /reset /tokens /compact /history /help exit\n")
            else:
                print(f"Unknown command: {cmd}\n")
            continue

        # normal message
        print("[MODEL] > ", end="", flush=True)
        try:
            if agent.stream:
                for chunk in agent.chat(user_input):
                    print(chunk, end="", flush=True)
                print("\n")
            else:
                print(agent.chat(user_input) + "\n")
        except Exception as e:
            print(f"\nAPI Error: {e}\n")


if __name__ == "__main__":
    run_chatbot()

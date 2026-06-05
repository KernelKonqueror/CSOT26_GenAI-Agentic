import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=os.environ["GEMINI_API_KEY"],
)

def run_chatbot():
    """
    A terminal chatbot that holds a coherent multi-turn conversation.

    Your implementation should:
    - Start with a system message that sets the assistant's behaviour.
    - Maintain a `messages` list with alternating user/assistant turns.
    - Append the assistant's reply to `messages` after each call.
    - Resend the full history on every API call.
    - Allow the user to type 'exit' or 'quit' to end the session.

    Stretch:
    - Add a '/reset' command that clears history so you can feel context loss live.
    - Add a '/tokens' command that prints response.usage after the last call.
    """
    messages = [
        {"role": "system", "content": "You are a helpful assistant."}
    ]

    last_usage = None
    print("Chat started. Type 'exit' to quit.\n")

    while True:
        try:
            user_input = input("[YOU] > ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nGoodbye!")
            break

        if not user_input:
            continue

        if user_input.lower() in ["exit", "quit"]:
            print("Goodbye!")
            break

        if user_input.lower() == "/reset":
            messages = [
                {"role": "system", "content": "You are a helpful assistant."}
            ]
            last_usage = None
            print("Chat history has been reset. Context lost!")
            continue

        if user_input.lower() == "/tokens":
            if last_usage:
                print(f"Tokens usage -> Prompt: {last_usage.prompt_tokens}, Completion: {last_usage.completion_tokens}, Total: {last_usage.total_tokens}")
            else:
                print("No usage history yet.")
            continue

        messages.append({"role": "user", "content": user_input})

        try:
            response = client.chat.completions.create(
                model="gemini-2.5-flash",
                messages=messages,
            )
            reply = response.choices[0].message.content
            last_usage = response.usage
            messages.append({"role": "assistant", "content": reply})
            print(f"[MODEL] > {reply}\n")
        except Exception as e:
            print(f"Error calling model: {e}\n")

if __name__ == "__main__":
    run_chatbot()

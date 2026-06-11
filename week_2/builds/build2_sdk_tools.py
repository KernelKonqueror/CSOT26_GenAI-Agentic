"""
Build 2: Tool Calling with the OpenAI SDK
==========================================
Build 1 had you implement the tool-call round-trip by hand using a custom text format.
This build does the same thing the production way: using the OpenAI SDK's native
`tools` parameter, `tool_calls` response field, and `"role": "tool"` messages.

The mechanics are identical. You're still parsing a tool name, running a function,
and sending the result back. The difference is that the SDK handles the encoding
and the model is trained to produce structured JSON tool calls rather than freeform XML.

Implement the same two tools as Build 1:
  - get_weather(city: str) -> dict
  - calculate(expression: str) -> dict

Then complete the agent loop and watch the pattern become clean.

Stretch goals (not required):
  - Add a third tool: get_time(timezone: str) -> dict
  - Handle multiple tool_calls in a single response (the model can call several at once)
  - Add a token counter that prints total tokens used after the loop ends
"""

import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ["OPENROUTER_API_KEY"],
)

MODEL = "deepseek/deepseek-v4-flash:free"

# ---------------------------------------------------------------------------
# Tool schemas (the contract between you and the model)
# ---------------------------------------------------------------------------

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": (
                "Returns the current weather for a given city. "
                "Call this whenever the user asks about weather, temperature, or climate. "
                "Do not guess weather. Always call this tool."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "The city name, e.g. 'Delhi' or 'San Francisco'",
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "Temperature unit. Default to celsius.",
                    },
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calculate",
            "description": (
                "Evaluates a mathematical expression and returns the result. "
                "Use this for any arithmetic the user asks about. "
                "Pass the expression as a string, e.g. '1337 * 42 + 7'."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "expression": {
                        "type": "string",
                        "description": "A Python arithmetic expression, e.g. '100 / 4 + 3'",
                    }
                },
                "required": ["expression"],
            },
        },
    },
]

# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def get_weather(city: str, unit: str = "celsius") -> dict:
    """
    Return realistic-looking fake weather data for the city.
    In production this would call a weather API.

    Return a dict like:
        {"city": city, "temperature": 28, "unit": unit, "condition": "partly cloudy"}
    """
    # TODO: implement (hardcode some reasonable values)
    pass


def calculate(expression: str) -> dict:
    """
    Safely evaluate a math expression.
    Use eval() with restricted globals so imports and builtins are blocked.
    Return {"result": value} or {"error": message}.
    """
    # TODO: implement
    pass


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

TOOL_REGISTRY = {
    "get_weather": get_weather,
    "calculate": calculate,
}

def dispatch(tool_call) -> str:
    """
    Execute a single tool_call object from the API response.

    tool_call has:
        tool_call.function.name       (the tool name)
        tool_call.function.arguments  (a JSON string of arguments)

    Return a JSON string of the result dict.
    On unknown tool or exception, return a JSON error dict.

    Note: tool_call.function.arguments is a *string*, not a dict. Parse it first.
    """
    # TODO: implement
    pass


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

MAX_ITERATIONS = 8

def run_agent(user_message: str) -> str:
    """
    Run the agent loop using native SDK tool calling.

    Steps:
      1. Append the user message to history.
      2. Call client.chat.completions.create() with tools=TOOLS.
      3. If response.choices[0].finish_reason == "tool_calls":
           a. Append the assistant message (it contains .tool_calls) to history.
           b. For each tool_call in message.tool_calls:
                - dispatch it
                - append a {"role": "tool", "tool_call_id": ..., "content": ...} message
           c. Go to 2.
      4. If finish_reason == "stop": return message.content.
      5. If MAX_ITERATIONS reached: return an error string.

    Print to stderr whenever a tool executes so you can follow the loop.

    Hint: the assistant message you append in step 3a must be the raw message object,
    not a dict. The SDK accepts both, but keep it consistent with what the API returned.
    """
    messages = [
        {"role": "system", "content": "You are a helpful assistant. Use tools when appropriate."},
        {"role": "user", "content": user_message},
    ]

    for _ in range(MAX_ITERATIONS):
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS,
        )
        message = response.choices[0].message
        finish_reason = response.choices[0].finish_reason

        # TODO: handle finish_reason == "tool_calls"
        # TODO: handle finish_reason == "stop"
        pass

    return f"[Agent stopped after {MAX_ITERATIONS} iterations without a final answer]"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    test_queries = [
        "What's the weather in Tokyo?",
        "Calculate: (2**10) - 1",
        "Compare the weather in London and Delhi, and tell me what 451 * 3 is.",
    ]

    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"{'='*60}")
        result = run_agent(query)
        print(f"\nFinal answer:\n{result}")

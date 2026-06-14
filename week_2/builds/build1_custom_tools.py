"""
Build 1: Custom Tool Call Parser
=================================
Before modern SDKs handled tool calls natively, developers used custom text formats
that the model was prompted to emit. This build has you implement that pattern from
scratch: prompt the model to emit tool calls in a structured format, parse them, run
the corresponding Python function, and feed the result back.

This is NOT the production way to do it (Build 2 is). But doing it manually first
makes the mechanics obvious. The SDK is doing exactly this, just more robustly.

The format we'll use:
    The model emits tool calls wrapped in <tool_call> tags, like:

        I need to read the file first.

        <tool_call>
        {"name": "read_file", "arguments": {"path": "notes.txt"}}
        </tool_call>

    Your code finds the tag, parses the JSON, runs the function, and injects
    the result back as a <tool_response> in the next message.

Tasks:
  1. Complete `parse_tool_call` to extract name + arguments from a model response
  2. Complete `dispatch` to route a tool call to the right Python function
  3. Complete `run_agent` to implement the back-and-forth loop

Tools to implement:
  - read_file(path: str) -> dict    reads a file from disk and returns its content
  - write_file(path: str, content: str) -> dict    writes content to a file on disk

Before running, create a file called `sample.txt` with some text in it.
"""

import os
import re
import json
import sys
from openai import OpenAI
from dotenv import load_dotenv
import time

load_dotenv()

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

if openrouter_client:
    MODEL = os.environ.get("OPENROUTER_MODEL", "openrouter/free")
else:
    MODEL = "gemini-2.5-flash"


def call_chat_completion(messages, temperature=0.0):
    global MODEL
    if openrouter_client:
        try:
            model_name = os.environ.get("OPENROUTER_MODEL", "openrouter/free")
            response = openrouter_client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=temperature,
            )
            MODEL = model_name
            return response
        except Exception as e:
            if gemini_client:
                print(f"Warning: OpenRouter call failed: {e}. Falling back to Gemini...", file=sys.stderr)
                MODEL = "gemini-2.5-flash"
                return gemini_client.chat.completions.create(
                    model=MODEL,
                    messages=messages,
                    temperature=temperature,
                )
            else:
                raise e
    if gemini_client:
        MODEL = "gemini-2.5-flash"
        return gemini_client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=temperature,
        )
    raise RuntimeError("No configured API clients available.")

SYSTEM_PROMPT = SYSTEM_PROMPT = """You are a helpful file assistant with access to the following tools:

- read_file(path: str): reads a file from disk and returns its content
- write_file(path: str, content: str): writes content to a file on disk

CRITICAL RULE: You MUST use the exact XML format specified below. 
DO NOT write raw python code. DO NOT wrap code inside <tool_code> tags. 
You are an agent, you must ONLY emit the JSON object inside <tool_call> tags.

When you need to use a tool, emit EXACTLY this format and nothing else:

<tool_call>
{"name": "TOOL_NAME", "arguments": {"arg1": "value1"}}
</tool_call>

After you receive the tool result in a <tool_response> block, continue your response
normally. Do not emit a tool_call and prose in the same turn. Pick one or the other.
"""

# ---------------------------------------------------------------------------
# Tool implementations
# ---------------------------------------------------------------------------

def read_file(path: str) -> dict:
    """
    Read a file from disk and return its content.
    Return {"content": ..., "path": ...} on success.
    Return {"error": ...} if the file doesn't exist or can't be read.
    """
    try:
        with open(path, "r") as file:
            content = file.read()
            return {"content": content, "path": path}
    except FileNotFoundError:
        return {"error": f"File not found: {path}"}
    except PermissionError:
        return {"error": "Permission denied"}
    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}


def write_file(path: str, content: str) -> dict:
    """
    Write content to a file on disk.
    Return {"success": True, "path": ..., "bytes_written": ...} on success.
    Return {"error": ...} on failure.

    Hint: open(path, 'w') and then f.write(content).
     """
    try:
        with open(path, "w") as file:
            bytes_written = file.write(content)
            return {"success": True, "path": path, "bytes_written": bytes_written}
    except PermissionError:
        return {"error": "Permission denied"}
    except Exception as e:
        return {"error": f"An error occurred: {str(e)}"}


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def parse_tool_call(response_text: str) -> dict | None:
    """
    Extract a tool call from the model's response text.

    Returns a dict {"name": str, "arguments": dict} if a <tool_call> block is found,
    or None if there is no tool call in the response.

    The format to parse:
        <tool_call>
        {"name": "...", "arguments": {...}}
        </tool_call>

    Hint: use re.search() with re.DOTALL to find the block, then json.loads() the body.
    """
    match=re.search(r'<tool_call>\s*(.*?)\s*</tool_call>',response_text, flags =   re.DOTALL)
    if not match:
         return None
    try:
         tool_call=json.loads(match.group(1))
         return tool_call
    except:
         return None
    # TODO: implement
    pass


def strip_tool_call(response_text: str) -> str:
    """
    Return the response text with any <tool_call>...</tool_call> block removed.
    Useful for printing the model's prose without the raw tag.
    """


    return re.sub(r'<tool_call>.*?</tool_call>' , '' , response_text , flags=re.DOTALL  )
    # TODO: implement (re.sub is your friend)
    pass


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------

TOOL_REGISTRY = {
    "read_file": read_file,
    "write_file": write_file,
}

def dispatch(name: str, arguments: dict) -> str:
    """
    Look up the tool by name, call it with the given arguments, and return a
    JSON string of the result.

    If the tool is not found, return: {"error": "Unknown tool: <name>"}
    If the call raises an exception, return: {"error": "<exception message>"}

    Always return a string (json.dumps the result dict).
    """
    if name not in TOOL_REGISTRY:
         return json.dumps({"error" : f"Unkown tool: {name}"})

    tool = TOOL_REGISTRY[name]
    try :
         result = tool(**arguments)
         return json.dumps(result)
    except Exception as e:
         return json.dumps({"error" : f'<{e}>'})
    


    # TODO: implement
    


# ---------------------------------------------------------------------------
# Agent loop
# ---------------------------------------------------------------------------

MAX_ITERATIONS = 6

def run_agent(user_message: str) -> str:
    """
    Run the tool-calling agent loop for a single user message.

    Steps:
      1. Build the initial messages list with SYSTEM_PROMPT + user message.
      2. Call the model.
      3. Parse the response for a <tool_call>.
      4. If found: run the tool, inject a <tool_response> block into messages, go to 2.
      5. If not found: return the model's text (the final answer).
      6. If MAX_ITERATIONS reached: return an error string.

    The <tool_response> you inject back should look like:
        <tool_response>
        {"content": "Hello, world!",     "path": "sample.txt"}
        </tool_response>

    Wrap it in a user message so the model sees it as a continuation:
        {"role": "user", "content": "<tool_response>\n...\n</tool_response>"}

    Print a line to stderr each time a tool is called so you can follow the loop.

    """


#step 1
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_message},
    ]


    for iteration in range(MAX_ITERATIONS):
        # TODO: call the model, parse the response, dispatch or return
        response = call_chat_completion(
             messages=messages,
             temperature=0.0
        )

        response_text = response.choices[0].message.content

        # 3. Save the actual string content to your history
        messages.append({"role": "assistant", "content": response_text})

        # 4. FIX: Pass the 'response_text' string to the parser, NOT the raw 'response' object
        tool_call = parse_tool_call(response_text)

        if tool_call is None:
             return strip_tool_call(response_text)

        tool_name=tool_call["name"]
        tool_args= tool_call["arguments"]

        print(f"--> [Iteration {iteration + 1}] Calling tool: {tool_name} with {tool_args}", file=sys.stderr)
        tool_result_json=dispatch(tool_name,tool_args)
        tool_response_text = f"<tool_response>\n{tool_result_json}\n</tool_response>"
        messages.append({"role" : "user" , "content" : tool_response_text})
        time.sleep(3)

        pass

    return f"[Agent stopped after {MAX_ITERATIONS} iterations]"


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Create a sample file for the agent to work with
    with open("sample.txt", "w") as f:
        f.write("IIT Delhi was established in 1961. It is one of the premier engineering institutions in India.\n")
        f.write("The campus spans 325 acres in Hauz Khas, New Delhi.\n")

    test_queries = [
        "Read sample.txt and summarise what it says.",
        "Read sample.txt and write a one-sentence version of its content to summary.txt.",
    ]

    for query in test_queries:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print(f"{'='*60}")
        result = run_agent(query)
        print(f"Answer: {result}")

import os
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

client = OpenAI(
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    api_key=os.environ["GEMINI_API_KEY"],
)

def call_model(prompt: str) -> str:
    """
    Make a single chat completion call.
    Print the full response object first and understand its structure.
    Then return just the assistant's text.
    """
    response = client.chat.completions.create(
        model="gemini-2.5-flash",
        messages=[
            {"role": "user", "content": prompt}
        ],
    )
    print("--- Full Response Object ---")
    print(response)
    print("----------------------------\n")
    return response.choices[0].message.content

if __name__ == "__main__":
    print(call_model("What is the capital of Australia?"))

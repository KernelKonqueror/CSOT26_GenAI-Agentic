# Week 1 Submission

## What I Built


A teminal chatbot as specified in the readme file, It used OpenAi library along with Google AI Studio as my LLM. The main file which contains the chatbot is `chatbot.py` which handles the multituen conversation.


## How It Works

The model doesnt have a memory it just processes the input we provide as a text. So I have implemented a history list in which previous messages are stored after compaction. As sending same messages over and over again will exponentially increase the cost of the API. Or else we may get exhauseted of the token limit.

So after a conversation gets too long so I have added a rolling buffer system that keeps the last N messages which is configurable but default is 5. When it is filled up then we just make a another api call to just summarize the old messages so that the model has some context bout the previous conversation or lose the previous messages as a result we lose context


## Decisions I Made

- **Why Google AI Studio instead of OpenRouter**: I started with OpenRouter but kept hitting rate limits on the free tier (429 errors every few messages). Google AI Studio has much more generous free limits so I switched to that. The code still uses the openai SDK since Gemini's API is OpenAI-compatible.

- **Summarize vs Drop**: I defaulted to summarize because just dropping messages means the model completely forgets earlier context. With summarization, it at least knows about the imp points about the conversation. The downside is it costs an extra API call each time compaction happens.

- **Streaming**: I implemented streaming because waiting for the full response felt slow. With streaming you see tokens appear as they're generated which feels more natural.

## What I Learned

- The model doesnt have any memory about the user but we can built it with proper prompting techniques
- Token usage adds up fast. A few turns of conversation and you're already at 100+ tokens just for the prompt.
- How to edit the .env file using nano command
- How can I keep the context about previous conversation in prompt itself without using any memory.
- Apart from it I learnt about how to keep my api key safe using env and gitignore
- I have learnt the format of the API, in order to manipulate the tone of the model.
- I learnt about how to enable data stream in order to feel the chatbot dynamic



## Files

- `build1.py` - Single turn script, sends one prompt and prints the full response object
- `build2.py` - Multi-turn chatbot with `/reset` and `/tokens` commands
- `chatbot.py` - Full ChatAgent class with rolling buffer, compaction, streaming

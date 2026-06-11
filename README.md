# CSOT GenAI/Agentic Track 2026

## Introduction

Welcome to the **GenAI/Agentic** track of CAIC Summer of Technology 2026.

Six weeks. One project, built entirely from scratch.

This track takes you from your first LLM API call to shipping a real, working AI agent — the kind that doesn't just generate text, but *takes action*. You'll implement every layer by hand: tool dispatchers, agent loops, memory systems, execution environments. No frameworks doing the heavy lifting (Langchain is overrated anyway). Just you and the primitives.

---

## Why the Agents Track?

AI powered engineering is moving fast — from prompt design to orchestration to smarter checks to make it harder for developers to shoot themselves in the foot. Here's what this track gives you:

* **Manual Orchestration Mastery**: Understand the exact mechanics of tool calling, function schemas, and multi-turn loops by coding them yourself — without high-level abstractions hiding the details.

* **State Management Architecture**: Move beyond stateless APIs by designing context buffers, working memory, and evolving long-term memory stores that persist across sessions.

* **Real-World Execution Capabilities**: Bridge the gap between text generation and environment interaction — your agent won't just *describe* what to do, it'll *do it*.

* **Leaderboard-Driven Validation**: Each week ships to an auto-graded eval set. You know exactly where you stand.

---

## What Are We Building?

![](https://media4.giphy.com/media/v1.Y2lkPTc5MGI3NjExdzR2YjB2emk1Mm8zYTJ1dTBqM3RtZjkycHo2dXY3NGlta3dmb2pvaiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/g0JP0HG6zF0o8/giphy.gif)

The project reveals itself as the weeks progress. Each week you add a new capability layer, and by Week 6 those layers compose into an agent you could actually hand to someone.

---

## Weekly Roadmap

### Week 1: LLM APIs, API-Key Safety & Conversation State

Foundation week — get the fundamentals right so everything built on top of them is solid.

Focus on:

* Understanding LLM API mechanics: requests, responses, tokens, and how to read a response object properly.
* Understanding chat templates: How the conversation is represented as system, assistant and user dialogues.
* Strict API-key hygiene using `.env` files, `python-dotenv`, and `.gitignore` — keys that leak cost you more than just money.
* Managing the stateless nature of LLM APIs by building manual, role-assigned conversation history from scratch.

✅ *Deliverable*: A terminal chatbot that holds a coherent multi-turn conversation, with the API key loaded from the environment and never touching the source code.

---

### Week 2: Tools, Agents, and TUIs

The heart of the course. A tool is a contract between your code and the model. An agent is a loop around tool calls. Once you see it, you can't unsee it.

Focus on:

* Implementing tool calling from scratch using a custom text format — so the SDK abstraction is never magic.
* Using the OpenAI SDK's native function calling: tool schemas, the `tool_calls` response field, and the full round-trip.
* Building web tools: fetching and cleaning pages with `requests`, searching the web with Serper, and understanding `llms.txt`.
* Connecting an online MCP server (AlphaXiv) to an OpenAI SDK agent loop, so the agent can search and read academic papers.
* Wrapping everything in a full-screen terminal UI with Textual.

✅ *Deliverable*: **Build your own Perplexity** — a TUI research agent that chains web search, page fetching, and academic paper search (via AlphaXiv MCP) to answer research questions it couldn't answer alone.
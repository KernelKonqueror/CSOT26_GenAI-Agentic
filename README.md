# CSOT GenAI/Agentic Track 2026: Building AI Coding Agents

## Introduction

Welcome to the **GenAI/Agentic** track of the CSOT (CAIC Summer of Technology) 2026! 

This vertical is designed to take you from executing basic API requests to building a **fully autonomous, stateful AI coding agent** that operates in your terminal. You will transition from simple single-turn prompts to implementing loops, hand-written tool dispatchers, persistent file-based memory frameworks, and self-verifying execution environments. By the end of this course, you will have built a CLI-native assistant capable of exploring codebases, modifying files, running tests, and debugging itself.

---

## Why the Agents Track?

AI engineering is rapidly moving from simple prompt design to orchestration loops. Here is what you will gain from this track:

* **Manual Orchestration Mastery**: Learn the exact mechanics of tool calling, function schemas, and multi-turn loops by coding them yourself—without relying on high-level frameworks.


* **State Management Architecture**: Move beyond stateless APIs by designing complex context management, short-term working memory buffers, and evolving long-term memory file stores.


* **Real-World Execution Capabilities**: Bridge the gap between text generation and environment interaction by building tools that read systems, run terminal commands, and review code diffs.


* **Leaderboard-Driven Validation**: Test your agent's performance, memory recall, and optimization metrics weekly on automated, held-out evaluation sets.



---

## What Project Are We Building?

Inspired by cutting-edge software engineering assistants like Claude Code, your ultimate objective is to build **Your Own CLI Claude Code**.

Your agent will be given complex coding tasks in plain English. Operating autonomously within a real local directory, it will:

1. **Explore & Analyze**: Map out project directories and parse codebase architecture.


2. **Execute Edits**: Make precise file adjustments with visual safety diffs and confirmation checks.


3. **Verify & Iterate**: Run test suites via terminal commands, capture errors, and recursively debug until all tests pass.



---

## Weekly Roadmap — CSOT Agents Track

### Week 1: LLM APIs, API-Key Safety & Conversation State

Focus on:

* Understanding LLM API mechanics (requests, responses, tokens, and response object structures).


* Mastering strict API-key hygiene using `.env` files and `.gitignore` configurations.


* Managing the stateless nature of APIs by building manual, role-assigned conversation history tracking.



✅ *Deliverable*: A terminal chatbot script that holds a coherent multi-turn conversation backed by environment-loaded keys.

---

### Week 2: Tools & the Agent Loop

Focus on:

* Writing precise `function_declaration` schemas so the model knows *when* to trigger external tools.


* Implementing the canonical agent loop: managing manual `function_call` and `function_response` round-trips.


* Building a modular, configuration-free tool `dispatcher` dictionary with iteration caps and text-based error routing.



✅ *Deliverable*: A search agent capable of chaining a custom Google Search tool and a web scraper tool across multiple loop iterations to answer deep research questions.

---

### Week 3: Agent Memory

Focus on:

* Exploring the CoALA cognitive framework taxonomy (Working, Semantic, Episodic, and Procedural memory).


* Building a context-window manager to handle token limits via rolling buffers and summarize-and-evict mechanisms.


* Constructing persistent, cross-session long-term memory using optimized file-based storage systems.



✅ *Deliverable*: A memory-enabled agent using hand-written storage systems to recall user facts and logs across entirely separate terminal sessions.

---

### Week 4: From General Agent to Coding Agent

Focus on:

* Applying tool design principles (sharp schemas, predictable returns, and unprompted tool usage execution).


* Implementing baseline repository navigation capabilities like `read_file` and `list_files` with elegant error catching.


* Merging week 3's memory foundations into a workspace-specific memory map.



✅ *Deliverable*: A CLI-native codebase-Q&A agent capable of independently exploring and explaining an existing project directory.

---

### Week 5: Editing, Running Code & Verifying

Focus on:

* Building safe text modification mechanisms (`edit_file` via string replacement) integrated with a colorized terminal diff utility.


* Constructing a `run_bash` tool utilizing subprocess execution, sandboxed by command allowlists and human approval gates.


* Injecting system prompts that govern engineering behaviors (minimal edits, verification workflows) combined with streaming terminal outputs.



✅ *Deliverable*: An iterative, self-correcting debugging agent that attempts to fix broken files, reads test feedback, and loops until all tests are green.

---

### Week 6: Final Project - Build Your Own CLI Claude Code

Focus on:

* Unifying all components: the agent loop, memory vaults, file-editing engines, and code execution blocks.


* Handling end-to-end user-submitted software requests in plain English on an un-searched codebase.


* Optimizing token usage and loop execution efficiency under tight test suite validation.



✅ *Deliverable*: A fully autonomous, production-grade terminal coding agent running entirely on the Gemini API.

---

## Let’s Go!

Loop it. Ground it. Verify it. Run it. 🚀
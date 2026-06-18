# Agent Parallelism

This document explores the concept of agent parallelism in the context of large language model (LLM) agents and multi-agent systems. It examines how parallelism is being leveraged to improve efficiency, scalability, and performance in various agentic tasks, from prompt learning to complex reasoning and information seeking.

## Key Research Papers:
### [Combee: Scaling Prompt Learning for Self-Improving Language Model Agents](https://arxiv.org/abs/2604.04247)

This paper proposes Combee, a framework for scaling parallel prompt learning in self-improving LLM agents. It addresses the limitations of existing methods (like ACE or GEPA) that struggle with quality degradation in high-parallelism settings. Combee uses parallel scans and an augmented shuffle mechanism, along with a dynamic batch size controller, to achieve up to 17x speedup with comparable or better accuracy and equivalent cost. It enables efficient learning from large sets of agentic traces or parallel agent executions.

### [MarsRL: Advancing Multi-Agent Reasoning System via Reinforcement Learning with Agentic Pipeline Parallelism](https://arxiv.org/abs/2511.11373)

This paper introduces MarsRL, a reinforcement learning framework for multi-agent reasoning systems that employs agentic pipeline parallelism. It aims to optimize all agents (Solver, Verifier, Corrector) in the system jointly, especially for open-source models where critic and correction capabilities are often insufficient. MarsRL incorporates agent-specific reward mechanisms to reduce noise and uses pipeline-inspired training for efficient handling of long trajectories. The framework demonstrates significant improvements in reasoning accuracy on complex benchmarks.

### [MARCO: Multi-Agent Code Optimization with Real-Time Knowledge Integration for High-Performance Computing](https://arxiv.org/abs/2505.03906)

MARCO (Multi-Agent Reactive Code Optimizer) is a framework designed to enhance LLM-generated code for High-Performance Computing (HPC) through a specialized multi-agent architecture. It uses separate agents for code generation and performance evaluation in a feedback loop. A key feature is its web-search component that retrieves real-time optimization techniques, bridging the knowledge gap in pre-trained LLMs. MARCO significantly reduces runtime compared to general-purpose LLMs, especially with the integrated web-search.


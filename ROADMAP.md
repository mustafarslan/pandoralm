# 🗺️ PandoraLM Roadmap

This document outlines the future development milestones and planned features for the PandoraLM project.

## 🚀 Upcoming Features

### 🧠 Cognitive Core 2.0

- [ ] **Advanced Code Graph Mapper**
  - Current support: `CONTAINS`, `HAS_METHOD`.
  - **Planned**: Extract and map `CALLS`, `INHERITS`, and `IMPORTS` relationships to enable deep dependency analysis and "Jump to Definition" reasoning.
  - *Goal*: Enable the "Code Brain" to answer questions like "What functions call `process_payment`?" or "Show me the class hierarchy for `BaseAgent`."

- [ ] **Memory Consolidation**
  - [ ] Periodic background tasks to summarize and compress user memories.
  - [ ] "Forgetting" mechanism for stale or irrelevant facts.

### 🔌 Distributed Agents

- [x] **arXiv Search Agent** (MCP)
  - Search and download academic papers from arXiv.org
- [ ] **Google Search Agent** (MCP)
- [ ] **Slack Connector** (MCP)
  - Bi-directional chat capability via Slack.

### 🛡️ Security & Governance

- [ ] **Audit Log UI**
  - Frontend visualization for the `audit_log` table (who accessed what, when).
- [ ] **PII Redaction Pipeline**
  - Automatic masking of sensitive data before vectorization.

## 🔮 Long-Term Vision

- **Federated Knowledge Graphs**: Connect multiple PandoraLM instances across different organizations.
- **Edge Deployment**: Optimized lightweight version for MacBook M3/M4 local usage without Kubernetes.

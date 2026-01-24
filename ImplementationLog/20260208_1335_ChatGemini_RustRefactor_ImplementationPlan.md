# Implementation Log: ChatGemini Rust Refactoring

> **Date:** 2026-02-08 13:35 (UTC+8)
> **Status:** Initializing

## Architecture Decisions

### 1. HTTP Client Strategy
Since Google's official Rust SDK might be less mature or non-existent compared to Python's `google-genai`, I will implement a robust REST API client using `reqwest`.
- **Base URL:** `https://generativelanguage.googleapis.com/v1beta` (or v1alpha for experimental).
- **Streaming:** Server-Sent Events (SSE) parsing for chat stream.

### 2. TUI Strategy
Replacing `prompt_toolkit` and `rich`.
- **Input:** `reedline` (used by Nushell) offers excellent history, highlighting, and multiline support.
- **Output:** `ratatui` for dashboards, but for simple chat output, `crossterm` + formatted printing might be sufficient and "lighter" than a full screen app. *Decision: Hybrid. Use `reedline` for the prompt loop and formatted stdout for the chat stream. Use `ratatui` only for full-screen menus (like Model Selector).*

### 3. State Management
- **ChatState struct:** Holds history, current model config, API key, and session cost.
- **Arc<Mutex<ChatState>>:** Thread-safe sharing if needed (though the CLI is mostly linear).

### 4. Vector DB (CodeGemini)
- Replacing FAISS. Python uses `faiss-cpu`.
- Rust has `lance` (modern, disk-based, fast) or `usearch`.
- **Choice:** `usearch` is lightweight and has good Rust bindings. Or simpler: `instant-distance`.
- *Refinement:* For v1, I might mock this or use a simple cosine similarity search on in-memory vectors if the dataset is small (< 10k files). The README says "Lightweight", so in-memory might suffice.

## Project Structure
```text
chat_gemini_rust/
├── Cargo.toml
├── src/
│   ├── main.rs           # Entry point
│   ├── config.rs         # Env and Settings
│   ├── client/           # Gemini API Client
│   │   ├── mod.rs
│   │   ├── models.rs     # Structs for JSON payload
│   │   └── rest.rs       # Reqwest logic
│   ├── chat/             # Chat Logic
│   │   ├── mod.rs
│   │   ├── session.rs    # History & Context
│   │   └── tools.rs      # [think], [cache] logic
│   └── ui/               # Terminal handling
│       ├── mod.rs
│       └── prompt.rs     # Reedline setup
└── tests/
```

# TaskMELIUS: ChatGemini Python to Rust Refactoring

> **Date:** 2026-02-08 13:30 (UTC+8)
> **Objective:** Update features and fully refactor ChatGemini_SakiTool from Python to Rust.

## Phase 1: Preparation & Analysis (Current Step)
1.  **Analyze Python Architecture**: Understand module dependencies in `ChatGemini_SakiTool`.
    *   *Core*: `CodeGemini.py` (Entry), `gemini_chat.py`, `gemini_config_ui.py`.
    *   *Gemini SDK*: Uses `google-genai` (v1.45.0).
    *   *Features*: Caching, FAISS, MCP, Multimedia.
2.  **Define Rust Architecture**:
    *   *Language*: Rust (2024 edition).
    *   *Async Runtime*: `tokio`.
    *   *HTTP Client*: `reqwest`.
    *   *TUI*: `ratatui` (replacing `rich`/`prompt_toolkit`).
    *   *Config*: `serde` + `toml` + `dotenvy`.
    *   *Vector DB*: `lance` or `usearch` (Pure Rust preferred over FAISS bindings for ease of build), or keep FAISS if strictly required. *Decision: Start with `usearch` for easier Rust integration or raw FAISS bindings if critical.*
3.  **Dependency Mapping**:
    *   `google-genai` -> Custom REST wrapper or community crate.
    *   `rich` -> `ratatui` + `tracing`.
    *   `prompt-toolkit` -> `reedline` or `rustyline`.

## Phase 2: Rust Foundation (Immediate Action)
1.  Initialize `chat_gemini_rust` project.
2.  Set up `Cargo.toml` with dependencies.
3.  Implement `config` module (reading `.env` and `config.toml`).
4.  Implement `gemini_client` module (REST API wrapper for Google GenAI).

## Phase 3: Core Chat Implementation
1.  Implement `chat_loop` (REPL).
2.  Implement `streaming_response` handler.
3.  Implement `history_manager` (saving JSON logs).

## Phase 4: Feature Migration (Iterative)
1.  **Thinking Mode**: Implement `[think:N]` logic.
2.  **Caching**: Implement Context Caching API calls.
3.  **Multimedia**: File upload and MIME type handling.
4.  **I18n**: Migrate YAML files and loading logic.
5.  **MCP**: Implement Model Context Protocol client in Rust.

## Phase 5: Testing & Finalization
1.  Unit tests for API client.
2.  Integration tests for Chat flow.
3.  Build release binary.

---

**Step 1 Breakdown: Python Code Analysis**
I will read `gemini_chat.py` and `config.py` to understand the exact logic to replicate.

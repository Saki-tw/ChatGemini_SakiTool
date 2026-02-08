# Contributing to ChatGemini

> "Code is poetry written in logic."

Thank you for your interest in contributing to ChatGemini (SakiTool).

## Development Setup

1.  **Rust**: Ensure you have Rust 1.75+ installed (`rustup`).
2.  **Clone**:
    ```bash
    git clone https://github.com/hc1034/ChatGemini_SakiTool.git
    cd ChatGemini_SakiTool/rust_rewrite/chat_gemini_rust
    ```
3.  **Environment**:
    Copy `.env.example` to `.env` and set your API keys.
4.  **Build**:
    ```bash
    cargo build
    ```

## Style Guide

*   **Language**: Documentation and comments should primarily be in **Traditional Chinese (Taiwan)**, maintaining the "Saki Studio" aesthetic (technical yet poetic).
*   **RustFmt**: Run `cargo fmt` before committing.
*   **Clippy**: Ensure `cargo clippy` passes without warnings.

## Architecture

*   `src/main.rs`: The main Agent Loop state machine.
*   `src/client/`: API clients (Auth, Rest, Files, Imagen).
*   `src/mcp/`: Model Context Protocol implementation.
*   `src/codegemini/`: RAG implementation.

## Pull Request Process

1.  Fork the repository.
2.  Create your feature branch (`git checkout -b feature/amazing-feature`).
3.  Commit your changes (`git commit -m 'Add some amazing feature'`).
4.  Push to the branch (`git push origin feature/amazing-feature`).
5.  Open a Pull Request.

---
*Saki Studio*

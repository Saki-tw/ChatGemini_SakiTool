# ChatGemini (Rust Version)

![Saki Studio](https://img.shields.io/badge/Saki_Studio-Project-purple)
![Rust](https://img.shields.io/badge/Rust-1.75+-orange)
![Gemini 2.0](https://img.shields.io/badge/Gemini-2.0_Flash-blue)

A high-performance, feature-rich CLI client for Google's Gemini API, rewritten in Rust for speed and stability.
Developed by **Saki Studio** (Taiwan).

## ✨ Features (功能亮點)

*   **⚡ Native Rust Performance**: No Python runtime required. Instant startup.
*   **🧠 Deep Thinking Mode**: Support for `[think:N]` to control thinking budget.
*   **💾 Context Caching**: Save 90%+ tokens on long conversations via `[cache:now]`.
*   **📂 Smart File Handling**: 
    *   Inline Base64 for small files (< 20MB).
    *   **Resumable Upload API** for large files (Video/PDF) > 20MB.
*   **🛠 MCP Support**: Basic Model Context Protocol client runtime.
*   **🔍 CodeGemini**: Semantic search for your local codebase.
*   **💰 Real-time Pricing**: Estimates cost in TWD/USD per turn.
*   **🌏 I18n**: Fully localized (Traditional Chinese / English / Japanese / Korean).

## 🚀 Installation (安裝)

### One-Click Install (macOS/Linux)
```bash
curl -fsSL https://raw.githubusercontent.com/hc1034/ChatGemini_SakiTool/main/INSTALL.sh | bash
# or locally:
./INSTALL.sh
```

### Manual Build
```bash
git clone https://github.com/hc1034/ChatGemini_SakiTool.git
cd ChatGemini_SakiTool/rust_rewrite/chat_gemini_rust
cargo build --release
cp target/release/chat_gemini_rust /usr/local/bin/chatgemini
```

## ⚙️ Configuration (設定)

Create a `.env` file in the execution directory:

```bash
GEMINI_API_KEY=your_api_key_here
GEMINI_MODEL=gemini-2.0-flash
GEMINI_LANG=zh-TW
```

## 🎮 Usage (使用指南)

Run the tool:
```bash
chatgemini
```

### Commands (指令)
*   `/help` - Show help menu.
*   `/clear` - Clear context history.
*   `/model <name>` - Switch model (e.g., `/model gemini-2.0-pro-exp`).
*   `/index <path>` - Index a folder for CodeGemini search.
*   `/search <query>` - Search the indexed codebase.
*   `/mcp start <cmd>` - Start an MCP server.

### Magic Tags (魔法標籤)
*   `[think:2048]`: Force "Thinking Mode" with 2048 token budget.
*   `[cache:now]`: Create a context cache checkpoint immediately.
*   `@filename`: Attach a file (image/pdf/video/text). 
    *   Example: `Analyze this video: @demo.mp4`

## 📜 License
MIT License. Copyright (c) 2026 Saki Studio.
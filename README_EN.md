# ChatGemini (SakiTool) - Rust Edition

<div align="center">

![Saki Studio](https://img.shields.io/badge/Saki_Studio-Project-7000FF?style=for-the-badge)
![Rust](https://img.shields.io/badge/Rust-1.75+-E57324?style=for-the-badge)
![Gemini](https://img.shields.io/badge/Google-Gemini_2.0-4285F4?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

[🇯🇵 日本語](README_JP.md) • [🇺🇸 English](README_EN.md) • [🇹🇼 繁體中文](README.md)

**"Fīnimus his…. fīnis est?…. Immo incipit."**

</div>

---

## 📖 Operational Briefing

This is not a toy. This is **ChatGemini v2.0**, a high-performance CLI client engineered by **Saki Studio**.
We have deprecated the Python prototype. The latency was... unacceptable.
We rebuilt it in **Rust**. Cold, efficient, and precise.

In the Commonwealth of code, where The Corporation (Google) looms overhead, this tool is your Pip-Boy. It interfaces directly with the Gemini neural network, bypassing the bloat of web browsers.

---

## ✨ System Specifications

### 🚀 Performance Matrix
*   **Rust Native**: Zero runtime dependencies. Execution is instantaneous.
*   **Agent Loop**: A continuous, autonomous loop. The model decides when to execute tools (`while true`).
*   **Context Caching**: Save your caps (tokens). `[cache:now]` reduces long-term memory costs by 90%.

### 🔐 Security Protocols
*   **Authentication Wizard**: Automated onboarding sequence.
*   **Tri-Level Auth**:
    1.  **API Key**: For mercenaries and scavengers.
    2.  **ADC**: Standard Institute protocol.
    3.  **OAuth 2.0**: Supports **Device Flow** for headless terminals deep in the glowing sea.

### 🎨 Visual Synthesis
*   **Imagen 3**: Execute `/image` to synthesize visual data from textual prompts.
*   **Smart File API**: Intelligent routing. Small packets use Base64; heavy data loads use Resumable Uploads.

---

## 🚀 Deployment

### Rapid Injection (Shell)
```bash
curl -fsSL https://raw.githubusercontent.com/hc1034/ChatGemini_SakiTool/main/INSTALL.sh | bash
```

### Manual Compilation
For those who prefer to forge their own power armor:
```bash
git clone https://github.com/hc1034/ChatGemini_SakiTool.git
cd ChatGemini_SakiTool/rust_rewrite/chat_gemini_rust
cargo build --release
```

---

## 🎮 Interface

Initialize:
```bash
chatgemini
```

### Directives (Commands)

| Directive | Function |
|-----------|----------|
| `/help` | Display HUD. |
| `/clear` | Flush cache. |
| `/model <id>` | Switch neural engine. |
| `/image <text>` | Visual synthesis. |
| `/doctor` | Run diagnostics. |
| `/mcp start` | Engage external tools. |

---

## 📜 Metadata

**Author**: 咲ちゃん（Saki-tw）
**Email**: `Saki@saki-studio.com.tw`
**Web**: [http://saki-studio.com.tw](http://saki-studio.com.tw)
**GitHub**: [https://saki-tw.github.io/](https://saki-tw.github.io/)

MIT License 2.0.

> "Instaurare omnia in INSULA."

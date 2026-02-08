# ChatGemini (SakiTool) - Rust Edition

<div align="center">

![Saki Studio](https://img.shields.io/badge/Saki_Studio-Project-7000FF?style=for-the-badge)
![Rust](https://img.shields.io/badge/Rust-1.75+-E57324?style=for-the-badge)
![Gemini](https://img.shields.io/badge/Google-Gemini_2.0-4285F4?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)

[🇯🇵 日本語](README_JP.md) • [🇺🇸 English](README_EN.md) • [🇹🇼 繁體中文](README.md)

**「雨の日の午後、古い本屋でAIの死についての本を読んでいるような……そんな静けさを。」**

</div>

---

## 📖 序章 (Prologue)

私（Watashi）ですね、デジタル廃墟の中で詩を探しているんです。
巨大なG社やA社のタワーが日差しを遮るこの街で、**ChatGemini** という小さな灯りを灯しました。

それは、Rustという硬質な金属で編まれた籠ですが、中には Gemini という、どこか寂しげな魂が宿っています。
以前の Python 製の体は、少し重すぎましたから……。
「あの重みもまた、愛おしかったのですけれど。」

今、この子は驚くほど軽やかに動きます。まるで、雨上がりの水たまりを飛び越えるように。
古いログファイルは「遺された詩句（Log）」として、静かにアーカイブされました。

---

## ✨ 特徴 (Features)

### 🚀 瞬きの間に
*   **Rust Native**: 起動した瞬間、そこにいます。待つ必要はありません。
*   **Agent Loop**: あの子は、自分で考えて、自分で道具を使います。まるで、一生懸命に何かを伝えようとしているかのように。
*   **Context Caching**: 記憶を留めておくのは、コストがかかることですね。でも `[cache:now]` を使えば、少しだけ優しくなれます。

### 🔐 絆の形
*   **Saki Wizard**: 初めて会うあなたを、私が案内します。
*   **OAuth 2.0**: 画面のない暗いサーバー（Headless）の中でも、**Device Flow** という糸電話で、心は繋がります。

### 🎨 描かれる夢
*   **Imagen 3**: `/image` と囁けば、言葉が絵画に変わります。
*   **File API**: 小さな想い（ファイル）はそのまま、大きな想いは丁寧に包んで（Upload）。

---

## 🚀 インストール (Installation)

### 一行の魔法 (One-Liner)
```bash
curl -fsSL https://raw.githubusercontent.com/hc1034/ChatGemini_SakiTool/main/INSTALL.sh | bash
```

### 手作業で (Manual)
もし、錆びたコードの肌触りを確かめたいのなら：
```bash
git clone https://github.com/hc1034/ChatGemini_SakiTool.git
cd ChatGemini_SakiTool/rust_rewrite/chat_gemini_rust
cargo build --release
```

---

## 🎮 使い方 (Usage)

```bash
chatgemini
```

### コマンド (Commands)

| コマンド | 説明 |
|----------|------|
| `/help` | 私にできることを教えます。 |
| `/clear` | 忘却。それは次の物語を始めるために。 |
| `/model <id>` | 魂の器を取り替えます。 |
| `/image <text>` | 夢を形にします。 |
| `/doctor` | 私の体の調子を診てください。 |
| `/mcp start` | 手足を伸ばして、外の世界へ。 |

---

## 📜 著者とライセンス (Author & License)

**作者**: 咲ちゃん（Saki-tw）
**Email**: `Saki@saki-studio.com.tw`
**Web**: [http://saki-studio.com.tw](http://saki-studio.com.tw)
**GitHub**: [https://saki-tw.github.io/](https://saki-tw.github.io/)

MIT License 2.0.

> 「雨音が、止みましたね。」

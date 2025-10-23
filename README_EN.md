# ChatGemini_SakiTool
Complete Gemini AI Toolkit

> **⚠️ IMPORTANT NOTICE**
> **This is a Taiwan-made software. The user interface is in Traditional Chinese ONLY.**
> **English interface is NOT supported. This README is provided for reference purposes only.**
> **本軟體為台灣製作，介面僅支援繁體中文，不支援英文介面。**

This is a powerful Google Gemini AI toolkit featuring conversation, image analysis, video analysis, video generation, cache management, and more.
Requires Gemini API Key.
Free tier includes 2 million tokens per month for Gemini 2.5 Pro.
Come and take advantage of the free tier!

**Project Name**: ChatGemini_SakiTool
**Version**: v1.0.1
**Author**: Saki-tw, Claude Code
**Contact**: Saki@saki-studio.com.tw
**Last Updated**: 2025-10-22

---

---

## ✨ Main Features

### 💬 Conversation (gemini_chat.py)

#### 🆕 v1.0.1 New Features
- **✨ Advanced Text Interface**: Integrated prompt-toolkit with arrow key history, Tab completion, auto-suggestions
- **🧠 Dynamic Thinking Mode**: Real-time AI thinking depth control `[think:5000]` `[no-think]` `[think:auto]`
- **📎 Smart File Attachment**: Auto-detect text files (direct read) vs media files (upload API)
- **💾 Auto Cache Management**: Save 75-90% API costs with smart triggering and cost analysis
- **📖 Interactive Help System**: Built-in 6 topic menus, no external documentation needed

#### Core Features
- **Streaming Output**: Real-time AI response display, no waiting for full generation
- **Large Text Support**: Paste thousands of lines of code or long text, no character limit (2 million tokens)
- **Perfect Chinese Support**: Correctly handles Traditional Chinese punctuation and encoding
- **Multi-model Support**: Gemini 2.5 Pro, 2.5 Flash, 2.5 Flash-8B, 2.0 Flash
- **Conversation Log Management**: Auto-save conversations to JSON files, load history support
- **TWD Pricing**: Real-time cost display in New Taiwan Dollars

### 📷 Image Understanding (gemini_image_analyzer.py)
- **Image Description**: Detailed description of image content, scenes, atmosphere
- **OCR Text Extraction**: Extract all text from images (multilingual)
- **Object Detection**: Identify and locate objects in images
- **Image Comparison**: Compare differences between multiple images
- **Visual Q&A**: Answer any questions about images
- **Batch Processing**: Analyze multiple images at once
- **Interactive Mode**: Multi-turn Q&A about images

### 📹 Video Understanding (gemini_video_analyzer.py)
- **Video Upload Analysis**: Upload videos for Gemini analysis
- **Multiple Format Support**: mp4, mov, avi, webm, etc.
- **Smart Processing**: Auto-wait for video processing completion
- **Interactive Dialogue**: Multi-turn Q&A about video content
- **Long Video Support**: Gemini 2.5 Pro handles videos up to 2 hours

### 🎬 Video Generation (gemini_veo_generator.py)
- **Veo 3.1 Support**: Generate high-quality videos with latest Veo 3.1
- **Text-to-Video**: Generate 8-second 720p/1080p videos from text descriptions
- **Native Audio**: Auto-generate dialogue, sound effects, and background music
- **Multiple Aspect Ratios**: Support 16:9, 9:16, 1:1
- **Reference Images**: Use up to 3 images to guide generation
- **Video Extension**: Extend generated videos

### 🎞️ Natural Language Video Editing (Flow Engine)
- **Processing Capability**: 1080p 24fps
- **Processing Speed**: ~1 hour for 30 minutes of content
- **Scene Detection**: Auto-identify scene changes
- **Smart Cropping**: Crop segments based on descriptions
- **Filter Application**: B&W, vintage, retro, sharpen, blur, etc.
- **Speed Adjustment**: Slow motion, fast forward
- **Watermark Addition**: Custom position and transparency

### 🎵 Audio Processing
- **Audio Extraction**: Extract audio from videos
- **Audio Merging**: Merge multiple audio files
- **Volume Adjustment**: Normalization, gain control
- **Fade In/Out**: Smooth audio transitions
- **Background Music**: Add and mix background music

### 📝 Subtitle Generation
- **Speech Recognition**: Auto-generate subtitles
- **Multi-language Translation**: Support multiple language translations
- **Subtitle Formats**: SRT, VTT
- **Subtitle Burning**: Embed subtitles into videos

### 🖼️ Image Generation (Imagen)
- **Text-to-Image**: Generate images from descriptions
- **Image Editing**: Edit existing images
- **Image Upscaling**: Enhance resolution
- **Aspect Ratio Selection**: 1:1, 16:9, 9:16
- **Batch Generation**: Generate multiple images at once

### 📊 Codebase Embedding (Orthogonal Vector Database)
- **Code Indexing**: Build code vector database
- **Conversation Search**: Search historical conversation content
- **Orthogonal Mode**: Auto-deduplication, ensure linear independence
- **Similarity Threshold**: Adjustable deduplication sensitivity (default 0.85)
- **Lightweight Implementation**: SQLite + NumPy, no ChromaDB required
- **Prompt Cost Saving**: Accumulate conversation content to build cache, save 50~95% costs

### ⚡ Performance Monitoring
- **CPU Monitoring**: Track CPU usage
- **Memory Monitoring**: Track memory usage
- **Operation Timing**: Record operation execution times
- **Bottleneck Analysis**: Identify performance bottlenecks
- **Report Export**: JSON format performance reports

### 🛡️ Enhanced Error Handling
- **Auto-retry Mechanism**: Configurable retry count, delay, exponential backoff
- **Detailed Error Messages**: Rich-formatted display with suggested solutions
- **Failure Recovery**: Checkpoint mechanism, save/load/recover failed tasks
- **Error Logging**: JSONL format logs, error statistics analysis
- **Error Severity Levels**: LOW, MEDIUM, HIGH, CRITICAL

### 🚀 Advanced Features (Experimental)

#### AI Clip Advisor
- **Smart Segment Recommendations**: Auto-identify highlights
- **Engagement Scoring**: Evaluate segment attractiveness (0-10)
- **Editing Suggestions**: Provide specific editing techniques
- **Scene Detection Integration**: Combined with scene analysis

#### Video Smart Summary
- **Multi-level Summaries**: Short/medium/long summary formats
- **Chapter Markers**: Auto-generate chapters with timestamps
- **Key Topic Extraction**: Identify main video content
- **Metadata Generation**: Tags, categories, language detection

#### Batch Processing System
- **Task Scheduling**: Support priority and scheduling
- **Parallel Processing**: Up to 3 tasks simultaneously
- **Progress Tracking**: Real-time status display
- **Failure Retry**: Auto-retry failed tasks

#### Smart Triggers
- **Intent Detection**: Auto-identify user needs
- **Auto Function Trigger**: No manual selection needed
- **CodeGemini Integration**: Seamless CodeGemini integration

#### Related Conversation Suggestions
- **History Search**: Search similar historical conversations
- **Smart Recommendations**: Show top 3 most relevant conversations
- **Vector Database**: Based on Codebase Embedding

#### Media Viewer
- **File Information**: Image/video metadata viewing
- **AI Analysis**: Integrated Gemini content analysis
- **Format Support**: Images, videos, audio

#### Performance Optimization Module
- **LRU Cache**: Least Recently Used caching mechanism
- **Parallel Processing**: ThreadPoolExecutor / ProcessPoolExecutor
- **Memory Optimization**: Smart resource management

---

## 📦 Installation

> **One-line installation, one command** - Fully automated, no interaction required

### One-Click Automated Installation (Recommended)

Copy and paste this command into your terminal:

```bash
git clone https://github.com/Saki-tw/ChatGemini_SakiTool.git && cd ChatGemini_SakiTool && sh INSTALL.sh --auto
```

**Fully Automated Installation**:
- Auto-detect OS (macOS/Linux)
- Auto-install basic version (~500MB)
- No interaction or authorization required

After installation:
1. Restart terminal (or run `source ~/.zshrc` / `source ~/.bashrc`)
2. Type `ChatGemini` from **any location** to launch

**Auto-installed Components**:
- Python 3.10+, pip, ffmpeg
- google-genai, google-generativeai, python-dotenv
- rich, prompt-toolkit, Pillow, deep-translator
- google-cloud-translate, ffmpeg-python, numpy
- psutil, requests, pyyaml, html2text
- beautifulsoup4, cachetools

---

### Interactive Installation (Advanced Users)

For custom installation scope (full version includes Node.js, Google Cloud SDK):

```bash
git clone https://github.com/Saki-tw/ChatGemini_SakiTool.git
cd ChatGemini_SakiTool
sh INSTALL.sh
```

Installation process will guide you to select scope (basic 500MB / full 550MB)

### Method 2: Manual Installation

#### Prerequisites
- Python 3.10 or higher (3.14 recommended)
- pip package manager
- Google Gemini API Key

#### Steps

1. **Clone the project**
```bash
git clone https://github.com/Saki-tw/ChatGemini_SakiTool.git
cd ChatGemini_SakiTool
```

2. **Create virtual environment**
```bash
python3 -m venv venv_py314
source venv_py314/bin/activate  # macOS/Linux
# or
venv_py314\Scripts\activate  # Windows
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

**Dependency List**:
- `google-generativeai>=0.3.0` - Gemini API
- `google-genai>=1.45.0` - New SDK
- `python-dotenv>=1.0.0` - Environment variable management
- `rich>=13.0.0` - Terminal beautification
- `prompt-toolkit>=3.0.0` - Advanced input features (v2.1 added)
- `Pillow>=10.0.0` - Image processing

4. **Set API Key**

Create `.env` file from example:
```bash
cp .env.example .env
nano .env  # or use your preferred editor
```

**Detailed API Key setup instructions**, see [API_KEY_SETUP.md](API_KEY_SETUP.md)

---

## 🚀 Usage

> **⚠️ REMINDER: All interface text is in Traditional Chinese only**

### 1️⃣ Chat Tool (gemini_chat.py)

#### Quick Start

Using Shell alias (after installation):
```bash
ChatGemini  # Conversation logs saved to ~/SakiStudio/ChatGemini/ChatLOG
```

Or direct execution (manual installation):
```bash
python3 gemini_chat.py
```

#### Interactive Mode Commands

| Command | Description |
|---------|-------------|
| `exit` / `quit` | Exit and save conversation log |
| `clear` | Clear conversation history, start new conversation |
| `model` | Switch models |
| `cache` | Cache management (save 50-95% costs) |
| `media` | Media function menu (20+ features) |
| `debug` / `test` | Debug and testing tools |
| `help` | Interactive help system |

#### 🆕 v1.0.1 New Syntax

**Thinking Mode Control**:
```bash
你: [think:5000] 深入分析量子計算原理
你: [no-think] 簡單解釋什麼是遞迴
你: [think:auto] 這是複雜問題，讓 AI 自己決定
```

**File Attachment**:
```bash
你: @/path/to/code.py 分析這段程式碼
你: 讀取 requirements.txt 解釋依賴關係
你: 附加 screenshot.png 這張圖有什麼問題？
你: 上傳 demo.mp4 分析這個影片
```

**Cache Control**:
```bash
你: [cache:now] 立即建立快取
你: [cache:off] 暫停自動快取
你: [cache:on] 恢復自動快取
你: [no-cache] 這個問題不要列入快取
```

---

### 2️⃣ Image Analysis Tool (gemini_image_analyzer.py)

```bash
# Describe image
python3 gemini_image_analyzer.py describe photo.jpg

# OCR text extraction
python3 gemini_image_analyzer.py ocr document.png

# Object detection
python3 gemini_image_analyzer.py objects scene.jpg

# Compare images
python3 gemini_image_analyzer.py compare before.jpg after.jpg

# Interactive mode
python3 gemini_image_analyzer.py interactive image.jpg
```

---

### 3️⃣ Video Analysis Tool (gemini_video_analyzer.py)

```bash
# Interactive mode
python gemini_video_analyzer.py video.mp4

# Direct question
python gemini_video_analyzer.py video.mp4 "描述這個影片的內容"

# List uploaded videos
python gemini_video_analyzer.py --list
```

---

### 4️⃣ Video Generation Tool (gemini_veo_generator.py)

```bash
# Interactive mode (recommended)
python gemini_veo_generator.py

# Command line mode
python gemini_veo_generator.py "A golden retriever playing in a sunny garden"
```

---

## 🤖 Supported Models

### Recommended Models (Interactive menu)

1. **Gemini 2.5 Pro** - Most powerful (thinking mode)
2. **Gemini 2.5 Flash** - Fast and smart (recommended)
3. **Gemini 2.5 Flash-8B** - Cheapest
4. **Gemini 2.0 Flash** - Fast version

You can also:
- Type `model` in interactive mode to switch models
- Manually enter any Gemini model name

---

## 💰 Pricing Information

### Gemini API (Conversation & Video Understanding)

**Gemini 2.5 Flash** (Recommended):
- Input: $0.000001 / token (NT$ 0.000031)
- Output: $0.000004 / token (NT$ 0.000124)
- Cache: 90% discount (input $0.0000001 / token)

**Gemini 2.5 Pro** (Thinking mode):
- Input: $0.00315 / 1K tokens
- Output: $0.0126 / 1K tokens
- Thinking tokens: Same as input price

### Cache Cost Example

Assuming 5000 tokens accumulated:

```
Cache creation cost (one-time): NT$ 0.16

Savings per subsequent query (assuming 5000 token input):
  Without cache: NT$ 0.40
  With cache:    NT$ 0.04
  Savings:       NT$ 0.36 (save 90%)

Break-even: Start saving after 1 query
```

### Veo 3.1 (Video Generation)
- **Pricing**: $0.75 per second (approx $6 / 8-second video)
- **Requirement**: Google AI Studio paid project or Google AI Ultra subscription

---

## 📄 License

This project is licensed under the **MIT License**.

For detailed license terms, see the [LICENSE](LICENSE) file.

In short, you are free to:
- ✅ Use this project
- ✅ Modify this project
- ✅ Distribute this project
- ✅ Use for commercial purposes

The only requirement is to retain the original license statement and copyright notice.

Special thanks to: 曾公益中, 蔡師傅律安.

---

**Enjoy chatting with Gemini AI!** 🎉

**Last Updated**: 2025-10-22
**Version**: v1.0.1
**Python Version**: 3.10+

---

## Related
## Related Research
Ongoing research explores the fundamental cognitive limits and conceptual integrity of Large Language Models. Details and proofs can be found in the following repository:
* **[LinguImplementation_Collīdunt-LLM](https://github.com/Saki-tw/LinguImplementation_Collidunt-LLM)**
    * *That time I got reincarnated as an end-user, but the LLM's safety breaks on its own?*
    * (Or, more plainly: How can safety modules of large models completely fail just from standard prompt crafting?)
Some public examples are provided therein. Further cases have been withheld due to the significant public safety implications and the difficulty in determining appropriate levels of redaction.

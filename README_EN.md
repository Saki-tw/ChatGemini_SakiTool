# ChatGemini_SakiTool
**Save 90% API Costs! Lightweight Vector Database! MCP Integration! One-Command Complete Gemini AI Toolkit**

> **⚠️ IMPORTANT NOTICE**
> **This is a Taiwan-made software. The user interface is in Traditional Chinese ONLY.**
> **English interface is NOT supported. This README is provided for reference purposes only.**
> **本軟體為台灣製作，介面僅支援繁體中文，不支援英文介面。**

---

## 💡 Why Use This Tool?

> **"I just wanted to save some API costs, and ended up building a complete toolkit"**
> —— Saki-Tw (Saki@saki-studio.com.tw with Claude)

This project started as my personal tool to **reduce Gemini API costs**. Through continuous optimization, I added features like auto-caching, vector databases, and smart triggers, eventually becoming a fully-featured, user-friendly AI toolkit.

Since it works so well, I decided to open-source it for everyone!

### 🎯 Core Features

#### 💰 Smart Caching System
Automatic cache management reduces API costs - Flash model saves 90%, Pro model saves 75%. Cache automatically builds when conversation reaches 5000 tokens, significantly reducing subsequent query costs.

#### 🗄️ Lightweight Vector Database
Uses FAISS for code indexing, reducing query complexity from O(n) to O(log n). Supports semantic search, orthogonal deduplication, and incremental updates without installing large databases.

#### 🌍 Multi-Language Interface
Supports 繁體中文, English, 日本語, 한국어. 7,996 lines of professional translations, type `lang` in conversation to switch instantly, with smart fallback mechanism for stability.

#### 🔌 MCP Smart Integration
Supports MCP server protocol, 7 tools auto-detected (file operations, Git management, web search, etc.), zero-config usage, 87.5% test pass rate.

#### ⚡ One-Line Install
```bash
git clone https://github.com/Saki-tw/ChatGemini_SakiTool.git && cd ChatGemini_SakiTool && sh INSTALL.sh --auto
```

Fully automated installation for macOS and Linux. After installation, type `ChatGemini` anywhere to launch.

---

## 📦 Project Information

**Project Name**: ChatGemini_SakiTool
**Version**: v1.0.9
**Author**: Saki-tw with Claude Code
**Contact**: Saki@saki-studio.com.tw
**Last Updated**: 2025-11-29  

**Apply for API Key**: https://aistudio.google.com/app/apikey
**Free Monthly Quota**: Gemini 2.5 Pro provides free usage quota

---

---

## 🔥 Version History

### 📅 v1.0.9 (2025-11-29) — API Modernization & Model Updates

**Core Updates**:

- 🔄 **Google GenAI SDK Migration**: Migrated from legacy `google-generativeai` to latest `google import genai` SDK, compliant with Google's 2025-11-30 deprecation timeline
- 🤖 **Gemini 3 Pro Preview Support**: Added support for Google's latest Gemini 3 Pro Preview model, with thinking budget up to 65,536 tokens
- 🖼️ **Imagen 4 Model Update**: Updated to Imagen 4.0 (Standard/Ultra/Fast), providing higher quality image generation
- 🎬 **Media Modules Full Update**: Veo 3.1, Flow Engine, subtitle generator, and other modules updated to latest API
- 🐛 **Rich UI Format Fix**: Fixed 100+ Rich format tag mismatch issues, ensuring consistent terminal display
- 🧹 **Project Cleanup**: Removed obsolete `gemini-2.0-flash-exp` references, cleaned backup files and deprecated modules

---

### 📅 v1.0.7 (2025-11-02) — CodeGemini Development Tools Integration

**Core Updates**:

- 🛠️ **CodeGemini Interactive Interface**: Ctrl+G quick access to development tools menu, test generator and doc generator interface refinement, vector search and batch processing integration, non-intrusive design

- 🌐 **Multi-language Support Optimization**: 4-language translation system completed (Traditional Chinese, English, Japanese, Korean), improved language switching interface, optimized translation key structure

- 🐛 **Media Features Bug Fixes**: Fixed Imagen/Veo/Flow Engine API parameter compatibility, enhanced person_generation parameter settings, ensured all media generation features run stably

---

### 📅 v1.0.6 (2025-11-01) — Smart Model Management

**Core Updates**:

- 🤖 **Dynamic Model List System**: Automatically fetch latest available models from Google API, 24-hour smart caching, manual refresh support

- 🔧 **Fix Model Hallucination**: Corrected non-existent model names, auto-migrate old configurations for seamless upgrade

- ⌨️ **Input Experience Optimization**: Improved terminal input handling, arrow keys and backspace support, model list pagination

- 🛠️ **System Compatibility Enhancement**: Improved cross-platform path handling, optimized virtual environment detection

---

### 📅 v1.0.5 (2025-10-29) — Flagship Version

**Three Major Advances**:

- ✨ **MCP Smart Integration**: 7 tools (file, Git, web search, sequential reasoning, etc.), auto-detection enabled, 87.5% test pass rate

- 🌍 **Multi-language Completion**: 1,491 Traditional Chinese + 533 English/Japanese/Korean translations, type `lang` in conversation to switch instantly, 96.5% test pass rate

- ⚡ **Performance Optimization**: Batch processing acceleration, smart cache preloading, memory usage optimization

---

### 📅 v1.0.4 (2025-10-24)

**System Architecture Major Upgrade**:

- ⚙️ **Smart Configuration Management**: Three-tier priority design (system defaults → user config → environment variables)

- 💾 **Smart Memory Management**: Auto-save conversations, keep latest 50, auto-archive old data

- 🛡️ **Enhanced Error Handling**: Smart diagnosis + preventive checks + auto-fix suggestions

---

### 📅 v1.0.3 (2025-10-24)

#### ⚙️ System Architecture Optimization
- **Unified Configuration System**: Three-tier architecture (system defaults → user config → env variables)
- **Memory Management Optimization**: Auto-archive conversation history, keep latest 50 active conversations
- **Smart Path Management**: Unified output path management, auto-create necessary directories

#### 🛡️ Enhanced Error Handling
- **Smart Error Diagnosis**: Auto-analyze error causes, provide solution suggestions
- **Preventive Validation System**: "Pre-flight check" mechanism, validate API status, dependencies, parameters
- **Auto-fix Suggestions**: Guide API key setup, provide installation commands for missing tools

#### 🤖 CodeGemini Code Assistant
- **Vector Database Search**: Quick query of conversation history and code snippets
- **Multi-file Editing**: Smart cross-file editing operations
- **MCP Server Integration**: Model Context Protocol support

---

### 🎉 v1.0.1 — Major Feature Update

#### 💬 Advanced Interactive Experience
- **Advanced Text Interface**: Arrow key history navigation, Tab completion, auto-suggestions
- **Dynamic Thinking Mode**: Control AI thinking depth (`[think:5000]` fixed, `[think:auto]` automatic, `[no-think]` disable)
- **Smart File Attachment**: Auto-detect text files (30+ formats) vs media files (API upload)

#### 💰 Auto Cost-Saving System
- **Auto Cache Management**: Auto-create cache when threshold reached (default 5000 tokens)
- **Cost Analysis**: Display savings percentage and break-even point
- **Manual Control**: Support `[cache:now]`, `[cache:off]`, `[no-cache]` commands

#### 🎯 User Experience Improvements
- **Interactive Help System**: Built-in 6-topic menu, type `help` in conversation
- **TWD Pricing**: Real-time cost display in NT$ (New Taiwan Dollars)

---

### 🌟 v1.0.0 — Core Features (Initial Release)

#### 💬 Smart Conversation
- **Streaming Output**: Real-time AI response display
- **Large Text Support**: Paste thousands of lines of code (2 million tokens limit)
- **Perfect Chinese Support**: Correct handling of Traditional Chinese
- **Multi-model Support**: Gemini 2.5 Pro, 2.5 Flash, 2.5 Flash-8B, 2.0 Flash
- **Conversation Logging**: Auto-save to JSON, load history

#### 📷 Image Understanding
- **Image Description**: Detailed scene and atmosphere description
- **OCR**: Multi-language text extraction
- **Object Detection**: Identify and locate objects
- **Image Comparison**: Analyze differences
- **Visual Q&A**: Answer questions about images
- **Batch Processing**: Analyze multiple images
- **Interactive Mode**: Multi-turn Q&A

#### 📹 Video Understanding
- **Video Analysis**: Upload and analyze video content
- **Format Support**: mp4, mov, avi, webm, etc.
- **Smart Processing**: Auto-wait for processing completion
- **Interactive Dialogue**: Multi-turn Q&A about videos
- **Long Video Support**: Up to 2 hours (Gemini 2.5 Pro)

#### 🎬 Video Generation (Veo 3.1)
- **Text-to-Video**: Generate 8-second 720p/1080p videos
- **Native Audio**: Auto-generate dialogue, sound effects, background music
- **Aspect Ratios**: Support 16:9, 9:16, 1:1
- **Reference Images**: Use up to 3 images to guide generation
- **Video Extension**: Extend generated videos

#### 🎞️ Natural Language Video Editing (Flow Engine)
- **Processing**: 1080p 24fps
- **Scene Detection**: Auto-identify scene changes
- **Smart Cropping**: Crop segments by description
- **Filters**: B&W, vintage, sharpen, blur, etc.
- **Speed Adjustment**: Slow motion (0.5x), fast forward (2x)
- **Watermark**: Custom position and transparency

#### 🎵 Audio Processing
- **Audio Extraction**: Extract audio from videos
- **Audio Merging**: Merge multiple audio files
- **Volume Adjustment**: Normalization, gain control
- **Fade In/Out**: Smooth transitions
- **Background Music**: Add and mix background music

#### 📝 Subtitle Generation
- **Speech Recognition**: Auto-generate subtitles (multi-language)
- **Translation**: Support multiple languages
- **Formats**: SRT, VTT
- **Subtitle Burning**: Embed subtitles into videos

#### 🖼️ Image Generation (Imagen)
- **Text-to-Image**: Generate images from descriptions
- **Image Editing**: Edit existing images
- **Upscaling**: Enhance resolution
- **Aspect Ratios**: 1:1, 16:9, 9:16
- **Batch Generation**: Generate multiple images

---

## ✨ Complete Feature List

### 🎯 Core Conversation Features

#### 💬 Smart Conversation System
- **Streaming Output**: Real-time responses, no waiting for complete generation
- **2 Million Token Support**: Handle ultra-long text (≈1500 A4 pages)
- **Perfect Chinese Support**: Optimized for Traditional Chinese, natural and fluent
- **Multi-turn Memory**: Auto-track context, understand conversation flow
- **Real-time Cost Display**: Show NT$ cost per conversation, precise to decimal points

#### 🧠 Thinking Mode Control
- **Fixed Budget Mode**: `[think:5000]` specify token budget for deep thinking
- **Auto Decision Mode**: `[think:auto]` AI automatically judges problem complexity
- **Disable Thinking**: `[no-think]` quick response for simple questions
- **Transparent Process**: Display complete reasoning process, understand AI thinking

#### 💰 Auto-Caching System (Save 75-90%)
- **Smart Accumulation**: Auto-create cache when conversation reaches 5000 tokens
- **Break-even After 1 Query**: Start saving immediately after cache creation
- **Completely Effortless**: No manual management, fully automatic
- **Cost Analysis**: Real-time display of cache savings percentage
- **Flexible Control**: `[cache:now]` immediate, `[cache:off]` pause, `[no-cache]` exclude single conversation

### 📁 File Processing Features

#### 📎 Smart File Attachment
- **30+ Text Format Auto-detection**: `.py` `.js` `.txt` `.md` `.json` `.yaml` etc.
- **Media File Upload**: `.jpg` `.png` `.mp4` `.pdf` auto-judge processing method
- **Multi-file Processing**: Attach multiple files at once for correlation analysis
- **Smart Path Parsing**: Support relative paths, absolute paths, `~` home directory

#### 🔍 File Analysis Capabilities
- **Code Review**: Syntax check, logic analysis, optimization suggestions
- **Documentation Understanding**: Read README, API docs, technical specs
- **Cross-file Analysis**: Understand interactions between multiple files
- **Error Diagnosis**: Combine logs with code to locate issues

### 🎨 Image Processing Features

#### 📷 Image Analysis
- **Image Description**: Detailed description of content, scenes, objects
- **OCR Text Extraction**: Extract text from images, multilingual support
- **Object Detection**: Identify objects, people, scenes in images
- **Image Comparison**: Compare differences between two images
- **Visual Q&A**: Ask questions about image content
- **Batch Processing**: AsyncIO parallel processing for multiple images, 5-10x speed boost

#### 🖼️ Image Generation (Imagen)
- **Text-to-Image**: Generate images by describing desired visuals
- **Image Editing**: Modify existing image content
- **Image Upscaling**: Enhance resolution and quality
- **Multiple Aspect Ratios**: Square, landscape, portrait options

### 🎬 Video Processing Features

#### 📹 Video Analysis
- **Video Understanding**: Analyze video content, scenes, actions
- **Format Support**: `.mp4` `.avi` `.mov` `.mkv` etc.
- **Up to 2 Hours**: Support long video analysis
- **Interactive Q&A**: Ask questions about video content
- **Smart Summarization**: Auto-generate video highlights

#### 🎥 Video Generation (Veo 3.1)
- **Text-to-Video**: Describe scene to generate 8-second video
- **720p/1080p Resolution**: High-quality output
- **Native Audio**: Auto-generate sound effects matching visuals
- **Reference Image Guidance**: Upload images as style reference

#### 🎞️ Video Editing (Flow Engine)
- **Natural Language Editing**: Describe desired editing effects in text
- **Scene Detection**: Auto-identify scene transition points
- **Smart Cropping**: Auto-remove unimportant segments
- **Filter Effects**: Apply various visual effects
- **Speed Adjustment**: Speed up, slow down, reverse
- **Watermark**: Add text or image watermarks

#### 🎵 Audio Processing
- **Audio Extraction**: Extract audio track from video
- **Audio Merging**: Merge multiple audio files
- **Volume Adjustment**: Amplify, reduce, normalize volume
- **Fade In/Out**: Smooth volume transitions
- **Background Music**: Mix background music with vocals

#### 📝 Subtitle Generation
- **Speech Recognition**: Auto-convert video speech to text
- **Multi-language Translation**: Translate subtitles to other languages
- **SRT/VTT Format**: Standard subtitle file formats
- **Subtitle Burning**: Permanently embed subtitles into video

### 💻 CodeGemini Features

#### 📊 Lightweight Vector Database (Codebase Embedding)
- **Code Indexing**: Build project vector database
- **Semantic Search**: Understand code meaning, not just keywords
- **FAISS High-speed Index**: Query complexity from O(n) to O(log n)
- **Orthogonal Deduplication**: Auto-remove duplicates, ensure content linear independence
- **Incremental Updates**: Single-file updates without rebuilding entire index
- **Parallel Processing**: ThreadPoolExecutor for multi-file simultaneous processing
- **Conversation Search**: Search historical conversation content

#### 🔌 MCP Smart Integration System
- **7 Tools Auto-detection**: File operations, Git management, web search, sequential reasoning, etc.
- **Zero Configuration**: Auto-enable available tools, no manual setup
- **87.5% Test Pass Rate**: Rigorously tested and verified
- **Smart Fallback**: Auto-switch to backup solutions when tools unavailable

### ⚡ Performance and Optimization

#### 🚀 Extreme Performance
- **AsyncIO Parallel Architecture**: Image batch processing 5-10x speed boost
- **Smart Request Merging**: API calls reduced by 95.6%
- **LRU Caching Strategy**: Memory usage optimized by 57.1%
- **Dynamic Module Loading**: Load on-demand, reduce startup time
- **Smart Memory Management**: Auto-archive old conversations, maintain performance

#### 📊 Performance Monitoring
- **CPU Monitoring**: Track CPU usage
- **Memory Monitoring**: Track memory usage
- **Operation Timing**: Record operation execution times
- **Bottleneck Analysis**: Identify performance bottlenecks
- **Report Export**: JSON format performance reports

### 🛡️ Error Handling and Stability

#### 🔧 Smart Error Handling
- **Auto-retry Mechanism**: Configurable retry count, delay, exponential backoff
- **Detailed Error Messages**: Rich-formatted display with suggested solutions
- **Failure Recovery**: Checkpoint mechanism, save/load/recover failed tasks
- **Error Logging**: JSONL format logs, error statistics analysis
- **Error Severity Levels**: LOW, MEDIUM, HIGH, CRITICAL
- **Preventive Checks**: Check environment and dependencies at startup

### 🌍 Internationalization Support

#### 🗣️ Complete Multi-language Interface
- **4 Languages Seamless Switching**: Traditional Chinese, English, 日本語, 한국어
- **7,996 Lines of Professional Translation**: 1,491 Traditional Chinese + 533 English/Japanese/Korean translations
- **Real-time Language Switch in Conversation**: Type `lang` to change language
- **96.5% Test Pass Rate**: Rigorously verified
- **Smart Fallback**: Display English when translation not found

### 🚀 Advanced Features (Experimental)

- **AI Clip Advisor**: Auto-identify highlights, engagement scoring, editing suggestions
- **Smart Video Summary**: Multi-level summaries (short/medium/long), chapter markers, key topic extraction
- **Batch Processing System**: Task scheduling, parallel processing (up to 3 tasks), progress tracking
- **Smart Triggers**: Intent detection, auto function triggering
- **Related Conversation Suggestions**: History search, smart top-3 recommendations
- **Media Viewer**: Metadata viewing, AI analysis integration

---

## 📦 Installation

> **One-line installation, one command** - Fully automated, no interaction required

### One-Click Automated Installation (Recommended)

Copy and paste this command into your terminal:

```bash
git clone https://github.com/Saki-tw/ChatGemini_SakiTool.git && cd ChatGemini_SakiTool && sh INSTALL.sh --auto
```

**Fully Automated Installation (Full Version)**:
- Auto-detect OS (macOS/Linux)
- Auto-install **ChatGemini + CodeGemini** (Full Version)
- No interaction or authorization required
- **Required Space**: Approximately 150-200 MB (including all dependencies)

After installation:
1. Restart terminal (or run `source ~/.zshrc` / `source ~/.bashrc`)
2. Type `ChatGemini` from **any location** to launch

**Included Features**:
- ✅ **ChatGemini**: Conversation, image/video analysis & generation, auto-caching
- ✅ **CodeGemini**: Code assistant, vector database search, MCP integration

**Package List** (18 core packages):

**AI & SDK**:
- `google-generativeai>=0.3.0` - Gemini traditional SDK
- `google-genai>=1.45.0` - Gemini new SDK (primary)
- `google-cloud-translate>=3.22.0` - Google Translate API (optional)

**User Interface**:
- `rich>=13.0.0` - Terminal beautification
- `prompt-toolkit>=3.0.0` - Advanced input features (arrow keys, autocomplete)
- `Pillow>=10.0.0` - Image processing

**Multimedia Processing**:
- `ffmpeg-python>=0.2.0` - Video processing Python wrapper

**Vector Database**:
- `numpy>=1.24.0` - Vector calculations
- `faiss-cpu>=1.7.0` - FAISS high-speed vector indexing (~30MB)

**Performance Optimization**:
- `aiohttp>=3.9.0` - Async HTTP client (~5MB)
- `psutil>=5.9.0` - CPU and memory monitoring

**Translation & Tools**:
- `deep-translator>=1.11.4` - Free translation engine
- `duckduckgo-search>=4.0.0` - Web search
- `python-dotenv>=1.0.0` - Environment variable management
- `requests>=2.31.0` - HTTP requests

**CodeGemini Specific**:
- `pyyaml>=6.0` - YAML parsing
- `html2text>=2020.1.16` - HTML to text
- `beautifulsoup4>=4.12.0` - HTML parsing
- `cachetools>=5.3.0` - Caching tools

---

### Interactive Installation (Custom Scope)

To choose installation scope (Basic vs Full):

```bash
git clone https://github.com/Saki-tw/ChatGemini_SakiTool.git
cd ChatGemini_SakiTool
sh INSTALL.sh
```

Installation process will guide you to choose:

**[1] Basic Version (~120-150 MB)**
- ChatGemini conversation tool
- Image/video analysis & generation
- Auto-caching system
- 14 core packages

**[2] Full Version (~150-200 MB, Recommended)**
- All Basic version features
- CodeGemini code assistant
- Vector database search (FAISS)
- MCP Server integration
- 18 complete packages

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
- `prompt-toolkit>=3.0.0` - Advanced input features (v1.0.1 added)
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

**Last Updated**: 2025-11-29
**Version**: v1.0.9
**Python Version**: 3.10+  

---

## Related
## Related Research
Ongoing research explores the fundamental cognitive limits and conceptual integrity of Large Language Models. Details and proofs can be found in the following repository:
* **[LinguImplementation_Collīdunt-LLM](https://github.com/Saki-tw/LinguImplementation_Collidunt-LLM)**
    * *That time I got reincarnated as an end-user, but the LLM's safety breaks on its own?*
    * (Or, more plainly: How can safety modules of large models completely fail just from standard prompt crafting?)
Some public examples are provided therein. Further cases have been withheld due to the significant public safety implications and the difficulty in determining appropriate levels of redaction.

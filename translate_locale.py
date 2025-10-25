#!/usr/bin/env python3
"""
語言包自動翻譯工具
使用字典映射進行快速翻譯（避免 API 調用）
"""

import yaml
from pathlib import Path


# 翻譯字典（繁中 → 英文）
TRANSLATIONS = {
    # Meta
    "繁體中文": "English",
    "台灣": "US",

    # Common - 基本操作
    "是": "Yes",
    "否": "No",
    "確定": "OK",
    "取消": "Cancel",
    "繼續": "Continue",
    "返回": "Back",
    "退出": "Exit",
    "離開": "Quit",
    "關閉": "Close",

    # Common - 狀態
    "成功": "Success",
    "錯誤": "Error",
    "警告": "Warning",
    "資訊": "Info",
    "載入中": "Loading",
    "處理中": "Processing",
    "已完成": "Completed",
    "失敗": "Failed",
    "等待中": "Pending",

    # Common - 動作
    "儲存": "Save",
    "載入": "Load",
    "刪除": "Delete",
    "建立": "Create",
    "更新": "Update",
    "重新整理": "Refresh",
    "搜尋": "Search",
    "選擇": "Select",
    "確認": "Confirm",

    # Common - 時間
    "秒": "second",
    "分鐘": "minute",
    "小時": "hour",
    "天": "day",
    "週": "week",
    "月": "month",
    "年": "year",

    # Common - 單位
    "字元": "characters",
    "行": "lines",
    "檔案": "files",
    "位元組": "bytes",

    # Common - 語言
    "語言": "Language",
    "語言已切換至 {lang}": "Language switched to {lang}",
    "當前語言": "Current Language",
    "可用語言": "Available Languages",

    # Chat
    "歡迎使用 ChatGemini！": "Welcome to ChatGemini!",
    "歡迎回來！": "Welcome back!",
    "感謝使用，再見！": "Thank you for using, goodbye!",
    "再見！": "Goodbye!",
    "你": "You",
    "模型": "Model",
    "系統": "System",
    "助理": "Assistant",
    "思考中": "Thinking",
    "生成中": "Generating",
    "串流輸出中": "Streaming",
    "等待回應": "Waiting for response",
    "分析中": "Analyzing",
    "請輸入訊息": "Please enter a message",
    "請輸入指令": "Please enter a command",
    "多行模式（輸入 $$$ 結束）": "Multi-line mode (enter $$$ to finish)",
    "指令模式": "Command mode",
    "開始新對話": "Start new conversation",
    "清除歷史記錄": "Clear history",
    "儲存對話": "Save conversation",
    "載入對話": "Load conversation",
    "匯出對話": "Export conversation",
    "選擇模型": "Select model",
    "當前模型": "Current model",
    "切換模型": "Switch model",
    "已切換至模型: {model}": "Switched to model: {model}",
    "可用模型": "Available models",
    "思考模式": "Thinking mode",
    "思考模式已啟用": "Thinking mode enabled",
    "思考模式已停用": "Thinking mode disabled",
    "思考 tokens 限制: {limit}": "Thinking tokens limit: {limit}",
    "思考過程": "Thinking process",
    "文字訊息": "Text message",
    "圖片訊息": "Image message",
    "檔案訊息": "File message",
    "多模態訊息": "Multimodal message",

    # Pricing - 標籤
    "成本": "Cost",
    "價格": "Price",
    "費用": "Fee",
    "輸入": "Input",
    "輸出": "Output",
    "思考": "Thinking",
    "快取": "Cache",
    "累計成本": "Total Cost",
    "會話成本": "Session Cost",
    "節省成本": "Savings",
    "折扣": "Discount",

    # Pricing - 顯示格式
    "💰 成本: {currency}{twd} (${usd} USD)": "💰 Cost: {currency}{twd} (${usd} USD)",
    "   輸入: {input} tokens, 輸出: {output} tokens": "   Input: {input} tokens, Output: {output} tokens",
    "   思考: {thinking} tokens": "   Thinking: {thinking} tokens",
    "   快取: {cached} tokens ({discount}% 折扣)": "   Cache: {cached} tokens ({discount}% discount)",
    "   累計成本: {currency}{total}": "   Total cost: {currency}{total}",
    "   💸 節省成本: {currency}{savings} (約 {percent}%)": "   💸 Savings: {currency}{savings} (about {percent}%)",

    # Pricing - 快取相關
    "快取使用": "Cache usage",
    "快取命中": "Cache hit",
    "快取未命中": "Cache miss",
    "快取折扣": "Cache discount",
    "快取節省": "Cache savings",

    # Pricing - 統計
    "會話統計": "Session summary",
    "總交易次數": "Total transactions",
    "會話時長": "Session duration",
    "平均成本": "Average cost",
    "總 tokens": "Total tokens",

    # Pricing - 功能標題
    "即時計價計算器": "Real-time Pricing Calculator",
    "💰 成本計算": "💰 Cost Calculation",
    "獲取會話總結": "Get Session Summary",
    "快速計算成本": "Quick Calculate Cost",
    "計算並打印成本": "Calculate and Print Cost",
    "此功能": "This feature",

    # Pricing - Flow Engine
    "類型: Flow Engine（自然語言影片生成）": "Type: Flow Engine (Natural Language Video Generation)",
    "目標時長: {duration} 秒": "Target duration: {duration} seconds",
    "實際時長: {duration} 秒": "Actual duration: {duration} seconds",
    "片段數量: {num} 段 x {seconds} 秒/段": "Segment count: {num} segments x {seconds} sec/segment",
    "Gemini 分段計畫:  {cost}": "Gemini planning:  {cost}",
    "Veo 影片生成:    {cost}": "Veo video generation:    {cost}",

    # Pricing - Token 詳細資訊
    "影片長度: {duration} 秒": "Video duration: {duration} seconds",
    "影片 Tokens: {tokens:,}": "Video Tokens: {tokens:,}",
    "文字輸入 Tokens: {tokens:,}": "Text input Tokens: {tokens:,}",
    "輸入 Tokens: {tokens:,}": "Input Tokens: {tokens:,}",
    "思考 Tokens: {tokens:,}": "Thinking Tokens: {tokens:,}",
    "輸出 Tokens: {tokens:,}": "Output Tokens: {tokens:,}",
    "總 Tokens: {tokens:,}": "Total Tokens: {tokens:,}",

    # Pricing - 成本細項
    "單價: {currency}{rate}/秒 (${usd}/sec)": "Unit price: {currency}{rate}/sec (${usd}/sec)",
    "輸入成本:  {cost}": "Input cost:  {cost}",
    "思考成本:  {cost}": "Thinking cost:  {cost}",
    "輸出成本:  {cost}": "Output cost:  {cost}",
    "本次成本:  {cost} ({percent})": "Current cost:  {cost} ({percent})",
    "累計成本:  {cost} ({percent})": "Total cost:  {cost} ({percent})",

    # Pricing - 本地處理
    "🎉 {feature}使用本地工具處理，無需調用 API": "🎉 {feature} uses local tools, no API calls needed",
    "💸 本次成本: NT$0.00 ($0.00 USD)": "💸 Current cost: NT$0.00 ($0.00 USD)",
    " 或 ": " or ",

    # Pricing - Cache報告
    "💰 Context Caching 成本節省報告": "💰 Context Caching Savings Report",
    "模型：{model}": "Model: {model}",
    "快取 Tokens：{tokens:,}": "Cache Tokens: {tokens:,}",
    "查詢次數：{count}": "Query count: {count}",
    "快取折扣：{percent}%": "Cache discount: {percent}%",
    "❌ 不使用快取成本：{currency}{twd} (${usd} USD)": "❌ Cost without cache: {currency}{twd} (${usd} USD)",
    "✅ 使用快取成本：  {currency}{twd} (${usd} USD)": "✅ Cost with cache:  {currency}{twd} (${usd} USD)",
    "💸 節省：         {currency}{twd} (${usd} USD)": "💸 Savings:         {currency}{twd} (${usd} USD)",
    "📊 節省比例：     {percent}%": "📊 Savings ratio:     {percent}%",

    # Pricing - 成本比較
    "💰 {feature} - 成本比較": "💰 {feature} - Cost Comparison",
    "💸 節省：{currency}{twd} (${usd} USD)": "💸 Savings: {currency}{twd} (${usd} USD)",
    "📊 節省比例：{percent}%": "📊 Savings ratio: {percent}%",
    "💡 建議使用：{method}": "💡 Recommended: {method}",
    "💸 額外成本：{currency}{twd} (${usd} USD)": "💸 Extra cost: {currency}{twd} (${usd} USD)",
    "💡 兩種方法成本相同": "💡 Both methods cost the same",

    # Errors - 完整翻譯
    "API 呼叫失敗": "API call failed",
    "API 呼叫失敗: {detail}": "API call failed: {detail}",
    "API 金鑰無效": "Invalid API key",
    "未設定 API 金鑰": "API key not set",
    "API 配額已用盡": "API quota exceeded",
    "API 速率限制": "API rate limit",
    "API 請求逾時": "API request timeout",
    "API 連線錯誤": "API connection error",
    "找不到檔案: {path}": "File not found: {path}",
    "讀取檔案失敗: {path}": "Failed to read file: {path}",
    "寫入檔案失敗: {path}": "Failed to write file: {path}",
    "檔案過大: {size}": "File too large: {size}",
    "檔案格式錯誤: {format}": "Invalid file format: {format}",
    "檔案權限錯誤": "File permission error",
    "無效的模型名稱: {model}": "Invalid model name: {model}",
    "找不到模型: {model}": "Model not found: {model}",
    "不支援的模型: {model}": "Unsupported model: {model}",
    "模型載入失敗": "Failed to load model",
    "網路連線錯誤": "Network connection error",
    "網路連線錯誤: {detail}": "Network connection error: {detail}",
    "連線逾時": "Connection timeout",
    "連線被拒絕": "Connection refused",
    "連線被重設": "Connection reset",
    "配置錯誤": "Configuration error",
    "缺少配置項: {key}": "Missing config: {key}",
    "無效的配置值: {key}={value}": "Invalid config value: {key}={value}",
    "載入配置失敗": "Failed to load config",
    "找不到語言包: {lang}": "Language pack not found: {lang}",
    "載入語言包失敗: {lang}": "Failed to load language pack: {lang}",
    "缺少翻譯: {key}": "Missing translation: {key}",
    "記憶體錯誤": "Memory error",
    "記憶體限制已超出": "Memory limit exceeded",
    "記憶體不足": "Out of memory",
    "未知錯誤": "Unknown error",
    "內部錯誤": "Internal error",
    "功能尚未實作": "Not implemented",
    "無效的輸入": "Invalid input",
    "無效的參數: {param}": "Invalid parameter: {param}",

    # Cache - 快取管理
    "建立快取": "Create cache",
    "刪除快取": "Delete cache",
    "清除快取": "Clear cache",
    "更新快取": "Update cache",
    "查詢快取": "Query cache",
    "列出快取": "List caches",
    "快取已建立": "Cache created",
    "快取已建立: {name}": "Cache created: {name}",
    "快取已刪除": "Cache deleted",
    "快取已刪除: {name}": "Cache deleted: {name}",
    "快取已更新": "Cache updated",
    "快取已更新: {name}": "Cache updated: {name}",
    "快取已過期": "Cache expired",
    "快取已過期: {name}": "Cache expired: {name}",
    "快取有效": "Cache active",
    "快取名稱": "Cache name",
    "快取模型": "Cache model",
    "有效期限": "TTL",
    "有效期限 (TTL)": "TTL (Time To Live)",
    "快取大小": "Cache size",
    "快取 tokens: {count}": "Cache tokens: {count}",
    "自動快取": "Auto cache",
    "自動快取已啟用": "Auto cache enabled",
    "自動快取已停用": "Auto cache disabled",
    "自動快取閾值: {threshold} tokens": "Auto cache threshold: {threshold} tokens",
    "建議建立快取以節省成本": "Recommend creating cache to save cost",
    "建議啟用快取（可節省約 {percent}% 成本）": "Recommend enabling cache (save ~{percent}% cost)",

    # Checkpoint - 檢查點
    "建立檢查點": "Create checkpoint",
    "恢復檢查點": "Restore checkpoint",
    "列出檢查點": "List checkpoints",
    "刪除檢查點": "Delete checkpoint",
    "回退": "Rewind",
    "自動檢查點": "Auto checkpoint",
    "手動檢查點": "Manual checkpoint",
    "快照檢查點": "Snapshot checkpoint",
    "分支檢查點": "Branch checkpoint",
    "檢查點已建立": "Checkpoint created",
    "檢查點已建立: {name}": "Checkpoint created: {name}",
    "已恢復至檢查點": "Restored to checkpoint",
    "已恢復至檢查點: {name}": "Restored to checkpoint: {name}",
    "檢查點已刪除": "Checkpoint deleted",
    "檢查點已刪除: {name}": "Checkpoint deleted: {name}",
    "檢查點名稱": "Checkpoint name",
    "檢查點名稱: {name}": "Checkpoint name: {name}",
    "建立時間": "Created at",
    "建立時間: {time}": "Created at: {time}",
    "訊息數量": "Message count",
    "訊息數量: {count}": "Message count: {count}",
    "大小": "Size",
    "大小: {size}": "Size: {size}",
    "描述": "Description",

    # Help - 幫助系統
    "指令說明": "Command help",
    "可用指令": "Available commands",
    "用法": "Usage",
    "說明": "Description",
    "範例": "Examples",
    "選項": "Options",
    "快速開始": "Quick start",
    "入門指南": "Getting started",
    "基本用法": "Basic usage",
    "進階用法": "Advanced usage",
    "幫助主題": "Help topics",
    "對話功能": "Chat features",
    "媒體處理": "Media processing",
    "快取管理": "Cache management",
    "檢查點系統": "Checkpoint system",
    "計價說明": "Pricing info",
    "配置設定": "Configuration",
    "模型選擇": "Model selection",
    "需要幫助嗎？輸入 /help 查看可用指令": "Need help? Type /help to see available commands",
    "輸入 /help [主題] 查看詳細說明": "Type /help [topic] for detailed info",
    "此主題暫無說明": "No help available for this topic",

    # Media - 媒體處理
    "圖片": "Image",
    "圖片分析": "Image analysis",
    "圖片生成": "Image generation",
    "圖片上傳": "Image upload",
    "圖片處理中": "Processing image",
    "調整圖片大小": "Resize image",
    "圖片格式": "Image format",
    "影片": "Video",
    "影片分析": "Video analysis",
    "影片生成": "Video generation",
    "影片上傳": "Video upload",
    "影片處理中": "Processing video",
    "影片編輯": "Video editing",
    "場景檢測": "Scene detection",
    "影片格式": "Video format",
    "影片長度": "Video duration",
    "音訊": "Audio",
    "音訊分析": "Audio analysis",
    "音訊處理": "Audio processing",
    "音訊轉錄": "Audio transcription",
    "音訊格式": "Audio format",
    "字幕": "Subtitle",
    "字幕生成": "Subtitle generation",
    "字幕翻譯": "Subtitle translation",
    "字幕格式": "Subtitle format",
    "上傳進度: {percent}%": "Upload progress: {percent}%",
    "處理進度: {percent}%": "Processing progress: {percent}%",
    "上傳完成": "Upload complete",
    "處理完成": "Processing complete",
    "媒體檔案": "Media file",
    "檔案大小": "File size",
    "檔案格式": "File format",
    "解析度": "Resolution",
    "位元率": "Bitrate",
    "幀率": "Frame rate",

    # File - 檔案操作
    "上傳": "Upload",
    "上傳檔案": "Upload file",
    "下載": "Download",
    "下載檔案": "Download file",
    "重新命名": "Rename",
    "重新命名檔案": "Rename file",
    "上傳中": "Uploading",
    "下載中": "Downloading",
    "已上傳": "Uploaded",
    "已下載": "Downloaded",
    "檔案名稱": "File name",
    "檔案路徑": "File path",
    "檔案類型": "File type",
    "找不到檔案": "File not found",
    "檔案已存在": "File exists",
    "無效的檔案": "Invalid file",

    # Config - 配置管理
    "載入配置": "Load config",
    "儲存配置": "Save config",
    "重設配置": "Reset config",
    "編輯配置": "Edit config",
    "API 金鑰": "API Key",
    "啟用快取": "Enable cache",
    "自動儲存": "Auto save",
    "主題": "Theme",
    "配置已載入": "Config loaded",
    "配置已儲存": "Config saved",
    "配置已重設": "Config reset",
    "配置檔案": "Config file",
    "配置路徑": "Config path",
    "預設配置": "Default config",

    # Install - 安裝
    "✓ 偵測到{language}，使用{language}介面": "✓ Detected {language}, using {language} interface",
    "按 Enter 繼續，或輸入語言代碼切換 ({languages}):": "Press Enter to continue, or enter language code ({languages}):",
    "語言設定已保存: {lang}": "Language setting saved: {lang}",
    "正在安裝 ChatGemini_SakiTool...": "Installing ChatGemini_SakiTool...",
    "檢查中": "Checking",
    "檢查 Python 版本": "Checking Python version",
    "安裝依賴套件": "Installing dependencies",
    "初始化中": "Initializing",
    "初始化配置": "Initializing config",
    "✅ 安裝完成！": "✅ Installation complete!",
    "✓ Python 版本: {version}": "✓ Python version: {version}",
    "✗ Python 版本過舊，需要 3.10+": "✗ Python version too old, requires 3.10+",
    "✓ API 金鑰已配置": "✓ API key configured",
    "✗ 未設定 API 金鑰": "✗ API key not set",
    "✓ 依賴套件已安裝": "✓ Dependencies installed",
    "✗ 缺少依賴套件": "✗ Missing dependencies",
    "後續步驟": "Next steps",
    "執行指令": "Run command",
    "閱讀文檔": "Read documentation",

    # Memory - 記憶體
    "記憶體使用量": "Memory usage",
    "可用記憶體": "Available memory",
    "總記憶體": "Total memory",
    "記憶體警告": "Memory warning",
    "清除記憶體": "Clear memory",
    "優化記憶體": "Optimize memory",
    "檢查記憶體": "Check memory",
    "記憶體不足": "Low memory",
    "記憶體已清除": "Memory cleared",
    "記憶體已優化": "Memory optimized",

    # Model - 模型
    "Gemini Pro": "Gemini Pro",
    "Gemini Flash": "Gemini Flash",
    "Gemini Flash 8B": "Gemini Flash 8B",
    "載入模型中": "Loading model",
    "模型已載入": "Model loaded",
    "切換模型中": "Switching model",
    "模型已切換": "Model switched",
    "模型名稱": "Model name",
    "模型版本": "Model version",
    "模型資訊": "Model info",
    "支援的模型": "Supported models",

    # Validation - 驗證
    "驗證中": "Validating",
    "有效": "Valid",
    "無效": "Invalid",
    "API 金鑰有效": "API key is valid",
    "API 金鑰無效": "API key is invalid",
    "輸入有效": "Input is valid",
    "輸入無效": "Input is invalid",
    "必填": "Required",
    "選填": "Optional",
    "格式錯誤": "Format error",

    # CodeGemini
    "程式碼分析": "Code analysis",
    "任務規劃": "Task planning",
    "檔案探索": "File exploration",
    "程式碼庫索引": "Codebase indexing",
    "程式碼審查": "Code review",
    "背景 Shell": "Background Shell",
    "待辦事項追蹤": "Todo tracker",
    "MCP 伺服器": "MCP Server",
    "分析程式碼中": "Analyzing code",
    "規劃任務中": "Planning task",
    "探索檔案中": "Exploring files",
    "建立索引中": "Indexing",
    "建立程式碼庫索引中": "Indexing codebase",
    "分析完成": "Analysis complete",
    "規劃完成": "Plan ready",
    "索引建立完成": "Index ready",
}


def translate_value(value):
    """翻譯值（字串）"""
    if not isinstance(value, str):
        return value

    # 直接匹配
    if value in TRANSLATIONS:
        return TRANSLATIONS[value]

    # 保留原樣（如果沒有翻譯）
    return value


def translate_dict(data):
    """遞迴翻譯字典"""
    if isinstance(data, dict):
        result = {}
        for key, value in data.items():
            if isinstance(value, dict):
                result[key] = translate_dict(value)
            else:
                result[key] = translate_value(value)
        return result
    return data


def main():
    """主函數"""
    zh_file = Path("locales/zh_TW.yaml")
    en_file = Path("locales/en.yaml")

    print(f"載入繁體中文語言包: {zh_file}")
    with open(zh_file, 'r', encoding='utf-8') as f:
        zh_data = yaml.safe_load(f)

    print(f"翻譯中...")
    en_data = translate_dict(zh_data)

    # 更新 meta 資訊
    en_data['meta'] = {
        'language': 'en',
        'name': 'English',
        'native_name': 'English',
        'author': 'Saki-tw (with Claude Code)',
        'version': '1.0.0',
        'encoding': 'UTF-8',
        'region': 'US',
    }

    # 統計翻譯率
    def count_strings(d):
        count = 0
        for v in d.values():
            if isinstance(v, dict):
                count += count_strings(v)
            elif isinstance(v, str):
                count += 1
        return count

    total_strings = count_strings(zh_data)
    translated = len([v for v in TRANSLATIONS.values()])

    print(f"翻譯字典大小: {translated} 條")
    print(f"總字串數: {total_strings}")
    print(f"預估覆蓋率: {translated/total_strings*100:.1f}%")

    print(f"寫入英文語言包: {en_file}")
    with open(en_file, 'w', encoding='utf-8') as f:
        # 寫入檔案頭
        f.write("# English Language Pack\n")
        f.write("# ChatGemini_SakiTool v1.1.0\n")
        f.write("#\n")
        f.write("# Version: 1.0.0\n")
        f.write("# Author: Saki-tw (with Claude Code)\n")
        f.write("# Date: 2025-10-25\n")
        f.write("# Locale: English (US)\n")
        f.write("#\n")
        f.write(f"# Translated from 35 core modules\n")
        f.write(f"# Total coverage: {translated/total_strings*100:.1f}%\n\n")

        yaml.dump(en_data, f, allow_unicode=True, sort_keys=False, default_flow_style=False)

    print(f"✅ 完成！")
    print(f"核心翻譯已完成，其餘字串保持原樣（可後續補充）")


if __name__ == "__main__":
    main()

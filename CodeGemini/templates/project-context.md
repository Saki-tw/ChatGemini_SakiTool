# 專案上下文模板

**專案名稱:** [您的專案名稱]
**版本:** [版本號]
**維護者:** [維護者名稱]
**最後更新:** [日期]

---

## 專案概述

[簡短描述專案的目的與核心功能]

### 核心功能

- [功能 1]
- [功能 2]
- [功能 3]

---

## 技術棧

### 程式語言
- [主要語言與版本]
- [次要語言]

### 框架與函式庫
- [框架名稱] v[版本] - [用途]
- [函式庫名稱] v[版本] - [用途]

### 開發工具
- **版本控制:** Git
- **套件管理:** [npm/pip/etc]
- **測試框架:** [框架名稱]
- **CI/CD:** [工具名稱]

---

## 專案結構

```
project-name/
├── src/                # 原始碼目錄
│   ├── components/    # 元件
│   ├── services/      # 服務層
│   ├── utils/         # 工具函數
│   └── main.ext       # 主程式入口
├── tests/             # 測試目錄
├── docs/              # 文檔
├── config/            # 配置檔案
├── README.md          # 專案說明
└── package.json       # 相依套件
```

---

## 核心模組說明

### [模組 1 名稱]
- **路徑:** `src/module1/`
- **用途:** [描述模組功能]
- **關鍵檔案:**
  - `file1.ext` - [檔案功能]
  - `file2.ext` - [檔案功能]

### [模組 2 名稱]
- **路徑:** `src/module2/`
- **用途:** [描述模組功能]
- **關鍵檔案:**
  - `file1.ext` - [檔案功能]

---

## API 與介面

### 外部 API
- [API 名稱] - [用途與端點]

### 內部介面
- [介面名稱] - [用途與方法]

---

## 配置說明

### 環境變數
```env
API_KEY=your_api_key_here
DATABASE_URL=your_database_url
PORT=3000
```

### 配置檔案
- `config/development.json` - 開發環境配置
- `config/production.json` - 生產環境配置

---

## 開發流程

### 環境設定
```bash
# 1. 安裝依賴
npm install

# 2. 配置環境變數
cp .env.example .env

# 3. 啟動開發伺服器
npm run dev
```

### 測試
```bash
# 執行所有測試
npm test

# 執行特定測試
npm test -- path/to/test
```

### 建置與部署
```bash
# 建置生產版本
npm run build

# 部署
npm run deploy
```

---

## 程式碼風格

### 命名規範
- **變數:** camelCase
- **常數:** UPPER_SNAKE_CASE
- **類別:** PascalCase
- **檔案:** kebab-case.ext

### 格式化工具
- [Prettier/ESLint/etc] - 配置檔：`.prettierrc`

---

## 測試策略

### 單元測試
- 覆蓋核心邏輯函數
- 目標覆蓋率：80%+

### 整合測試
- API 端點測試
- 資料庫整合測試

### E2E 測試
- 關鍵使用者流程

---

## 依賴套件

### 生產依賴
```json
{
  "package-name": "version",
  "another-package": "version"
}
```

### 開發依賴
```json
{
  "dev-package": "version"
}
```

---

## 故障排除

### 常見問題

#### [問題 1]
**症狀:** [描述問題]
**解決方案:** [解決步驟]

#### [問題 2]
**症狀:** [描述問題]
**解決方案:** [解決步驟]

---

## 安全考量

- [安全措施 1]
- [安全措施 2]
- [資料保護策略]

---

## 效能最佳化

- [最佳化策略 1]
- [最佳化策略 2]

---

## 相關資源

### 文檔
- [官方文檔連結]
- [API 參考文檔]

### 外部資源
- [相關教學]
- [社群資源]

---

## 貢獻指南

請參閱 [CONTRIBUTING.md](./CONTRIBUTING.md)

---

## 授權

[授權類型] - 詳見 [LICENSE](./LICENSE)

---

**使用方式:**

當使用 Gemini CLI 時，載入此上下文檔案：

```bash
gemini --context ./path/to/this/context.md
```

這將幫助 Gemini 更好地理解您的專案結構與需求。

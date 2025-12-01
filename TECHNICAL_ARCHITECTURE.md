# AI LINE Bot 技術架構文件

## 📋 專案概述

這是一個基於 LINE Bot 的智慧商品搜尋系統，整合了 AI 視覺辨識、自然語言處理和資料庫查詢功能，提供商品搜尋、位置查詢和智能問答服務。

---

## 🏗️ 系統架構

```
┌─────────────────────────────────────────────────────────────┐
│                        LINE Platform                         │
│                  (用戶端訊息接收與發送)                        │
└──────────────────────────┬──────────────────────────────────┘
                           │
                           │ Webhook (HTTPS)
                           │
┌──────────────────────────▼──────────────────────────────────┐
│                    Flask Web Server                          │
│  ┌──────────────────────────────────────────────────────┐   │
│  │  app.py (主應用程式)                                   │   │
│  │  - Webhook 處理                                        │   │
│  │  - 訊息路由                                            │   │
│  │  - 回應格式化                                          │   │
│  └──────────────────────────────────────────────────────┘   │
└──────────┬───────────────────────────┬───────────────────────┘
           │                           │
           │                           │
    ┌──────▼──────┐            ┌───────▼────────┐
    │ 文字訊息處理  │            │  圖片訊息處理    │
    └──────┬──────┘            └───────┬────────┘
           │                           │
           │                           │
    ┌──────▼───────────────────────────▼────────┐
    │         Gemini AI 服務                      │
    │  ┌──────────────────────────────────────┐  │
    │  │ gemini_qa_utils.py                   │  │
    │  │ - 問題分析 (Intent Recognition)      │  │
    │  │ - 自然語言生成 (NLG)                 │  │
    │  └──────────────────────────────────────┘  │
    │  ┌──────────────────────────────────────┐  │
    │  │ vision_utils.py                      │  │
    │  │ - 圖片 OCR                           │  │
    │  │ - 商品辨識                           │  │
    │  │ - 關鍵字提取                         │  │
    │  └──────────────────────────────────────┘  │
    └──────────────────┬──────────────────────────┘
                       │
                       │
    ┌───────────────────▼──────────────────────────┐
    │         Supabase 資料庫層                      │
    │  ┌────────────────────────────────────────┐  │
    │  │ supabase_utils.py                      │  │
    │  │ - 商品 CRUD 操作                       │  │
    │  │ - 位置資訊查詢                         │  │
    │  │ - 圖片儲存管理                         │  │
    │  │ - 搜尋功能 (多欄位模糊搜尋)            │  │
    │  └────────────────────────────────────────┘  │
    │                                               │
    │  ┌────────────────────────────────────────┐  │
    │  │ PostgreSQL 資料庫                       │  │
    │  │ - products (商品表)                     │  │
    │  │ - product_locations (位置表)            │  │
    │  └────────────────────────────────────────┘  │
    │                                               │
    │  ┌────────────────────────────────────────┐  │
    │  │ Supabase Storage                       │  │
    │  │ - product-images bucket                │  │
    │  │ - 圖片 CDN 服務                        │  │
    │  └────────────────────────────────────────┘  │
    └───────────────────────────────────────────────┘
```

---

## 🛠️ 技術棧

### 後端框架
- **Flask 3.0.3** - Python Web 框架
- **Gunicorn 23.0.0** - WSGI HTTP 伺服器（生產環境）

### LINE Bot SDK
- **line-bot-sdk 3.14.1** - LINE Messaging API SDK

### AI/ML 服務
- **Google Gemini 2.5 Flash** - 多模態 AI 模型
  - 文字問答處理 (`gemini_qa_utils.py`)
  - 圖片視覺辨識 (`vision_utils.py`)
  - 自然語言生成

### 資料庫與儲存
- **Supabase 2.8.0** - Backend-as-a-Service
  - PostgreSQL 資料庫
  - Storage (物件儲存)
  - RESTful API

### 網頁爬蟲
- **Playwright 1.48.0** - 瀏覽器自動化工具
  - 用於爬取家樂福商品資料 (`scrape_carrefour.py`)

### 其他依賴
- **python-dotenv 1.0.0** - 環境變數管理
- **requests 2.32.3** - HTTP 請求庫
- **aiohttp 3.10.10** - 異步 HTTP 客戶端

---

## 📁 專案結構

```
AILineBot/
├── app.py                          # 主應用程式入口
├── requirements.txt                # Python 依賴套件
├── Procfile                        # Heroku/Render 部署配置
├── supabase_schema.sql             # 資料庫結構定義
│
├── utils.py                        # 工具函數（環境變數檢查）
├── supabase_utils.py               # Supabase 資料庫操作模組
├── gemini_qa_utils.py              # Gemini 智能問答模組
├── vision_utils.py                 # 圖片視覺辨識模組
├── scrape_carrefour.py             # 家樂福商品爬蟲
├── setup_storage_bucket.py         # Supabase Storage 設定腳本
│
└── 文件/
    ├── SUPABASE_SETUP.md           # Supabase 設定指南
    ├── SUPABASE_STORAGE_GUIDE.md   # Storage 使用指南
    ├── NGROK_SETUP.md              # ngrok 本地開發指南
    ├── IMAGE_UPLOAD_GUIDE.md       # 圖片上傳指南
    └── TECHNICAL_ARCHITECTURE.md   # 本文件
```

---

## 🔄 核心功能流程

### 1. 文字訊息處理流程

```
用戶發送文字訊息
    ↓
app.py: handle_text_message()
    ↓
判斷是否為問題（包含疑問詞）
    ├─ 是 → gemini_qa_utils.py: answer_question()
    │         ├─ analyze_question() → 分析問題意圖
    │         ├─ query_database() → 查詢資料庫
    │         └─ generate_answer() → 生成自然語言回答
    │
    └─ 否 → supabase_utils.py: search_products_with_locations()
              └─ 搜尋商品並回傳結果
    ↓
格式化回應（文字或 Carousel）
    ↓
回傳給用戶
```

### 2. 圖片訊息處理流程

```
用戶上傳圖片
    ↓
app.py: handle_image_message()
    ↓
下載圖片內容 (bytes)
    ↓
vision_utils.py: extract_keywords_from_image_gemini()
    ├─ 使用 Gemini Vision API 分析圖片
    ├─ OCR 文字辨識
    └─ 提取商品名稱和品牌關鍵字
    ↓
第一階段：逐關鍵字搜尋
    ├─ 找到商品 → 回傳 Carousel 結果
    └─ 未找到 → 進入第二階段
    ↓
第二階段：合併所有關鍵字搜尋
    ├─ 找到商品 → 回傳合併結果
    └─ 未找到 → 回傳 Gemini 辨識內容協助用戶
```

### 3. 智能問答流程

```
用戶問題：「最便宜的可樂是什麼？」
    ↓
gemini_qa_utils.py: analyze_question()
    ├─ 使用 Gemini 分析問題
    └─ 輸出 JSON：
       {
         "intent": "search_by_price",
         "search_term": "可樂",
         "price_range": {"min": null, "max": null},
         "sort_by": "price_asc",
         "limit": 5
       }
    ↓
query_database(analysis)
    ├─ 根據 intent 建立查詢
    ├─ 價格範圍過濾
    ├─ 排序（價格升序）
    └─ 限制數量
    ↓
generate_answer(question, products, analysis)
    ├─ 使用 Gemini 生成自然語言回答
    └─ 包含商品資訊和位置
    ↓
回傳給用戶
```

---

## 🗄️ 資料庫設計

### 資料表結構

#### 1. `products` (商品表)
| 欄位 | 類型 | 說明 |
|------|------|------|
| id | UUID | 主鍵 |
| name | TEXT | 商品名稱 |
| price | DECIMAL(10,2) | 價格 |
| description | TEXT | 商品描述 |
| category | TEXT | 商品分類 |
| image_url | TEXT | 圖片 URL (Supabase Storage) |
| ingredients | TEXT | 成分/規格 |
| brand | TEXT | 品牌 |
| barcode | TEXT | 條碼 (唯一) |
| stock | INTEGER | 存貨數量 |
| created_at | TIMESTAMP | 建立時間 |
| updated_at | TIMESTAMP | 更新時間 |

**索引：**
- `idx_products_name` - 商品名稱索引
- `idx_products_category` - 分類索引
- `idx_products_barcode` - 條碼索引

#### 2. `product_locations` (商品位置表)
| 欄位 | 類型 | 說明 |
|------|------|------|
| id | UUID | 主鍵 |
| product_id | UUID | 商品 ID (外鍵) |
| area | TEXT | 區域 (如：A區、B區) |
| shelf | TEXT | 貨架編號 |
| floor | INTEGER | 樓層 |
| position_x | DECIMAL(10,2) | X 座標 |
| position_y | DECIMAL(10,2) | Y 座標 |
| notes | TEXT | 備註 |
| created_at | TIMESTAMP | 建立時間 |
| updated_at | TIMESTAMP | 更新時間 |

**索引：**
- `idx_product_locations_product_id` - 商品 ID 索引
- `idx_product_locations_area` - 區域索引
- `idx_product_locations_shelf` - 貨架索引
- `idx_product_locations_floor` - 樓層索引

**約束：**
- `UNIQUE(product_id, area, shelf)` - 同一商品在同一區域的同一貨架只能有一個位置

---

## 🔌 API 端點

### LINE Webhook
- **POST `/callback`** - 接收 LINE 平台訊息事件
  - 驗證簽名 (`X-Line-Signature`)
  - 處理文字訊息 (`TextMessage`)
  - 處理圖片訊息 (`ImageMessage`)

### 健康檢查
- **GET `/`** - 服務狀態檢查
  - 返回 JSON：`{"status": "running", "service": "Enote LINE Bot", "version": "1.0.0"}`

---

## 🔐 環境變數配置

### 必要環境變數

```bash
# LINE Bot 設定
CHANNEL_ACCESS_TOKEN=your_line_channel_access_token
CHANNEL_SECRET=your_line_channel_secret

# Supabase 設定
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_supabase_anon_key
SUPABASE_STORAGE_BUCKET=product-images  # 選填，預設為 product-images

# Google Gemini API
GEMINI_API_KEY=your_gemini_api_key

# 部署設定（Render/Heroku）
PORT=5000  # 選填，預設 5000
```

---

## 🚀 部署架構

### 開發環境
- **本地 Flask 伺服器** (port 5000)
- **ngrok** - 本地隧道服務（用於 LINE Webhook 測試）

### 生產環境
- **Render / Heroku** - 雲端平台部署
- **Gunicorn** - WSGI 伺服器
  - Workers: 2
  - Threads: 2
  - Timeout: 120 秒

### 部署流程
1. 推送程式碼到 Git 倉庫
2. Render/Heroku 自動部署
3. 設定環境變數
4. 配置 LINE Webhook URL
5. 驗證服務運行

---

## 📦 核心模組說明

### `app.py` - 主應用程式
- **職責：** Flask 應用初始化、Webhook 處理、訊息路由
- **主要功能：**
  - LINE Bot API 初始化
  - 文字訊息處理（搜尋/問答）
  - 圖片訊息處理（視覺辨識）
  - 回應格式化（文字/Carousel）

### `supabase_utils.py` - 資料庫操作
- **職責：** Supabase 資料庫和 Storage 操作
- **主要功能：**
  - 商品 CRUD 操作
  - 位置資訊管理
  - 多欄位模糊搜尋（名稱、品牌、分類、描述）
  - 關鍵字擴展（同義詞、品牌別名）
  - 圖片上傳/刪除

### `gemini_qa_utils.py` - 智能問答
- **職責：** 使用 Gemini 進行問題分析和回答生成
- **主要功能：**
  - 問題意圖分析（`analyze_question()`）
  - 資料庫查詢（`query_database()`）
  - 自然語言回答生成（`generate_answer()`）
  - 完整問答流程（`answer_question()`）

### `vision_utils.py` - 圖片辨識
- **職責：** 使用 Gemini Vision API 分析圖片
- **主要功能：**
  - 圖片 OCR 文字辨識
  - 商品名稱和品牌提取
  - 關鍵字生成

### `scrape_carrefour.py` - 商品爬蟲
- **職責：** 從家樂福網站爬取商品資料
- **主要功能：**
  - 使用 Playwright 爬取商品列表
  - 下載商品圖片
  - 上傳到 Supabase Storage
  - 存入資料庫

---

## 🔍 搜尋功能詳解

### 搜尋策略

1. **關鍵字擴展** (`expand_search_terms()`)
   - 品牌別名對照（如：kikoman → 龜甲萬、kikkoman）
   - 商品類別關鍵字（如：可樂 → cola、碳酸飲料）
   - 同義詞擴展

2. **多欄位搜尋**
   - 商品名稱 (`name`) - 模糊搜尋
   - 品牌 (`brand`) - 模糊搜尋
   - 分類 (`category`) - 模糊搜尋
   - 描述 (`description`) - 模糊搜尋

3. **結果合併與去重**
   - 使用商品 ID 去重
   - 限制回傳數量

4. **位置資訊附加**
   - 每個商品自動附加 `locations` 陣列
   - 包含區域、貨架、樓層資訊

---

## 🎨 回應格式

### 文字訊息格式
```
🔍 找到 X 個包含「關鍵字」的產品：

==============================

【1】商品名稱
💰 價格：$XX
✅ 有存貨 / ❌ 【缺貨中】
🏷️ 品牌：XXX
📦 分類：XXX
📍 位置資訊：
   • A區 - 3號貨架 (樓層 1)
📝 商品描述...

------------------------------
```

### Carousel 訊息格式
- 使用 LINE Carousel Template
- 每個商品顯示：
  - 縮圖（商品圖片或預設圖片）
  - 標題（商品名稱，最多 40 字）
  - 文字（價格、存貨、品牌、位置、描述，最多 120 字）
  - 動作按鈕（查看詳情）

---

## 🔄 資料流程

### 商品資料建立流程
```
爬蟲/手動輸入
    ↓
scrape_carrefour.py 或 create_product()
    ↓
下載圖片 → Supabase Storage
    ↓
取得公開 URL
    ↓
存入 products 表
    ↓
新增位置資訊 → product_locations 表
```

### 搜尋流程
```
用戶輸入關鍵字
    ↓
expand_search_terms() → 擴展關鍵字
    ↓
多欄位模糊搜尋（名稱、品牌、分類、描述）
    ↓
結果去重（以 ID 為 key）
    ↓
為每個商品附加位置資訊
    ↓
格式化回應
```

---

## 🛡️ 錯誤處理

### 環境變數檢查
- `utils.py: check_environment_variables()` - 啟動時檢查必要環境變數

### Supabase 連線檢查
- 初始化時測試連線
- 連線失敗時記錄警告，功能降級

### 異常處理
- 所有主要函數都有 try-except 包裝
- 記錄詳細錯誤日誌
- 用戶友好的錯誤訊息

---

## 📊 效能優化

1. **資料庫索引**
   - 為常用查詢欄位建立索引
   - 加速搜尋效能

2. **搜尋限制**
   - 限制每次搜尋結果數量（預設 10 個）
   - 避免過多資料傳輸

3. **圖片快取**
   - 使用 Supabase Storage CDN
   - 公開 URL 可快取

4. **非同步處理**
   - 爬蟲使用 Playwright 異步 API
   - 提升爬取效率

---

## 🔮 未來擴展方向

1. **語音訊息處理**
   - 整合語音轉文字（Speech-to-Text）
   - 支援語音查詢商品

2. **商品推薦系統**
   - 基於用戶歷史查詢
   - 協同過濾推薦

3. **地圖整合**
   - 商品位置視覺化
   - 導航功能

4. **多語言支援**
   - 英文、日文等語言搜尋
   - 多語言回應

5. **存貨即時更新**
   - 整合 POS 系統
   - 即時存貨狀態

---

## 📝 開發注意事項

1. **環境變數管理**
   - 使用 `.env` 檔案（不要提交到 Git）
   - 生產環境使用平台環境變數設定

2. **API 限制**
   - Gemini API 有請求頻率限制
   - 需要適當的錯誤處理和重試機制

3. **資料庫效能**
   - 大量商品時考慮分頁
   - 定期清理過期資料

4. **安全性**
   - LINE Webhook 簽名驗證
   - Supabase RLS 政策設定
   - API Key 保護

---

## 📚 相關文件

- [Supabase 設定指南](./SUPABASE_SETUP.md)
- [Supabase Storage 使用指南](./SUPABASE_STORAGE_GUIDE.md)
- [ngrok 本地開發指南](./NGROK_SETUP.md)
- [圖片上傳指南](./IMAGE_UPLOAD_GUIDE.md)

---

**最後更新：** 2024年
**版本：** 1.0.0



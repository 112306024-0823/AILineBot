# 商品資料豐富化腳本使用說明

## 📋 概述

本目錄包含兩個腳本，用於豐富 Supabase 資料庫中的商品資料：

1. **`enhanced_carrefour_scraper.py`** - 增強版家樂福爬蟲，涵蓋更多分類
2. **`enrich_product_data.py`** - 使用 AI 補充缺失的商品資料

## 🚀 快速開始

### 1. 補充現有商品的缺失資料

```bash
cd AILineBot/scripts
python enrich_product_data.py
```

**功能：**
- 自動找出缺少 `ingredients`、`barcode`、`description` 的商品
- 使用 Gemini AI 生成缺失的資訊
- 批量更新資料庫

**選項：**
- 選項 1：補充所有缺少資料的商品（分批處理）
- 選項 2：只補充前 20 個商品（測試用）
- 選項 3：只補充前 50 個商品

### 2. 爬取更多家樂福商品

```bash
cd AILineBot/scripts
python enhanced_carrefour_scraper.py
```

**功能：**
- 涵蓋 20+ 個商品分類
- 自動獲取商品詳細資訊（品牌、描述、成分等）
- 上傳商品圖片到 Supabase Storage
- 自動建立商品位置資訊

**可用分類：**

#### 飲料類
- 冷藏飲品
- 果汁
- 茶飲
- 咖啡
- 碳酸飲料

#### 零食類
- 洋芋片
- 糖果
- 餅乾
- 堅果

#### 食品類
- 泡麵
- 罐頭
- 調味料
- 米

#### 生鮮類
- 蔬菜
- 水果
- 肉類
- 海鮮

#### 乳製品
- 鮮乳
- 優格
- 起司

#### 冷凍食品
- 水餃
- 冰淇淋
- 冷凍調理

#### 生活用品
- 清潔用品
- 衛生紙
- 個人護理

**選項：**
- 選項 1：爬取所有分類（每個分類最多 20 個商品）
- 選項 2：選擇特定分類
- 選項 3：只爬取飲料類
- 選項 4：只爬取零食類
- 選項 5：只爬取生鮮類
- 選項 6：只爬取生活用品類

## ⚙️ 環境變數設定

確保 `.env` 檔案包含以下變數：

```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
SUPABASE_STORAGE_BUCKET=product-images
GEMINI_API_KEY=your_gemini_api_key
```

## 📊 資料庫欄位說明

### products 表格欄位

| 欄位 | 類型 | 說明 | 是否必填 |
|------|------|------|----------|
| id | uuid | 商品 ID | ✅ |
| name | text | 商品名稱 | ✅ |
| price | numeric | 價格 | ✅ |
| description | text | 商品描述 | ❌ |
| category | text | 商品分類 | ❌ |
| image_url | text | 商品圖片 URL | ❌ |
| ingredients | text | 成分/原料 | ❌ |
| brand | text | 品牌 | ❌ |
| barcode | text | 條碼 | ❌ |
| stock | integer | 存貨數量 | ✅ (預設 0) |
| calories | integer | 卡路里 | ❌ |
| created_at | timestamptz | 建立時間 | ✅ |
| updated_at | timestamptz | 更新時間 | ✅ |

## 🔧 使用建議

### 建議執行順序

1. **先補充現有商品資料**
   ```bash
   python enrich_product_data.py
   # 選擇選項 2 或 3 先測試
   ```

2. **再爬取新商品**
   ```bash
   python enhanced_carrefour_scraper.py
   # 選擇選項 3-6 爬取特定分類
   ```

3. **最後再次補充新商品的缺失資料**
   ```bash
   python enrich_product_data.py
   # 選擇選項 1 補充所有商品
   ```

### 注意事項

1. **API 限制**
   - Gemini API 有請求頻率限制，腳本已內建延遲機制
   - 建議分批處理，避免一次性處理太多商品

2. **爬蟲速度**
   - 爬蟲腳本會自動控制請求速度（每個商品間隔 1.5 秒）
   - 獲取詳細資訊會增加爬取時間，但資料更完整

3. **資料品質**
   - AI 生成的資料僅供參考，建議人工檢查重要商品
   - 條碼為 AI 生成，可能不是真實條碼

4. **重複商品**
   - 腳本會自動檢查商品是否已存在（基於商品名稱）
   - 已存在的商品會被跳過

## 📈 預期效果

執行完成後，你的資料庫應該會有：

- ✅ 更多商品（從 121 筆增加到 300+ 筆）
- ✅ 更完整的商品資訊（成分、描述、條碼）
- ✅ 更多樣化的分類（生鮮、生活用品等）
- ✅ 更豐富的商品圖片

## 🐛 疑難排解

### 問題：Supabase 連線失敗
- 檢查 `.env` 檔案中的 `SUPABASE_URL` 和 `SUPABASE_KEY`
- 確認 Supabase 專案狀態正常

### 問題：Gemini API 錯誤
- 檢查 `.env` 檔案中的 `GEMINI_API_KEY`
- 確認 API 額度是否足夠

### 問題：爬蟲無法找到商品
- 家樂福網站結構可能已變更，需要更新選擇器
- 檢查網路連線是否正常

### 問題：圖片上傳失敗
- 確認 Supabase Storage bucket 已建立
- 檢查 bucket 權限設定

## 📝 更新日誌

- 2024-12-04: 初始版本
  - 新增增強版爬蟲腳本
  - 新增資料補充腳本
  - 支援 20+ 商品分類


# Supabase 設定指南

## 📋 資料庫結構設計

### 1. 商品資料表 (products)
儲存商品的基本資訊、規格和照片：
- `id`: UUID（主鍵）
- `name`: 商品名稱
- `price`: 價格
- `description`: 商品描述
- `category`: 商品分類
- `image_url`: 商品圖片 URL（存在 Supabase Storage）
- `ingredients`: 成分/規格說明
- `brand`: 品牌（選填）
- `barcode`: 條碼（選填，用於掃描辨識）

### 2. 商品位置表 (product_locations)
儲存商品在實體賣場的位置資訊：
- `id`: UUID（主鍵）
- `product_id`: 商品 ID（外鍵）
- `area`: 區域（例如：A區、B區）
- `shelf`: 貨架編號（例如：3號貨架）
- `floor`: 樓層（選填）
- `position_x`, `position_y`: 座標（選填，用於地圖定位）
- `notes`: 備註

## 🚀 設定步驟

### 步驟 1: 建立 Supabase 專案
1. 前往 [Supabase](https://supabase.com/) 註冊/登入
2. 點擊 "New Project" 建立新專案
3. 記下專案的 URL 和 API Key

### 步驟 2: 執行 SQL 腳本
1. 在 Supabase Dashboard 中，點擊左側的 "SQL Editor"
2. 複製 `supabase_schema.sql` 的內容
3. 貼上並執行 SQL 腳本，建立資料表和索引

### 步驟 3: 設定環境變數
在 Render 或本地環境中設定以下環境變數：
```
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your-anon-key
```

### 步驟 4: 設定 Supabase Storage（用於商品圖片）
1. 在 Supabase Dashboard 中，點擊左側的 "Storage"
2. 建立新的 bucket，命名為 `product-images`
3. 設定 bucket 為公開讀取（Public bucket）
4. 上傳商品圖片後，取得公開 URL 並存入 `products.image_url`

## 📝 使用範例

### Python 程式碼範例

```python
from supabase_utils import (
    create_product,
    add_product_location,
    search_products,
    get_product_with_location
)

# 建立商品
product = create_product(
    name="可口可樂 330ml",
    price=25.00,
    description="經典碳酸飲料",
    category="飲料",
    image_url="https://your-project.supabase.co/storage/v1/object/public/product-images/coke.jpg",
    ingredients="水、糖、二氧化碳、焦糖色素"
)

# 新增商品位置
if product:
    add_product_location(
        product_id=product["id"],
        area="A區",
        shelf="3號貨架",
        floor=1,
        notes="靠近入口"
    )

# 搜尋商品
products = search_products(name="可樂", category="飲料")

# 獲取商品及其位置
product_with_location = get_product_with_location(product["id"])
```

## 🔍 查詢範例

### 1. 根據商品名稱搜尋
```python
products = search_products(name="可樂")
```

### 2. 根據位置查詢商品
```python
from supabase_utils import search_products_by_location

products_at_location = search_products_by_location(
    area="A區",
    shelf="3號貨架"
)
```

### 3. 獲取商品完整資訊（含位置）
```python
product = get_product_with_location(product_id)
# 返回格式：
# {
#   "id": "...",
#   "name": "可口可樂",
#   "price": 25.00,
#   "locations": [
#     {"area": "A區", "shelf": "3號貨架", "floor": 1}
#   ]
# }
```

## 📸 圖片上傳流程

1. 使用 Supabase Storage API 上傳圖片
2. 取得公開 URL
3. 將 URL 存入 `products.image_url`

範例程式碼（之後可整合）：
```python
from supabase import create_client

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# 上傳圖片
with open("product_image.jpg", "rb") as f:
    result = supabase.storage.from_("product-images").upload(
        f"coke_{timestamp}.jpg",
        f.read()
    )

# 取得公開 URL
image_url = supabase.storage.from_("product-images").get_public_url(result.path)
```

## ⚠️ 注意事項

1. **安全性**：使用 `SUPABASE_KEY`（anon key）即可，這是公開的 API key
2. **Row Level Security (RLS)**：如果需要限制存取，可在 Supabase Dashboard 中設定 RLS 政策
3. **圖片儲存**：建議使用 Supabase Storage，有 CDN 加速且方便管理
4. **索引**：已為常用查詢欄位建立索引，提升查詢效能

## 🔄 下一步

1. 整合商品查詢功能到 LineBot
2. 實作圖片辨識功能（上傳商品圖 → 查詢商品資訊）
3. 實作語音查詢功能（語音 → 文字 → 查詢商品位置）


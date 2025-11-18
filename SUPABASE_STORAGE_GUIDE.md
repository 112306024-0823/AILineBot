# Supabase Storage 圖片上傳指南

## 📸 設定 Supabase Storage

### 方式 1: 使用 Python 腳本自動建立（推薦）

1. **取得 Service Role Key**：
   - 前往 [Supabase Dashboard](https://app.supabase.com/)
   - 選擇您的專案
   - 點擊左側 **Settings** > **API**
   - 複製 **service_role** key（⚠️ 注意：這是機密金鑰，不要公開）

2. **設定環境變數**：
   ```bash
   export SUPABASE_SERVICE_KEY=your-service-role-key
   ```

3. **執行腳本**：
   ```bash
   python setup_storage_bucket.py
   ```

### 方式 2: 手動在 Dashboard 建立

1. 登入 [Supabase Dashboard](https://app.supabase.com/)
2. 選擇您的專案
3. 點擊左側選單的 **"Storage"**
4. 點擊 **"New bucket"**
5. 設定：
   - **Name**: `product-images`（或您喜歡的名稱）
   - **Public bucket**: ✅ **勾選**（這樣才能取得公開 URL）
   - **File size limit**: 建議設定 5MB 或更大
   - **Allowed MIME types**: `image/jpeg,image/png,image/webp`（選填）  
6. 點擊 **"Create bucket"**

### 步驟 3: 設定環境變數（選填）

如果您的 bucket 名稱不是 `product-images`，請設定：

```bash
SUPABASE_STORAGE_BUCKET=your-bucket-name
```

## 🚀 使用方式

### 方式 1: 從本地檔案上傳

```python
from supabase_utils import upload_product_image

# 上傳本地圖片
image_url = upload_product_image(
    file_path='/path/to/product_image.jpg',
    product_name='可口可樂'
)

if image_url:
    print(f"圖片 URL: {image_url}")
    # 使用 image_url 建立商品
    from supabase_utils import create_product
    product = create_product(
        name='可口可樂',
        price=25.00,
        image_url=image_url
    )
```

### 方式 2: 從 bytes 上傳（適用於 LINE Bot）

```python
from supabase_utils import upload_product_image_from_bytes

# 從 LINE Bot 接收的圖片
image_content = b'...'  # 圖片的 bytes 內容

image_url = upload_product_image_from_bytes(
    file_content=image_content,
    file_extension='jpg',
    product_name='可口可樂'
)
```

### 方式 3: 一次完成（上傳圖片 + 建立商品）

```python
from supabase_utils import create_product_with_image

# 從本地檔案
product = create_product_with_image(
    name='可口可樂',
    price=25.00,
    image_path='/path/to/image.jpg',
    description='經典碳酸飲料',
    category='飲料'
)

# 或從 bytes
product = create_product_with_image(
    name='可口可樂',
    price=25.00,
    image_content=image_bytes,
    description='經典碳酸飲料',
    category='飲料'
)
```

## 📝 整合到 LINE Bot

### 範例：處理用戶上傳的商品圖片

```python
from supabase_utils import upload_product_image_from_bytes, create_product
from linebot import LineBotApi
from linebot.models import TextSendMessage

@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    user_id = event.source.user_id
    message_id = event.message.id
    
    # 1. 從 LINE 下載圖片
    message_content = line_bot_api.get_message_content(message_id)
    image_bytes = b''
    for chunk in message_content.iter_content():
        image_bytes += chunk
    
    # 2. 上傳到 Supabase Storage
    image_url = upload_product_image_from_bytes(
        file_content=image_bytes,
        file_extension='jpg',
        product_name='用戶上傳商品'  # 或從用戶輸入取得
    )
    
    if image_url:
        # 3. 建立商品（需要從用戶取得其他資訊）
        product = create_product(
            name='待確認商品',
            price=0.00,
            image_url=image_url
        )
        
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=f"✅ 圖片上傳成功！\n商品 ID: {product['id']}\n圖片: {image_url}")
        )
    else:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="❌ 圖片上傳失敗，請稍後再試")
        )
```

## 🔍 取得圖片 URL 格式

上傳成功後，會得到類似這樣的 URL：

```
https://your-project.supabase.co/storage/v1/object/public/product-images/products/可口可樂_20241201_123456_abc123.jpg
```

這個 URL 可以直接：
- 在網頁中顯示
- 在 LINE Bot 的 Flex Message 中使用
- 在手機 App 中顯示

## 🗑️ 刪除圖片

```python
from supabase_utils import delete_product_image

# 刪除圖片
success = delete_product_image(image_url)

if success:
    print("圖片刪除成功")
```

## ⚠️ 注意事項

1. **Bucket 必須設為公開**：才能取得公開 URL
2. **檔案大小限制**：預設 Supabase 免費方案有 50MB 限制
3. **檔案名稱**：函數會自動生成唯一檔名，避免覆蓋
4. **檔案格式**：建議使用 JPG、PNG 或 WebP
5. **CDN 加速**：Supabase Storage 自動提供 CDN，圖片載入速度快

## 🔐 安全性建議

1. **檔案驗證**：上傳前檢查檔案大小和格式
2. **權限控制**：如果需要限制上傳，可在 Supabase Dashboard 設定 Storage Policies
3. **檔案清理**：定期清理未使用的圖片以節省空間

## 📊 檔案結構

上傳的圖片會儲存在 Storage 中，結構如下：

```
product-images/
  └── products/
      ├── 可口可樂_20241201_123456_abc123.jpg
      ├── 統一泡麵_20241201_123457_def456.jpg
      └── ...
```

這樣的結構方便管理，也方便未來擴展（例如：`products/`, `categories/`, `banners/` 等）


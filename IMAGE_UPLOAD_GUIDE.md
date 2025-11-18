# 📸 產品圖片上傳與關聯指南

本指南說明如何將產品圖片上傳到 Supabase Storage，並與 `products` 資料表建立關聯。

## 📋 目錄

1. [圖片與資料表的關聯方式](#圖片與資料表的關聯方式)
2. [上傳圖片到 Supabase Storage](#上傳圖片到-supabase-storage)
3. [更新資料表的 image_url](#更新資料表的-image_url)
4. [在 LINE Bot 中顯示圖片](#在-line-bot-中顯示圖片)
5. [完整範例](#完整範例)

---

## 🔗 圖片與資料表的關聯方式

### 關聯架構

```
products 表
├── id (UUID) - 主鍵
├── name (TEXT)
├── image_url (TEXT) ← 儲存 Supabase Storage 的公開 URL
└── ... 其他欄位
```

**關聯方式**：`products.image_url` 欄位儲存圖片在 Supabase Storage 的公開 URL。

### 圖片 URL 格式

上傳成功後，圖片 URL 格式如下：

```
https://{project_id}.supabase.co/storage/v1/object/public/product-images/{檔案名稱}
```

例如：
```
https://abcdefghijklmnop.supabase.co/storage/v1/object/public/product-images/可口可樂_20241201_123456_abc123.jpg
```

---

## 📤 上傳圖片到 Supabase Storage

### 方式 1: 使用 `supabase_utils.py` 的函數（推薦）

#### 從本地檔案上傳

```python
from supabase_utils import upload_product_image

# 上傳圖片並取得 URL
image_url = upload_product_image(
    file_path='/path/to/product_image.jpg',
    product_name='可口可樂'
)

if image_url:
    print(f"圖片上傳成功！URL: {image_url}")
else:
    print("圖片上傳失敗")
```

#### 從 bytes 上傳（例如從 LINE Bot 接收）

```python
from supabase_utils import upload_product_image_from_bytes

# 假設你已經有圖片的 bytes 內容
image_bytes = b'...'  # 圖片的 bytes

image_url = upload_product_image_from_bytes(
    file_content=image_bytes,
    file_extension='jpg',
    product_name='可口可樂'
)

if image_url:
    print(f"圖片上傳成功！URL: {image_url}")
```

### 方式 2: 使用 Supabase Client 直接上傳

```python
from supabase_utils import supabase
import os
from datetime import datetime

def upload_image_direct(file_path: str, product_name: str) -> str:
    """直接使用 Supabase Client 上傳圖片"""
    if not supabase:
        return None
    
    # 讀取檔案
    with open(file_path, 'rb') as f:
        file_content = f.read()
    
    # 生成唯一檔名
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    file_extension = os.path.splitext(file_path)[1][1:]  # 取得副檔名
    safe_name = product_name.replace(' ', '_').replace('/', '_')
    file_name = f"{safe_name}_{timestamp}.{file_extension}"
    storage_path = f"products/{file_name}"
    
    # 上傳到 Storage
    try:
        result = supabase.storage.from_('product-images').upload(
            path=storage_path,
            file=file_content,
            file_options={"content-type": f"image/{file_extension}"}
        )
        
        # 取得公開 URL
        public_url = supabase.storage.from_('product-images').get_public_url(storage_path)
        return public_url
    except Exception as e:
        print(f"上傳失敗：{e}")
        return None
```

---

## 🔄 更新資料表的 image_url

### 方式 1: 上傳圖片 + 建立產品（一次完成）

```python
from supabase_utils import create_product_with_image

# 建立產品並上傳圖片
product = create_product_with_image(
    name='可口可樂',
    price=25.00,
    image_path='/path/to/coke.jpg',  # 或使用 image_content=image_bytes
    description='經典碳酸飲料',
    category='飲料',
    brand='可口可樂'
)

print(f"產品建立成功！ID: {product['id']}")
print(f"圖片 URL: {product['image_url']}")
```

### 方式 2: 先上傳圖片，再更新現有產品

```python
from supabase_utils import upload_product_image, update_product

# 1. 上傳圖片
image_url = upload_product_image(
    file_path='/path/to/new_image.jpg',
    product_name='可口可樂'
)

if image_url:
    # 2. 更新產品的 image_url
    product_id = 'your-product-uuid-here'
    updated_product = update_product(
        product_id=product_id,
        image_url=image_url
    )
    print(f"產品圖片更新成功！")
```

### 方式 3: 使用 SQL 直接更新

```python
from supabase_utils import supabase

# 假設你已經有 image_url 和 product_id
product_id = 'your-product-uuid-here'
image_url = 'https://...supabase.co/storage/v1/object/public/product-images/...'

# 更新資料表
result = supabase.table('products').update({
    'image_url': image_url
}).eq('id', product_id).execute()

if result.data:
    print("更新成功！")
```

---

## 📱 在 LINE Bot 中顯示圖片

### 自動顯示（已實作）

當產品有有效的 `image_url` 時，LINE Bot 會自動使用 **Carousel Template** 顯示圖片和文字。

**條件**：
- `image_url` 必須是有效的 HTTPS URL
- 不能是 `https://example.com` 開頭的假 URL
- 圖片必須可以公開存取

### 手動測試

```python
# 測試搜尋功能
from supabase_utils import search_products_with_locations

products = search_products_with_locations('醬油', limit=5)

for product in products:
    print(f"產品：{product['name']}")
    print(f"圖片 URL：{product.get('image_url', '無圖片')}")
    print("---")
```

---

## 💡 完整範例

### 範例 1: 批次上傳產品圖片

```python
import os
from supabase_utils import upload_product_image, update_product, search_products

# 圖片資料夾
image_folder = '/path/to/product_images'

# 取得所有產品
products = search_products(limit=100)

for product in products:
    product_name = product['name']
    product_id = product['id']
    
    # 尋找對應的圖片檔案（假設檔名與產品名稱相同）
    image_file = None
    for ext in ['jpg', 'jpeg', 'png', 'webp']:
        potential_file = os.path.join(image_folder, f"{product_name}.{ext}")
        if os.path.exists(potential_file):
            image_file = potential_file
            break
    
    if image_file:
        # 上傳圖片
        image_url = upload_product_image(
            file_path=image_file,
            product_name=product_name
        )
        
        if image_url:
            # 更新產品
            update_product(product_id, image_url=image_url)
            print(f"✅ {product_name} 圖片上傳成功")
        else:
            print(f"❌ {product_name} 圖片上傳失敗")
    else:
        print(f"⚠️ {product_name} 找不到對應圖片")
```

### 範例 2: 從 LINE Bot 接收圖片並建立產品

```python
from linebot import LineBotApi
from linebot.models import TextSendMessage
from supabase_utils import upload_product_image_from_bytes, create_product

@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    user_id = event.source.user_id
    message_id = event.message.id
    
    try:
        # 1. 從 LINE 下載圖片
        message_content = line_bot_api.get_message_content(message_id)
        image_bytes = b''
        for chunk in message_content.iter_content():
            image_bytes += chunk
        
        # 2. 上傳到 Supabase Storage
        image_url = upload_product_image_from_bytes(
            file_content=image_bytes,
            file_extension='jpg',
            product_name='用戶上傳商品'
        )
        
        if image_url:
            # 3. 建立產品（需要從用戶取得其他資訊，這裡用預設值）
            product = create_product(
                name='待確認商品',
                price=0.00,
                image_url=image_url,
                description='用戶上傳的商品圖片'
            )
            
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text=f"✅ 圖片上傳成功！\n"
                         f"商品 ID: {product['id']}\n"
                         f"圖片 URL: {image_url}"
                )
            )
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="❌ 圖片上傳失敗，請稍後再試")
            )
    except Exception as e:
        app.logger.error(f"處理圖片訊息時發生錯誤: {e}")
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="❌ 處理圖片時發生錯誤")
        )
```

---

## ⚠️ 注意事項

### 1. Storage Bucket 設定

確保 `product-images` bucket 已設定為**公開**：

```python
# 檢查 bucket 是否公開
from supabase_utils import supabase

buckets = supabase.storage.list_buckets()
for bucket in buckets:
    if bucket.name == 'product-images':
        print(f"Bucket: {bucket.name}, Public: {bucket.public}")
```

### 2. 圖片格式建議

- **格式**：JPG、PNG、WebP
- **大小**：建議 1MB 以下（LINE Carousel 建議）
- **尺寸**：建議 800x800 或 1024x1024 像素

### 3. URL 驗證

LINE Bot 會自動過濾無效的圖片 URL：
- 必須是 HTTPS
- 不能是 `https://example.com` 開頭
- 必須可以公開存取

### 4. 效能考量

- 圖片會自動透過 Supabase CDN 加速
- 建議使用 WebP 格式以減少檔案大小
- 大量圖片上傳時，考慮使用批次處理

---

## 🔍 疑難排解

### 問題 1: 圖片無法顯示

**檢查項目**：
1. `image_url` 是否為有效的 HTTPS URL
2. Storage bucket 是否設為公開
3. 圖片檔案是否存在於 Storage
4. URL 是否可以透過瀏覽器直接開啟

### 問題 2: 上傳失敗

**可能原因**：
1. Storage bucket 不存在
2. 權限不足（檢查 SUPABASE_KEY）
3. 檔案大小超過限制
4. 檔案格式不支援

### 問題 3: 資料表更新失敗

**檢查項目**：
1. `product_id` 是否正確
2. `image_url` 格式是否正確
3. 資料表權限設定（RLS）

---

## 📚 相關文件

- [Supabase Storage 設定指南](./SUPABASE_STORAGE_GUIDE.md)
- [Supabase 設定說明](./SUPABASE_SETUP.md)
- [supabase_utils.py 函數說明](./supabase_utils.py)

---

## 🎯 快速開始

1. **確認 Storage bucket 已建立並設為公開**
   ```bash
   python setup_storage_bucket.py
   ```

2. **上傳第一張圖片**
   ```python
   from supabase_utils import upload_product_image
   
   image_url = upload_product_image(
       file_path='./test_image.jpg',
       product_name='測試商品'
   )
   print(f"圖片 URL: {image_url}")
   ```

3. **更新產品資料**
   ```python
   from supabase_utils import update_product
   
   update_product(product_id, image_url=image_url)
   ```

4. **測試 LINE Bot**
   - 在 LINE 中搜尋產品
   - 應該會看到 Carousel 顯示圖片和文字

---

完成！現在你的產品圖片已經與資料表關聯，並可以在 LINE Bot 中顯示了！🎉



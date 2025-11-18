# Supabase Storage Bucket 設定說明

## 🚀 快速設定（推薦）

### 步驟 1: 取得 Service Role Key

1. 前往 [Supabase Dashboard](https://app.supabase.com/)
2. 選擇您的專案：`scbgrkmnbnkzdzzqdnjo`
3. 點擊左側 **Settings** > **API**
4. 找到 **service_role** key（⚠️ 這是機密金鑰，請妥善保管）
5. 複製這個 key

### 步驟 2: 執行設定腳本

**選項 A: 使用環境變數（推薦）**

```bash
# Windows PowerShell
$env:SUPABASE_SERVICE_KEY="your-service-role-key"
python setup_storage_bucket.py

# Windows CMD
set SUPABASE_SERVICE_KEY=your-service-role-key
python setup_storage_bucket.py

# Linux/Mac
export SUPABASE_SERVICE_KEY=your-service-role-key
python setup_storage_bucket.py
```

**選項 B: 直接在腳本中設定（僅測試用）**

編輯 `setup_storage_bucket.py`，將第 8 行改為：
```python
SUPABASE_SERVICE_KEY = "your-service-role-key"  # 僅測試用，不要提交到 Git
```

然後執行：
```bash
python setup_storage_bucket.py
```

### 步驟 3: 驗證

腳本執行成功後，您應該會看到：
```
✅ Storage bucket 'product-images' 建立成功！
   公開存取：是
```

## 📋 手動設定（如果腳本無法執行）

### 在 Supabase Dashboard 中建立

1. **登入 Dashboard**
   - 前往：https://app.supabase.com/
   - 選擇專案：`scbgrkmnbnkzdzzqdnjo`

2. **進入 Storage**
   - 點擊左側選單的 **"Storage"**

3. **建立新 Bucket**
   - 點擊 **"New bucket"** 按鈕
   - 填寫以下資訊：
     - **Name**: `product-images`
     - **Public bucket**: ✅ **勾選**（重要！）
     - **File size limit**: `5242880` (5MB) 或更大
     - **Allowed MIME types**: `image/jpeg,image/png,image/webp,image/gif`（選填）
   - 點擊 **"Create bucket"**

4. **驗證設定**
   - 確認 bucket 出現在列表中
   - 確認 "Public" 欄位顯示為 ✅

## ✅ 設定完成後

設定完成後，您就可以使用 `supabase_utils.py` 中的圖片上傳功能了：

```python
from supabase_utils import upload_product_image, create_product_with_image

# 上傳圖片
image_url = upload_product_image('/path/to/image.jpg', product_name='可口可樂')

# 或一次完成（上傳圖片 + 建立商品）
product = create_product_with_image(
    name='可口可樂',
    price=25.00,
    image_path='/path/to/image.jpg'
)
```

## 🔍 驗證 Storage 是否設定成功

執行以下 Python 程式碼驗證：

```python
from supabase_utils import supabase, STORAGE_BUCKET

if supabase:
    try:
        # 列出所有 buckets
        buckets = supabase.storage.list_buckets()
        print("現有的 buckets:")
        for bucket in buckets:
            print(f"  - {bucket.name} (公開: {bucket.public})")
        
        # 檢查 product-images 是否存在
        bucket_names = [b.name for b in buckets]
        if STORAGE_BUCKET in bucket_names:
            print(f"\n✅ {STORAGE_BUCKET} bucket 已存在！")
        else:
            print(f"\n❌ {STORAGE_BUCKET} bucket 不存在，請先建立")
    except Exception as e:
        print(f"❌ 錯誤：{e}")
else:
    print("❌ Supabase 未初始化，請檢查環境變數")
```

## ⚠️ 注意事項

1. **Service Role Key 是機密資訊**
   - 不要提交到 Git
   - 不要分享給他人
   - 僅在本地開發環境使用

2. **Public Bucket 設定**
   - 必須設為公開，才能取得公開 URL
   - 公開 URL 格式：`https://xxx.supabase.co/storage/v1/object/public/product-images/products/xxx.jpg`

3. **檔案大小限制**
   - 免費方案通常有 50MB 的限制
   - 建議圖片大小控制在 5MB 以內

4. **安全性**
   - 如果需要限制上傳，可在 Dashboard 中設定 Storage Policies
   - 建議只允許特定角色上傳圖片

## 🆘 常見問題

**Q: 腳本執行時出現 "需要設定 SUPABASE_SERVICE_KEY"**
A: 請確認已正確設定環境變數，或直接在腳本中設定（僅測試用）

**Q: 出現 401 Unauthorized 錯誤**
A: 請確認 Service Role Key 是否正確，不是 Anon Key

**Q: 出現 409 Conflict 錯誤**
A: Bucket 已存在，這是正常的，可以繼續使用

**Q: 如何刪除現有的 bucket？**
A: 在 Supabase Dashboard > Storage 中，點擊 bucket 右側的選單 > Delete


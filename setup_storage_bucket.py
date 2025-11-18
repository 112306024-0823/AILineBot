"""
Supabase Storage Bucket 設定腳本
使用 Supabase Management API 建立 Storage bucket
"""
import os
import requests
import json

# Supabase 專案資訊
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://scbgrkmnbnkzdzzqdnjo.supabase.co")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")  # 需要 service_role key，不是 anon key

def create_storage_bucket(bucket_name: str, public: bool = True):
    """
    建立 Supabase Storage bucket
    
    Args:
        bucket_name: bucket 名稱
        public: 是否為公開 bucket（預設 True，才能取得公開 URL）
    
    Returns:
        成功返回 True，失敗返回 False
    """
    if not SUPABASE_SERVICE_KEY:
        print("❌ 錯誤：需要設定 SUPABASE_SERVICE_KEY 環境變數")
        print("   請從 Supabase Dashboard > Settings > API > service_role key 取得")
        return False
    
    url = f"{SUPABASE_URL}/storage/v1/bucket"
    
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "apikey": SUPABASE_SERVICE_KEY
    }
    
    data = {
        "name": bucket_name,
        "public": public,
        "file_size_limit": 5242880,  # 5MB
        "allowed_mime_types": ["image/jpeg", "image/png", "image/webp", "image/gif"]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            print(f"✅ Storage bucket '{bucket_name}' 建立成功！")
            print(f"   公開存取：{'是' if public else '否'}")
            return True
        elif response.status_code == 409:
            print(f"ℹ️  Storage bucket '{bucket_name}' 已存在")
            return True
        else:
            print(f"❌ 建立失敗：{response.status_code}")
            print(f"   錯誤訊息：{response.text}")
            return False
    except Exception as e:
        print(f"❌ 發生錯誤：{e}")
        return False


def list_storage_buckets():
    """列出所有 Storage buckets"""
    if not SUPABASE_SERVICE_KEY:
        print("❌ 錯誤：需要設定 SUPABASE_SERVICE_KEY 環境變數")
        return []
    
    url = f"{SUPABASE_URL}/storage/v1/bucket"
    
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "apikey": SUPABASE_SERVICE_KEY
    }
    
    try:
        response = requests.get(url, headers=headers)
        
        if response.status_code == 200:
            buckets = response.json()
            print(f"📦 現有的 Storage buckets：")
            for bucket in buckets:
                print(f"   - {bucket.get('name')} (公開：{'是' if bucket.get('public') else '否'})")
            return buckets
        else:
            print(f"❌ 查詢失敗：{response.status_code}")
            print(f"   錯誤訊息：{response.text}")
            return []
    except Exception as e:
        print(f"❌ 發生錯誤：{e}")
        return []


if __name__ == "__main__":
    print("=" * 50)
    print("Supabase Storage Bucket 設定")
    print("=" * 50)
    print()
    
    # 列出現有的 buckets
    print("1. 檢查現有的 buckets...")
    list_storage_buckets()
    print()
    
    # 建立 product-images bucket
    print("2. 建立 product-images bucket...")
    if create_storage_bucket("product-images", public=True):
        print()
        print("✅ 設定完成！")
        print()
        print("📝 使用方式：")
        print("   現在可以使用 supabase_utils.py 中的函數上傳圖片了")
        print("   例如：")
        print("   from supabase_utils import upload_product_image")
        print("   image_url = upload_product_image('/path/to/image.jpg')")
    else:
        print()
        print("❌ 設定失敗，請檢查：")
        print("   1. SUPABASE_SERVICE_KEY 是否正確設定")
        print("   2. 是否有足夠的權限")
        print()
        print("💡 替代方案：")
        print("   可以手動在 Supabase Dashboard 中建立 bucket")
        print("   步驟請參考 SUPABASE_STORAGE_GUIDE.md")


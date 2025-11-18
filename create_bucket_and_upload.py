"""
建立 Storage bucket 並上傳圖片
"""
import sys
import io

# 設定 UTF-8 編碼
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

import os
import requests
from dotenv import load_dotenv

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

def create_bucket():
    """建立 Storage bucket"""
    if not SUPABASE_SERVICE_KEY:
        print("[ERROR] 需要設定 SUPABASE_SERVICE_KEY 環境變數")
        print("請從 Supabase Dashboard > Settings > API > service_role key 取得")
        return False
    
    bucket_name = "product-images"
    url = f"{SUPABASE_URL}/storage/v1/bucket"
    
    headers = {
        "Authorization": f"Bearer {SUPABASE_SERVICE_KEY}",
        "Content-Type": "application/json",
        "apikey": SUPABASE_SERVICE_KEY
    }
    
    data = {
        "name": bucket_name,
        "public": True,
        "file_size_limit": 5242880,  # 5MB
        "allowed_mime_types": ["image/jpeg", "image/png", "image/webp", "image/gif"]
    }
    
    try:
        response = requests.post(url, headers=headers, json=data)
        
        if response.status_code == 200:
            print(f"[OK] Storage bucket '{bucket_name}' 建立成功！")
            return True
        elif response.status_code == 409:
            print(f"[INFO] Storage bucket '{bucket_name}' 已存在")
            return True
        else:
            print(f"[ERROR] 建立失敗：{response.status_code}")
            print(f"錯誤訊息：{response.text}")
            return False
    except Exception as e:
        print(f"[ERROR] 發生錯誤：{e}")
        return False

if __name__ == '__main__':
    print("=" * 60)
    print("建立 Storage Bucket")
    print("=" * 60)
    
    if create_bucket():
        print("\n[OK] Bucket 建立完成！")
        print("\n現在可以執行圖片上傳：")
        print("  python do_upload_images.py")
    else:
        print("\n[ERROR] Bucket 建立失敗")
        print("\n替代方案：")
        print("1. 手動在 Supabase Dashboard 中建立 bucket 'product-images'")
        print("2. 確保 bucket 設為公開（Public）")


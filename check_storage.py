"""快速檢查 Storage 設定"""
import sys
import io

# 設定 UTF-8 編碼
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

from dotenv import load_dotenv
load_dotenv()

from supabase_utils import supabase, STORAGE_BUCKET

if not supabase:
    print("[ERROR] Supabase 未初始化")
    exit(1)

try:
    buckets = supabase.storage.list_buckets()
    bucket_names = [b.name for b in buckets]
    
    if STORAGE_BUCKET in bucket_names:
        print(f"[OK] Storage bucket '{STORAGE_BUCKET}' 已存在")
        for bucket in buckets:
            if bucket.name == STORAGE_BUCKET:
                print(f"   公開: {'是' if bucket.public else '否'}")
    else:
        print(f"[ERROR] Storage bucket '{STORAGE_BUCKET}' 不存在")
        print("   請執行: python setup_storage_bucket.py")
except Exception as e:
    print(f"[ERROR] 錯誤: {e}")


"""
簡單測試 Supabase 連線
執行：python test_supabase.py
"""
import os
import sys

# 嘗試載入環境變數（如果有 python-dotenv）
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # 如果沒有 dotenv，使用系統環境變數

# 檢查環境變數
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

print("=" * 60)
print("🔍 Supabase 連線測試")
print("=" * 60)

# 檢查環境變數
if not supabase_url:
    print("❌ 錯誤：未設定 SUPABASE_URL")
    print("   請在 .env 檔案中設定：SUPABASE_URL=https://xxx.supabase.co")
    sys.exit(1)

if not supabase_key:
    print("❌ 錯誤：未設定 SUPABASE_KEY")
    print("   請在 .env 檔案中設定：SUPABASE_KEY=your-anon-key")
    sys.exit(1)

print(f"✅ SUPABASE_URL: {supabase_url}")
print(f"✅ SUPABASE_KEY: {supabase_key[:30]}...")
print()

# 測試連線
try:
    from supabase import create_client
    
    print("📡 正在連線到 Supabase...")
    supabase = create_client(supabase_url, supabase_key)
    
    # 測試查詢（測試資料表是否存在）
    print("📊 測試查詢資料表...")
    result = supabase.table("products").select("id").limit(1).execute()
    
    print("=" * 60)
    print("✅ 連線成功！")
    print(f"✅ 資料表可正常存取")
    print("=" * 60)
    
except ImportError:
    print("❌ 錯誤：未安裝 supabase 套件")
    print("   請執行：pip install supabase")
    sys.exit(1)
    
except Exception as e:
    print("=" * 60)
    print("❌ 連線失敗！")
    print(f"   錯誤訊息：{str(e)}")
    print()
    print("💡 可能的原因：")
    print("   1. SUPABASE_URL 或 SUPABASE_KEY 設定錯誤")
    print("   2. 資料表尚未建立（請執行 supabase_schema.sql）")
    print("   3. 網路連線問題")
    print("=" * 60)
    sys.exit(1)



"""
自動上傳範例產品圖片腳本

此腳本會：
1. 檢查 Supabase Storage 是否已設定
2. 從網路下載範例圖片（或使用本地圖片）
3. 上傳圖片到 Supabase Storage
4. 更新 products 表的 image_url

使用方法：
    python upload_sample_images.py
"""

import os
import sys
import requests
import tempfile
from typing import Optional, Dict, Any
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

from supabase_utils import (
    supabase,
    STORAGE_BUCKET,
    upload_product_image,
    update_product,
    search_products
)


def check_storage_setup() -> bool:
    """檢查 Storage bucket 是否已設定"""
    if not supabase:
        print("❌ Supabase 未初始化，請檢查環境變數")
        return False
    
    try:
        buckets = supabase.storage.list_buckets()
        bucket_names = [b.name for b in buckets]
        
        if STORAGE_BUCKET in bucket_names:
            print(f"✅ Storage bucket '{STORAGE_BUCKET}' 已存在")
            # 檢查是否為公開
            for bucket in buckets:
                if bucket.name == STORAGE_BUCKET:
                    if bucket.public:
                        print(f"   ✅ 已設為公開")
                    else:
                        print(f"   ⚠️  未設為公開，圖片可能無法顯示")
            return True
        else:
            print(f"❌ Storage bucket '{STORAGE_BUCKET}' 不存在")
            print(f"   請執行：python setup_storage_bucket.py")
            return False
    except Exception as e:
        print(f"❌ 檢查 Storage 時發生錯誤：{e}")
        return False


def download_image(url: str, save_path: str) -> bool:
    """從網路下載圖片"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                f.write(response.content)
            return True
        else:
            print(f"   ⚠️  下載失敗：HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"   ⚠️  下載失敗：{e}")
        return False


def upload_product_image_safe(product: Dict[str, Any], image_path: Optional[str] = None, image_url: Optional[str] = None) -> bool:
    """
    安全地上傳產品圖片並更新資料表
    
    Args:
        product: 產品資料
        image_path: 本地圖片路徑
        image_url: 已上傳的圖片 URL（如果已經上傳）
    
    Returns:
        是否成功
    """
    product_id = product['id']
    product_name = product['name']
    
    try:
        # 如果已經有有效的圖片 URL，直接使用
        if image_url and image_url.startswith('https://') and not image_url.startswith('https://example.com'):
            print(f"   ✅ 使用現有圖片 URL")
            final_url = image_url
        elif image_path and os.path.exists(image_path):
            # 上傳圖片
            print(f"   📤 上傳圖片：{os.path.basename(image_path)}")
            final_url = upload_product_image(
                file_path=image_path,
                product_name=product_name
            )
            if not final_url:
                print(f"   ❌ 上傳失敗")
                return False
        else:
            print(f"   ⚠️  沒有有效的圖片來源")
            return False
        
        # 更新資料表
        updated = update_product(product_id, image_url=final_url)
        if updated:
            print(f"   ✅ 更新成功：{product_name}")
            return True
        else:
            print(f"   ❌ 更新失敗")
            return False
    except Exception as e:
        print(f"   ❌ 發生錯誤：{e}")
        return False


def upload_sample_images_from_web():
    """
    從網路下載範例圖片並上傳
    
    注意：這只是示範，實際使用時應該使用真實的產品圖片
    """
    print("\n📥 從網路下載範例圖片...")
    print("   ⚠️  注意：這只是測試用，實際使用時請使用真實的產品圖片")
    
    # 範例圖片 URL（使用 placeholder 服務）
    # 實際使用時，你應該替換成真實的產品圖片 URL
    sample_images = {
        '可口可樂': 'https://via.placeholder.com/800x800.jpg?text=Coca-Cola',
        '統一泡麵': 'https://via.placeholder.com/800x800.jpg?text=Instant+Noodles',
        '義美小泡芙': 'https://via.placeholder.com/800x800.jpg?text=Puff',
        '光泉鮮奶': 'https://via.placeholder.com/800x800.jpg?text=Milk',
    }
    
    # 取得所有產品
    all_products = search_products(limit=50)
    
    if not all_products:
        print("❌ 找不到任何產品")
        return
    
    print(f"📦 找到 {len(all_products)} 個產品")
    
    # 建立臨時資料夾
    with tempfile.TemporaryDirectory() as temp_dir:
        success_count = 0
        
        for product in all_products:
            product_name = product['name']
            print(f"\n處理：{product_name}")
            
            # 檢查是否已有有效圖片
            current_image_url = product.get('image_url', '')
            if current_image_url and current_image_url.startswith('https://') and not current_image_url.startswith('https://example.com'):
                print(f"   ℹ️  已有有效圖片，跳過")
                continue
            
            # 嘗試從範例圖片中找對應的
            image_url = None
            for key, url in sample_images.items():
                if key in product_name:
                    image_url = url
                    break
            
            if image_url:
                # 下載圖片
                temp_image_path = os.path.join(temp_dir, f"{product_name.replace('/', '_')}.jpg")
                if download_image(image_url, temp_image_path):
                    # 上傳並更新
                    if upload_product_image_safe(product, image_path=temp_image_path):
                        success_count += 1
                else:
                    print(f"   ⚠️  跳過（下載失敗）")
            else:
                print(f"   ⚠️  找不到對應的範例圖片，跳過")
        
        print(f"\n📊 處理結果：成功 {success_count}/{len(all_products)} 個產品")


def upload_images_from_local_folder(folder_path: str):
    """
    從本地資料夾上傳圖片
    
    Args:
        folder_path: 圖片資料夾路徑
    """
    if not os.path.exists(folder_path):
        print(f"❌ 資料夾不存在：{folder_path}")
        return
    
    print(f"\n📁 從資料夾上傳圖片：{folder_path}")
    
    # 取得所有圖片檔案
    image_files = []
    for ext in ['jpg', 'jpeg', 'png', 'webp', 'gif']:
        for file in os.listdir(folder_path):
            if file.lower().endswith(f'.{ext}'):
                image_files.append(os.path.join(folder_path, file))
    
    if not image_files:
        print("❌ 資料夾中沒有找到圖片檔案")
        return
    
    print(f"📦 找到 {len(image_files)} 個圖片檔案")
    
    # 取得所有產品
    all_products = search_products(limit=100)
    
    if not all_products:
        print("❌ 找不到任何產品")
        return
    
    success_count = 0
    
    for image_path in image_files:
        # 從檔名取得產品名稱（移除副檔名）
        image_filename = os.path.basename(image_path)
        product_name = os.path.splitext(image_filename)[0]
        
        # 尋找對應的產品（模糊匹配）
        matched_product = None
        for product in all_products:
            if product_name in product['name'] or product['name'] in product_name:
                matched_product = product
                break
        
        if matched_product:
            print(f"\n處理：{product_name} -> {matched_product['name']}")
            if upload_product_image_safe(matched_product, image_path=image_path):
                success_count += 1
        else:
            print(f"\n⚠️  找不到對應的產品：{product_name}")
    
    print(f"\n📊 處理結果：成功 {success_count}/{len(image_files)} 個圖片")


def main():
    """主函數"""
    print("=" * 60)
    print("產品圖片自動上傳腳本")
    print("=" * 60)
    
    # 1. 檢查 Storage 設定
    print("\n1. 檢查 Supabase Storage 設定...")
    if not check_storage_setup():
        print("\n❌ Storage 未設定完成，無法繼續")
        print("   請先執行：python setup_storage_bucket.py")
        sys.exit(1)
    
    # 2. 選擇上傳方式
    print("\n2. 選擇上傳方式：")
    print("   [1] 從網路下載範例圖片（測試用）")
    print("   [2] 從本地資料夾上傳")
    print("   [3] 只更新現有產品（使用假 URL，不推薦）")
    
    choice = input("\n請選擇 (1/2/3，直接按 Enter 選擇 1): ").strip() or "1"
    
    if choice == "1":
        upload_sample_images_from_web()
    elif choice == "2":
        folder_path = input("請輸入圖片資料夾路徑: ").strip()
        if folder_path:
            upload_images_from_local_folder(folder_path)
        else:
            print("❌ 未輸入資料夾路徑")
    elif choice == "3":
        print("\n⚠️  不推薦使用假 URL，圖片將無法顯示")
        print("   建議使用選項 1 或 2")
    else:
        print("❌ 無效的選擇")
    
    print("\n" + "=" * 60)
    print("✅ 完成！")
    print("\n💡 提示：")
    print("   - 現在可以在 LINE Bot 中搜尋產品，應該會看到圖片")
    print("   - 如果圖片無法顯示，請檢查 Storage bucket 是否設為公開")
    print("   - 實際使用時，請使用真實的產品圖片")


if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  已取消")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ 發生錯誤：{e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)




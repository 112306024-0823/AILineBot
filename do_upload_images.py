"""
執行圖片上傳（簡化版）
"""
import sys
import io
import os

# 設定 UTF-8 編碼
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from dotenv import load_dotenv
load_dotenv()

from supabase_utils import (
    supabase,
    STORAGE_BUCKET,
    upload_product_image,
    update_product,
    search_products
)

def main():
    print("=" * 60)
    print("產品圖片上傳工具")
    print("=" * 60)
    
    # 檢查 Supabase
    if not supabase:
        print("[ERROR] Supabase 未初始化")
        return
    
    # 檢查 Storage bucket
    try:
        buckets = supabase.storage.list_buckets()
        bucket_names = [b.name for b in buckets]
        
        if STORAGE_BUCKET not in bucket_names:
            print(f"[ERROR] Storage bucket '{STORAGE_BUCKET}' 不存在")
            print("請先執行: python setup_storage_bucket.py")
            print("或手動在 Supabase Dashboard 中建立 bucket")
            return
        
        print(f"[OK] Storage bucket '{STORAGE_BUCKET}' 已存在")
        for bucket in buckets:
            if bucket.name == STORAGE_BUCKET:
                if not bucket.public:
                    print("[WARNING] Bucket 未設為公開，圖片可能無法顯示")
                else:
                    print("[OK] Bucket 已設為公開")
    except Exception as e:
        print(f"[ERROR] 檢查 Storage 時發生錯誤: {e}")
        return
    
    # 取得所有產品
    print("\n取得產品列表...")
    products = search_products(limit=50)
    
    if not products:
        print("[ERROR] 找不到任何產品")
        return
    
    print(f"找到 {len(products)} 個產品")
    
    # 檢查哪些產品需要更新圖片
    products_to_update = []
    for product in products:
        image_url = product.get('image_url', '')
        if not image_url or image_url.startswith('https://example.com'):
            products_to_update.append(product)
    
    print(f"\n需要更新圖片的產品: {len(products_to_update)} 個")
    
    if not products_to_update:
        print("[OK] 所有產品都已有有效圖片")
        return
    
    # 詢問用戶
    print("\n選項:")
    print("1. 使用 placeholder 圖片（測試用，不推薦）")
    print("2. 從本地資料夾上傳（需要準備圖片檔案）")
    print("3. 跳過（稍後手動上傳）")
    
    choice = input("\n請選擇 (1/2/3): ").strip()
    
    if choice == "1":
        print("\n[INFO] 使用 placeholder 圖片（僅測試用）")
        print("實際使用時請使用真實的產品圖片")
        
        # 使用 placeholder 服務建立圖片 URL
        success_count = 0
        for product in products_to_update[:10]:  # 限制前 10 個
            product_name = product['name']
            product_id = product['id']
            
            # 建立 placeholder URL（實際使用時應該上傳真實圖片）
            placeholder_url = f"https://via.placeholder.com/800x800.jpg?text={product_name.replace(' ', '+')}"
            
            try:
                updated = update_product(product_id, image_url=placeholder_url)
                if updated:
                    print(f"  [OK] {product_name}")
                    success_count += 1
                else:
                    print(f"  [ERROR] {product_name}")
            except Exception as e:
                print(f"  [ERROR] {product_name}: {e}")
        
        print(f"\n[OK] 完成！更新了 {success_count} 個產品")
        print("[WARNING] 這些是 placeholder 圖片，實際使用時請替換成真實圖片")
        
    elif choice == "2":
        folder_path = input("請輸入圖片資料夾路徑: ").strip()
        if not folder_path or not os.path.exists(folder_path):
            print("[ERROR] 資料夾不存在")
            return
        
        # 從資料夾上傳
        image_files = []
        for ext in ['jpg', 'jpeg', 'png', 'webp']:
            for file in os.listdir(folder_path):
                if file.lower().endswith(f'.{ext}'):
                    image_files.append(os.path.join(folder_path, file))
        
        if not image_files:
            print("[ERROR] 資料夾中沒有找到圖片檔案")
            return
        
        print(f"找到 {len(image_files)} 個圖片檔案")
        
        success_count = 0
        for image_path in image_files:
            filename = os.path.basename(image_path)
            product_name = os.path.splitext(filename)[0]
            
            # 尋找對應的產品
            matched_product = None
            for product in products_to_update:
                if product_name in product['name'] or product['name'] in product_name:
                    matched_product = product
                    break
            
            if matched_product:
                print(f"\n處理: {product_name} -> {matched_product['name']}")
                try:
                    image_url = upload_product_image(
                        file_path=image_path,
                        product_name=matched_product['name']
                    )
                    if image_url:
                        updated = update_product(matched_product['id'], image_url=image_url)
                        if updated:
                            print(f"  [OK] 上傳成功")
                            success_count += 1
                        else:
                            print(f"  [ERROR] 更新失敗")
                    else:
                        print(f"  [ERROR] 上傳失敗")
                except Exception as e:
                    print(f"  [ERROR] {e}")
            else:
                print(f"\n[WARNING] 找不到對應的產品: {product_name}")
        
        print(f"\n[OK] 完成！成功上傳 {success_count} 個圖片")
        
    else:
        print("\n已取消")
        print("\n提示: 可以使用以下方式手動上傳:")
        print("  python update_product_images.py --product-name \"產品名稱\" --image-path \"./image.jpg\"")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[INFO] 已取消")
    except Exception as e:
        print(f"\n[ERROR] 發生錯誤: {e}")
        import traceback
        traceback.print_exc()


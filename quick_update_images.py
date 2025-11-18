"""
快速更新產品圖片（使用 placeholder，之後可替換）
"""
import sys
import io

# 設定 UTF-8 編碼
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from dotenv import load_dotenv
load_dotenv()

from supabase_utils import search_products, update_product

def main():
    print("=" * 60)
    print("快速更新產品圖片 URL")
    print("=" * 60)
    print("\n[INFO] 這會使用 placeholder 圖片 URL 更新產品")
    print("實際使用時，請替換成真實的 Supabase Storage URL\n")
    
    # 取得所有產品
    products = search_products(limit=100)
    
    if not products:
        print("[ERROR] 找不到任何產品")
        return
    
    print(f"找到 {len(products)} 個產品\n")
    
    # 找出需要更新的產品
    to_update = []
    for product in products:
        image_url = product.get('image_url', '')
        if not image_url or image_url.startswith('https://example.com'):
            to_update.append(product)
    
    print(f"需要更新的產品: {len(to_update)} 個\n")
    
    if not to_update:
        print("[OK] 所有產品都已有有效圖片")
        return
    
    # 確認
    confirm = input(f"確定要更新 {len(to_update)} 個產品嗎？(y/n): ").strip().lower()
    if confirm != 'y':
        print("已取消")
        return
    
    # 更新產品
    print("\n開始更新...")
    success_count = 0
    
    for product in to_update:
        product_name = product['name']
        product_id = product['id']
        
        # 使用 placeholder URL（實際使用時應該替換成真實的 Supabase Storage URL）
        # 這裡使用一個可以顯示產品名稱的 placeholder
        safe_name = product_name.replace(' ', '+').replace('/', '+')
        placeholder_url = f"https://via.placeholder.com/800x800/4A90E2/FFFFFF.jpg?text={safe_name}"
        
        try:
            updated = update_product(product_id, image_url=placeholder_url)
            if updated:
                print(f"  [OK] {product_name}")
                success_count += 1
            else:
                print(f"  [ERROR] {product_name} - 更新失敗")
        except Exception as e:
            print(f"  [ERROR] {product_name} - {e}")
    
    print(f"\n[OK] 完成！更新了 {success_count}/{len(to_update)} 個產品")
    print("\n[WARNING] 這些是 placeholder 圖片，實際使用時請：")
    print("1. 上傳真實圖片到 Supabase Storage")
    print("2. 使用 update_product_images.py 更新圖片 URL")
    print("\n或執行: python do_upload_images.py 選擇選項 2 從本地資料夾上傳")

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[INFO] 已取消")
    except Exception as e:
        print(f"\n[ERROR] 發生錯誤: {e}")
        import traceback
        traceback.print_exc()


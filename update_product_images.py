"""
為商品添加圖片 URL
使用 Unsplash Source API 獲取商品相關圖片
"""
import os
import requests
import time
from dotenv import load_dotenv
from supabase_utils import supabase

load_dotenv()

def get_unsplash_image_url(search_term: str, width: int = 400, height: int = 400) -> str:
    """
    使用 Unsplash Source API 獲取圖片 URL
    不需要 API key，但圖片是隨機的
    """
    # Unsplash Source API: https://source.unsplash.com/
    # 格式: https://source.unsplash.com/{width}x{height}/?{keywords}
    search_query = search_term.replace(' ', ',')
    url = f"https://source.unsplash.com/{width}x{height}/?{search_query}"
    return url


def get_better_image_url(product_name: str, brand: str = None, category: str = None) -> str:
    """
    根據商品名稱、品牌、分類生成更精確的圖片搜尋關鍵字
    """
    # 優先使用品牌和商品名稱
    if brand:
        search_query = f"{brand} {product_name}"
    else:
        search_query = product_name
    
    # 如果分類是零食，添加相關關鍵字
    if category == "零食":
        search_query += " snack chips"
    elif category == "食品":
        search_query += " food instant noodle"
    elif category == "乳製品":
        search_query += " dairy milk"
    elif category == "罐頭":
        search_query += " canned food"
    
    # 使用 Unsplash Source API
    return get_unsplash_image_url(search_query)


def update_product_images():
    """更新所有沒有圖片的商品"""
    if not supabase:
        print("❌ Supabase 未初始化")
        return
    
    try:
        # 查詢所有沒有圖片的商品
        result = supabase.table("products").select("id, name, brand, category, image_url").execute()
        
        products = result.data if result.data else []
        products_without_image = [
            p for p in products 
            if not p.get('image_url') or p.get('image_url') == '' or 'example.com' in p.get('image_url', '')
        ]
        
        print(f"找到 {len(products_without_image)} 個沒有圖片的商品")
        print("=" * 60)
        
        success_count = 0
        for idx, product in enumerate(products_without_image, 1):
            product_id = product['id']
            product_name = product['name']
            brand = product.get('brand')
            category = product.get('category')
            
            print(f"\n[{idx}/{len(products_without_image)}] 處理：{product_name}")
            
            # 生成圖片 URL
            image_url = get_better_image_url(product_name, brand, category)
            print(f"  圖片 URL: {image_url}")
            
            # 更新資料庫
            try:
                update_result = supabase.table("products").update({
                    "image_url": image_url
                }).eq("id", product_id).execute()
                
                if update_result.data:
                    print(f"  ✅ 更新成功")
                    success_count += 1
                else:
                    print(f"  ❌ 更新失敗")
            except Exception as e:
                print(f"  ❌ 更新錯誤：{e}")
            
            # 避免請求過快
            time.sleep(0.5)
        
        print("\n" + "=" * 60)
        print(f"✅ 完成！成功更新 {success_count}/{len(products_without_image)} 個商品")
        
    except Exception as e:
        print(f"❌ 發生錯誤：{e}")


if __name__ == "__main__":
    print("🖼️  開始為商品添加圖片 URL...")
    print("=" * 60)
    update_product_images()


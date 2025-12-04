"""
增強版家樂福產品爬蟲腳本
涵蓋更多分類，並獲取更詳細的商品資訊
"""

import os
import sys
import io
import asyncio
import re
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright, Page
from dotenv import load_dotenv

# 設定 UTF-8 編碼
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

load_dotenv()

# 加入父目錄到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from supabase_utils import supabase, upload_product_image_from_bytes
import requests

# 擴展的分類列表（參考家樂福官網）
CATEGORIES = {
    # 飲料類
    'drinks_cold': {
        'name': '冷藏飲品',
        'category': '飲料',
        'url': 'https://c4fast.carrefour.com.tw/category?cid=A05A009'
    },
    'drinks_juice': {
        'name': '果汁',
        'category': '飲料',
        'url': 'https://c4fast.carrefour.com.tw/category?cid=A05A010'
    },
    'drinks_tea': {
        'name': '茶飲',
        'category': '飲料',
        'url': 'https://c4fast.carrefour.com.tw/category?cid=A05A011'
    },
    'drinks_coffee': {
        'name': '咖啡',
        'category': '飲料',
        'url': 'https://c4fast.carrefour.com.tw/category?cid=A05A012'
    },
    'drinks_soda': {
        'name': '碳酸飲料',
        'category': '飲料',
        'url': 'https://c4fast.carrefour.com.tw/category?cid=A05A013'
    },
    
    # 零食類
    'snacks_chips': {
        'name': '洋芋片',
        'category': '零食',
        'url': 'https://c4fast.carrefour.com.tw/category?cid=A14A002'
    },
    'snacks_candy': {
        'name': '糖果',
        'category': '零食',
        'url': 'https://c4fast.carrefour.com.tw/category?cid=A14A003'
    },
    'snacks_cookies': {
        'name': '餅乾',
        'category': '零食',
        'url': 'https://c4fast.carrefour.com.tw/category?cid=A14A004'
    },
    'snacks_nuts': {
        'name': '堅果',
        'category': '零食',
        'url': 'https://c4fast.carrefour.com.tw/category?cid=A14A005'
    },
    
    # 食品類
    'food_instant_noodles': {
        'name': '泡麵',
        'category': '食品',
        'url': 'https://c4fast.carrefour.com.tw/category?cid=A06A001'
    },
    'food_canned': {
        'name': '罐頭',
        'category': '罐頭',
        'url': 'https://c4fast.carrefour.com.tw/category?cid=A06A002'
    },
    'food_sauce': {
        'name': '調味料',
        'category': '調味料',
        'url': 'https://c4fast.carrefour.com.tw/category?cid=A06A003'
    },
    'food_rice': {
        'name': '米',
        'category': '食品',
        'url': 'https://c4fast.carrefour.com.tw/category?cid=A06A004'
    },
    
    # 生鮮類
    'fresh_vegetables': {
        'name': '蔬菜',
        'category': '生鮮',
        'url': 'https://c4fast.carrefour.com.tw/category?cid=A01A001'
    },
    'fresh_fruits': {
        'name': '水果',
        'category': '生鮮',
        'url': 'https://c4fast.carrefour.com.tw/category?cid=A01A002'
    },
    'fresh_meat': {
        'name': '肉類',
        'category': '生鮮',
        'url': 'https://c4fast.carrefour.com.tw/category?cid=A01A003'
    },
    'fresh_seafood': {
        'name': '海鮮',
        'category': '生鮮',
        'url': 'https://c4fast.carrefour.com.tw/category?cid=A01A004'
    },
    
    # 乳製品
    'dairy_milk': {
        'name': '鮮乳',
        'category': '乳製品',
        'url': 'https://c4fast.carrefour.com.tw/category?cid=A05A001'
    },
    'dairy_yogurt': {
        'name': '優格',
        'category': '乳製品',
        'url': 'https://c4fast.carrefour.com.tw/category?cid=A05A002'
    },
    'dairy_cheese': {
        'name': '起司',
        'category': '乳製品',
        'url': 'https://c4fast.carrefour.com.tw/category?cid=A05A003'
    },
    
    # 冷凍食品
    'frozen_dumplings': {
        'name': '水餃',
        'category': '冷凍食品',
        'url': 'https://c4fast.carrefour.com.tw/category?cid=A07A001'
    },
    'frozen_ice_cream': {
        'name': '冰淇淋',
        'category': '冷凍食品',
        'url': 'https://c4fast.carrefour.com.tw/category?cid=A07A002'
    },
    'frozen_ready_meals': {
        'name': '冷凍調理',
        'category': '冷凍食品',
        'url': 'https://c4fast.carrefour.com.tw/category?cid=A07A003'
    },
    
    # 生活用品
    'household_cleaning': {
        'name': '清潔用品',
        'category': '生活用品',
        'url': 'https://c4fast.carrefour.com.tw/category?cid=A15A001'
    },
    'household_paper': {
        'name': '衛生紙',
        'category': '生活用品',
        'url': 'https://c4fast.carrefour.com.tw/category?cid=A15A002'
    },
    'household_personal': {
        'name': '個人護理',
        'category': '生活用品',
        'url': 'https://c4fast.carrefour.com.tw/category?cid=A15A003'
    },
}


async def extract_products_from_page(page: Page) -> List[Dict[str, Any]]:
    """
    從當前頁面提取產品資訊
    
    Returns:
        產品列表，每個產品包含：name, price, image_url, product_url
    """
    products = []
    
    # 等待產品列表載入
    try:
        await page.wait_for_selector('a[href*="/product?pid="]', timeout=15000)
    except Exception as e:
        print(f"[警告] 等待產品列表載入超時: {e}")
        return products
    
    # 獲取所有產品連結
    product_links = await page.query_selector_all('a[href*="/product?pid="]')
    
    print(f"[INFO] 找到 {len(product_links)} 個產品連結")
    
    for link in product_links[:30]:  # 每頁最多 30 個產品
        try:
            # 獲取產品 URL
            product_url = await link.get_attribute('href')
            if not product_url:
                continue
            
            # 完整 URL
            if not product_url.startswith('http'):
                product_url = f"https://c4fast.carrefour.com.tw{product_url}"
            
            # 獲取產品名稱
            name_elem = await link.query_selector('img')
            if name_elem:
                name = await name_elem.get_attribute('alt')
            else:
                name = await link.inner_text()
            
            # 清理產品名稱
            if name:
                name = re.sub(r'※實際到貨效期約\d+天以上', '', name).strip()
                name = re.sub(r'\s+', ' ', name).strip()
            
            # 獲取價格
            price_elem = await link.query_selector('generic')
            price_text = ""
            if price_elem:
                price_text = await price_elem.inner_text()
            
            # 解析價格
            price = 0
            price_match = re.search(r'\$(\d+)', price_text)
            if price_match:
                price = int(price_match.group(1))
            
            # 獲取圖片 URL
            img_elem = await link.query_selector('img')
            image_url = ""
            if img_elem:
                image_url = await img_elem.get_attribute('src')
                if image_url and not image_url.startswith('http'):
                    image_url = f"https://c4fast.carrefour.com.tw{image_url}"
            
            if name and price > 0:
                products.append({
                    'name': name,
                    'price': price,
                    'image_url': image_url,
                    'product_url': product_url
                })
                print(f"  - {name}: ${price}")
        
        except Exception as e:
            print(f"[錯誤] 提取產品資訊失敗: {e}")
            continue
    
    return products


async def get_product_details(page: Page, product_url: str) -> Dict[str, Any]:
    """
    獲取產品詳細資訊（品牌、描述、成分等）
    
    Args:
        page: Playwright 頁面物件
        product_url: 產品詳情頁 URL
    
    Returns:
        產品詳細資訊字典
    """
    details = {}
    
    try:
        await page.goto(product_url, wait_until='domcontentloaded', timeout=20000)
        await asyncio.sleep(2)  # 等待 JavaScript 渲染
        
        # 獲取品牌
        try:
            brand_selectors = [
                'text=/品牌/',
                '[class*="brand"]',
                '[data-testid*="brand"]'
            ]
            for selector in brand_selectors:
                try:
                    brand_elem = await page.query_selector(selector)
                    if brand_elem:
                        brand_text = await brand_elem.inner_text()
                        if brand_text and '品牌' in brand_text:
                            details['brand'] = brand_text.replace('品牌', '').strip()
                            break
                except:
                    continue
        except:
            pass
        
        # 獲取描述
        try:
            desc_elem = await page.query_selector('meta[property="og:description"]')
            if desc_elem:
                details['description'] = await desc_elem.get_attribute('content')
        except:
            pass
        
        # 獲取成分/規格（嘗試多種選擇器）
        try:
            ingredient_selectors = [
                'text=/成分/',
                'text=/原料/',
                '[class*="ingredient"]',
                '[class*="specification"]'
            ]
            for selector in ingredient_selectors:
                try:
                    ing_elem = await page.query_selector(selector)
                    if ing_elem:
                        ingredients_text = await ing_elem.inner_text()
                        if ingredients_text:
                            details['ingredients'] = ingredients_text
                            break
                except:
                    continue
        except:
            pass
        
        # 獲取條碼（如果頁面有顯示）
        try:
            barcode_elem = await page.query_selector('text=/條碼/')
            if barcode_elem:
                barcode_text = await barcode_elem.inner_text()
                if barcode_text:
                    barcode_match = re.search(r'(\d{8,13})', barcode_text)
                    if barcode_match:
                        details['barcode'] = barcode_match.group(1)
        except:
            pass
    
    except Exception as e:
        print(f"    [警告] 無法獲取產品詳情: {e}")
    
    return details


def download_image(image_url: str) -> Optional[bytes]:
    """
    下載圖片並返回 bytes
    
    Args:
        image_url: 圖片 URL
    
    Returns:
        圖片 bytes 或 None
    """
    try:
        response = requests.get(image_url, timeout=10, headers={
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        if response.status_code == 200:
            return response.content
        else:
            print(f"    [錯誤] 下載圖片失敗，HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"    [錯誤] 下載圖片異常: {e}")
        return None


def check_product_exists(name: str) -> bool:
    """
    檢查商品是否已存在
    
    Args:
        name: 商品名稱
    
    Returns:
        是否存在
    """
    if not supabase:
        return False
    
    try:
        result = supabase.table('products').select('id').ilike('name', f'%{name}%').limit(1).execute()
        return len(result.data) > 0 if result.data else False
    except:
        return False


def save_product_to_supabase(product: Dict[str, Any], category: str) -> bool:
    """
    將產品資料存入 Supabase
    
    Args:
        product: 產品資料字典
        category: 產品分類
    
    Returns:
        是否成功
    """
    try:
        # 檢查是否已存在
        if check_product_exists(product['name']):
            print(f"    [跳過] 商品已存在: {product['name']}")
            return False
        
        # 下載並上傳圖片到 Supabase Storage
        image_public_url = None
        if product.get('image_url'):
            print(f"    [INFO] 下載圖片: {product['image_url'][:60]}...")
            image_bytes = download_image(product['image_url'])
            
            if image_bytes:
                safe_name = re.sub(r'[^\w\s-]', '', product['name'])
                safe_name = safe_name.replace(' ', '_')[:50]
                filename = f"carrefour_{category}_{safe_name}.jpg"
                
                print(f"    [INFO] 上傳圖片到 Supabase Storage: {filename}")
                image_public_url = upload_product_image_from_bytes(
                    image_bytes,
                    filename
                )
                
                if image_public_url:
                    print(f"    [✓] 圖片上傳成功")
        
        # 將產品資料插入 products 表
        product_data = {
            'name': product['name'],
            'brand': product.get('brand') or product.get('brand', '家樂福'),
            'description': product.get('description', ''),
            'ingredients': product.get('ingredients'),
            'barcode': product.get('barcode'),
            'price': product['price'],
            'stock': 10,  # 預設存貨
            'image_url': image_public_url or product.get('image_url', ''),
            'category': category,
            'calories': product.get('calories')  # 如果有卡路里資訊
        }
        
        # 移除 None 值
        product_data = {k: v for k, v in product_data.items() if v is not None}
        
        result = supabase.table('products').insert(product_data).execute()
        
        if result.data:
            product_id = result.data[0]['id']
            print(f"    [✓] 產品已存入 Supabase (ID: {product_id})")
            
            # 新增產品位置資訊
            location_data = {
                'product_id': product_id,
                'area': f'{category}區',
                'shelf': 'A架',
                'notes': f'從家樂福網站爬取'
            }
            supabase.table('product_locations').insert(location_data).execute()
            print(f"    [✓] 位置資訊已新增")
            
            return True
        else:
            print(f"    [✗] 產品存入失敗")
            return False
    
    except Exception as e:
        print(f"    [✗] 存入 Supabase 時發生錯誤: {e}")
        return False


async def scrape_category(category_key: str, max_products: int = 30, get_details: bool = True):
    """
    爬取指定分類的產品
    
    Args:
        category_key: 分類鍵值
        max_products: 最多爬取幾個產品
        get_details: 是否獲取詳細資訊（會增加爬取時間）
    """
    category = CATEGORIES.get(category_key)
    if not category:
        print(f"[錯誤] 未知的分類: {category_key}")
        return
    
    print(f"\n{'='*60}")
    print(f"開始爬取分類: {category['name']} ({category['category']})")
    print(f"URL: {category['url']}")
    print(f"{'='*60}\n")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            print(f"[INFO] 正在載入頁面...")
            await page.goto(category['url'], wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(3)  # 等待 JavaScript 渲染
            
            print(f"[INFO] 正在提取產品資訊...")
            products = await extract_products_from_page(page)
            
            if not products:
                print(f"[警告] 未找到任何產品")
                return
            
            print(f"\n[INFO] 找到 {len(products)} 個產品，開始處理...\n")
            
            success_count = 0
            for i, product in enumerate(products[:max_products], 1):
                print(f"[{i}/{min(len(products), max_products)}] 處理產品: {product['name']}")
                
                # 獲取產品詳情
                if get_details:
                    details = await get_product_details(page, product['product_url'])
                    product.update(details)
                
                # 存入 Supabase
                if save_product_to_supabase(product, category['category']):
                    success_count += 1
                
                # 避免請求過快
                await asyncio.sleep(1.5)
            
            print(f"\n{'='*60}")
            print(f"分類 {category['name']} 完成！")
            print(f"成功: {success_count}/{min(len(products), max_products)}")
            print(f"{'='*60}\n")
        
        finally:
            await browser.close()


async def main():
    """主函數"""
    print("\n🛒 增強版家樂福產品爬蟲")
    print("="*60)
    
    if not supabase:
        print("[錯誤] Supabase 未連線，請檢查環境變數設定")
        return
    
    print("[✓] Supabase 已連線\n")
    
    # 顯示所有可用分類
    print("可用分類：")
    for i, (key, cat) in enumerate(CATEGORIES.items(), 1):
        print(f"{i:2d}. {cat['name']} ({cat['category']})")
    
    print("\n選項：")
    print("1. 爬取所有分類（每個分類最多 20 個商品）")
    print("2. 選擇特定分類")
    print("3. 只爬取飲料類")
    print("4. 只爬取零食類")
    print("5. 只爬取生鮮類")
    print("6. 只爬取生活用品類")
    
    choice = input("\n請輸入選項 (1-6): ").strip()
    
    if choice == '1':
        # 爬取所有分類
        for key in CATEGORIES.keys():
            await scrape_category(key, max_products=20, get_details=True)
            await asyncio.sleep(2)  # 分類間暫停
    
    elif choice == '2':
        # 選擇特定分類
        cat_key = input("請輸入分類鍵值（例如：drinks_cold）: ").strip()
        max_prod = int(input("最多爬取幾個商品（預設 30）: ").strip() or "30")
        await scrape_category(cat_key, max_products=max_prod, get_details=True)
    
    elif choice == '3':
        # 只爬取飲料類
        drink_keys = [k for k in CATEGORIES.keys() if k.startswith('drinks_')]
        for key in drink_keys:
            await scrape_category(key, max_products=25, get_details=True)
            await asyncio.sleep(2)
    
    elif choice == '4':
        # 只爬取零食類
        snack_keys = [k for k in CATEGORIES.keys() if k.startswith('snacks_')]
        for key in snack_keys:
            await scrape_category(key, max_products=25, get_details=True)
            await asyncio.sleep(2)
    
    elif choice == '5':
        # 只爬取生鮮類
        fresh_keys = [k for k in CATEGORIES.keys() if k.startswith('fresh_')]
        for key in fresh_keys:
            await scrape_category(key, max_products=25, get_details=True)
            await asyncio.sleep(2)
    
    elif choice == '6':
        # 只爬取生活用品類
        household_keys = [k for k in CATEGORIES.keys() if k.startswith('household_')]
        for key in household_keys:
            await scrape_category(key, max_products=25, get_details=True)
            await asyncio.sleep(2)
    
    else:
        print("[錯誤] 無效的選項")
        return
    
    print("\n✅ 所有任務完成！")


if __name__ == "__main__":
    asyncio.run(main())


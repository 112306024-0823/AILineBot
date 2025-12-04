"""
家樂福產品爬蟲腳本
使用 Playwright 從家樂福網站抓取產品資料並存入 Supabase
"""

import os
import sys
import io
import asyncio
import re
from typing import List, Dict, Any
from playwright.async_api import async_playwright, Page
from dotenv import load_dotenv

# 設定 UTF-8 編碼
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

load_dotenv()

from supabase_utils import supabase, upload_product_image_from_bytes
import requests

# 分類列表
CATEGORIES = {
    'drinks': {
        'name': '冷藏飲品',
        'url': 'https://c4fast.carrefour.com.tw/category?cid=A05A009'
    },
    'snacks': {
        'name': '洋芋片專區',
        'url': 'https://c4fast.carrefour.com.tw/category?cid=A14A002'
    }
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
        await page.wait_for_selector('a[href*="/product?pid="]', timeout=10000)
    except Exception as e:
        print(f"[警告] 等待產品列表載入超時: {e}")
        return products
    
    # 獲取所有產品連結
    product_links = await page.query_selector_all('a[href*="/product?pid="]')
    
    print(f"[INFO] 找到 {len(product_links)} 個產品連結")
    
    for link in product_links[:20]:  # 限制每頁 20 個產品
        try:
            # 獲取產品 URL
            product_url = await link.get_attribute('href')
            if not product_url:
                continue
            
            # 完整 URL
            if not product_url.startswith('http'):
                product_url = f"https://c4fast.carrefour.com.tw{product_url}"
            
            # 獲取產品名稱（從 link 內的文字或 img alt）
            name_elem = await link.query_selector('img')
            if name_elem:
                name = await name_elem.get_attribute('alt')
            else:
                name = await link.inner_text()
            
            # 清理產品名稱（移除實際到貨效期等說明文字）
            if name:
                name = re.sub(r'※實際到貨效期約\d+天以上', '', name).strip()
            
            # 獲取價格
            price_elem = await link.query_selector('generic')
            price_text = ""
            if price_elem:
                price_text = await price_elem.inner_text()
            
            # 解析價格（取第一個價格）
            price = 0
            price_match = re.search(r'\$(\d+)', price_text)
            if price_match:
                price = int(price_match.group(1))
            
            # 獲取圖片 URL
            img_elem = await link.query_selector('img')
            image_url = ""
            if img_elem:
                image_url = await img_elem.get_attribute('src')
                # 確保是完整 URL
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
    獲取產品詳細資訊（品牌、描述等）
    
    Args:
        page: Playwright 頁面物件
        product_url: 產品詳情頁 URL
    
    Returns:
        產品詳細資訊字典
    """
    details = {}
    
    try:
        # 導航到產品詳情頁
        await page.goto(product_url, wait_until='domcontentloaded', timeout=15000)
        await asyncio.sleep(1)  # 等待 JavaScript 渲染
        
        # 嘗試獲取品牌（通常在產品名稱或描述中）
        # 這裡需要根據實際網頁結構調整選擇器
        try:
            brand_elem = await page.query_selector('text=/品牌/')
            if brand_elem:
                details['brand'] = await brand_elem.inner_text()
        except:
            pass
        
        # 嘗試獲取描述
        try:
            desc_elem = await page.query_selector('meta[property="og:description"]')
            if desc_elem:
                details['description'] = await desc_elem.get_attribute('content')
        except:
            pass
    
    except Exception as e:
        print(f"    [警告] 無法獲取產品詳情: {e}")
    
    return details


def download_image(image_url: str) -> bytes:
    """
    下載圖片並返回 bytes
    
    Args:
        image_url: 圖片 URL
    
    Returns:
        圖片 bytes 或 None
    """
    try:
        response = requests.get(image_url, timeout=10)
        if response.status_code == 200:
            return response.content
        else:
            print(f"    [錯誤] 下載圖片失敗，HTTP {response.status_code}")
            return None
    except Exception as e:
        print(f"    [錯誤] 下載圖片異常: {e}")
        return None


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
        # 1. 下載並上傳圖片到 Supabase Storage
        image_public_url = None
        if product.get('image_url'):
            print(f"    [INFO] 下載圖片: {product['image_url'][:60]}...")
            image_bytes = download_image(product['image_url'])
            
            if image_bytes:
                # 生成檔案名稱（使用產品名稱）
                safe_name = re.sub(r'[^\w\s-]', '', product['name'])
                safe_name = safe_name.replace(' ', '_')[:50]
                filename = f"carrefour_{category}_{safe_name}.jpg"
                
                print(f"    [INFO] 上傳圖片到 Supabase Storage: {filename}")
                image_public_url = upload_product_image_from_bytes(
                    image_bytes,
                    filename
                )
                
                if image_public_url:
                    print(f"    [✓] 圖片上傳成功: {image_public_url[:60]}...")
        
        # 2. 將產品資料插入 products 表
        product_data = {
            'name': product['name'],
            'brand': product.get('brand', '家樂福'),
            'description': product.get('description', ''),
            'price': product['price'],
            'stock': 10,  # 預設存貨
            'image_url': image_public_url or product.get('image_url', ''),
            'category': category
        }
        
        result = supabase.table('products').insert(product_data).execute()
        
        if result.data:
            product_id = result.data[0]['id']
            print(f"    [✓] 產品已存入 Supabase (ID: {product_id})")
            
            # 3. 新增產品位置資訊（示例）
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


async def scrape_category(category_key: str, max_products: int = 20):
    """
    爬取指定分類的產品
    
    Args:
        category_key: 分類鍵值 ('drinks' 或 'snacks')
        max_products: 最多爬取幾個產品
    """
    category = CATEGORIES.get(category_key)
    if not category:
        print(f"[錯誤] 未知的分類: {category_key}")
        return
    
    print(f"\n{'='*60}")
    print(f"開始爬取分類: {category['name']}")
    print(f"URL: {category['url']}")
    print(f"{'='*60}\n")
    
    
    async with async_playwright() as p:
        # 啟動瀏覽器
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            # 導航到分類頁面
            print(f"[INFO] 正在載入頁面...")
            await page.goto(category['url'], wait_until='domcontentloaded', timeout=30000)
            await asyncio.sleep(2)  # 等待 JavaScript 渲染
            
            # 提取產品列表
            
            print(f"[INFO] 正在提取產品資訊...")
            products = await extract_products_from_page(page)
            
            if not products:
                print(f"[警告] 未找到任何產品")
                return
            
            print(f"\n[INFO] 找到 {len(products)} 個產品，開始處理...\n")
            
            # 處理每個產品
            success_count = 0
            for i, product in enumerate(products[:max_products], 1):
                print(f"[{i}/{min(len(products), max_products)}] 處理產品: {product['name']}")
                
                # 獲取產品詳情（可選，會增加爬取時間）
                # details = await get_product_details(page, product['product_url'])
                # product.update(details)
                
                # 存入 Supabase
                if save_product_to_supabase(product, category['name']):
                    success_count += 1
                
                # 避免請求過快
                await asyncio.sleep(1)
            
            print(f"\n{'='*60}")
            print(f"分類 {category['name']} 完成！")
            print(f"成功: {success_count}/{min(len(products), max_products)}")
            print(f"{'='*60}\n")
        
        finally:
            await browser.close()


async def main():
    """主函數"""
    print("\n🛒 家樂福產品爬蟲")
    print("="*60)
    
    # 檢查 Supabase 連線
    if not supabase:
        print("[錯誤] Supabase 未連線，請檢查環境變數設定")
        return
    
    print("[✓] Supabase 已連線\n")
    
    # 選擇要爬取的分類
    print("請選擇要爬取的分類:")
    print("1. 冷藏飲品 (drinks)")
    print("2. 休閒零食 (snacks)")
    print("3. 兩者都要")
    
    choice = input("\n請輸入選項 (1/2/3): ").strip()
    
    if choice == '1':
        await scrape_category('drinks', max_products=20)
    elif choice == '2':
        await scrape_category('snacks', max_products=20)
    elif choice == '3':
        await scrape_category('drinks', max_products=20)
        await scrape_category('snacks', max_products=20)
    else:
        print("[錯誤] 無效的選項")
        return
    
    print("\n✅ 所有任務完成！")


if __name__ == "__main__":
    asyncio.run(main())


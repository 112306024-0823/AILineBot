"""
更新使用 Unsplash 圖片的商品，到家樂福網站搜尋對應的商品圖片
"""

import os
import sys
import io
import asyncio
import re
from typing import List, Dict, Any, Optional
from playwright.async_api import async_playwright, Page
from dotenv import load_dotenv
import requests
from urllib.parse import quote

# 設定 UTF-8 編碼
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

load_dotenv()

# 加入父目錄到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from supabase_utils import supabase
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


async def search_product_on_carrefour(page: Page, product_name: str, brand: Optional[str] = None) -> Optional[str]:
    """
    到家樂福網站搜尋商品並獲取圖片 URL（改進版）
    
    Args:
        page: Playwright 頁面物件
        product_name: 商品名稱
        brand: 品牌名稱（可選，用於更精確的搜尋）
        
    Returns:
        商品圖片 URL，如果找不到則返回 None
    """
    try:
        # 清理商品名稱，移除多餘的資訊
        clean_name = product_name
        # 移除容量、規格等資訊，只保留核心商品名稱
        clean_name = re.sub(r'\s+\d+[mlgkg]+\s*', ' ', clean_name)
        clean_name = re.sub(r'\s+大包\s*', ' ', clean_name)
        clean_name = re.sub(r'\s+大瓶\s*', ' ', clean_name)
        clean_name = clean_name.strip()
        
        # 構建搜尋關鍵字（優先使用品牌+商品名稱）
        if brand:
            search_query = f"{brand} {clean_name}".strip()
        else:
            search_query = clean_name
        
        # URL 編碼（使用正確的搜尋 URL 格式）
        encoded_query = quote(search_query)
        # 家樂福的搜尋 URL 格式：https://online.carrefour.com.tw/zh/search/?q=關鍵字
        search_url = f"https://online.carrefour.com.tw/zh/search/?q={encoded_query}"
        
        logger.info(f"搜尋商品：{product_name}")
        if brand:
            logger.info(f"使用品牌：{brand}")
        logger.info(f"搜尋 URL：{search_url}")
        
        # 導航到搜尋頁面
        try:
            await page.goto(search_url, wait_until='networkidle', timeout=30000)
        except:
            # 如果 networkidle 失敗，使用 domcontentloaded
            await page.goto(search_url, wait_until='domcontentloaded', timeout=30000)
        await asyncio.sleep(5)  # 等待頁面載入和 JavaScript 執行
        
        # 直接從搜尋結果頁面提取第一張商品圖片
        try:
            img_url = None
            
            # 方法1：從搜尋結果頁面直接查找商品圖片（多種選擇器）
            img_selectors = [
                'img[src*="demandware.static"][src*="/large/"]',
                'img[src*="demandware.static"]',
                '.product-item img',
                '.product-card img',
                '.product img',
                'article img',
                '[class*="product"] img'
            ]
            
            for selector in img_selectors:
                try:
                    img_elements = await page.query_selector_all(selector)
                    for img_element in img_elements:
                        img_url = await img_element.get_attribute('src')
                        if img_url and 'demandware.static' in img_url:
                            # 確保是完整 URL
                            if not img_url.startswith('http'):
                                img_url = f"https://online.carrefour.com.tw{img_url}"
                            
                            # 優先選擇 large 尺寸的圖片
                            if '/large/' in img_url:
                                logger.info(f"✓ 找到圖片（搜尋結果頁）：{img_url}")
                                return img_url
                            elif not img_url.endswith('.gif'):  # 避免 GIF 動圖
                                # 備選：如果不是 large，但符合格式，也使用
                                if img_url not in [None, '']:
                                    logger.info(f"✓ 找到圖片（搜尋結果頁-備選）：{img_url}")
                                    return img_url
                except Exception as e:
                    continue
            
            # 方法2：從頁面源碼中提取第一個商品圖片 URL
            try:
                page_content = await page.content()
                # 使用正則表達式查找圖片 URL（優先找 large 尺寸）
                large_pattern = r'(https://online\.carrefour\.com\.tw/on/demandware\.static[^"\s<>]+/large/[^"\s<>]+\.(?:jpg|png|jpeg))'
                large_matches = re.findall(large_pattern, page_content, re.IGNORECASE)
                if large_matches:
                    # 取第一個匹配的圖片 URL
                    img_url = large_matches[0]
                    logger.info(f"✓ 從源碼找到圖片（large）：{img_url}")
                    return img_url
                
                # 如果沒有 large，找其他尺寸
                general_pattern = r'(https://online\.carrefour\.com\.tw/on/demandware\.static[^"\s<>]+/[^"\s<>]+\.(?:jpg|png|jpeg))'
                general_matches = re.findall(general_pattern, page_content, re.IGNORECASE)
                if general_matches:
                    # 過濾掉非商品圖片（如 logo、banner 等）
                    for match in general_matches:
                        if '/large/' in match or '/medium/' in match or '/small/' in match:
                            if 'logo' not in match.lower() and 'banner' not in match.lower():
                                img_url = match
                                logger.info(f"✓ 從源碼找到圖片：{img_url}")
                                return img_url
            except Exception as e:
                logger.debug(f"從源碼提取失敗：{e}")
            
            logger.warning(f"無法找到商品圖片：{product_name}")
            return None
                
        except Exception as e:
            logger.warning(f"搜尋商品失敗：{e}")
            return None
            
    except Exception as e:
        logger.error(f"搜尋商品時發生錯誤：{e}")
        return None


async def update_product_image(product_id: str, product_name: str, new_image_url: str) -> bool:
    """
    更新商品的圖片 URL
    
    Args:
        product_id: 商品 ID
        product_name: 商品名稱
        new_image_url: 新的圖片 URL
        
    Returns:
        是否成功
    """
    try:
        result = supabase.table("products").update({
            "image_url": new_image_url
        }).eq("id", product_id).execute()
        
        if result.data:
            logger.info(f"✓ 更新成功：{product_name} -> {new_image_url[:60]}...")
            return True
        else:
            logger.warning(f"✗ 更新失敗：{product_name}")
            return False
    except Exception as e:
        logger.error(f"更新商品圖片失敗：{e}")
        return False


async def process_products(products: List[Dict[str, Any]], max_products: int = 20):
    """
    處理商品列表，更新圖片 URL
    
    Args:
        products: 商品列表
        max_products: 最多處理幾個商品
    """
    async with async_playwright() as p:
        # 啟動瀏覽器
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            updated_count = 0
            failed_count = 0
            
            for i, product in enumerate(products[:max_products], 1):
                product_id = product.get("id")
                product_name = product.get("name", "未知商品")
                current_image_url = product.get("image_url", "")
                
                print(f"\n[{i}/{min(len(products), max_products)}] 處理：{product_name}")
                print(f"  當前圖片：{current_image_url[:60]}...")
                
                # 搜尋商品圖片（傳入品牌資訊）
                brand = product.get("brand")
                new_image_url = await search_product_on_carrefour(page, product_name, brand)
                
                if new_image_url:
                    # 更新資料庫
                    if await update_product_image(product_id, product_name, new_image_url):
                        updated_count += 1
                    else:
                        failed_count += 1
                else:
                    failed_count += 1
                    print(f"  ✗ 無法找到對應的圖片")
                
                # 避免請求過快
                await asyncio.sleep(2)
            
            print("\n" + "=" * 60)
            print("處理完成！")
            print("=" * 60)
            print(f"✓ 成功更新：{updated_count} 個商品")
            print(f"✗ 更新失敗：{failed_count} 個商品")
            print(f"總計處理：{min(len(products), max_products)} 個商品")
            
        finally:
            await browser.close()


def main():
    """主函數"""
    print("=" * 60)
    print("更新 Unsplash 圖片為家樂福商品圖片")
    print("=" * 60)
    
    if not supabase:
        print("❌ Supabase 未初始化，請檢查環境變數")
        return
    
    # 1. 查詢所有使用 Unsplash 圖片的商品
    print("\n[1/2] 查詢使用 Unsplash 圖片的商品...")
    result = supabase.table("products").select("id, name, price, category, brand, image_url").like("image_url", "https://images.unsplash.com/%").execute()
    
    products = result.data if result.data else []
    print(f"✓ 找到 {len(products)} 個使用 Unsplash 圖片的商品")
    
    if not products:
        print("✓ 沒有需要更新的商品！")
        return
    
    # 顯示商品列表
    print("\n需要更新的商品列表：")
    for i, product in enumerate(products[:20], 1):
        print(f"  {i}. {product.get('name')} ({product.get('category')})")
    
    if len(products) > 20:
        print(f"  ... 還有 {len(products) - 20} 個商品")
    
    # 2. 處理商品
    print("\n[2/2] 開始搜尋並更新圖片...")
    print("這可能需要一些時間，請耐心等待...\n")
    
    # 詢問要處理多少個商品（預設處理前 10 個作為測試）
    import sys
    if len(sys.argv) > 1:
        try:
            max_count = int(sys.argv[1])
        except:
            max_count = 50
    else:
        max_count = 50  # 預設先處理 10 個
    
    print(f"將處理前 {max_count} 個商品（如需處理全部，請執行：python update_unsplash_images.py {len(products)}）\n")
    
    asyncio.run(process_products(products, max_products=max_count))


if __name__ == "__main__":
    main()


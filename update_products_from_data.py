"""
從商品資料更新 Supabase 資料庫
處理商品名稱、價格和圖片 URL 的更新或新增
"""

import re
from typing import List, Dict, Any, Optional, Tuple
from difflib import SequenceMatcher


def parse_product_data(raw_text: str) -> List[Dict[str, Any]]:
    """
    解析原始文字資料，提取商品名稱、價格和圖片 URL
    
    Args:
        raw_text: 原始文字資料
        
    Returns:
        商品資料列表，每個商品包含 name, price, image_url
    """
    products = []
    lines = raw_text.strip().split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 使用正則表達式提取商品名稱、價格和 URL
        # 格式：商品名稱\t價格\tSearch Result: ...\tURL
        parts = line.split('\t')
        
        if len(parts) >= 4:
            name = parts[0].strip()
            try:
                price = float(parts[1].strip())
            except (ValueError, IndexError):
                continue
            
            # 提取 URL（最後一個部分）
            image_url = parts[-1].strip()
            
            if name and price > 0 and image_url.startswith('http'):
                products.append({
                    'name': name,
                    'price': price,
                    'image_url': image_url
                })
    
    # 去除重複商品（基於商品名稱）
    seen = {}
    unique_products = []
    for product in products:
        # 標準化商品名稱用於去重
        normalized_name = re.sub(r'\s+', ' ', product['name'].strip())
        if normalized_name not in seen:
            seen[normalized_name] = product
            unique_products.append(product)
        else:
            # 如果價格不同，保留價格較低的（通常是促銷價）
            existing = seen[normalized_name]
            if product['price'] < existing['price']:
                seen[normalized_name] = product
    
    return list(seen.values())


def similarity_score(str1: str, str2: str) -> float:
    """
    計算兩個字串的相似度（0-1）
    
    Args:
        str1: 第一個字串
        str2: 第二個字串
        
    Returns:
        相似度分數（0-1）
    """
    # 標準化字串（移除空格、轉小寫）
    s1 = re.sub(r'\s+', '', str1.lower())
    s2 = re.sub(r'\s+', '', str2.lower())
    
    # 使用 SequenceMatcher 計算相似度
    return SequenceMatcher(None, s1, s2).ratio()


def find_similar_product(product_name: str, existing_products: List[Dict[str, Any]], threshold: float = 0.7) -> Optional[Dict[str, Any]]:
    """
    在現有商品中尋找相似的商品
    
    Args:
        product_name: 要搜尋的商品名稱
        existing_products: 現有商品列表
        threshold: 相似度閾值（預設 0.7）
        
    Returns:
        最相似的商品，如果沒有找到則返回 None
    """
    best_match = None
    best_score = 0.0
    
    for product in existing_products:
        score = similarity_score(product_name, product.get('name', ''))
        if score > best_score and score >= threshold:
            best_score = score
            best_match = product
    
    return best_match if best_match else None


def infer_category_and_brand(product_name: str) -> Tuple[Optional[str], Optional[str]]:
    """
    根據商品名稱推斷分類和品牌
    
    Args:
        product_name: 商品名稱
        
    Returns:
        (category, brand) 元組
    """
    name_lower = product_name.lower()
    
    # 分類推斷
    category = None
    if any(keyword in name_lower for keyword in ['可樂', 'cola', '沙士', '汽水', '雪碧', 'sprite']):
        category = '飲料'
    elif any(keyword in name_lower for keyword in ['水', 'water', '礦泉水', '純水', '竹炭水', '鹼性水']):
        category = '飲料'
    elif any(keyword in name_lower for keyword in ['水壺', '水杯', '隨行杯', '拉花杯', '沖泡壺', '濾壓壺', '手沖壺', '耐熱壺']):
        category = '生活用品'
    elif any(keyword in name_lower for keyword in ['西打', 'cider']):
        category = '飲料'
    else:
        category = '其他'
    
    # 品牌推斷
    brand = None
    brand_keywords = {
        '可口可樂': ['可口可樂', 'coca-cola', 'coca cola', 'coke'],
        '百事可樂': ['百事可樂', 'pepsi'],
        '雪碧': ['雪碧', 'sprite'],
        '家樂福': ['家樂福', 'carrefour'],
        '悅氏': ['悅氏', 'yes'],
        '象印': ['象印', 'zojirushi'],
        'AIDIO': ['aidio'],
        'YOI': ['yoi'],
        '蘋果西打': ['蘋果西打', 'apple cider'],
        '黑松': ['黑松', 'hey song']
    }
    
    for brand_name, keywords in brand_keywords.items():
        if any(keyword in name_lower for keyword in keywords):
            brand = brand_name
            break
    
    return category, brand


# 商品資料
raw_data = """家樂福純水  600ml	144	Search Result: 黑松沙士 600ml	https://online.carrefour.com.tw/on/demandware.static/-/Sites-carrefour-tw-m-inner/default/dwe73cbd65/images/large/1004006300124.png
百事可樂600ml	99	Search Result: 黑松沙士 600ml	https://online.carrefour.com.tw/on/demandware.static/-/Sites-carrefour-tw-m-inner/default/dw25b5be9f/images/large/1000002300104.jpg
好室喵悠閒時光廣口直飲水壺600ml(顏色隨機出貨)	109	Search Result: 黑松沙士 600ml	https://online.carrefour.com.tw/on/demandware.static/-/Sites-carrefour-tw-m-inner/default/dw7cd03318/images/large/3140991800101_NR_00.jpg
UD手提彈蓋水壺600ml-活力白	149	Search Result: 黑松沙士 600ml	https://online.carrefour.com.tw/on/demandware.static/-/Sites-carrefour-tw-m-inner/default/dwcf59bc2f/images/large/3140893000101_NR_00.jpg
可口可樂600ml	534	Search Result: 黑松沙士 600ml	https://online.carrefour.com.tw/on/demandware.static/-/Sites-carrefour-tw-m-inner/default/dw79f20153/images/large/1000001200124_NR_00.jpg
悅氏礦泉水600ml	218	Search Result: 黑松沙士 600ml	https://online.carrefour.com.tw/on/demandware.static/-/Sites-carrefour-tw-m-inner/default/dwd0433e2a/images/large/0081134_600ml.jpeg
AIDIO｜耐熱玻璃壺(600ml)	390	Search Result: 黑松沙士 600ml	https://online.carrefour.com.tw/on/demandware.static/-/Sites-carrefour-tw-m-inner/default/dw9720f740/images/scm/large/25143602/1000pot61.png
家樂福竹炭水600ml	54	Search Result: 黑松沙士 600ml	https://online.carrefour.com.tw/on/demandware.static/-/Sites-carrefour-tw-m-inner/default/dw8fbc1a2e/images/large/0238800_600ml.png
溫度不鏽鋼拉花杯 600ml｜JA-S-600-TM	760	Search Result: 黑松沙士 600ml	https://online.carrefour.com.tw/on/demandware.static/-/Sites-carrefour-tw-m-inner/default/dwaa66a006/images/scm/large/97145087/117101/溫度拉花杯600.png
可口可樂600ml	89	Search Result: 黑松沙士 600ml	https://online.carrefour.com.tw/on/demandware.static/-/Sites-carrefour-tw-m-inner/default/dw79f20153/images/large/1000001200124_NR_00.jpg
慢拾光濾壓式玻璃沖泡壺600ml	269	Search Result: 黑松沙士 600ml	https://online.carrefour.com.tw/on/demandware.static/-/Sites-carrefour-tw-m-inner/default/dw83ce9702/images/large/3111206000101_NR_00.jpg
胖胖黑濾壓壺-600ml	1059	Search Result: 黑松沙士 600ml	https://online.carrefour.com.tw/on/demandware.static/-/Sites-carrefour-tw-m-inner/default/dw1b32489d/images/large/3111205400101.jpg
雪碧600ml	89	Search Result: 黑松沙士 600ml	https://online.carrefour.com.tw/on/demandware.static/-/Sites-carrefour-tw-m-inner/default/dw13b95fe1/images/large/1000101500104_NR_02.jpg
雪碧600ml	534	Search Result: 黑松沙士 600ml	https://online.carrefour.com.tw/on/demandware.static/-/Sites-carrefour-tw-m-inner/default/dw13b95fe1/images/large/1000101500104_NR_02.jpg
寶馬牌 雅典耐熱壺 600ml｜TA-G-07-600	185	Search Result: 黑松沙士 600ml	https://online.carrefour.com.tw/on/demandware.static/-/Sites-carrefour-tw-m-inner/default/dwd38ad614/images/scm/large/97145087/雅典G07-600.png
百事可樂 - 600ml	589	Search Result: 黑松沙士 600ml	https://online.carrefour.com.tw/on/demandware.static/-/Sites-carrefour-tw-m-inner/default/dw25b5be9f/images/large/1000002300104.jpg
象印吊環式隨行杯600ml-霧灰藍色	988	Search Result: 黑松沙士 600ml	https://online.carrefour.com.tw/on/demandware.static/-/Sites-carrefour-tw-m-inner/default/dwa110c7ee/images/large/3141221200301_NR_00.jpg
象印吊環式隨行杯600ml-曜石黑色	988	Search Result: 黑松沙士 600ml	https://online.carrefour.com.tw/on/demandware.static/-/Sites-carrefour-tw-m-inner/default/dw1fb47373/images/large/3141221200201_NR_00.jpg
YOI 鹼性水 600ml	480	Search Result: 黑松沙士 600ml	https://online.carrefour.com.tw/on/demandware.static/-/Sites-carrefour-tw-m-inner/default/dwd72c8d7b/images/large/1004090800101.png
蘋果西打 600ml	42	Search Result: 黑松沙士 600ml	https://online.carrefour.com.tw/on/demandware.static/-/Sites-carrefour-tw-m-inner/default/dw84ec8437/images/large/1000294600101.png
可口可樂ZERO無糖零卡600ml	534	Search Result: 黑松沙士 600ml	https://online.carrefour.com.tw/on/demandware.static/-/Sites-carrefour-tw-m-inner/default/dwf679d8c1/images/large/1000000100124_NR_00.jpg
AIDIO｜鈦金木手沖壺(600ml)	1690	Search Result: 黑松沙士 600ml	https://online.carrefour.com.tw/on/demandware.static/-/Sites-carrefour-tw-m-inner/default/dwc7f75d7f/images/scm/large/25143602/1000DSC7501.png
日光生活可愛鹿角吸管水壺600ml-花色隨機出貨	239	Search Result: 黑松沙士 600ml	https://online.carrefour.com.tw/on/demandware.static/-/Sites-carrefour-tw-m-inner/default/dw7c380a9a/images/large/31409115001.jpg
手提彈蓋直飲水壺-600ml-4支	648	Search Result: 黑松沙士 600ml	https://online.carrefour.com.tw/on/demandware.static/-/Sites-carrefour-tw-m-inner/default/dwa0bdcb67/images/scm/large/91311236/173631/1000-21.png"""


if __name__ == "__main__":
    print("=" * 60)
    print("商品資料更新腳本")
    print("=" * 60)
    
    # 解析商品資料
    print("\n[1/4] 解析商品資料...")
    products = parse_product_data(raw_data)
    print(f"✓ 解析完成，共 {len(products)} 個唯一商品")
    
    # 顯示解析結果
    for i, product in enumerate(products, 1):
        print(f"  {i}. {product['name']} - ${product['price']}")
    
    print("\n[2/4] 準備更新資料...")
    print("請執行以下步驟：")
    print("1. 使用 MCP Supabase 工具查詢現有商品")
    print("2. 比對相似商品並更新 image_url")
    print("3. 新增不存在的商品")


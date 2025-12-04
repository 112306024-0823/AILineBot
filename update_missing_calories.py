"""
補齊商品卡路里資料
使用 Gemini 推斷或根據商品分類設定卡路里
"""

import os
import sys
import io
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import google.generativeai as genai

# 設定 UTF-8 編碼
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

load_dotenv()

from supabase_utils import supabase
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# 設定 Gemini API Key
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


def estimate_calories_with_gemini(product: Dict[str, Any]) -> Optional[int]:
    """
    使用 Gemini 根據商品資訊推斷卡路里
    
    Args:
        product: 商品資料字典
        
    Returns:
        推斷的卡路里數值，如果無法推斷則返回 None
    """
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        name = product.get("name", "")
        category = product.get("category", "")
        brand = product.get("brand", "")
        
        prompt = f"""
請根據以下商品資訊，推斷該商品的卡路里（大卡）數值。

商品名稱：{name}
分類：{category}
品牌：{brand if brand else "未知"}

請根據商品名稱和分類，推斷一個合理的卡路里數值。
規則：
1. 如果是生活用品、容器、器具等非食品，卡路里應為 0
2. 如果是飲料，根據類型推斷（例如：可樂約140大卡/330ml，水為0大卡）
3. 如果是食品，根據類型推斷合理的卡路里範圍
4. 如果無法確定，返回 null

只輸出一個數字（卡路里數值）或 "null"，不要其他文字。
如果商品是容器、器具、生活用品等非食品，輸出 0。
"""
        
        response = model.generate_content(prompt)
        result_text = response.text.strip()
        
        # 移除可能的標點符號和文字
        result_text = result_text.replace("大卡", "").replace("kcal", "").replace("卡路里", "").strip()
        
        # 嘗試解析數字
        try:
            calories = int(float(result_text))
            if calories < 0:
                return None
            if calories > 5000:  # 合理的上限
                return None
            return calories
        except (ValueError, TypeError):
            # 檢查是否為 null
            if "null" in result_text.lower() or "無法" in result_text or "不確定" in result_text:
                return None
            return None
            
    except Exception as e:
        logger.error(f"使用 Gemini 推斷卡路里失敗：{e}")
        return None


def estimate_calories_by_category(product: Dict[str, Any]) -> Optional[int]:
    """
    根據商品分類和名稱推斷卡路里（回退方案）
    
    Args:
        product: 商品資料字典
        
    Returns:
        推斷的卡路里數值
    """
    name = product.get("name", "").lower()
    category = product.get("category", "")
    
    # 生活用品通常沒有卡路里
    if category == "生活用品" or "水壺" in name or "壺" in name or "杯" in name or "容器" in name:
        return 0
    
    # 根據商品名稱推斷
    if "水" in name and ("純水" in name or "礦泉水" in name or "竹炭水" in name):
        return 0
    
    # 可樂類飲料（600ml 約為 330ml 的 1.8 倍）
    if "可樂" in name:
        if "600ml" in name or "600" in name:
            return 252  # 約 140 * 1.8
        elif "330ml" in name or "330" in name:
            return 140
        else:
            return 140  # 預設
    
    # 雪碧（類似可樂）
    if "雪碧" in name:
        if "600ml" in name or "600" in name:
            return 252
        elif "330ml" in name or "330" in name:
            return 140
        else:
            return 140
    
    # 百事可樂
    if "百事" in name:
        if "600ml" in name or "600" in name:
            return 252
        elif "330ml" in name or "330" in name:
            return 140
        else:
            return 140
    
    # 蘋果西打
    if "蘋果西打" in name or "西打" in name:
        if "600ml" in name or "600" in name:
            return 240
        else:
            return 130
    
    # 如果無法推斷，返回 None
    return None


def update_product_calories(product_id: str, calories: int) -> bool:
    """
    更新商品的卡路里資料
    
    Args:
        product_id: 商品 ID
        calories: 卡路里數值
        
    Returns:
        是否成功
    """
    try:
        result = supabase.table("products").update({
            "calories": calories
        }).eq("id", product_id).execute()
        
        if result.data:
            logger.info(f"✓ 更新成功：{product_id} -> {calories} 大卡")
            return True
        else:
            logger.warning(f"✗ 更新失敗：{product_id}")
            return False
    except Exception as e:
        logger.error(f"更新商品卡路里失敗：{e}")
        return False


def main():
    """主函數：補齊所有缺少卡路里資料的商品"""
    print("=" * 60)
    print("補齊商品卡路里資料")
    print("=" * 60)
    
    if not supabase:
        print("❌ Supabase 未初始化，請檢查環境變數")
        return
    
    # 1. 查詢所有沒有卡路里資料的商品
    print("\n[1/3] 查詢缺少卡路里資料的商品...")
    result = supabase.table("products").select("id, name, price, category, brand, calories").is_("calories", "null").execute()
    
    products = result.data if result.data else []
    print(f"✓ 找到 {len(products)} 個缺少卡路里資料的商品")
    
    if not products:
        print("✓ 所有商品都已有卡路里資料！")
        return
    
    # 2. 為每個商品推斷卡路里
    print("\n[2/3] 推斷卡路里資料...")
    updated_count = 0
    failed_count = 0
    
    for i, product in enumerate(products, 1):
        name = product.get("name", "未知商品")
        category = product.get("category", "")
        product_id = product.get("id")
        
        print(f"\n[{i}/{len(products)}] 處理：{name} ({category})")
        
        # 先嘗試使用分類推斷（快速且準確）
        calories = estimate_calories_by_category(product)
        
        # 如果分類推斷失敗，使用 Gemini
        if calories is None:
            print(f"  使用 Gemini 推斷...")
            calories = estimate_calories_with_gemini(product)
        
        if calories is not None:
            # 更新資料庫
            if update_product_calories(product_id, calories):
                updated_count += 1
                print(f"  ✓ 設定為 {calories} 大卡")
            else:
                failed_count += 1
                print(f"  ✗ 更新失敗")
        else:
            failed_count += 1
            print(f"  ✗ 無法推斷卡路里")
    
    # 3. 顯示結果
    print("\n" + "=" * 60)
    print("[3/3] 完成！")
    print("=" * 60)
    print(f"✓ 成功更新：{updated_count} 個商品")
    print(f"✗ 更新失敗：{failed_count} 個商品")
    print(f"總計處理：{len(products)} 個商品")


if __name__ == "__main__":
    main()


"""
Gemini 智能問答模組
使用 Gemini 分析用戶問題，查詢 Supabase 資料庫，並生成自然語言回答
"""
import os
import google.generativeai as genai
from typing import Optional, List, Dict, Any
from supabase_utils import (
    search_products_with_locations,
    search_products,
    search_products_by_location,
    get_product_by_id
)
import logging

logger = logging.getLogger(__name__)

# 設定 API Key
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))


def analyze_question(question: str) -> Dict[str, Any]:
    """
    使用 Gemini 分析用戶問題，提取搜尋意圖和參數
    
    Args:
        question: 用戶的問題
        
    Returns:
        包含搜尋意圖和參數的字典
    """
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        prompt = f"""
請分析以下用戶問題，並以 JSON 格式輸出分析結果。

用戶問題：{question}

請分析問題並輸出 JSON 格式：
{{
    "intent": "搜尋意圖（search_product, search_by_price, search_by_location, search_by_category, compare_products, get_product_info）",
    "search_term": "搜尋關鍵字（如果有的話）",
    "price_range": {{"min": 最小價格或null, "max": 最大價格或null}},
    "location": "位置資訊（如果有的話，例如：A區、B區）",
    "category": "商品分類（如果有的話）",
    "sort_by": "排序方式（price_asc, price_desc, name）或null",
    "limit": 回傳數量（預設10）
}}

範例：
問題：「最便宜的可樂是什麼？」
輸出：{{"intent": "search_by_price", "search_term": "可樂", "price_range": {{"min": null, "max": null}}, "location": null, "category": null, "sort_by": "price_asc", "limit": 5}}

問題：「A區有哪些商品？」
輸出：{{"intent": "search_by_location", "search_term": null, "price_range": {{"min": null, "max": null}}, "location": "A區", "category": null, "sort_by": null, "limit": 20}}

問題：「飲料類的商品有哪些？」
輸出：{{"intent": "search_by_category", "search_term": null, "price_range": {{"min": null, "max": null}}, "location": null, "category": "飲料", "sort_by": null, "limit": 20}}

只輸出 JSON，不要其他文字。
"""
        
        response = model.generate_content(prompt)
        result_text = response.text.strip()
        
        # 移除可能的 markdown 格式
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
            result_text = result_text[:-3]
        result_text = result_text.strip()
        
        import json
        try:
            analysis = json.loads(result_text)
            logger.info(f"問題分析結果：{analysis}")
            return analysis
        except json.JSONDecodeError as e:
            logger.warning(f"JSON 解析失敗，使用預設分析：{e}")
            logger.warning(f"原始回應：{result_text}")
            # 回退到簡單搜尋
            return {
                "intent": "search_product",
                "search_term": question,
                "price_range": {"min": None, "max": None},
                "location": None,
                "category": None,
                "sort_by": None,
                "limit": 10
            }
        
    except Exception as e:
        logger.error(f"分析問題失敗：{e}")
        # 回退到簡單搜尋
        return {
            "intent": "search_product",
            "search_term": question,
            "price_range": {"min": None, "max": None},
            "location": None,
            "category": None,
            "sort_by": None,
            "limit": 10
        }


def query_database(analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    根據分析結果查詢資料庫（使用高效的 Supabase 查詢）
    
    Args:
        analysis: 問題分析結果
        
    Returns:
        商品列表（包含 locations）
    """
    try:
        from supabase_utils import supabase, get_product_locations
        if not supabase:
            logger.error("Supabase 未初始化")
            return []
        
        intent = analysis.get("intent", "search_product")
        limit = analysis.get("limit", 10)
        search_term = analysis.get("search_term")
        price_min = analysis.get("price_range", {}).get("min")
        price_max = analysis.get("price_range", {}).get("max")
        location = analysis.get("location")
        category = analysis.get("category")
        sort_by = analysis.get("sort_by", "name")
        
        query = supabase.table("products").select("*")
        
        # 根據意圖建立查詢條件
        if intent == "search_by_location" and location:
            # 使用回退方案：透過 search_products_by_location
            return _query_database_fallback(analysis)
        
        elif intent == "search_by_category" and category:
            query = query.ilike("category", f"%{category}%")
            result = query.limit(limit * 2).execute()
            products = result.data if result.data else []
        
        elif search_term:
            # 使用 OR 條件搜尋名稱、品牌、描述
            # 注意：Supabase 客戶端不直接支援 OR，所以我們需要分別查詢後合併
            name_results = supabase.table("products").select("*").ilike("name", f"%{search_term}%").limit(limit * 2).execute()
            brand_results = supabase.table("products").select("*").ilike("brand", f"%{search_term}%").limit(limit * 2).execute()
            desc_results = supabase.table("products").select("*").ilike("description", f"%{search_term}%").limit(limit * 2).execute()
            
            # 合併結果並去重
            all_products = {}
            for result_set in [name_results, brand_results, desc_results]:
                if result_set.data:
                    for product in result_set.data:
                        all_products[product["id"]] = product
            
            products = list(all_products.values())
        else:
            # 一般查詢
            result = query.limit(limit * 2).execute()
            products = result.data if result.data else []
        
        # 價格範圍過濾
        if price_min is not None:
            products = [p for p in products if float(p.get("price", 0)) >= price_min]
        if price_max is not None:
            products = [p for p in products if float(p.get("price", 0)) <= price_max]
        
        # 排序
        if sort_by == "price_asc":
            products.sort(key=lambda x: float(x.get("price", 0)))
        elif sort_by == "price_desc":
            products.sort(key=lambda x: float(x.get("price", 0)), reverse=True)
        elif sort_by == "name":
            products.sort(key=lambda x: x.get("name", ""))
        
        # 限制數量
        products = products[:limit]
        
        # 為每個商品添加位置資訊
        for product in products:
            try:
                product["locations"] = get_product_locations(product["id"])
            except Exception as e:
                logger.error(f"獲取商品位置失敗：{e}")
                product["locations"] = []
        
        logger.info(f"查詢結果：找到 {len(products)} 個商品")
        return products
        
    except Exception as e:
        logger.error(f"查詢資料庫失敗：{e}", exc_info=True)
        return _query_database_fallback(analysis)


def _query_database_fallback(analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    回退方案：使用原有的函數查詢
    """
    try:
        intent = analysis.get("intent", "search_product")
        limit = analysis.get("limit", 10)
        
        if intent == "search_by_location":
            location = analysis.get("location")
            if location:
                results = search_products_by_location(area=location)
                products = []
                for item in results:
                    if "products" in item and item["products"]:
                        product = item["products"]
                        product["locations"] = [{
                            "area": item.get("area"),
                            "shelf": item.get("shelf"),
                            "floor": item.get("floor")
                        }]
                        products.append(product)
                return products[:limit]
        
        elif intent == "search_by_category":
            category = analysis.get("category")
            if category:
                products = search_products(category=category, limit=limit)
                # 為每個商品添加位置資訊
                for product in products:
                    from supabase_utils import get_product_locations
                    product["locations"] = get_product_locations(product["id"])
                return products
        
        elif intent == "search_by_price":
            search_term = analysis.get("search_term")
            price_min = analysis.get("price_range", {}).get("min")
            price_max = analysis.get("price_range", {}).get("max")
            
            # 先搜尋商品
            if search_term:
                products = search_products_with_locations(search_term, limit=50)
            else:
                products = search_products(limit=50)
                # 為每個商品添加位置資訊
                for product in products:
                    from supabase_utils import get_product_locations
                    product["locations"] = get_product_locations(product["id"])
            
            # 過濾價格範圍
            if price_min is not None:
                products = [p for p in products if float(p.get("price", 0)) >= price_min]
            if price_max is not None:
                products = [p for p in products if float(p.get("price", 0)) <= price_max]
            
            # 排序
            sort_by = analysis.get("sort_by")
            if sort_by == "price_asc":
                products.sort(key=lambda x: float(x.get("price", 0)))
            elif sort_by == "price_desc":
                products.sort(key=lambda x: float(x.get("price", 0)), reverse=True)
            elif sort_by == "name":
                products.sort(key=lambda x: x.get("name", ""))
            
            return products[:limit]
        
        else:
            # 預設搜尋
            search_term = analysis.get("search_term")
            if search_term:
                return search_products_with_locations(search_term, limit=limit)
            else:
                products = search_products(limit=limit)
                # 為每個商品添加位置資訊
                for product in products:
                    from supabase_utils import get_product_locations
                    product["locations"] = get_product_locations(product["id"])
                return products
                
    except Exception as e:
        logger.error(f"回退查詢失敗：{e}")
        return []


def generate_answer(question: str, products: List[Dict[str, Any]], analysis: Dict[str, Any]) -> str:
    """
    使用 Gemini 根據查詢結果生成自然語言回答
    
    Args:
        question: 原始問題
        products: 查詢到的商品列表
        analysis: 問題分析結果
        
    Returns:
        自然語言回答
    """
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        # 格式化商品資料
        products_text = ""
        if products:
            for i, product in enumerate(products[:10], 1):  # 最多顯示10個
                name = product.get("name", "未知商品")
                price = product.get("price", 0)
                category = product.get("category", "")
                brand = product.get("brand", "")
                locations = product.get("locations", [])
                
                products_text += f"\n【{i}】{name}\n"
                products_text += f"  價格：${float(price):.0f}\n"
                if category:
                    products_text += f"  分類：{category}\n"
                if brand:
                    products_text += f"  品牌：{brand}\n"
                if locations:
                    loc_info = locations[0] if locations else {}
                    area = loc_info.get("area", "")
                    shelf = loc_info.get("shelf", "")
                    if area:
                        products_text += f"  位置：{area}"
                        if shelf:
                            products_text += f" - {shelf}"
                        products_text += "\n"
                products_text += "\n"
        else:
            products_text = "（沒有找到相關商品）\n"
        
        prompt = f"""
用戶問了這個問題：{question}

根據資料庫查詢結果，請用自然、友善的繁體中文回答用戶的問題。

查詢到的商品：
{products_text}

請根據查詢結果回答問題，回答要：
1. 直接回答用戶的問題
2. 如果找到商品，列出主要商品資訊
3. 如果沒找到，友善地說明
4. 使用繁體中文
5. 語氣要親切自然
6. 不要重複問題

只輸出回答內容，不要其他說明。
"""
        
        response = model.generate_content(prompt)
        answer = response.text.strip()
        
        # 如果沒找到商品，提供更詳細的說明
        if not products:
            answer += "\n\n💡 提示：您可以嘗試：\n"
            answer += "• 使用不同的關鍵字搜尋\n"
            answer += "• 檢查拼字是否正確\n"
            answer += "• 使用更通用的商品名稱"
        
        return answer
        
    except Exception as e:
        logger.error(f"生成回答失敗：{e}")
        # 回退到簡單回答
        if products:
            return f"找到 {len(products)} 個相關商品。"
        else:
            return "抱歉，找不到相關商品。請嘗試其他關鍵字搜尋。"


def answer_question(question: str) -> str:
    """
    完整的問答流程：分析問題 → 查詢資料庫 → 生成回答
    
    Args:
        question: 用戶的問題
        
    Returns:
        自然語言回答
    """
    try:
        # 1. 分析問題
        analysis = analyze_question(question)
        
        # 2. 查詢資料庫
        products = query_database(analysis)
        
        # 3. 生成回答
        answer = generate_answer(question, products, analysis)
        
        return answer
        
    except Exception as e:
        logger.error(f"處理問題失敗：{e}", exc_info=True)
        return "抱歉，處理您的問題時發生錯誤。請稍後再試或嘗試其他問題。"


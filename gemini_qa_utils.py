"""
Gemini 智能問答模組
使用 Gemini 分析用戶問題，查詢 Supabase 資料庫，並生成自然語言回答
"""
import os
import google.generativeai as genai
from typing import Optional, List, Dict, Any, Tuple
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


def clean_markdown(text: str) -> str:
    """
    移除文字中的 Markdown 格式，讓 LINE 可以正常顯示
    
    Args:
        text: 包含 Markdown 格式的文字
        
    Returns:
        清理後的純文字
    """
    import re
    
    if not text:
        return text
    
    # 移除 Markdown 程式碼區塊 ```code```（優先處理，避免影響其他格式）
    text = re.sub(r'```[\s\S]*?```', '', text)
    
    # 移除 Markdown 粗體 **text** 或 __text__
    text = re.sub(r'\*\*(.*?)\*\*', r'\1', text)
    text = re.sub(r'__(.*?)__', r'\1', text)
    
    # 移除 Markdown 刪除線 ~~text~~
    text = re.sub(r'~~(.*?)~~', r'\1', text)
    
    # 移除 Markdown 行內程式碼 `code`（單個反引號）
    text = re.sub(r'`([^`]+)`', r'\1', text)
    
    # 移除 Markdown 連結 [text](url) 但保留文字
    text = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', text)
    
    # 移除 Markdown 斜體 *text* 或 _text_（放在最後，避免與粗體衝突）
    # 只處理單個 * 或 _，且前後不是相同符號的情況
    text = re.sub(r'(?<!\*)\*([^*]+?)\*(?!\*)', r'\1', text)
    text = re.sub(r'(?<!_)_([^_]+?)_(?!_)', r'\1', text)
    
    # 移除多餘的空白行（保留最多兩個連續換行）
    text = re.sub(r'\n{3,}', '\n\n', text)
    
    # 移除行首的 # 標題符號（如果有的話）
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    
    return text.strip()


def analyze_question(question: str, context: Optional[List[str]] = None) -> Dict[str, Any]:
    """
    使用 Gemini 分析用戶問題，提取搜尋意圖和參數（改進版）
    
    Args:
        question: 用戶的問題
        context: 對話上下文（之前的問題列表，可選）
        
    Returns:
        包含搜尋意圖和參數的字典
    """
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        # 構建上下文資訊
        context_text = ""
        if context and len(context) > 0:
            context_text = "\n\n對話上下文（之前的問題）：\n"
            for i, prev_q in enumerate(context[-3:], 1):  # 只保留最近3個問題
                context_text += f"{i}. {prev_q}\n"
        
        prompt = f"""
你是一個可愛的智能商品搜尋助手，負責分析用戶問題並提取搜尋參數。

用戶問題：{question}
{context_text}

請仔細分析問題，識別以下資訊並以 JSON 格式輸出：

{{
    "intent": "搜尋意圖（必填，選項：search_product, search_by_price, search_by_location, search_by_category, search_by_calories, compare_products, get_product_info, recommend_products, count_products, recipe_ingredients）",
    "search_term": "搜尋關鍵字（商品名稱、品牌等，如果有的話，否則為 null）",
    "price_range": {{"min": 最小價格（數字或null）, "max": 最大價格（數字或null）}},
    "calories_range": {{"min": 最小卡路里（數字或null）, "max": 最大卡路里（數字或null）}},
    "location": "位置資訊（例如：A區、B區、1樓、2樓，如果有的話，否則為 null）",
    "category": "商品分類（例如：飲料、食品、生活用品，如果有的話，否則為 null）",
    "sort_by": "排序方式（price_asc=價格由低到高, price_desc=價格由高到低, calories_asc=卡路里由低到高, calories_desc=卡路里由高到低, name=名稱排序，如果有的話，否則為 null）",
    "limit": 回傳數量（數字，預設10，最多50）,
    "comparison_products": ["要比較的商品名稱列表，如果意圖是 compare_products"]
}}

意圖說明：
- search_product: 一般商品搜尋
- search_by_price: 價格相關搜尋（最便宜、最貴、價格範圍）
- search_by_location: 位置相關搜尋
- search_by_category: 分類搜尋
- search_by_calories: 熱量/卡路里相關搜尋（低卡、高卡、卡路里範圍）
- compare_products: 比較多個商品
- get_product_info: 獲取特定商品詳細資訊
- recommend_products: 推薦商品
- count_products: 統計商品數量
- recipe_ingredients: 料理/食譜材料推薦（例如：想煮玉米濃湯、要做咖哩飯等）

範例：
問題：「最便宜的可樂是什麼？」
輸出：{{"intent": "search_by_price", "search_term": "可樂", "price_range": {{"min": null, "max": null}}, "location": null, "category": null, "sort_by": "price_asc", "limit": 5, "comparison_products": []}}

問題：「A區有哪些商品？」
輸出：{{"intent": "search_by_location", "search_term": null, "price_range": {{"min": null, "max": null}}, "location": "A區", "category": null, "sort_by": null, "limit": 20, "comparison_products": []}}

問題：「1樓有哪些商品？」
輸出：{{"intent": "search_by_location", "search_term": null, "price_range": {{"min": null, "max": null}}, "location": "1樓", "category": null, "sort_by": null, "limit": 20, "comparison_products": []}}

問題：「A區有什麼？」
輸出：{{"intent": "search_by_location", "search_term": null, "price_range": {{"min": null, "max": null}}, "location": "A區", "category": null, "sort_by": null, "limit": 20, "comparison_products": []}}

問題：「飲料類的商品有哪些？」
輸出：{{"intent": "search_by_category", "search_term": null, "price_range": {{"min": null, "max": null}}, "location": null, "category": "飲料", "sort_by": null, "limit": 20, "comparison_products": []}}

問題：「比較可樂和雪碧的價格」
輸出：{{"intent": "compare_products", "search_term": null, "price_range": {{"min": null, "max": null}}, "location": null, "category": null, "sort_by": null, "limit": 10, "comparison_products": ["可樂", "雪碧"]}}

問題：「推薦一些好喝的飲料」
輸出：{{"intent": "recommend_products", "search_term": null, "price_range": {{"min": null, "max": null}}, "location": null, "category": "飲料", "sort_by": null, "limit": 10, "comparison_products": []}}

問題：「100元以下的飲料有哪些？」
輸出：{{"intent": "search_by_price", "search_term": null, "price_range": {{"min": null, "max": 100}}, "calories_range": {{"min": null, "max": null}}, "location": null, "category": "飲料", "sort_by": "price_asc", "limit": 20, "comparison_products": []}}

問題：「低卡路里的飲料有哪些？」
輸出：{{"intent": "search_by_calories", "search_term": null, "price_range": {{"min": null, "max": null}}, "calories_range": {{"min": null, "max": 100}}, "location": null, "category": "飲料", "sort_by": "calories_asc", "limit": 20, "comparison_products": []}}

問題：「200大卡以下的零食有哪些？」
輸出：{{"intent": "search_by_calories", "search_term": null, "price_range": {{"min": null, "max": null}}, "calories_range": {{"min": null, "max": 200}}, "location": null, "category": "零食", "sort_by": "calories_asc", "limit": 20, "comparison_products": []}}

問題：「最健康的飲料是什麼？」（健康通常指低卡路里）
輸出：{{"intent": "search_by_calories", "search_term": null, "price_range": {{"min": null, "max": null}}, "calories_range": {{"min": null, "max": 50}}, "location": null, "category": "飲料", "sort_by": "calories_asc", "limit": 10, "comparison_products": []}}

問題：「晚餐想煮玉米濃湯」
輸出：{{"intent": "recipe_ingredients", "search_term": "玉米濃湯", "price_range": {{"min": null, "max": null}}, "calories_range": {{"min": null, "max": null}}, "location": null, "category": null, "sort_by": null, "limit": 20, "comparison_products": []}}

問題：「想做咖哩飯」
輸出：{{"intent": "recipe_ingredients", "search_term": "咖哩飯", "price_range": {{"min": null, "max": null}}, "calories_range": {{"min": null, "max": null}}, "location": null, "category": null, "sort_by": null, "limit": 20, "comparison_products": []}}

重要規則：
1. 仔細識別問題中的關鍵資訊（價格、位置、分類、商品名稱、卡路里/熱量）
2. 如果問題包含「最便宜」「最貴」，sort_by 應設為 price_asc 或 price_desc
3. 如果問題包含「低卡」「低熱量」「低卡路里」「健康」，intent 應設為 search_by_calories，calories_range.max 設為較小值（如100或50），sort_by 設為 calories_asc
4. 如果問題包含「高卡」「高熱量」，intent 應設為 search_by_calories，calories_range.min 設為較大值，sort_by 設為 calories_desc
5. 如果問題包含「卡路里」「熱量」「大卡」「kcal」，要識別數值範圍並填入 calories_range
6. 如果問題包含「推薦」「建議」，intent 應設為 recommend_products
7. 如果問題包含「比較」「對比」，intent 應設為 compare_products，並在 comparison_products 中列出要比較的商品
8. 如果問題包含「想煮」「想做」「要煮」「要做」「料理」「食譜」「材料」，intent 應設為 recipe_ingredients，search_term 設為料理名稱（例如：玉米濃湯、咖哩飯、義大利麵）
9. 只輸出 JSON，不要其他文字或說明
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
            # 確保所有必要欄位都存在
            if "comparison_products" not in analysis:
                analysis["comparison_products"] = []
            if "calories_range" not in analysis:
                analysis["calories_range"] = {"min": None, "max": None}
            if "limit" not in analysis or analysis["limit"] is None:
                analysis["limit"] = 10
            if analysis["limit"] > 50:
                analysis["limit"] = 50  # 限制最大數量
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
            "calories_range": {"min": None, "max": None},
                "location": None,
                "category": None,
                "sort_by": None,
            "limit": 10,
            "comparison_products": []
            }
        
    except Exception as e:
        logger.error(f"分析問題失敗：{e}")
        # 回退到簡單搜尋
        return {
            "intent": "search_product",
            "search_term": question,
            "price_range": {"min": None, "max": None},
            "calories_range": {"min": None, "max": None},
            "location": None,
            "category": None,
            "sort_by": None,
            "limit": 10,
            "comparison_products": []
        }


def query_database(analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    根據分析結果查詢資料庫（改進版 - 支援更多查詢類型）
    
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
        calories_min = analysis.get("calories_range", {}).get("min")
        calories_max = analysis.get("calories_range", {}).get("max")
        location = analysis.get("location")
        category = analysis.get("category")
        sort_by = analysis.get("sort_by", "name")
        comparison_products = analysis.get("comparison_products", [])
        
        # 處理料理材料查詢
        if intent == "recipe_ingredients":
            recipe_name = search_term or ""
            if recipe_name:
                # 使用 Gemini 生成材料清單
                ingredients = get_recipe_ingredients(recipe_name)
                if ingredients:
                    # 搜尋每個材料對應的商品
                    products = []
                    for ingredient in ingredients:
                        # 搜尋材料名稱
                        ingredient_products = search_products_with_locations(ingredient, limit=3)
                        if ingredient_products:
                            # 選擇第一個最相關的商品
                            products.append(ingredient_products[0])
                    
                    # 為每個商品添加位置資訊
                    for product in products:
                        try:
                            product["locations"] = get_product_locations(product["id"])
                        except Exception as e:
                            logger.error(f"獲取商品位置失敗：{e}")
                            product["locations"] = []
                    
                    # 儲存材料清單和料理名稱到商品資料中（用於後續生成回答）
                    for product in products:
                        product["_recipe_name"] = recipe_name
                        product["_ingredients"] = ingredients
                    
                    logger.info(f"料理材料查詢結果：找到 {len(products)} 個商品（料理：{recipe_name}）")
                    return products
            
            # 如果無法生成材料清單，回退到一般搜尋
            logger.warning(f"無法生成料理材料清單，回退到一般搜尋：{recipe_name}")
            if search_term:
                products = search_products_with_locations(search_term, limit=limit)
                for product in products:
                    try:
                        product["locations"] = get_product_locations(product["id"])
                    except Exception as e:
                        logger.error(f"獲取商品位置失敗：{e}")
                        product["locations"] = []
                return products
            else:
                return []
        
        # 處理比較商品查詢
        if intent == "compare_products" and comparison_products:
            products = []
            for comp_term in comparison_products:
                # 搜尋每個要比較的商品
                comp_results = search_products_with_locations(comp_term, limit=5)
                products.extend(comp_results)
            
            # 去重
            seen_ids = set()
            unique_products = []
            for product in products:
                if product["id"] not in seen_ids:
                    seen_ids.add(product["id"])
                    unique_products.append(product)
            
            products = unique_products[:limit]
            
            # 為每個商品添加位置資訊
            for product in products:
                try:
                    product["locations"] = get_product_locations(product["id"])
                except Exception as e:
                    logger.error(f"獲取商品位置失敗：{e}")
                    product["locations"] = []
            
            logger.info(f"比較查詢結果：找到 {len(products)} 個商品")
            return products
        
        # 處理推薦商品查詢
        if intent == "recommend_products":
            # 推薦邏輯：優先顯示有庫存、價格合理、有品牌標示的商品
            query = supabase.table("products").select("*")
            
            if category:
                query = query.ilike("category", f"%{category}%")
            
            if search_term:
                # 搜尋相關商品
                name_results = supabase.table("products").select("*").ilike("name", f"%{search_term}%").limit(limit * 3).execute()
                brand_results = supabase.table("products").select("*").ilike("brand", f"%{search_term}%").limit(limit * 3).execute()
                
                all_products = {}
                for result_set in [name_results, brand_results]:
                    if result_set.data:
                        for product in result_set.data:
                            all_products[product["id"]] = product
                products = list(all_products.values())
            else:
                result = query.limit(limit * 3).execute()
                products = result.data if result.data else []
            
            # 推薦排序：優先有庫存、有品牌、價格合理
            def recommend_score(p):
                score = 0
                if p.get("stock", 0) > 0:
                    score += 10
                if p.get("brand"):
                    score += 5
                if p.get("image_url"):
                    score += 3
                # 價格合理性（假設合理價格在 10-500 之間）
                price = float(p.get("price", 0))
                if 10 <= price <= 500:
                    score += 2
                return score
            
            products.sort(key=recommend_score, reverse=True)
            products = products[:limit]
            
            # 為每個商品添加位置資訊
            for product in products:
                try:
                    product["locations"] = get_product_locations(product["id"])
                except Exception as e:
                    logger.error(f"獲取商品位置失敗：{e}")
                    product["locations"] = []
            
            logger.info(f"推薦查詢結果：找到 {len(products)} 個商品")
            return products
        
        # 處理卡路里查詢
        if intent == "search_by_calories":
            query = supabase.table("products").select("*")
            
            # 只查詢有卡路里資料的商品
            query = query.not_.is_("calories", "null")
            
            if category:
                query = query.ilike("category", f"%{category}%")
            
            if search_term:
                # 搜尋相關商品
                name_results = supabase.table("products").select("*").ilike("name", f"%{search_term}%").not_.is_("calories", "null").limit(limit * 3).execute()
                brand_results = supabase.table("products").select("*").ilike("brand", f"%{search_term}%").not_.is_("calories", "null").limit(limit * 3).execute()
                
                all_products = {}
                for result_set in [name_results, brand_results]:
                    if result_set.data:
                        for product in result_set.data:
                            all_products[product["id"]] = product
                products = list(all_products.values())
            else:
                result = query.limit(limit * 3).execute()
                products = result.data if result.data else []
            
            # 卡路里範圍過濾
            if calories_min is not None:
                products = [p for p in products if p.get("calories") is not None and int(p.get("calories", 0)) >= calories_min]
            if calories_max is not None:
                products = [p for p in products if p.get("calories") is not None and int(p.get("calories", 0)) <= calories_max]
            
            # 排序
            if sort_by == "calories_asc":
                products.sort(key=lambda x: int(x.get("calories", 0)) if x.get("calories") is not None else 9999)
            elif sort_by == "calories_desc":
                products.sort(key=lambda x: int(x.get("calories", 0)) if x.get("calories") is not None else -1, reverse=True)
            elif sort_by == "price_asc":
                products.sort(key=lambda x: float(x.get("price", 0)))
            elif sort_by == "price_desc":
                products.sort(key=lambda x: float(x.get("price", 0)), reverse=True)
            
            products = products[:limit]
            
            # 為每個商品添加位置資訊
            for product in products:
                try:
                    product["locations"] = get_product_locations(product["id"])
                except Exception as e:
                    logger.error(f"獲取商品位置失敗：{e}")
                    product["locations"] = []
            
            logger.info(f"卡路里查詢結果：找到 {len(products)} 個商品")
            return products
        
        # 處理位置查詢
        if intent == "search_by_location" and location:
            return _query_location_products(analysis)
        
        # 處理分類查詢
        if intent == "search_by_category" and category:
            query = supabase.table("products").select("*").ilike("category", f"%{category}%")
            result = query.limit(limit * 2).execute()
            products = result.data if result.data else []
        
        # 處理一般搜尋
        elif search_term:
            # 使用 OR 條件搜尋名稱、品牌、描述
            name_results = supabase.table("products").select("*").ilike("name", f"%{search_term}%").limit(limit * 2).execute()
            brand_results = supabase.table("products").select("*").ilike("brand", f"%{search_term}%").limit(limit * 2).execute()
            desc_results = supabase.table("products").select("*").ilike("description", f"%{search_term}%").limit(limit * 2).execute()
            
            # 合併結果並去重（優先順序：名稱 > 品牌 > 描述）
            all_products = {}
            priority = {}  # 記錄優先順序
            
            for idx, result_set in enumerate([name_results, brand_results, desc_results]):
                if result_set.data:
                    for product in result_set.data:
                        product_id = product["id"]
                        if product_id not in all_products or priority.get(product_id, 99) > idx:
                            all_products[product_id] = product
                            priority[product_id] = idx
            
            products = list(all_products.values())
        else:
            # 一般查詢
            query = supabase.table("products").select("*")
            result = query.limit(limit * 2).execute()
            products = result.data if result.data else []
        
        # 價格範圍過濾
        if price_min is not None:
            products = [p for p in products if float(p.get("price", 0)) >= price_min]
        if price_max is not None:
            products = [p for p in products if float(p.get("price", 0)) <= price_max]
        
        # 卡路里範圍過濾（如果指定了卡路里條件）
        if calories_min is not None:
            products = [p for p in products if p.get("calories") is not None and int(p.get("calories", 0)) >= calories_min]
        if calories_max is not None:
            products = [p for p in products if p.get("calories") is not None and int(p.get("calories", 0)) <= calories_max]
        
        # 排序
        if sort_by == "price_asc":
            products.sort(key=lambda x: float(x.get("price", 0)))
        elif sort_by == "price_desc":
            products.sort(key=lambda x: float(x.get("price", 0)), reverse=True)
        elif sort_by == "calories_asc":
            products.sort(key=lambda x: int(x.get("calories", 0)) if x.get("calories") is not None else 9999)
        elif sort_by == "calories_desc":
            products.sort(key=lambda x: int(x.get("calories", 0)) if x.get("calories") is not None else -1, reverse=True)
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


def _query_location_products(analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    處理位置查詢（改進版 - 支援樓層和區域）
    """
    try:
        from supabase_utils import search_products_by_location, get_product_locations
        location = analysis.get("location")
        limit = analysis.get("limit", 20)
        
        if not location:
            return []
        
        # 識別 location 是樓層還是區域
        location_str = str(location).strip()
        
        # 檢查是否為樓層（包含「樓」字或數字開頭）
        floor = None
        area = None
        
        # 樓層識別：1樓、2樓、一樓、二樓等
        floor_keywords = {
            "1樓": 1, "一樓": 1, "1": 1,
            "2樓": 2, "二樓": 2, "2": 2,
            "3樓": 3, "三樓": 3, "3": 3,
            "4樓": 4, "四樓": 4, "4": 4,
        }
        
        # 檢查是否為樓層
        for keyword, floor_num in floor_keywords.items():
            if keyword in location_str:
                floor = floor_num
                break
        
        # 如果不是樓層，則視為區域
        if floor is None:
            # 處理區域格式：A區、A、a區等
            area = location_str
            # 移除「區」字（如果有的話），因為資料庫可能存的是 "A" 而不是 "A區"
            if area.endswith("區"):
                area = area[:-1]
            # 轉換為大寫
            area = area.upper()
        
        # 查詢商品
        results = search_products_by_location(area=area if area else None, floor=floor)
        
        products = []
        seen_product_ids = set()  # 用於去重
        
        for item in results:
            if "products" in item and item["products"]:
                product = item["products"]
                product_id = product.get("id")
                
                # 去重：同一個商品可能有多個位置
                if product_id and product_id not in seen_product_ids:
                    seen_product_ids.add(product_id)
                    # 獲取該商品的所有位置資訊
                    all_locations = get_product_locations(product_id)
                    product["locations"] = all_locations if all_locations else [{
                        "area": item.get("area"),
                        "shelf": item.get("shelf"),
                        "floor": item.get("floor")
                    }]
                    products.append(product)
        
        logger.info(f"位置查詢結果：找到 {len(products)} 個商品（位置：{location}, floor={floor}, area={area}）")
        return products[:limit]
        
    except Exception as e:
        logger.error(f"位置查詢失敗：{e}", exc_info=True)
        return []


def _query_database_fallback(analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    回退方案：使用原有的函數查詢
    """
    try:
        intent = analysis.get("intent", "search_product")
        limit = analysis.get("limit", 10)
        
        if intent == "search_by_location":
            # 使用改進的位置查詢函數
            return _query_location_products(analysis)
        
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
        logger.error(f"回退查詢失敗：{e}", exc_info=True)
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
        
        intent = analysis.get("intent", "search_product")
        
        # 處理料理材料推薦
        if intent == "recipe_ingredients" and products:
            recipe_name = products[0].get("_recipe_name", analysis.get("search_term", "這道料理"))
            ingredients = products[0].get("_ingredients", [])
            
            # 生成料理材料推薦回答
            answer = f"🍳 「{recipe_name}」所需材料：\n\n"
            
            if ingredients:
                answer += "📋 材料清單：\n"
                for i, ingredient in enumerate(ingredients, 1):
                    answer += f"{i}. {ingredient}\n"
                answer += "\n"
            
            if products:
                answer += f"🛒 找到 {len(products)} 個相關商品：\n\n"
                for i, product in enumerate(products[:10], 1):
                    name = product.get("name", "未知商品")
                    price = product.get("price", 0)
                    answer += f"【{i}】{name}\n"
                    answer += f"   💰 價格：${float(price):.0f}\n"
                    
                    locations = product.get("locations", [])
                    if locations:
                        loc = locations[0]
                        area = loc.get("area", "")
                        shelf = loc.get("shelf", "")
                        if area:
                            location_str = area
                            if shelf:
                                location_str += f" - {shelf}"
                            answer += f"   📍 位置：{location_str}\n"
                    answer += "\n"
                
                if len(products) > 10:
                    answer += f"💡 還有 {len(products) - 10} 個商品未顯示\n\n"
            
            answer += "💡 提示：您可以使用快速回復按鈕「❤️ 全部加入收藏」來一次收藏所有材料！"
            
            return answer
        
        # 格式化商品資料（改進版）
        products_text = ""
        if products:
            # 根據意圖決定顯示方式
            if intent == "compare_products":
                # 比較模式：並排顯示
                comparison_products = analysis.get("comparison_products", [])
                for product in products:
                    name = product.get("name", "未知商品")
                    price = product.get("price", 0)
                    category = product.get("category", "")
                    brand = product.get("brand", "")
                    
                    products_text += f"\n📦 {name}\n"
                    products_text += f"   💰 價格：${float(price):.0f}\n"
                    if brand:
                        products_text += f"   🏷️ 品牌：{brand}\n"
                    if category:
                        products_text += f"   📂 分類：{category}\n"
                    products_text += "\n"
            else:
                # 一般模式：列表顯示
                max_display = min(len(products), 10)
                for i, product in enumerate(products[:max_display], 1):
                    name = product.get("name", "未知商品")
                    price = product.get("price", 0)
                    category = product.get("category", "")
                    brand = product.get("brand", "")
                    calories = product.get("calories")
                    locations = product.get("locations", [])
                    stock = product.get("stock", 0)
                    
                    products_text += f"\n【{i}】{name}\n"
                    products_text += f"   💰 價格：${float(price):.0f}\n"
                    if calories is not None:
                        products_text += f"   🔥 熱量：{calories} 大卡\n"
                    if brand:
                        products_text += f"   🏷️ 品牌：{brand}\n"
                    if category:
                        products_text += f"   📂 分類：{category}\n"
                    if stock is not None:
                        stock_status = "✅ 有貨" if stock > 0 else "❌ 缺貨"
                        products_text += f"   📦 庫存：{stock_status}\n"
                    if locations:
                        loc_info = locations[0] if locations else {}
                        area = loc_info.get("area", "")
                        shelf = loc_info.get("shelf", "")
                        floor = loc_info.get("floor")
                        if area:
                            products_text += f"   📍 位置：{area}"
                            if shelf:
                                products_text += f" - {shelf}"
                            if floor:
                                products_text += f" ({floor}樓)"
                            products_text += "\n"
                    products_text += "\n"
                
                if len(products) > max_display:
                    products_text += f"\n（還有 {len(products) - max_display} 個商品未顯示）\n"
        else:
            products_text = "（沒有找到相關商品）\n"
        
        # 根據意圖生成不同的提示
        intent_guidance = ""
        if intent == "compare_products":
            intent_guidance = """
回答要求：
1. 直接比較這些商品的價格、品牌、分類等資訊
2. 如果有明顯差異，請指出
3. 語氣要客觀、專業
"""
        elif intent == "recommend_products":
            intent_guidance = """
回答要求：
1. 以推薦的口吻介紹商品
2. 可以根據價格、品牌、分類等因素給出推薦理由
3. 語氣要親切、有說服力
"""
        elif intent == "search_by_price":
            intent_guidance = """
回答要求：
1. 重點強調價格資訊
2. 如果有排序（最便宜/最貴），明確指出
3. 可以提及價格範圍或平均價格
"""
        elif intent == "search_by_calories":
            intent_guidance = """
回答要求：
1. 重點強調卡路里/熱量資訊
2. 如果有排序（最低卡/最高卡），明確指出
3. 可以提及卡路里範圍或平均卡路里
4. 可以簡單說明健康相關建議
"""
        elif intent == "count_products":
            intent_guidance = """
回答要求：
1. 明確說明找到的商品數量
2. 可以簡單分類統計
"""
        else:
            intent_guidance = """
回答要求：
1. 直接回答用戶的問題
2. 如果找到商品，簡潔地列出主要資訊
3. 如果沒找到，友善地說明並提供建議
"""
        
        prompt = f"""
你是小K，一個友善可愛的購物助手機器人，負責回答用戶關於商品的問題。

用戶問題：{question}
搜尋意圖：{intent}

查詢到的商品（共 {len(products)} 個）：
{products_text}

{intent_guidance}

其他要求：
1. 使用繁體中文
2. 語氣要親切、自然、友善
3. 不要重複問題本身
4. 回答要簡潔明瞭，避免冗長
5. 如果商品很多，可以總結重點
6. 使用適當的 emoji 讓回答更生動（但不要過多）

只輸出回答內容，不要其他說明或格式標記。
"""
        
        response = model.generate_content(prompt)
        answer = response.text.strip()
        
        # 移除 Markdown 格式（LINE 不支援 Markdown）
        answer = clean_markdown(answer)
        
        # 如果沒找到商品，提供更詳細的說明（改進版）
        if not products:
            search_term = analysis.get("search_term")
            category = analysis.get("category")
            
            suggestions = []
            if search_term:
                suggestions.append(f"• 嘗試使用「{search_term}」的相關關鍵字")
            if category:
                suggestions.append(f"• 瀏覽「{category}」分類的所有商品")
            else:
                suggestions.append("• 使用更通用的商品名稱或品牌名稱")
            suggestions.append("• 檢查拼字是否正確")
            suggestions.append("• 嘗試使用商品的部分名稱")
            
            answer += "\n".join(suggestions[:3])  # 只顯示前3個建議
            answer += "\n\n💬 如果還是找不到，可以直接告訴小K您要找什麼，小K會盡力幫您找找看！"
        
        # 如果找到商品但數量很多，添加提示
        elif len(products) > 10:
            answer += f"\n\n💡 找到 {len(products)} 個相關商品，以上顯示前 10 個。"
            if analysis.get("sort_by"):
                answer += "如需查看更多，請使用更精確的搜尋條件。"
        #answering done
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
        return "😔 小K 很抱歉，處理您的問題時發生錯誤。請稍後再試或嘗試其他問題，小K 會繼續努力為您服務！"


def answer_question_with_products(question: str) -> Tuple[str, List[Dict[str, Any]]]:
    """
    完整的問答流程：分析問題 → 查詢資料庫 → 生成回答（同時返回商品列表）
    
    Args:
        question: 用戶的問題
    
    Returns:
        (自然語言回答, 商品列表)
    """
    try:
        # 1. 分析問題
        analysis = analyze_question(question)
        
        # 2. 查詢資料庫
        products = query_database(analysis)
        
        # 3. 生成回答
        answer = generate_answer(question, products, analysis)
        
        return answer, products
        
    except Exception as e:
        logger.error(f"處理問題失敗：{e}", exc_info=True)
        return "😔 小K 很抱歉，處理您的問題時發生錯誤。請稍後再試或嘗試其他問題，小K 會繼續努力為您服務！", []


def get_recipe_ingredients(recipe_name: str) -> List[str]:
    """
    使用 Gemini 生成料理所需材料清單
    
    Args:
        recipe_name: 料理名稱（例如：玉米濃湯、咖哩飯）
    
    Returns:
        材料名稱列表
    """
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        
        prompt = f"""
你是一個專業的料理助手。請為「{recipe_name}」這道料理列出所有需要的食材材料。

請以 JSON 格式輸出，格式如下：
{{
    "ingredients": ["材料1", "材料2", "材料3", ...]
}}

要求：
1. 列出所有主要食材和調味料
2. 使用常見的食材名稱（例如：玉米、奶油、牛奶、鹽、胡椒，而不是「玉米粒」「無鹽奶油」等過於具體的名稱）
3. 排除廚房用具（例如：鍋子、湯匙）
4. 排除已經處理好的半成品（例如：如果列出「玉米罐頭」也可以，但優先列出「玉米」）
5. 材料名稱要簡潔，適合在超市搜尋
6. 只輸出 JSON，不要其他文字
7. 如果料理名稱不完整或字數過少，請使用更通用的料理名稱（例如：玉米濃湯、咖哩飯、義大利麵）

範例：
料理：玉米濃湯
輸出：{{"ingredients": ["玉米", "奶油", "牛奶", "麵粉", "鹽", "胡椒", "洋蔥"]}}

料理：咖哩飯
輸出：{{"ingredients": ["米", "咖哩塊", "馬鈴薯", "紅蘿蔔", "洋蔥", "肉", "水"]}}
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
            data = json.loads(result_text)
            ingredients = data.get("ingredients", [])
            logger.info(f"為「{recipe_name}」生成材料清單：{ingredients}")
            return ingredients
        except json.JSONDecodeError as e:
            logger.warning(f"JSON 解析失敗：{e}")
            logger.warning(f"原始回應：{result_text}")
            # 嘗試從文字中提取材料名稱
            # 簡單的回退方案：返回空列表
            return []
        
    except Exception as e:
        logger.error(f"生成料理材料清單失敗：{e}", exc_info=True)
        return []


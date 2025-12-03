"""
模式處理函數模組
負責處理不同模式的業務邏輯
"""
from linebot.models import TextSendMessage
from supabase_utils import (
    search_products_with_locations,
    get_store_area_by_name, get_store_areas_by_type, get_store_areas_by_floor,
    get_all_store_areas, search_store_areas
)
from gemini_qa_utils import answer_question_with_products
from formatters import (
    format_product_carousel, format_product_search_result,
    format_area_info, format_areas_list, format_areas_by_floor, format_all_areas
)
from mode_router import user_modes


def handle_product_search_mode(event, search_term: str, user_id: str, line_bot_api, app):
    """
    商品搜尋模式：處理文字搜尋
    
    Args:
        event: LINE 事件
        search_term: 搜尋關鍵字
        user_id: 用戶 ID
        line_bot_api: LINE Bot API 實例
        app: Flask app 實例
    """
    try:
        # 檢查是否為開啟搜尋模式的指令
        search_mode_keywords = ["搜尋商品", "商品搜尋", "搜尋", "找商品", "商品辨識"]
        is_search_mode_trigger = any(keyword == search_term.strip() for keyword in search_mode_keywords)
        
        if is_search_mode_trigger:
            # 用戶輸入「搜尋商品」等關鍵字，顯示提示訊息
            help_text = """🔍 商品搜尋模式已開啟

您可以透過以下方式搜尋商品：

📝 文字搜尋
直接輸入商品名稱，例如：
• 可樂
• 泡麵
• 鮮奶
• 品客洋芋片

📷 圖片辨識
上傳商品圖片，AI 會自動辨識並搜尋

💡 搜尋技巧
• 可以輸入品牌名稱（如：統一、義美）
• 可以輸入商品分類（如：飲料、零食）
• 可以輸入部分關鍵字（如：可樂、泡麵）

直接輸入商品名稱或上傳圖片即可開始搜尋！"""
            
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=help_text)
            )
            app.logger.info(f"[商品搜尋模式] 顯示使用提示給 {user_id}")
            return
        
        # 正常處理搜尋
        app.logger.info(f"[商品搜尋模式] 開始搜尋產品：{search_term}")
        products = search_products_with_locations(search_term, limit=10)
        app.logger.info(f"[商品搜尋模式] 搜尋結果：找到 {len(products)} 個產品")
        
        if products:
            # 嘗試使用 Carousel 顯示產品（圖片+文字）
            carousel_message = format_product_carousel(products, search_term, line_bot_api, app)
            if carousel_message:
                # 有圖片，使用 Carousel
                line_bot_api.reply_message(
                    event.reply_token,
                    carousel_message
                )
                app.logger.info(f"[商品搜尋模式] 成功回覆 Carousel 訊息給 {user_id}: {len(products)} 個產品")
            else:
                # 沒有圖片，回退到文字訊息
                reply_text = format_product_search_result(products, search_term)
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=reply_text)
                )
                app.logger.info(f"[商品搜尋模式] 成功回覆文字訊息給 {user_id}: {len(products)} 個產品")
        else:
            reply_text = f"🔍 找不到包含「{search_term}」的產品\n\n請嘗試其他關鍵字搜尋。"
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=reply_text)
            )
    except Exception as e:
        app.logger.error(f"[商品搜尋模式] 搜尋時發生錯誤: {str(e)}", exc_info=True)
        try:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=f"❌ 搜尋時發生錯誤，請稍後再試。")
            )
        except:
            pass


def handle_qa_mode(event, question: str, user_id: str, line_bot_api, app):
    """
    智能問答模式：處理 AI 問答
    
    Args:
        event: LINE 事件
        question: 用戶問題
        user_id: 用戶 ID
        line_bot_api: LINE Bot API 實例
        app: Flask app 實例
    """
    try:
        # 檢查是否為開啟智能問答模式的指令
        qa_mode_keywords = ["智能問答", "問答", "問你", "請問"]
        is_qa_mode_trigger = any(keyword == question.strip() for keyword in qa_mode_keywords)
        
        if is_qa_mode_trigger:
            # 用戶輸入「智能問答」等關鍵字，設定為智能問答模式並顯示提示訊息
            user_modes[user_id] = 'qa'
            
            help_text = """💬 智能問答模式已開啟

您可以問我任何關於商品的問題，例如：

🔍 價格相關
• 最便宜的可樂是什麼？
• 哪個品牌的泡麵最貴？

📍 位置相關
• 可樂在哪裡？
• 哪裡可以找到泡麵？

📊 比較與推薦
• 推薦的飲料有哪些？
• 比較可樂和雪碧的價格

💡 其他問題
• 有哪些商品在特價？
• 缺貨的商品有哪些？

💬 現在您可以直接輸入問題，我會以智能問答方式回答，如果有相關商品也會顯示商品卡片

輸入「退出」或「搜尋商品」可返回商品搜尋模式"""
            
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=help_text)
            )
            app.logger.info(f"[智能問答模式] 已切換到智能問答模式，顯示使用提示給 {user_id}")
            return
        
        # 正常處理問題
        app.logger.info(f"[智能問答模式] 處理問題：{question}")
        answer, products = answer_question_with_products(question)
        
        # 準備回覆訊息列表
        messages = []
        
        # 1. 先回覆文字回答
        messages.append(TextSendMessage(text=answer))
        
        # 2. 如果有相關商品，也顯示商品卡片
        if products:
            carousel_message = format_product_carousel(products, question, line_bot_api, app)
            if carousel_message:
                messages.append(carousel_message)
                app.logger.info(f"[智能問答模式] 同時顯示 {len(products)} 個相關商品")
        
        # 發送所有訊息
        line_bot_api.reply_message(
            event.reply_token,
            messages
        )
        app.logger.info(f"[智能問答模式] 成功回覆智能問答給 {user_id}（回答 + {len(products) if products else 0} 個商品）")
    except Exception as e:
        app.logger.error(f"[智能問答模式] 智能問答失敗：{str(e)}", exc_info=True)
        # 回退到商品搜尋模式
        app.logger.info(f"[智能問答模式] 回退到商品搜尋模式")
        handle_product_search_mode(event, question, user_id, line_bot_api, app)


def handle_help_mode(event, user_id: str, line_bot_api, app):
    """
    使用說明模式：顯示使用說明
    
    Args:
        event: LINE 事件
        user_id: 用戶 ID
        line_bot_api: LINE Bot API 實例
        app: Flask app 實例
    """
    help_text = """📖 使用說明

🔍 搜尋商品
直接輸入商品名稱即可搜尋，例如：
• 可樂
• 泡麵
• 鮮奶

📷 拍照辨識
上傳商品圖片，AI 會自動辨識並搜尋

💬 智能問答
問我問題，例如：
• 最便宜的可樂是什麼？
• 哪裡可以找到泡麵？
• 推薦的飲料有哪些？

📍 區域查詢
詢問區域位置，例如：
• 飲料區在哪裡？
• 零食專區在幾樓？
• 冷凍食品在哪裡？

❤️ 我的收藏
輸入「我的收藏」查看您收藏的商品

🎫 我的優惠券
輸入「我的優惠券」查看您的優惠券

💡 提示
• 可以透過圖文選單快速使用各項功能
• 搜尋結果可以點擊「收藏商品」加入收藏
• 有任何問題都可以問我！"""
    
    try:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=help_text)
        )
        app.logger.info(f"[使用說明] 成功回覆使用說明給 {user_id}")
    except Exception as e:
        app.logger.error(f"[使用說明] 回覆失敗：{str(e)}", exc_info=True)


def handle_area_query_mode(event, query_text: str, user_id: str, line_bot_api, app):
    """
    區域查詢模式：處理區域位置查詢
    
    Args:
        event: LINE 事件
        query_text: 查詢文字
        user_id: 用戶 ID
        line_bot_api: LINE Bot API 實例
        app: Flask app 實例
    """
    try:
        app.logger.info(f"[區域查詢模式] 查詢：{query_text}")
        
        # 嘗試從查詢文字中提取區域名稱
        area_names = ["飲料區", "零食專區", "泡麵專區", "調味料區", "乳製品專區", "罐頭專區", "冷凍食品專區", "冷凍肉品區", "米類專區", "冷藏飲料區"]
        found_area_name = None
        for area_name in area_names:
            if area_name in query_text:
                found_area_name = area_name
                break
        
        # 如果找到具體區域名稱，查詢該區域
        if found_area_name:
            area = get_store_area_by_name(found_area_name)
            if area:
                reply_text = format_area_info(area)
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=reply_text)
                )
                app.logger.info(f"[區域查詢模式] 成功回覆區域資訊：{found_area_name}")
                return
        
        # 嘗試搜尋區域類型
        area_types = {
            "飲料": "飲料",
            "零食": "零食",
            "泡麵": "食品",
            "食品": "食品",
            "調味料": "調味料",
            "乳製品": "乳製品",
            "罐頭": "罐頭",
            "冷凍": "冷凍食品"
        }
        
        found_area_type = None
        for keyword, area_type in area_types.items():
            if keyword in query_text:
                found_area_type = area_type
                break
        
        if found_area_type:
            areas = get_store_areas_by_type(found_area_type)
            if areas:
                reply_text = format_areas_list(areas, found_area_type)
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=reply_text)
                )
                app.logger.info(f"[區域查詢模式] 成功回覆區域類型：{found_area_type}")
                return
        
        # 嘗試搜尋樓層
        floor_keywords = ["1樓", "2樓", "3樓", "4樓", "一樓", "二樓", "三樓", "四樓"]
        floor_map = {"1樓": 1, "2樓": 2, "3樓": 3, "4樓": 4, "一樓": 1, "二樓": 2, "三樓": 3, "四樓": 4}
        found_floor = None
        for keyword, floor_num in floor_map.items():
            if keyword in query_text:
                found_floor = floor_num
                break
        
        if found_floor:
            areas = get_store_areas_by_floor(found_floor)
            if areas:
                reply_text = format_areas_by_floor(areas, found_floor)
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=reply_text)
                )
                app.logger.info(f"[區域查詢模式] 成功回覆樓層資訊：{found_floor}樓")
                return
        
        # 模糊搜尋
        areas = search_store_areas(query_text)
        if areas:
            reply_text = format_areas_list(areas, "相關區域")
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=reply_text)
            )
            app.logger.info(f"[區域查詢模式] 成功回覆模糊搜尋結果：{len(areas)} 個區域")
            return
        
        # 沒找到，顯示所有區域
        all_areas = get_all_store_areas()
        if all_areas:
            reply_text = format_all_areas(all_areas)
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=reply_text)
            )
            app.logger.info(f"[區域查詢模式] 顯示所有區域")
        else:
            reply_text = f"🔍 找不到相關區域資訊\n\n請嘗試詢問：\n• 飲料區在哪裡？\n• 零食專區在幾樓？\n• 1樓有哪些區域？"
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=reply_text)
            )
            
    except Exception as e:
        app.logger.error(f"[區域查詢模式] 處理失敗：{str(e)}", exc_info=True)
        try:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="❌ 查詢區域時發生錯誤，請稍後再試。")
            )
        except:
            pass


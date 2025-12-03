from flask import Flask, request, abort, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, ImageMessage,
    TemplateSendMessage, CarouselTemplate, CarouselColumn, ImageCarouselTemplate, ImageCarouselColumn,
    URIAction, MessageAction, PostbackAction, PostbackEvent,
    FlexSendMessage, BubbleContainer, BoxComponent, TextComponent, ImageComponent, ButtonComponent
)

import os
from dotenv import load_dotenv
from typing import Dict, Any, List

# 先載入環境變數，再 import 其他模組
load_dotenv()

from utils import check_environment_variables
from supabase_utils import (
    search_products_with_locations, add_to_favorites, remove_from_favorites, 
    get_user_favorites, is_favorited,
    get_store_area_by_name, get_store_areas_by_type, get_store_areas_by_floor,
    get_all_store_areas, search_store_areas
)
from vision_utils import extract_keywords_from_image_gemini
from gemini_qa_utils import answer_question, answer_question_with_products

# 初始化環境變數檢查
check_environment_variables()

# 初始化 Flask 和 LINE API
app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

# 用戶模式狀態管理（記憶體儲存）
# key: user_id, value: 'qa' (智能問答模式) 或 None (預設商品搜尋模式)
user_modes: Dict[str, str] = {}

@app.route("/", methods=['GET'])
def index():
    """根路由，返回服務狀態"""
    return jsonify({
        "status": "running",
        "service": "Enote LINE Bot",
        "version": "1.0.0"
    }), 200

@app.route("/callback", methods=['POST'])
def callback():
    """處理 LINE Webhook 請求"""
    signature = request.headers.get('X-Line-Signature', None)
    body = request.get_data(as_text=True)

    app.logger.info(f"收到 webhook 請求")
    if not signature:
        app.logger.error("缺少 X-Line-Signature")
        abort(400)

    try:
        handler.handle(body, signature)
        app.logger.info("Webhook 處理成功")
    except InvalidSignatureError:
        app.logger.error("簽名驗證失敗")
        abort(400)
    except Exception as e:
        app.logger.error(f"處理 webhook 時發生錯誤: {str(e)}", exc_info=True)
        abort(500)
    return 'OK'

# ==================== 模式判斷與路由 ====================

def determine_mode(message_text: str, user_id: str = None) -> str:
    """
    判斷訊息應該進入哪個模式
    
    Args:
        message_text: 用戶訊息
        user_id: 用戶 ID（用於檢查用戶當前模式）
    
    Returns:
        'qa': 智能問答模式
        'search': 商品搜尋模式
        'favorite': 收藏功能
        'help': 使用說明
        'area': 區域查詢模式
        'search': 預設為商品搜尋模式
    """
    message_text = message_text.strip()
    
    # 檢查用戶當前模式（如果用戶在智能問答模式中）
    if user_id and user_id in user_modes and user_modes[user_id] == 'qa':
        # 檢查是否要退出智能問答模式
        exit_keywords = ["退出", "返回", "結束", "取消", "搜尋商品", "商品搜尋"]
        if any(keyword in message_text for keyword in exit_keywords):
            # 清除模式狀態
            user_modes.pop(user_id, None)
            return 'search' if "搜尋" in message_text else 'help'
        # 否則保持在智能問答模式
        return 'qa'
    
    # 使用說明關鍵字
    help_keywords = ["使用說明", "說明", "幫助", "help", "如何使用", "功能"]
    if any(keyword in message_text for keyword in help_keywords):
        return 'help'
    
    # 收藏功能關鍵字（已在 handle_favorite_commands 中處理，這裡只是標記）
    favorite_keywords = ["我的收藏", "收藏列表", "收藏"]
    if message_text in favorite_keywords:
        return 'favorite'
    
    # 區域查詢關鍵字
    area_keywords = ["區在哪", "專區在哪", "在哪裡", "在哪", "位置", "樓層", "幾樓"]
    area_names = ["飲料區", "零食專區", "泡麵專區", "調味料區", "乳製品專區", "罐頭專區", "冷凍食品專區"]
    if any(keyword in message_text for keyword in area_keywords) or \
       any(area_name in message_text for area_name in area_names):
        return 'area'
    
    # 商品搜尋模式觸發詞（用於顯示提示）
    search_trigger_keywords = ["搜尋商品", "商品搜尋", "搜尋", "找商品"]
    if any(keyword == message_text for keyword in search_trigger_keywords):
        # 清除智能問答模式（如果有的話）
        if user_id:
            user_modes.pop(user_id, None)
        return 'search_help'  # 特殊標記，用於顯示搜尋提示
    
    # 明確的智能問答觸發詞
    qa_trigger_keywords = ["智能問答", "問答", "問你", "請問"]
    if any(keyword in message_text for keyword in qa_trigger_keywords):
        # 設定用戶為智能問答模式
        if user_id:
            user_modes[user_id] = 'qa'
        return 'qa'
    
    # 智能問答模式關鍵字（如果包含疑問詞，進入智能問答模式）
    qa_keywords = ["什麼", "哪些", "哪裡", "多少", "最", "比較", "推薦", "便宜", "貴", "價格", "位置", "區"]
    is_question = any(keyword in message_text for keyword in qa_keywords) or \
                 message_text.endswith("?") or message_text.endswith("？")
    
    if is_question:
        return 'qa'
    
    # 預設為商品搜尋模式
    return 'search'


# ==================== 模式處理函數 ====================

def handle_product_search_mode(event, search_term: str, user_id: str):
    """
    商品搜尋模式：處理文字搜尋
    
    Args:
        event: LINE 事件
        search_term: 搜尋關鍵字
        user_id: 用戶 ID
    """
    try:
        # 檢查是否為開啟搜尋模式的指令
        search_mode_keywords = ["搜尋商品", "商品搜尋", "搜尋", "找商品","商品辨識"]
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
            carousel_message = format_product_carousel(products, search_term)
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


def handle_qa_mode(event, question: str, user_id: str):
    """
    智能問答模式：處理 AI 問答
    
    Args:
        event: LINE 事件
        question: 用戶問題
        user_id: 用戶 ID
    """
    try:
        # 檢查是否為開啟智能問答模式的指令
        qa_mode_keywords = ["智能問答", "問答", "問你", "請問"]
        is_qa_mode_trigger = any(keyword == question.strip() for keyword in qa_mode_keywords)
        
        if is_qa_mode_trigger:
            # 用戶輸入「智能問答」等關鍵字，設定為智能問答模式並顯示提示訊息
            # 設定用戶為智能問答模式
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
            carousel_message = format_product_carousel(products, question)
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
        handle_product_search_mode(event, question, user_id)


def handle_help_mode(event, user_id: str):
    """
    使用說明模式：顯示使用說明
    
    Args:
        event: LINE 事件
        user_id: 用戶 ID
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


def handle_area_query_mode(event, query_text: str, user_id: str):
    """
    區域查詢模式：處理區域位置查詢
    
    Args:
        event: LINE 事件
        query_text: 查詢文字
        user_id: 用戶 ID
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


def format_area_info(area: Dict[str, Any]) -> str:
    """格式化單個區域資訊"""
    area_name = area.get("area_name", "未知區域")
    floor = area.get("floor", 0)
    area_code = area.get("area_code", "")
    description = area.get("description", "")
    notes = area.get("notes", "")
    
    text = f"📍 {area_name}\n\n"
    text += f"🏢 {floor}樓\n"
    if area_code:
        text += f"📍 {area_code}\n"
    if description:
        text += f"📝 {description}\n"
    if notes:
        text += f"💡 {notes}\n"
    
    return text


def format_areas_list(areas: List[Dict[str, Any]], area_type: str) -> str:
    """格式化區域列表"""
    if not areas:
        return f"找不到{area_type}相關區域"
    
    text = f"📍 {area_type}相關區域：\n\n"
    for area in areas:
        area_name = area.get("area_name", "未知區域")
        floor = area.get("floor", 0)
        area_code = area.get("area_code", "")
        text += f"• {area_name} - {floor}樓 {area_code}\n"
    
    return text


def format_areas_by_floor(areas: List[Dict[str, Any]], floor: int) -> str:
    """格式化樓層區域資訊"""
    if not areas:
        return f"{floor}樓沒有區域資訊"
    
    text = f"🏢 {floor}樓區域資訊：\n\n"
    for area in areas:
        area_name = area.get("area_name", "未知區域")
        area_code = area.get("area_code", "")
        description = area.get("description", "")
        text += f"📍 {area_name} ({area_code})\n"
        if description:
            text += f"   {description}\n"
        text += "\n"
    
    return text


def format_all_areas(areas: List[Dict[str, Any]]) -> str:
    """格式化所有區域資訊（按樓層分組）"""
    if not areas:
        return "目前沒有區域資訊"
    
    # 按樓層分組
    floors = {}
    for area in areas:
        floor = area.get("floor", 0)
        if floor not in floors:
            floors[floor] = []
        floors[floor].append(area)
    
    text = "📍 賣場區域資訊：\n\n"
    for floor in sorted(floors.keys()):
        text += f"🏢 {floor}樓：\n"
        for area in floors[floor]:
            area_name = area.get("area_name", "未知區域")
            area_code = area.get("area_code", "")
            text += f"  • {area_name} ({area_code})\n"
        text += "\n"
    
    text += "💡 提示：可以詢問「飲料區在哪裡？」或「1樓有哪些區域？」"
    
    return text


# ==================== 訊息處理器 ====================

# 處理文字訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    """處理文字訊息 - 根據模式路由到對應處理函數"""
    try:
        user_id = getattr(event.source, 'user_id', None)
        if not user_id:
            app.logger.warning("無法獲取用戶 ID")
            return

        message_text = event.message.text.strip()
        app.logger.info(f"收到文字訊息 from {user_id}: {message_text}")
        
        # 檢查 Supabase 是否已初始化
        from supabase_utils import supabase
        if not supabase:
            app.logger.warning("Supabase 未初始化")
            reply_text = (
                "⚠️ Supabase 資料庫未連接\n\n"
                "請檢查環境變數設定：\n"
                "- SUPABASE_URL\n"
                "- SUPABASE_KEY\n\n"
                "設定完成後請重啟應用程式。"
            )
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=reply_text)
            )
            return
        
        # 先檢查是否為收藏相關指令
        if handle_favorite_commands(event, message_text, user_id):
            return  # 已處理收藏指令，直接返回
        
        # 判斷模式（傳入 user_id 以檢查用戶當前模式）
        mode = determine_mode(message_text, user_id)
        app.logger.info(f"判斷模式：{mode} (用戶當前模式：{user_modes.get(user_id, '無')})")
        
        # 根據模式路由到對應處理函數
        if mode == 'help':
            handle_help_mode(event, user_id)
        elif mode == 'area':
            handle_area_query_mode(event, message_text, user_id)
        elif mode == 'qa':
            handle_qa_mode(event, message_text, user_id)
        elif mode == 'search_help':
            # 搜尋模式提示（會由 handle_product_search_mode 內部處理）
            handle_product_search_mode(event, message_text, user_id)
        else:  # 'search' 或其他，預設為商品搜尋模式
            handle_product_search_mode(event, message_text, user_id)
            
    except Exception as e:
        app.logger.error(f"處理文字訊息時發生錯誤: {str(e)}", exc_info=True)


def format_product_search_result(products: list, search_term: str) -> str:
    """
    格式化產品搜尋結果轉為 LINE 訊息
    
    Args:
        products: 產品列表（包含位置資訊）
        search_term: 搜尋關鍵字
    
    Returns:
        格式化後的字串
    """
    if not products:
        return f"🔍 找不到包含「{search_term}」的產品"
    
    result_text = f"🔍 找到 {len(products)} 個包含「{search_term}」的產品：\n\n"
    result_text += "=" * 30 + "\n\n"
    
    for idx, product in enumerate(products, 1):
        result_text += f"【{idx}】{product.get('name', '未知產品')}\n"
        result_text += f"💰 價格：${float(product.get('price', 0)):.0f}\n"
        
        # 存貨狀態
        stock = product.get('stock', 0)
        if stock is None:
            stock = 0
        else:
            try:
                stock = int(stock)
            except (ValueError, TypeError):
                stock = 0
        
        if stock > 0:
            result_text += f"✅ 有存貨\n" # 存貨：{stock} 個（有貨）
        else:
            result_text += f"❌ 【缺貨中】\n"
        
        if product.get('brand'):
            result_text += f"🏷️ 品牌：{product['brand']}\n"
        
        if product.get('category'):
            result_text += f"📦 分類：{product['category']}\n"
        
        # 位置資訊
        locations = product.get('locations', [])
        if locations:
            result_text += f"📍 位置資訊：\n"
            for loc in locations:
                area = loc.get('area', '未知區域')
                shelf = loc.get('shelf', '')
                floor = loc.get('floor', '')
                location_str = f"   • {area}"
                if shelf:
                    location_str += f" - {shelf}"
                if floor:
                    location_str += f" (樓層 {floor})"
                result_text += location_str + "\n"
        else:
            result_text += "📍 位置：暫無位置資訊\n"
        
        if product.get('description'):
            desc = product['description'][:50]  # 限制描述長度
            if len(product['description']) > 50:
                desc += "..."
            result_text += f"📝 {desc}\n"
        
        result_text += "\n" + "-" * 30 + "\n\n"
    
    return result_text


# 預設圖片 URL（如果商品沒有圖片時使用）
DEFAULT_PRODUCT_IMAGE_URL = "https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=300&h=300&fit=crop"

def format_product_carousel(products: list, search_term: str):
    """
    格式化產品搜尋結果為 LINE Carousel Template（圖片+文字）
    
    Args:
        products: 產品列表（包含位置資訊和 image_url）
        search_term: 搜尋關鍵字
    
    Returns:
        TemplateSendMessage 或 None（如果沒有商品）
    """
    if not products:
        return None
    
    # 處理所有產品（最多 10 個，LINE Carousel 限制）
    products_to_show = []
    for product in products[:10]:  # LINE Carousel 最多 10 個項目
        image_url = product.get('image_url')
        # 檢查圖片 URL 是否有效（必須是 HTTPS）
        if image_url and image_url.startswith('https://') and not image_url.startswith('https://example.com'):
            # 使用商品自己的圖片
            product['display_image_url'] = image_url
        else:
            # 使用預設圖片
            product['display_image_url'] = DEFAULT_PRODUCT_IMAGE_URL
            app.logger.info(f"商品 {product.get('name')} 沒有有效圖片，使用預設圖片")
        
        products_to_show.append(product)
    
    # 如果沒有商品，返回 None
    if not products_to_show:
        app.logger.info("沒有商品可顯示")
        return None
    
    # 建立 Carousel Columns
    columns = []
    for product in products_to_show:
        name = product.get('name', '未知產品')
        price = float(product.get('price', 0))
        stock = product.get('stock', 0)
        
        # 處理存貨狀態
        if stock is None:
            stock = 0
        else:
            try:
                stock = int(stock)
            except (ValueError, TypeError):
                stock = 0
        
        # 建立文字內容
        text = f"💰 ${price:.0f}\n"
        if stock > 0:
            text += f"✅ 有存貨（{stock} 個）\n"
        else:
            text += "❌ 【缺貨中】\n"
        
        if product.get('brand'):
            text += f"🏷️ {product['brand']}\n"
        
        # 位置資訊（只顯示第一個位置）
        locations = product.get('locations', [])
        if locations:
            loc = locations[0]
            area = loc.get('area', '未知區域')
            shelf = loc.get('shelf', '')
            location_str = area
            if shelf:
                location_str += f" - {shelf}"
            text += f"📍 {location_str}\n"
        
        # 描述（限制長度）
        if product.get('description'):
            desc = product['description'][:50]
            if len(product['description']) > 50:
                desc += "..."
            text += f"\n📝 {desc}"
        
        # 建立 CarouselColumn
        # LINE Carousel 限制：title 最多 40 字，text 最多 120 字
        title = name[:40] if len(name) <= 40 else name[:37] + "..."
        text = text[:120] if len(text) <= 120 else text[:117] + "..."
        
        # 建立按鈕動作
        product_id = product.get('id')
        actions = [
            MessageAction(
                label='查看詳情',
                text=f"詳情：{name}"
            )
        ]
        
        # 添加收藏按鈕（如果有 product_id）
        # 在搜尋結果中，只做收藏操作，不做取消收藏
        if product_id:
            actions.append(
                PostbackAction(
                    label='收藏商品',
                    data=f"action=favorite&product_id={product_id}&source=search"
                )
            )
        
        column = CarouselColumn(
            thumbnail_image_url=product.get('display_image_url', DEFAULT_PRODUCT_IMAGE_URL),
            title=title,
            text=text,
            actions=actions
        )
        columns.append(column)
    
    if not columns:
        return None
    
    # 建立 Carousel Template
    carousel_template = CarouselTemplate(columns=columns)
    
    # 建立 TemplateSendMessage
    template_message = TemplateSendMessage(
        alt_text=f"找到 {len(columns)} 個包含「{search_term}」的產品",
        template=carousel_template
    )
    
    return template_message


# 處理圖片訊息（商品搜尋模式）
@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    """
    處理圖片訊息 - 商品搜尋模式（圖片辨識）
    圖片訊息統一進入商品搜尋模式
    """
    try:
        user_id = getattr(event.source, 'user_id', None)
        if not user_id:
            app.logger.warning("無法獲取用戶 ID")
            return
        
        app.logger.info(f"[商品搜尋模式-圖片] 收到圖片訊息 from {user_id}")
        
        message_content = line_bot_api.get_message_content(event.message.id)
        image_bytes = b"".join(message_content.iter_content())

        # Gemini 分析圖片
        keywords, full_text = extract_keywords_from_image_gemini(image_bytes)
        app.logger.info(f"[商品搜尋模式-圖片] Gemini 回傳：{full_text}")
        app.logger.info(f"[商品搜尋模式-圖片] 關鍵字：{keywords}")

        # ----------- 第一階段：逐關鍵字搜尋，找到第一個命中就回傳 -----------
        products = []
        hit_keyword = None

        for k in keywords:
            result = search_products_with_locations(k, limit=10)
            if result:
                products = result
                hit_keyword = k
                break

        # 如果第一階段有找到 → 用原本邏輯回覆
        if products:
            carousel = format_product_carousel(products, hit_keyword)
            if carousel:
                line_bot_api.reply_message(event.reply_token, carousel)
                app.logger.info(f"[商品搜尋模式-圖片] 成功回覆 Carousel：{len(products)} 個產品")
            else:
                reply_text = format_product_search_result(products, hit_keyword)
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
                app.logger.info(f"[商品搜尋模式-圖片] 成功回覆文字訊息：{len(products)} 個產品")
            return  

        # ----------- 第二階段：完全沒找到 → 用所有 keywords 合併搜尋 -----------
        merged_products = {}
        
        for k in keywords:
            result = search_products_with_locations(k, limit=10)
            for p in result:
                merged_products[p["id"]] = p  # 用 id 去重複

        merged_products_list = list(merged_products.values())

        if merged_products_list:
            # 回傳合併搜尋結果
            carousel = format_product_carousel(merged_products_list, " ".join(keywords))
            if carousel:
                line_bot_api.reply_message(event.reply_token, carousel)
                app.logger.info(f"[商品搜尋模式-圖片] 成功回覆合併搜尋結果：{len(merged_products_list)} 個產品")
            else:
                reply_text = format_product_search_result(merged_products_list, " ".join(keywords))
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
        else:
            # 完全找不到 → 回傳 Gemini 辨識內容
            reply_text = f"📷 圖片辨識結果：\n\n{full_text}\n\n🔍 未找到相符商品，請嘗試其他關鍵字搜尋。"
            line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
            app.logger.info(f"[商品搜尋模式-圖片] 未找到商品，回傳辨識內容")

    except Exception as e:
        app.logger.error(f"[商品搜尋模式-圖片] 處理圖片時發生錯誤: {str(e)}", exc_info=True)
        try:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="❌ 處理圖片時發生錯誤，請稍後再試。")
            )
        except:
            pass


# 處理 Postback 事件（收藏商品）
@handler.add(PostbackEvent)
def handle_postback(event):
    """處理 Postback 事件 - 收藏商品功能"""
    try:
        user_id = getattr(event.source, 'user_id', None)
        if not user_id:
            app.logger.warning("無法獲取用戶 ID")
            return
        
        postback_data = event.postback.data
        app.logger.info(f"收到 Postback 事件 from {user_id}: {postback_data}")
        
        # 解析 Postback 資料
        # 格式：action=favorite&product_id=xxx
        data_parts = postback_data.split('&')
        action_data = {}
        for part in data_parts:
            if '=' in part:
                key, value = part.split('=', 1)
                action_data[key] = value
        
        action = action_data.get('action')
        product_id = action_data.get('product_id')
        source = action_data.get('source', 'search')  # 預設為 search
        
        if action == 'favorite' and product_id:
            # 檢查是否已收藏
            already_favorited = is_favorited(user_id, product_id)
            
            if source == 'search':
                # 在搜尋結果中：只做收藏操作，不做取消收藏
                if already_favorited:
                    reply_text = "❤️ 此商品已在您的收藏中\n\n請到「我的收藏」查看或取消收藏"
                else:
                    # 新增收藏
                    success = add_to_favorites(user_id, product_id)
                    if success:
                        reply_text = "❤️ 已加入收藏"
                    else:
                        reply_text = "❌ 收藏失敗，請稍後再試"
            elif source == 'favorites':
                # 在收藏列表中：可以做取消收藏操作
                if already_favorited:
                    # 取消收藏
                    success = remove_from_favorites(user_id, product_id)
                    if success:
                        reply_text = "✅ 已取消收藏"
                    else:
                        reply_text = "❌ 取消收藏失敗，請稍後再試"
                else:
                    # 理論上不會發生，但以防萬一
                    reply_text = "❌ 此商品不在您的收藏中"
            else:
                # 未知來源，預設行為（只做收藏）
                if already_favorited:
                    reply_text = "❤️ 此商品已在您的收藏中"
                else:
                    success = add_to_favorites(user_id, product_id)
                    if success:
                        reply_text = "❤️ 已加入收藏"
                    else:
                        reply_text = "❌ 收藏失敗，請稍後再試"
            
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=reply_text)
            )
            app.logger.info(f"處理收藏操作完成：{user_id} - {product_id} - {action} - source:{source}")
        else:
            app.logger.warning(f"未知的 Postback 動作：{postback_data}")
            
    except Exception as e:
        app.logger.error(f"處理 Postback 事件時發生錯誤: {str(e)}", exc_info=True)
        try:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="❌ 處理收藏時發生錯誤，請稍後再試")
            )
        except:
            pass


# 處理文字訊息：收藏相關指令
def handle_favorite_commands(event, message_text: str, user_id: str):
    """處理收藏相關的文字指令"""
    try:
        # 處理「我的收藏」指令
        if message_text in ["我的收藏", "收藏列表", "收藏"]:
            favorites = get_user_favorites(user_id, limit=12)  # Flex Message 最多 12 個
            
            if not favorites:
                reply_text = "📭 您還沒有收藏任何商品\n\n搜尋商品後，點擊「收藏商品」按鈕即可收藏！"
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=reply_text)
                )
            else:
                # 優先使用 Flex Message（更美觀的卡片式呈現）
                flex_messages = format_favorites_flex(favorites)
                if flex_messages:
                    # Flex Message 返回的是列表，需要逐個發送
                    # 但 LINE API 的 reply_message 可以接受列表
                    line_bot_api.reply_message(
                        event.reply_token,
                        flex_messages
                    )
                    app.logger.info(f"成功回覆 Flex Message 收藏列表給 {user_id}: {len(favorites)} 個商品")
                else:
                    # 回退到 Carousel
                    carousel_message = format_favorites_carousel(favorites)
                    if carousel_message:
                        line_bot_api.reply_message(
                            event.reply_token,
                            carousel_message
                        )
                        app.logger.info(f"成功回覆 Carousel 收藏列表給 {user_id}: {len(favorites)} 個商品")
                    else:
                        # 最後回退到文字訊息
                        reply_text = f"❤️ 我的收藏（共 {len(favorites)} 個商品）：\n\n"
                        for idx, product in enumerate(favorites[:10], 1):
                            reply_text += f"【{idx}】{product.get('name', '未知產品')}\n"
                            reply_text += f"💰 ${float(product.get('price', 0)):.0f}\n\n"
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextSendMessage(text=reply_text)
                        )
            return True
        
        return False
    except Exception as e:
        app.logger.error(f"處理收藏指令時發生錯誤: {str(e)}", exc_info=True)
        return False


def format_favorites_carousel(favorites: list):
    """
    格式化收藏列表為 LINE Carousel Template
    
    Args:
        favorites: 收藏的商品列表（包含位置資訊和 image_url）
    
    Returns:
        TemplateSendMessage 或 None（如果沒有商品）
    """
    if not favorites:
        return None
    
    # 處理所有收藏商品（最多 10 個，LINE Carousel 限制）
    products_to_show = []
    for product in favorites[:10]:
        image_url = product.get('image_url')
        # 檢查圖片 URL 是否有效（必須是 HTTPS）
        if image_url and image_url.startswith('https://') and not image_url.startswith('https://example.com'):
            product['display_image_url'] = image_url
        else:
            product['display_image_url'] = DEFAULT_PRODUCT_IMAGE_URL
        
        products_to_show.append(product)
    
    if not products_to_show:
        return None
    
    # 建立 Carousel Columns
    columns = []
    for product in products_to_show:
        name = product.get('name', '未知產品')
        price = float(product.get('price', 0))
        stock = product.get('stock', 0)
        product_id = product.get('id')
        
        # 處理存貨狀態
        if stock is None:
            stock = 0
        else:
            try:
                stock = int(stock)
            except (ValueError, TypeError):
                stock = 0
        
        # 建立文字內容
        text = f"💰 ${price:.0f}\n"
        if stock > 0:
            text += f"✅ 有存貨（{stock} 個）\n"
        else:
            text += "❌ 【缺貨中】\n"
        
        if product.get('brand'):
            text += f"🏷️ {product['brand']}\n"
        
        # 位置資訊（只顯示第一個位置）
        locations = product.get('locations', [])
        if locations:
            loc = locations[0]
            area = loc.get('area', '未知區域')
            shelf = loc.get('shelf', '')
            location_str = area
            if shelf:
                location_str += f" - {shelf}"
            text += f"📍 {location_str}\n"
        
        # 描述（限制長度）
        if product.get('description'):
            desc = product['description'][:40]
            if len(product['description']) > 40:
                desc += "..."
            text += f"\n📝 {desc}"
        
        # 建立 CarouselColumn
        title = name[:40] if len(name) <= 40 else name[:37] + "..."
        text = text[:120] if len(text) <= 120 else text[:117] + "..."
        
        # 建立按鈕動作
        actions = [
            MessageAction(
                label='查看詳情',
                text=f"詳情：{name}"
            )
        ]
        
        # 添加取消收藏按鈕（因為在收藏列表中，所以顯示取消收藏）
        if product_id:
            actions.append(
                PostbackAction(
                    label='取消收藏',
                    data=f"action=favorite&product_id={product_id}&source=favorites"
                )
            )
        
        column = CarouselColumn(
            thumbnail_image_url=product.get('display_image_url', DEFAULT_PRODUCT_IMAGE_URL),
            title=title,
            text=text,
            actions=actions
        )
        columns.append(column)
    
    if not columns:
        return None
    
    # 建立 Carousel Template
    carousel_template = CarouselTemplate(columns=columns)
    
    # 建立 TemplateSendMessage
    template_message = TemplateSendMessage(
        alt_text=f"我的收藏（共 {len(columns)} 個商品）",
        template=carousel_template
    )
    
    return template_message


def format_favorites_flex(favorites: list):
    """
    格式化收藏列表為 LINE Flex Message（更美觀的卡片式呈現）
    
    Args:
        favorites: 收藏的商品列表（包含位置資訊和 image_url）
    
    Returns:
        FlexSendMessage 列表或 None
    """
    if not favorites:
        return None
    
    try:
        flex_messages = []
        
        # 為每個收藏商品建立一個 Flex Bubble
        for product in favorites[:12]:  # Flex Message 可以顯示更多商品
            name = product.get('name', '未知產品')
            price = float(product.get('price', 0))
            stock = product.get('stock', 0)
            product_id = product.get('id')
            image_url = product.get('image_url') or DEFAULT_PRODUCT_IMAGE_URL
            brand = product.get('brand', '')
            
            # 處理存貨狀態
            if stock is None:
                stock = 0
            else:
                try:
                    stock = int(stock)
                except (ValueError, TypeError):
                    stock = 0
            
            # 位置資訊
            locations = product.get('locations', [])
            location_text = "📍 位置：暫無"
            if locations:
                loc = locations[0]
                area = loc.get('area', '未知區域')
                shelf = loc.get('shelf', '')
                location_text = f"📍 {area}"
                if shelf:
                    location_text += f" - {shelf}"
            
            # 建立 Flex Bubble
            bubble = BubbleContainer(
                hero=ImageComponent(
                    url=image_url if image_url.startswith('https://') else DEFAULT_PRODUCT_IMAGE_URL,
                    size="full",
                    aspect_ratio="20:13",
                    aspect_mode="cover"
                ),
                body=BoxComponent(
                    layout="vertical",
                    spacing="sm",
                    contents=[
                        TextComponent(
                            text=name[:40] if len(name) <= 40 else name[:37] + "...",
                            weight="bold",
                            size="xl",
                            wrap=True
                        ),
                        BoxComponent(
                            layout="vertical",
                            margin="md",
                            spacing="xs",
                            contents=[
                                BoxComponent(
                                    layout="baseline",
                                    spacing="sm",
                                    contents=[
                                        TextComponent(
                                            text="價格",
                                            color="#aaaaaa",
                                            size="sm",
                                            flex=1
                                        ),
                                        TextComponent(
                                            text=f"${price:.0f}",
                                            wrap=True,
                                            color="#666666",
                                            size="sm",
                                            flex=5
                                        )
                                    ]
                                ),
                                BoxComponent(
                                    layout="baseline",
                                    spacing="sm",
                                    contents=[
                                        TextComponent(
                                            text="存貨",
                                            color="#aaaaaa",
                                            size="sm",
                                            flex=1
                                        ),
                                        TextComponent(
                                            text="✅ 有存貨" if stock > 0 else "❌ 缺貨中",
                                            wrap=True,
                                            color="#666666",
                                            size="sm",
                                            flex=5
                                        )
                                    ]
                                ),
                                BoxComponent(
                                    layout="baseline",
                                    spacing="sm",
                                    contents=[
                                        TextComponent(
                                            text="位置",
                                            color="#aaaaaa",
                                            size="sm",
                                            flex=1
                                        ),
                                        TextComponent(
                                            text=location_text,
                                            wrap=True,
                                            color="#666666",
                                            size="sm",
                                            flex=5
                                        )
                                    ]
                                )
                            ]
                        )
                    ]
                ),
                footer=BoxComponent(
                    layout="vertical",
                    spacing="sm",
                    contents=[
                        ButtonComponent(
                            style="primary",
                            color="#FF6B9D",
                            action=MessageAction(
                                label="查看詳情",
                                text=f"詳情：{name}"
                            )
                        ),
                        ButtonComponent(
                            style="secondary",
                            action=PostbackAction(
                                label="取消收藏",
                                data=f"action=favorite&product_id={product_id}&source=favorites"
                            )
                        )
                    ]
                )
            )
            
            flex_messages.append(FlexSendMessage(alt_text=f"收藏商品：{name}", contents=bubble))
        
        return flex_messages if flex_messages else None

    except Exception as e:
        app.logger.error(f"建立 Flex Message 失敗：{e}", exc_info=True)
        return None


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    # 啟動 Flask 應用
    app.run(host='0.0.0.0', port=port)
    

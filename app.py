from flask import Flask, request, abort, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, ImageMessage,
    TemplateSendMessage, CarouselTemplate, CarouselColumn, ImageCarouselTemplate, ImageCarouselColumn,
    URIAction, MessageAction
)

import os
from dotenv import load_dotenv

# 先載入環境變數，再 import 其他模組
load_dotenv()

from utils import check_environment_variables
from supabase_utils import search_products_with_locations
from vision_utils import extract_keywords_from_image_gemini
from gemini_qa_utils import answer_question

# 初始化環境變數檢查
check_environment_variables()

# 初始化 Flask 和 LINE API
app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

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

# 處理文字訊息：搜尋產品或 echo
@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    """處理文字訊息 - 搜尋產品功能"""
    try:
        user_id = getattr(event.source, 'user_id', None)
        if not user_id:
            app.logger.warning("無法獲取用戶 ID")
            return

        message_text = event.message.text.strip()
        app.logger.info(f"收到訊息 from {user_id}: {message_text}")
        
        # 搜尋產品功能
        try:
            # 檢查 Supabase 是否已初始化
            from supabase_utils import supabase
            if not supabase:
                app.logger.warning("Supabase 未初始化，無法搜尋產品")
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
            else:
                # 判斷是否為問題（包含疑問詞或複雜查詢）
                question_keywords = ["什麼", "哪些", "哪裡", "多少", "最", "比較", "推薦", "便宜", "貴", "價格", "位置", "區"]
                is_question = any(keyword in message_text for keyword in question_keywords) or \
                             message_text.endswith("?") or message_text.endswith("？")
                
                if is_question:
                    # 使用 Gemini 智能問答
                    try:
                        app.logger.info(f"使用智能問答處理問題：{message_text}")
                        answer = answer_question(message_text)
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextSendMessage(text=answer)
                        )
                        app.logger.info(f"成功回覆智能問答給 {user_id}")
                    except Exception as e:
                        app.logger.error(f"智能問答失敗：{str(e)}", exc_info=True)
                        # 回退到簡單搜尋
                        products = search_products_with_locations(message_text, limit=10)
                        if products:
                            reply_text = format_product_search_result(products, message_text)
                            line_bot_api.reply_message(
                                event.reply_token,
                                TextSendMessage(text=reply_text)
                            )
                        else:
                            reply_text = f"🔍 找不到包含「{message_text}」的產品\n\n請嘗試其他關鍵字搜尋。"
                            line_bot_api.reply_message(
                                event.reply_token,
                                TextSendMessage(text=reply_text)
                            )
                else:
                    # 簡單搜尋產品
                    app.logger.info(f"開始搜尋產品：{message_text}")
                    products = search_products_with_locations(message_text, limit=10)
                    app.logger.info(f"搜尋結果：找到 {len(products)} 個產品")
                    
                    if products:
                        # 嘗試使用 Carousel 顯示產品（圖片+文字）
                        carousel_message = format_product_carousel(products, message_text)
                        if carousel_message:
                            # 有圖片，使用 Carousel
                            line_bot_api.reply_message(
                                event.reply_token,
                                carousel_message
                            )
                            app.logger.info(f"成功回覆 Carousel 訊息給 {user_id}: {len(products)} 個產品")
                        else:
                            # 沒有圖片，回退到文字訊息
                            reply_text = format_product_search_result(products, message_text)
                            line_bot_api.reply_message(
                                event.reply_token,
                                TextSendMessage(text=reply_text)
                            )
                            app.logger.info(f"成功回覆文字訊息給 {user_id}: {len(products)} 個產品")
                    else:
                        reply_text = f"🔍 找不到包含「{message_text}」的產品\n\n請嘗試其他關鍵字搜尋。"
                        line_bot_api.reply_message(
                            event.reply_token,
                            TextSendMessage(text=reply_text)
                        )
        except Exception as e:
            app.logger.error(f"搜尋或回覆訊息時發生錯誤: {str(e)}", exc_info=True)
            # 發生錯誤時回覆簡單訊息
            try:
                line_bot_api.reply_message(
                    event.reply_token,
                    TextSendMessage(text=f"❌ 搜尋時發生錯誤：{str(e)}\n\n請檢查日誌或稍後再試。")
                )
            except:
                pass
    except Exception as e:
        app.logger.error(f"處理訊息時發生錯誤: {str(e)}", exc_info=True)


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
        
        column = CarouselColumn(
            thumbnail_image_url=product.get('display_image_url', DEFAULT_PRODUCT_IMAGE_URL),
            title=title,
            text=text,
            actions=[
                MessageAction(
                    label='查看詳情',
                    text=f"詳情：{name}"
                )
            ]
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


# 處理圖片訊息
@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    try:
        message_content = line_bot_api.get_message_content(event.message.id)
        image_bytes = b"".join(message_content.iter_content())

        # Gemini 分析圖片
        keywords, full_text = extract_keywords_from_image_gemini(image_bytes)
        app.logger.info(f"Gemini 回傳：{full_text}")
        app.logger.info(f"關鍵字：{keywords}")

        # ----------- 第一階段：逐字搜尋，找到第一個命中就回傳 -----------
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
            else:
                reply_text = format_product_search_result(products, hit_keyword)
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
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
            carousel = format_product_carousel(merged_products_list, "圖片識別關鍵字")
            if carousel:
                line_bot_api.reply_message(event.reply_token, carousel)
            else:
                reply_text = format_product_search_result(merged_products_list, "圖片識別關鍵字")
                line_bot_api.reply_message(event.reply_token, TextSendMessage(text=reply_text))
        else:
            # 完全找不到：回報 Gemini 結果協助使用者
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(
                    text=f"❌ 找不到相關商品\n🔍 辨識內容：\n{full_text}"
                )
            )

    except Exception as e:
        app.logger.error(f"處理圖片訊息時發生錯誤: {str(e)}", exc_info=True)




if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    # 啟動 Flask 應用
    app.run(host='0.0.0.0', port=port)
    

"""
事件處理器模組
負責處理 LINE Bot 的各種事件（文字、圖片、Postback）
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from linebot.models import TextSendMessage
from supabase_utils import (
    search_products_with_locations, add_to_favorites, remove_from_favorites,
    get_user_favorites, is_favorited
)
from vision_utils import extract_keywords_from_image_gemini
from core.mode_router import determine_mode, user_modes
from core.mode_handlers import (
    handle_product_search_mode, handle_qa_mode,
    handle_help_mode, handle_area_query_mode
)
from core.formatters import (
    format_product_carousel, format_product_search_result,
    format_favorites_flex, format_favorites_carousel, format_favorites_compact,
    add_quick_reply_to_message
)


def handle_text_message(event, line_bot_api, app):
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
        if handle_favorite_commands(event, message_text, user_id, line_bot_api, app):
            return  # 已處理收藏指令，直接返回
        
        # 判斷模式（傳入 user_id 以檢查用戶當前模式）
        mode = determine_mode(message_text, user_id)
        app.logger.info(f"判斷模式：{mode} (用戶當前模式：{user_modes.get(user_id, '無')})")
        
        # 根據模式路由到對應處理函數
        if mode == 'help':
            handle_help_mode(event, user_id, line_bot_api, app)
        elif mode == 'area':
            handle_area_query_mode(event, message_text, user_id, line_bot_api, app)
        elif mode == 'qa':
            handle_qa_mode(event, message_text, user_id, line_bot_api, app)
        elif mode == 'search_help':
            # 搜尋模式提示（會由 handle_product_search_mode 內部處理）
            handle_product_search_mode(event, message_text, user_id, line_bot_api, app)
        else:  # 'search' 或其他，預設為商品搜尋模式
            handle_product_search_mode(event, message_text, user_id, line_bot_api, app)
            
    except Exception as e:
        app.logger.error(f"處理文字訊息時發生錯誤: {str(e)}", exc_info=True)


def handle_image_message(event, line_bot_api, app):
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
            carousel = format_product_carousel(products, hit_keyword, line_bot_api, app, mode='search')
            if carousel:
                line_bot_api.reply_message(event.reply_token, carousel)
                app.logger.info(f"[商品搜尋模式-圖片] 成功回覆 Carousel：{len(products)} 個產品")
            else:
                reply_text = format_product_search_result(products, hit_keyword)
                message = TextSendMessage(text=reply_text)
                message = add_quick_reply_to_message(message, mode='search')
                line_bot_api.reply_message(event.reply_token, message)
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
            carousel = format_product_carousel(merged_products_list, " ".join(keywords), line_bot_api, app, mode='search')
            if carousel:
                line_bot_api.reply_message(event.reply_token, carousel)
                app.logger.info(f"[商品搜尋模式-圖片] 成功回覆合併搜尋結果：{len(merged_products_list)} 個產品")
            else:
                reply_text = format_product_search_result(merged_products_list, " ".join(keywords))
                message = TextSendMessage(text=reply_text)
                message = add_quick_reply_to_message(message, mode='search')
                line_bot_api.reply_message(event.reply_token, message)
        else:
            # 完全找不到 → 回傳 Gemini 辨識內容
            reply_text = f"📷 圖片辨識結果：\n\n{full_text}\n\n🔍 未找到相符商品，請嘗試其他關鍵字搜尋。"
            message = TextSendMessage(text=reply_text)
            message = add_quick_reply_to_message(message, mode='search')
            line_bot_api.reply_message(event.reply_token, message)
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


def handle_postback(event, line_bot_api, app):
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


def handle_favorite_commands(event, message_text: str, user_id: str, line_bot_api, app):
    """處理收藏相關的文字指令"""
    try:
        # 處理「我的收藏」指令
        if message_text in ["我的收藏", "收藏列表", "收藏"]:
            favorites = get_user_favorites(user_id, limit=12)  # Flex Message 最多 12 個
            
            if not favorites:
                reply_text = "📭 您還沒有收藏任何商品\n\n搜尋商品後，點擊「收藏商品」按鈕即可收藏！"
                message = TextSendMessage(text=reply_text)
                message = add_quick_reply_to_message(message, mode='default')
                line_bot_api.reply_message(
                    event.reply_token,
                    message
                )
            else:
                # 優先使用 Carousel（有互動按鈕，可查看詳情和取消收藏）
                carousel_message = format_favorites_carousel(favorites)
                if carousel_message:
                    line_bot_api.reply_message(
                        event.reply_token,
                        carousel_message
                    )
                    app.logger.info(f"成功回覆 Carousel 收藏列表給 {user_id}: {len(favorites)} 個商品")
                else:
                    # 回退到緊湊的 Flex Message
                    flex_messages = format_favorites_flex(favorites, app)
                    if flex_messages:
                        # Flex Message 列表後加上一個帶快速回復的提示訊息
                        quick_reply_message = TextSendMessage(text=f"❤️ 共 {len(favorites)} 個收藏商品")
                        quick_reply_message = add_quick_reply_to_message(quick_reply_message, mode='default')
                        # 將快速回復訊息加入列表最後
                        all_messages = flex_messages + [quick_reply_message]
                        line_bot_api.reply_message(
                            event.reply_token,
                            all_messages
                        )
                        app.logger.info(f"成功回覆 Flex Message 收藏列表給 {user_id}: {len(favorites)} 個商品")
                    else:
                        # 最後回退到緊湊文字格式（但這個沒有互動功能，所以不推薦）
                        compact_message = format_favorites_compact(favorites, app)
                        if compact_message:
                            compact_message = add_quick_reply_to_message(compact_message, mode='default')
                            line_bot_api.reply_message(
                                event.reply_token,
                                compact_message
                            )
                            app.logger.info(f"成功回覆緊湊收藏列表給 {user_id}: {len(favorites)} 個商品")
            return True
        
        return False
    except Exception as e:
        app.logger.error(f"處理收藏指令時發生錯誤: {str(e)}", exc_info=True)
        return False


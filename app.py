from flask import Flask, request, abort, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageMessage
from utils import check_environment_variables
import os

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

# 處理文字訊息：使用者傳什麼，bot 就回什麼
@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    """處理文字訊息 - echo 功能"""
    try:
        user_id = getattr(event.source, 'user_id', None)
        if not user_id:
            app.logger.warning("無法獲取用戶 ID")
            return

        message_text = event.message.text.strip()
        app.logger.info(f"收到訊息 from {user_id}: {message_text}")
        
        # Echo 功能：傳什麼回什麼
        try:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text=message_text)
            )
            app.logger.info(f"成功回覆訊息給 {user_id}: {message_text}")
        except Exception as e:
            app.logger.error(f"回覆訊息時發生錯誤: {str(e)}", exc_info=True)
    except Exception as e:
        app.logger.error(f"處理訊息時發生錯誤: {str(e)}", exc_info=True)

# 處理圖片訊息
@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    """處理圖片訊息"""
    try:
        user_id = getattr(event.source, 'user_id', None)
        app.logger.info(f"收到圖片訊息 from {user_id}")
        
        # 簡單回覆：收到圖片
        try:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="✅ 已收到您的圖片")
            )
            app.logger.info(f"成功回覆圖片訊息給 {user_id}")
        except Exception as e:
            app.logger.error(f"回覆圖片訊息時發生錯誤: {str(e)}", exc_info=True)
    except Exception as e:
        app.logger.error(f"處理圖片訊息時發生錯誤: {str(e)}", exc_info=True)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    # 啟動 Flask 應用
    app.run(host='0.0.0.0', port=port)

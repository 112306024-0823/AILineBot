"""
LINE Bot 主應用程式
負責 Flask 路由、LINE Webhook 處理和模組整合
"""
from flask import Flask, request, abort, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, ImageMessage, PostbackEvent

import os
from dotenv import load_dotenv

# 先載入環境變數，再 import 其他模組
load_dotenv()

from utils import check_environment_variables
from core.handlers import handle_text_message, handle_image_message, handle_postback

# 初始化環境變數檢查
check_environment_variables()

# 初始化 Flask 和 LINE API
# 設定靜態檔案路徑
app = Flask(__name__, static_folder='static', static_url_path='/static')

# 設定 BASE_URL（用於生成圖片 URL）
# 優先使用環境變數，沒有則使用預設值
base_url = os.getenv('BASE_URL')
if base_url:
    app.config['BASE_URL'] = base_url
    app.logger.info(f"BASE_URL 已設定：{base_url}")

line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

# 確保生成地圖目錄存在
generated_maps_dir = os.path.join(os.path.dirname(__file__), 'static', 'generated_maps')
os.makedirs(generated_maps_dir, exist_ok=True)


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


# ==================== LINE 事件處理器註冊 ====================

@handler.add(MessageEvent, message=TextMessage)
def on_text_message(event):
    """處理文字訊息"""
    handle_text_message(event, line_bot_api, app)


@handler.add(MessageEvent, message=ImageMessage)
def on_image_message(event):
    """處理圖片訊息"""
    handle_image_message(event, line_bot_api, app)


@handler.add(PostbackEvent)
def on_postback(event):
    """處理 Postback 事件"""
    handle_postback(event, line_bot_api, app)


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    # 啟動 Flask 應用
    app.run(host='0.0.0.0', port=port)

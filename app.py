from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
import os

app = Flask(__name__)

# LINE BOT info
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

@app.route("/callback", methods=['POST'])
def callback():
    # 確認 LINE 的簽名
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# Message event: 處理文字訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    reply_token = event.reply_token
    message_text = event.message.text.strip()

    # 基本測試回應
    if message_text == "我要上傳筆記":
        line_bot_api.reply_message(reply_token, TextSendMessage(text="請上傳您的筆記檔案。"))
    elif message_text == "我要取得筆記":
        line_bot_api.reply_message(reply_token, TextSendMessage(text="這裡是您的筆記連結範例。"))
    else:
        line_bot_api.reply_message(reply_token, TextSendMessage(text=f"我有收到您的訊息：{message_text}"))

# 啟動 Flask 伺服器
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

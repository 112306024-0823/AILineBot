from flask import Flask, request, abort, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, QuickReply, QuickReplyButton,
    URIAction, ImageSendMessage, MessageAction, ImageMessage
)
from Upload_Handler import UploadHandler
from utils import upload_file_to_google_drive, check_environment_variables, save_file_metadata
import os
import firebase_admin
from firebase_admin import credentials, firestore

# 初始化環境變數檢查
check_environment_variables()

# 初始化 Firebase
try:
    firebase_info = json.loads(os.getenv("FIREBASE_CREDENTIALS"))
    cred = credentials.Certificate(firebase_info)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Firebase 初始化成功")
except Exception as e:
    print(f"Firebase 初始化失敗：{e}")
    raise

# 初始化 Flask 和 LINE API
app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

# 註冊 UploadHandler
FOLDER_ID = "1h7DL1gRlB96Dpxmad0-gMvSDdVjm57vn"
upload_handler = UploadHandler(upload_folder="uploads", line_bot_api=line_bot_api, folder_id=FOLDER_ID)
app.register_blueprint(upload_handler.blueprint)


@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature', None)
    body = request.get_data(as_text=True)

    app.logger.info(f"Request body: {body}")
    if not signature:
        app.logger.error("缺少 X-Line-Signature")
        abort(400)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.error("簽名驗證失敗")
        abort(400)
    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    user_id = getattr(event.source, 'user_id', None)
    if not user_id:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="無法獲取用戶 ID，請確保您已添加好友。")
        )
        return

    message_text = event.message.text.strip()

    if message_text == "我要上傳筆記":
        quick_reply = QuickReply(items=[
            QuickReplyButton(action=URIAction(label="點擊上傳檔案", uri=f"https://{request.host}/upload"))
        ])
        reply_message = TextSendMessage(
            text="請點擊下方按鈕上傳檔案：", quick_reply=quick_reply
        )
        line_bot_api.reply_message(event.reply_token, reply_message)

    elif message_text == "選擇 LINE Pay":
        linepay_image_url = f"https://{request.host}/static/images/linepay_qrcode.jpg"
        reply_message = [
            TextSendMessage(
                text=(
                    "✨ 感謝您的支持！\n\n"
                    "📷 請掃描以下的 QR Code 完成付款：\n\n"
                    "📤 完成匯款後，請回傳付款截圖，我們將在確認款項後提供限時有效的下載連結給您！\n\n"
                    "🌟 感謝您的支持，祝您有美好的一天！ 🎉"
                )
            ),
            ImageSendMessage(
                original_content_url=linepay_image_url,
                preview_image_url=linepay_image_url
            )
        ]

        line_bot_api.reply_message(event.reply_token, reply_message)

    elif message_text == "選擇 郵局匯款":
        reply_message = TextSendMessage(
            text=(
                "🏦 **郵局匯款方式**\n\n"
                "銀行代碼：700\n"
                "帳號：0000023980362050\n\n"
                "📤 完成匯款後，請回傳付款截圖，我們將在確認款項後提供限時有效的下載連結給您！\n\n"
                "🌟 感謝您的支持，祝您有美好的一天！ 🎉"
            )
        )
        line_bot_api.reply_message(event.reply_token, reply_message)


@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    reply_token = event.reply_token
    confirmation_message = TextSendMessage(
        text="✅ 已收到您的付款證明。我們將盡快處理並提供下載連結！"
    )
    line_bot_api.reply_message(reply_token, confirmation_message)


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

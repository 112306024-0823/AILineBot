from flask import Flask, request, abort, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, QuickReply, QuickReplyButton, URIAction
import os
import firebase_admin
from firebase_admin import credentials, firestore
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import json
from threading import Thread
import Upload_Handler


# 初始化 Google Drive 和 Firebase 配置
google_drive_info = json.loads(os.getenv("GOOGLE_DRIVE_CREDENTIALS"))
creds = service_account.Credentials.from_service_account_info(google_drive_info)
service = build('drive', 'v3', credentials=creds)

FOLDER_ID = "1h7DL1gRlB96Dpxmad0-gMvSDdVjm57vn"

firebase_info = json.loads(os.getenv("FIREBASE_CREDENTIALS"))
cred = credentials.Certificate(firebase_info)
firebase_admin.initialize_app(cred)
db = firestore.client()

# 初始化 Flask 和 LINE API
app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

# 註冊 UploadHandler
upload_handler = UploadHandler(upload_folder="uploads", line_bot_api=line_bot_api, folder_id=FOLDER_ID)
app.register_blueprint(upload_handler.blueprint)


# 上傳檔案到 Google Drive 並返回下載連結
def upload_file_to_google_drive(file_path, file_name):
    try:
        file_metadata = {'name': file_name, 'parents': [FOLDER_ID]}
        media = MediaFileUpload(file_path, resumable=True)
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        file_id = file.get('id')
        service.permissions().create(fileId=file_id, body={'type': 'anyone', 'role': 'reader'}).execute()
        return f"https://drive.google.com/uc?id={file_id}&export=download"
    except Exception as e:
        print(f"Google Drive 上傳失敗：{e}")
        return None


# 儲存檔案元數據到 Firestore
def save_file_metadata(user_id, file_name, file_url, subject="", grade=""):
    try:
        db.collection("notes").add({
            "user_id": user_id,
            "file_name": file_name,
            "file_url": file_url,
            "subject": subject,
            "grade": grade,
            "status": "審核中"
        })
        print(f"檔案元數據已儲存到 Firebase：{file_name}")
    except Exception as e:
        print(f"儲存檔案元數據失敗：{e}")





@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info(f"Request body: {body}")
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'


@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    user_id = event.source.user_id
    reply_token = event.reply_token
    message_text = event.message.text.strip()

    if message_text == "我要上傳筆記":
        quick_reply = QuickReply(items=[
            QuickReplyButton(action=URIAction(label="點擊上傳檔案", uri=f"https://{request.host}/upload"))
        ])
        line_bot_api.reply_message(
            reply_token,
            TextSendMessage(text="請點擊下方按鈕上傳檔案：", quick_reply=quick_reply)
        )
    elif "購買筆記" in message_text:
        reply_message = (
            "📌 付款方式：\n"
            "🏦 郵局轉帳\n"
            "銀行代碼：700\n"
            "帳號：0000023980362050\n"
            "💚 **LINE Pay**\n"
            "點擊以下連結進行付款：\n"
            "🔗 [LINE Pay 付款連結]\n\n"
            "📤 完成付款後，請回傳付款截圖，我們將再確收款項後提供限時有效的下載連結給您！"
        )
        line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_message))


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

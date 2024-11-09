from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, FileMessage
import os
import firebase_admin
from firebase_admin import credentials, firestore
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import json
from threading import Thread

# 從環境變數中加載 Google Drive API 憑證
google_drive_info = json.loads(os.getenv("GOOGLE_DRIVE_CREDENTIALS"))
creds = service_account.Credentials.from_service_account_info(google_drive_info)
service = build('drive', 'v3', credentials=creds)

# 指定上傳目標資料夾的 folder_id
FOLDER_ID = "1h7DL1gRlB96Dpxmad0-gMvSDdVjm57vn"  # 替換成你的 folder_id

# 從環境變數中加載 Firebase 憑證
firebase_info = json.loads(os.getenv("FIREBASE_CREDENTIALS"))
cred = credentials.Certificate(firebase_info)
firebase_admin.initialize_app(cred)

# 建立 Firestore 客戶端
db = firestore.client()

app = Flask(__name__)
# LINE BOT info
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

# 上傳檔案到 Google Drive 的指定資料夾並返回下載連結
def upload_file_to_google_drive(file_path, file_name):
    file_metadata = {
        'name': file_name,
        'parents': [FOLDER_ID]  # 將文件上傳至指定資料夾
    }
    media = MediaFileUpload(file_path, resumable=True)
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    file_id = file.get('id')
    service.permissions().create(fileId=file_id, body={'type': 'anyone', 'role': 'reader'}).execute()
    file_url = f"https://drive.google.com/uc?id={file_id}&export=download"
    return file_url

# 儲存檔案元數據到 Firestore
def save_file_metadata(user_id, file_name, file_url):
    db.collection("notes").add({
        "user_id": user_id,
        "file_name": file_name,
        "file_url": file_url
    })

# 背景處理上傳和儲存操作
def background_upload_and_save(user_id, file_name, file_path):
    file_url = upload_file_to_google_drive(file_path, file_name)
    save_file_metadata(user_id, file_name, file_url)
    os.remove(file_path)  # 清除本地文件以節省空間

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)
    print(body)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

# Message event: 處理文字訊息
@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    user_id = event.source.user_id
    reply_token = event.reply_token
    message_text = event.message.text.strip()

    if message_text == "我要上傳筆記":
        line_bot_api.reply_message(reply_token, TextSendMessage(text="請上傳您的筆記檔案。"))
    elif message_text == "我要取得筆記":
        # 從 Firestore 中查詢使用者的筆記
        notes = db.collection("notes").where("user_id", "==", user_id).stream()
        notes_text = "\n".join([f"{note.to_dict()['file_name']}: {note.to_dict()['file_url']}" for note in notes])
        
        if notes_text:
            line_bot_api.reply_message(reply_token, TextSendMessage(text=f"這是您的筆記連結：\n{notes_text}"))
        else:
            line_bot_api.reply_message(reply_token, TextSendMessage(text="目前沒有找到您的筆記。"))
    else:
        line_bot_api.reply_message(reply_token, TextSendMessage(text="我有收到您的訊息，但不確定您的需求。請輸入「我要上傳筆記」或「我要取得筆記」。"))

# FileMessage event: 處理檔案上傳
@handler.add(MessageEvent, message=FileMessage)
def handle_file_message(event):
    user_id = event.source.user_id
    reply_token = event.reply_token
    message_id = event.message.id
    file_name = event.message.file_name

    # 下載檔案內容
    message_content = line_bot_api.get_message_content(message_id)
    file_path = f"/tmp/{file_name}"

    # 儲存檔案到本地 /tmp 資料夾
    with open(file_path, 'wb') as f:
        for chunk in message_content.iter_content():
            f.write(chunk)

    # 回覆使用者，告知檔案正在處理中
    line_bot_api.reply_message(reply_token, TextSendMessage(text="檔案已收到，正在處理中，稍後會提供下載連結。"))

    # 在背景執行上傳和儲存操作
    Thread(target=background_upload_and_save, args=(user_id, file_name, file_path)).start()

# 啟動 Flask 伺服器
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

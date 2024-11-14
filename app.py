from flask import Flask, request, abort, jsonify
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, FileMessage, QuickReply, QuickReplyButton, MessageAction
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
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

# 儲存使用者選擇的科目和年級
user_selections = {}

# 上傳檔案到 Google Drive 並返回下載連結
def upload_file_to_google_drive(file_path, file_name):
    file_metadata = {
        'name': file_name,
        'parents': [FOLDER_ID]
    }
    media = MediaFileUpload(file_path, resumable=True)
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    file_id = file.get('id')
    service.permissions().create(fileId=file_id, body={'type': 'anyone', 'role': 'reader'}).execute()
    file_url = f"https://drive.google.com/uc?id={file_id}&export=download"
    return file_url

# 儲存檔案元數據到 Firestore
def save_file_metadata(user_id, file_name, file_url, subject="", grade=""):
    db.collection("notes").add({
        "user_id": user_id,
        "file_name": file_name,
        "file_url": file_url,
        "subject": subject,
        "grade": grade
    })

# 背景處理上傳和儲存操作
def background_upload_and_save(user_id, file_name, file_path, subject, grade):
    file_url = upload_file_to_google_drive(file_path, file_name)
    save_file_metadata(user_id, file_name, file_url, subject, grade)
    os.remove(file_path)

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

# 顯示初始選單的 Quick Reply 回應
def show_initial_options(reply_token):
    options = [
        QuickReplyButton(action=MessageAction(label="我要上傳筆記", text="我要上傳筆記")),
        QuickReplyButton(action=MessageAction(label="我要取得筆記", text="我要取得筆記"))
    ]
    quick_reply = QuickReply(items=options)
    line_bot_api.reply_message(reply_token, TextSendMessage(text="請選擇操作：", quick_reply=quick_reply))

@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    user_id = event.source.user_id
    reply_token = event.reply_token
    message_text = event.message.text.strip()

    # 無論收到什麼訊息，先顯示初始選單
    if message_text not in ["我要上傳筆記", "我要取得筆記", "科目:", "年級:"]:
        show_initial_options(reply_token)
        return

    if message_text == "我要上傳筆記":
        user_selections[user_id] = {"mode": "upload"}
        subjects = ["經濟學", "統計學", "會計學", "微積分", "管理學"]
        quick_reply_items = [QuickReplyButton(action=MessageAction(label=subject, text=f"科目: {subject}")) for subject in subjects]
        quick_reply = QuickReply(items=quick_reply_items)
        line_bot_api.reply_message(reply_token, TextSendMessage(text="請選擇上傳的科目：", quick_reply=quick_reply))

    elif message_text.startswith("科目:") and user_selections.get(user_id, {}).get("mode") == "upload":
        subject = message_text.split(": ")[1]
        user_selections[user_id]["subject"] = subject
        grades = ["高一", "高二", "高三", "大一", "大二"]
        quick_reply_items = [QuickReplyButton(action=MessageAction(label=grade, text=f"年級: {grade}")) for grade in grades]
        quick_reply = QuickReply(items=quick_reply_items)
        line_bot_api.reply_message(reply_token, TextSendMessage(text="請選擇年級：", quick_reply=quick_reply))

    elif message_text.startswith("年級:") and user_selections.get(user_id, {}).get("mode") == "upload":
        grade = message_text.split(": ")[1]
        user_selections[user_id]["grade"] = grade
        line_bot_api.reply_message(reply_token, TextSendMessage(text="請上傳您的筆記檔案。"))

    elif message_text == "我要取得筆記":
        subjects = ["經濟學", "統計學", "會計學", "微積分", "管理學"]
        quick_reply_items = [QuickReplyButton(action=MessageAction(label=subject, text=f"搜尋科目: {subject}")) for subject in subjects]
        quick_reply = QuickReply(items=quick_reply_items)
        line_bot_api.reply_message(reply_token, TextSendMessage(text="請選擇要搜尋的科目", quick_reply=quick_reply))

    elif message_text.startswith("搜尋科目:"):
        selected_subject = message_text.split(": ")[1]
        notes = db.collection("notes").where("subject", "==", selected_subject).stream()
        notes_text = "\n".join([f"{note.to_dict()['file_name']}: {note.to_dict()['file_url']}" for note in notes])

        if notes_text:
            line_bot_api.reply_message(reply_token, TextSendMessage(text=f"{selected_subject}的筆記：\n{notes_text}"))
        else:
            line_bot_api.reply_message(reply_token, TextSendMessage(text=f"目前沒有{selected_subject}的筆記。"))

@handler.add(MessageEvent, message=FileMessage)
def handle_file_message(event):
    user_id = event.source.user_id
    reply_token = event.reply_token
    message_id = event.message.id
    file_name = event.message.file_name

    if user_selections.get(user_id, {}).get("mode") == "upload":
        subject = user_selections[user_id].get("subject", "")
        grade = user_selections[user_id].get("grade", "")

        if not subject or not grade:
            line_bot_api.reply_message(reply_token, TextSendMessage(text="請先選擇科目和年級。"))
            return

        message_content = line_bot_api.get_message_content(message_id)
        file_path = f"/tmp/{file_name}"

        with open(file_path, 'wb') as f:
            for chunk in message_content.iter_content():
                f.write(chunk)

        Thread(target=background_upload_and_save, args=(user_id, file_name, file_path, subject, grade)).start()
        line_bot_api.reply_message(reply_token, TextSendMessage(text="檔案已成功上傳！"))
    else:
        line_bot_api.reply_message(reply_token, TextSendMessage(text="請先點擊「我要上傳筆記」並完成科目與年級選擇。"))

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

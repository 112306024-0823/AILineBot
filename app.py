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
from flask import Blueprint, request, jsonify
from threading import Thread
from UploadHandler import UploadHandler

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

# 儲存用戶的模式
user_modes = {}

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
# 模擬背景處理邏輯（實際應替換為你自己的實現）
def background_upload_and_save(user_id, file_name, file_path, subject, grade):
    file_url = upload_file_to_google_drive(file_path, file_name)
    save_file_metadata(user_id, file_name, file_url, subject, grade)
    print(f"開始處理檔案上傳：{file_name}, 科目：{subject}, 年級：{grade}")
    # 模擬 Google Drive 上傳
    file_url = f"https://drive.google.com/uc?id=dummy_file_id&export=download"
    # 模擬儲存到 Firebase
    print(f"檔案已儲存到 Firebase，檔案連結：{file_url}")
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

@app.route("/upload", methods=["GET", "POST"])
def upload():
    if request.method == "POST":
        file = request.files.get("file")
        if file and allowed_file(file.filename):
            file_path = os.path.join("uploads", file.filename)
            os.makedirs("uploads", exist_ok=True)
            file.save(file_path)

            # 假設用戶 ID 與科目、年級已知，這裡簡化處理
            user_id = "demo_user_id"
            subject = "預設科目"
            grade = "預設年級"

            # 背景處理 Google Drive 和 Firebase 上傳
            Thread(target=background_upload_and_save, args=(user_id, file.filename, file_path, subject, grade)).start()

            return jsonify({
                "status": "success",
                "message": "檔案已成功上傳！",
                "file_url": f"https://{request.host}/uploads/{file.filename}"
            })
        return jsonify({"status": "error", "message": "檔案格式不正確！"})
    return '''
    <!doctype html>
    <title>檔案上傳</title>
    <h1>請上傳檔案</h1>
    <form method="post" enctype="multipart/form-data">
        <input type="file" name="file">
        <button type="submit">上傳</button>
    </form>
    '''

def allowed_file(filename):
    allowed_extensions = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    user_id = event.source.user_id
    reply_token = event.reply_token
    message_text = event.message.text.strip()
    purchase_keywords = ["購買筆記", "如何購買", "我要購買","欲購買的筆記"]


    if message_text == "我要上傳筆記":
        quick_reply = QuickReply(items=[
            QuickReplyButton(action=URIAction(label="點擊上傳檔案", uri=f"https://{request.host}/upload"))
        ])
        line_bot_api.reply_message(
            reply_token,
            TextSendMessage(text="請點擊下方按鈕上傳檔案：", quick_reply=quick_reply)
        )
    elif any(keyword in message_text for keyword in purchase_keywords):
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
        # 將訊息回傳給使用者
        line_bot_api.reply_message(reply_token, TextSendMessage(text=reply_message))


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
    print(f"本地檔案已刪除：{file_path}")

class UploadHandler:
    def __init__(self, upload_folder="uploads"):
        self.upload_folder = upload_folder
        os.makedirs(self.upload_folder, exist_ok=True)

        # 建立 Blueprint
        self.blueprint = Blueprint("upload_handler", __name__)
        self.setup_routes()

    def setup_routes(self):
        @self.blueprint.route("/upload", methods=["GET", "POST"])
        def upload():
            if request.method == "POST":
                # 獲取表單資料
                file = request.files.get("file")
                subject = request.form.get("subject")
                grade = request.form.get("grade")

                if not subject or not grade:
                    return jsonify({"status": "error", "message": "請填寫完整的科目與年級資訊！"})

                if file and self.allowed_file(file.filename):
                    file_path = os.path.join(self.upload_folder, file.filename)
                    file.save(file_path)

                    # 模擬用戶 ID
                    user_id = "demo_user_id"

                    # 背景處理 Google Drive 和 Firebase 上傳
                    Thread(target=background_upload_and_save, args=(user_id, file.filename, file_path, subject, grade)).start()

                    return jsonify({"status": "success", "message": "檔案已成功上傳！"})
                return jsonify({"status": "error", "message": "檔案格式不正確！"})

            return self.render_upload_form()

    def allowed_file(self, filename):
        allowed_extensions = {"pdf", "png", "jpg", "jpeg", "doc", "docx"}
        return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions


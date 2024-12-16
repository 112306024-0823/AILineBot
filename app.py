from flask import Flask, request, jsonify, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, QuickReply, QuickReplyButton, URIAction
import os
from firebase_admin import credentials, firestore, initialize_app
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import threading

# 初始化 Flask
app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

# 設定檔案上傳資料夾
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# 初始化 Firebase
firebase_cred = credentials.Certificate("path_to_your_firebase_credential.json")
initialize_app(firebase_cred)
db = firestore.client()

# 初始化 Google Drive API
google_drive_creds = "path_to_your_google_drive_credentials.json"
drive_service = build('drive', 'v3', credentials=credentials.Credentials.from_service_account_file(google_drive_creds))

# ========== LINE Bot 相關路由 ==========
@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)
    return 'OK'

@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    reply_token = event.reply_token
    message_text = event.message.text.strip()

    if message_text == "上傳檔案":
        quick_reply = QuickReply(items=[
            QuickReplyButton(action=URIAction(label="點擊上傳檔案", uri=f"https://{request.host}/upload"))
        ])
        line_bot_api.reply_message(
            reply_token,
            TextSendMessage(text="請點擊下方按鈕上傳檔案：", quick_reply=quick_reply)
        )
    else:
        line_bot_api.reply_message(reply_token, TextSendMessage(text="請選擇正確的操作！"))

# ========== 檔案上傳功能 ==========
class UploadHandler:
    def __init__(self, app, upload_folder="uploads"):
        self.app = app
        self.upload_folder = upload_folder
        os.makedirs(self.upload_folder, exist_ok=True)
        self.setup_routes()

    def setup_routes(self):
        @self.app.route('/upload', methods=['GET', 'POST'])
        def upload():
            if request.method == 'POST':
                file = request.files.get('file')
                if file and self.allowed_file(file.filename):
                    file_path = os.path.join(self.upload_folder, file.filename)
                    file.save(file_path)

                    # 儲存到 Google Drive
                    thread = threading.Thread(target=self.upload_to_google_drive, args=(file_path, file.filename))
                    thread.start()

                    # 儲存檔案資料到 Firebase
                    self.save_to_firebase(file.filename, f"https://{request.host}/{file_path}")

                    return jsonify({
                        "status": "success",
                        "message": "檔案已成功上傳",
                        "local_url": f"https://{request.host}/uploads/{file.filename}"
                    })
                return jsonify({"status": "error", "message": "無效檔案"})
            return self.render_upload_form()

    def allowed_file(self, filename):
        allowed_extensions = {'pdf', 'png', 'jpg', 'jpeg', 'doc', 'docx'}
        return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

    def render_upload_form(self):
        return '''
        <!doctype html>
        <title>檔案上傳</title>
        <h1>請上傳您的檔案</h1>
        <form method="post" enctype="multipart/form-data">
            <input type="file" name="file" accept=".pdf,.png,.jpg,.jpeg,.doc,.docx">
            <button type="submit">上傳</button>
        </form>
        '''

    def upload_to_google_drive(self, file_path, file_name):
        """上傳檔案到 Google Drive 並設定分享權限"""
        file_metadata = {'name': file_name, 'parents': ["YOUR_FOLDER_ID"]}
        media = MediaFileUpload(file_path, resumable=True)
        drive_file = drive_service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        file_id = drive_file.get('id')

        # 設定檔案為可公開訪問
        drive_service.permissions().create(fileId=file_id, body={"role": "reader", "type": "anyone"}).execute()
        drive_url = f"https://drive.google.com/uc?id={file_id}&export=download"

        print(f"檔案已上傳到 Google Drive: {drive_url}")

    def save_to_firebase(self, file_name, file_url):
        """將檔案資訊儲存到 Firebase Firestore"""
        db.collection("notes").add({
            "file_name": file_name,
            "file_url": file_url,
        })
        print(f"檔案資訊已儲存到 Firebase: {file_name}")

# 初始化檔案上傳功能
upload_handler = UploadHandler(app)

# 啟動 Flask 應用
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)

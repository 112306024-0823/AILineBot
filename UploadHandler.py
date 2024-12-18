import os
from flask import Blueprint, request, jsonify
from threading import Thread
from utils import background_upload_and_save

class UploadHandler:
    def __init__(self, upload_folder="uploads", line_bot_api=None, folder_id=None):
        self.upload_folder = upload_folder
        self.line_bot_api = line_bot_api
        self.folder_id = folder_id
        os.makedirs(self.upload_folder, exist_ok=True)

        # 建立 Blueprint
        self.blueprint = Blueprint("upload_handler", __name__)
        self.setup_routes()

    def setup_routes(self):
        @self.blueprint.route("/upload", methods=["GET", "POST"])
        def upload():
            if request.method == "POST":
                file = request.files.get("file")
                subject = request.form.get("subject")
                grade = request.form.get("grade")
                user_id = request.form.get("user_id")  # 透過隱藏欄位或 URL 參數接收

                if not subject or not grade or not user_id:
                    return jsonify({"status": "error", "message": "請填寫完整的資訊！"})

                if file and self.allowed_file(file.filename):
                    file_path = os.path.join(self.upload_folder, file.filename)
                    file.save(file_path)

                    # 背景處理檔案上傳和通知
                    Thread(target=background_upload_and_save, args=(
                        user_id, file.filename, file_path, subject, grade, self.folder_id, self.line_bot_api
                    )).start()

                    return '''
                    <!doctype html>
                    <html>
                    <head>
                        <script>
                            alert("檔案上傳成功！即將返回 LINE");
                            window.location.href = "line://nv/chat";
                        </script>
                    </head>
                    <body></body>
                    </html>
                    '''
                return jsonify({"status": "error", "message": "檔案格式不正確！"})

            return self.render_upload_form()

    def allowed_file(self, filename):
        allowed_extensions = {"pdf", "png", "jpg", "jpeg", "doc", "docx"}
        return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions

    def render_upload_form(self):
        return '''
        <!doctype html>
        <html>
        <head>
            <title>檔案上傳</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <script>
                function handleUpload(event) {
                    event.preventDefault();
                    const form = event.target;
                    const formData = new FormData(form);

                    fetch(form.action, {
                        method: form.method,
                        body: formData
                    })
                    .then(response => response.text())
                    .then(html => document.body.innerHTML = html)
                    .catch(err => alert("上傳失敗，請重試！"));
                }
            </script>
        </head>
        <body>
            <form method="post" enctype="multipart/form-data" onsubmit="handleUpload(event)">
                <label>科目名稱</label><input type="text" name="subject" required><br>
                <label>選擇年級</label><input type="text" name="grade" required><br>
                <input type="hidden" name="user_id" value="demo_user_id"> <!-- 從 URL 或預填 -->
                <label>選擇檔案</label><input type="file" name="file" required><br>
                <button type="submit">上傳</button>
            </form>
        </body>
        </html>
        '''

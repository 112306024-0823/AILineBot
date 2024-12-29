from flask import Blueprint, render_template, request, jsonify
from werkzeug.utils import secure_filename
from threading import Thread
from utils import background_upload_and_save
import os
import json
from flexmessage import create_upload_success_flex

class UploadHandler:
    ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg"}

    def __init__(self, upload_folder="uploads", line_bot_api=None, folder_id=None):
        self.upload_folder = upload_folder
        self.line_bot_api = line_bot_api
        self.folder_id = folder_id
        os.makedirs(self.upload_folder, exist_ok=True)

        # 建立 Blueprint
        self.blueprint = Blueprint("upload_handler", __name__, template_folder="templates")
        self.setup_routes()

    def setup_routes(self):
        @self.blueprint.route("/upload", methods=["GET", "POST"])
        def upload():
            # 獲取 user_id 從 URL 查詢參數
            user_id = request.args.get("user_id")
            if not user_id:
                return "無法取得用戶 ID", 400

            if request.method == "POST":
                file = request.files.get("file")
                subject = request.form.get("subject")
                grade = request.form.get("grade")
                year = request.form.get("year")

                # 驗證表單數據
                if not subject or not grade or not year:
                    return jsonify({"status": "error", "message": "請填寫完整訊息！"}), 400

                # 驗證文件格式
                if file and self.allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(self.upload_folder, filename)
                    file.save(file_path)

                    # 後台處理檔案上傳
                    Thread(target=background_upload_and_save, args=(
                        user_id, year, filename, file_path, subject, grade, self.folder_id, self.line_bot_api
                    )).start()

                    # 發送 Flex Message 通知用戶
                    flex_message = create_upload_success_flex(filename, subject, grade)
                    try:
                        self.line_bot_api.push_message(user_id, flex_message)
                    except Exception as e:
                        return jsonify({"status": "error", "message": f"通知發送失敗: {e}"}), 500

                    return '''
                    <!doctype html>
                    <html>
                    <head>
                        <script>
                            alert("檔案上傳成功，筆記將於審核後上架，返回LINE頁面");
                            window.location.href = "https://line.me/R/ti/p/@625evpbz";
                        </script>
                    </head>
                    <body></body>
                    </html>
                    '''
                else:
                    return jsonify({"status": "error", "message": "不支持的文件格式！"}), 400

            return render_template("upload.html")

    def allowed_file(self, filename):
        """檢查檔案格式是否允許"""
        return "." in filename and filename.rsplit(".", 1)[1].lower() in self.ALLOWED_EXTENSIONS

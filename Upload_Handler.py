from flask import Blueprint, render_template, request, jsonify
from werkzeug.utils import secure_filename
from threading import Thread
from utils import background_upload_and_save
import os
import json


class UploadHandler:
    ALLOWED_EXTENSIONS = {"pdf", "png", "jpg", "jpeg", "doc", "docx"}

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
            if request.method == "POST":
                file = request.files.get("file")
                subject = request.form.get("subject")
                grade = request.form.get("grade")
                username = request.form.get("username")
                year = request.form.get("year")

                # 驗證表單數據
                if not subject or not grade:
                    return jsonify({"status": "error", "message": "請填寫完整訊息！"}), 400
                if not username or not self.is_valid_username(username):
                    return jsonify({"status": "error", "message": "請提供有效的用戶名！"}), 400

                # 驗證文件格式
                if file and self.allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(self.upload_folder, filename)
                    file.save(file_path)

                    # 後台處理檔案上傳
                    Thread(target=background_upload_and_save, args=(
                        username, year,filename, file_path, subject, grade, self.folder_id, self.line_bot_api
                    )).start()

                    return '''
                    <!doctype html>
                    <html>
                    <head>
                        <script>
                            alert("檔案上傳成功，筆記將於審核後上架，返回 LINE頁面");
                            window.location.href = "line://nv/chat";
                        </script>
                    </head>
                    <body></body>
                    </html>
                    '''
                return jsonify({"status": "error", "message": "不支持的文件格式！"}), 400

            return render_template("upload.html")

    def allowed_file(self, filename):
        """檢查檔案格式是否允許"""
        return "." in filename and filename.rsplit(".", 1)[1].lower() in self.ALLOWED_EXTENSIONS

    def is_valid_username(self, username):
        """驗證用戶名是否有效"""
        return username.isalnum() and len(username) <= 30

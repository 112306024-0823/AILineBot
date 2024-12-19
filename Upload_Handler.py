from flask import Blueprint, render_template, request, jsonify
from threading import Thread
from utils import background_upload_and_save
import os

class UploadHandler:
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
                user_id = request.form.get("user_id")   #隱藏字段


                if not subject or not grade:
                    return jsonify({"status": "error", "message": "請填寫完整的資訊！"})
                
                if not user_id:
                    return "無法獲取 user_id", 401

                if file and self.allowed_file(file.filename):
                    file_path = os.path.join(self.upload_folder, file.filename)
                    file.save(file_path)

                    # 後台處理檔案上傳
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

            return render_template("upload.html")

    def allowed_file(self, filename):
        """檢查檔案格式是否允許"""
        allowed_extensions = {"pdf", "png", "jpg", "jpeg", "doc", "docx"}
        return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions

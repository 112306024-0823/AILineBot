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
                # 獲取表單資料
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
        """檢查檔案是否符合允許的格式"""
        allowed_extensions = {"pdf", "png", "jpg", "jpeg", "doc", "docx"}
        return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions

    def render_upload_form(self):
        """返回美化的上傳檔案 HTML 表單頁面"""
        return '''
        <!doctype html>
        <html>
        <head>
            <title>檔案上傳</title>
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <style>
                body {
                    font-family: Arial, sans-serif;
                    background-color: #f4f4f4;
                    margin: 0;
                    padding: 0;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                }
                .upload-container {
                    background: white;
                    padding: 20px 30px;
                    border-radius: 10px;
                    box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);
                    width: 100%;
                    max-width: 400px;
                    box-sizing: border-box;
                }
                .upload-container h1 {
                    font-size: 24px;
                    margin-bottom: 20px;
                    text-align: center;
                    color: #333;
                }
                .upload-container label {
                    font-size: 14px;
                    color: #555;
                    margin-bottom: 5px;
                    display: block;
                }
                .upload-container input[type="text"],
                .upload-container select,
                .upload-container input[type="file"] {
                    width: 100%;
                    padding: 10px;
                    margin-bottom: 15px;
                    border: 1px solid #ddd;
                    border-radius: 5px;
                    font-size: 14px;
                    box-sizing: border-box;
                }
                .upload-container button {
                    background-color: #4CAF50;
                    color: white;
                    padding: 10px 15px;
                    border: none;
                    border-radius: 5px;
                    font-size: 16px;
                    cursor: pointer;
                    width: 100%;
                }
                .upload-container button:hover {
                    background-color: #45a049;
                }
                .upload-container .help-text {
                    font-size: 12px;
                    color: #888;
                    margin-top: -10px;
                    margin-bottom: 15px;
                }
            </style>
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
            <div class="upload-container">
                <h1>上傳檔案</h1>
                <form method="post" enctype="multipart/form-data" onsubmit="handleUpload(event)">
                    <label for="subject">科目名稱</label>
                    <input type="text" id="subject" name="subject" placeholder="例如：數學、物理" required>
                    <span class="help-text">* 可自行填寫科目名稱</span>
                    
                    <label for="grade">選擇年級</label>
                    <select id="grade" name="grade" required>
                        <option value="" disabled selected>請選擇年級</option>
                        <option value="大一">大一</option>
                        <option value="大二">大二</option>
                        <option value="大三">大三</option>
                        <option value="大四">大四</option>
                        <option value="研究生">研究生</option>
                    </select>
                    
                    <label for="file">選擇檔案</label>
                    <input type="file" id="file" name="file" accept=".pdf,.png,.jpg,.jpeg,.doc,.docx" required>
                    
                    <button type="submit">上傳</button>
                </form>
            </div>
        </body>
        </html>
        '''


import os
from flask import Blueprint, request, jsonify
from threading import Thread

def background_upload_and_save(user_id, file_name, file_path, subject, grade):
    """
    背景處理檔案上傳到 Google Drive 和儲存到 Firebase 的邏輯。
    """
    try:
        print(f"開始處理檔案上傳：{file_name}, 科目：{subject}, 年級：{grade}")

        # 上傳到 Google Drive 並獲取下載連結
        file_url = upload_file_to_google_drive(file_path, file_name)

        # 儲存檔案資訊到 Firebase
        db.collection("notes").add({
            "user_id": user_id,
            "file_name": file_name,
            "file_url": file_url,
            "subject": subject,
            "grade": grade,
            "status": "審核中"  # 設置檔案狀態
        })

        print(f"檔案已上傳到 Google Drive，並儲存到 Firebase：{file_url}")

        # 刪除本地檔案
        os.remove(file_path)
        print(f"本地檔案已刪除：{file_path}")

    except Exception as e:
        print(f"背景處理失敗：{e}")

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

    def render_upload_form(self):
        return '''
        <!doctype html>
        <html>
        <head>
            <title>檔案上傳</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    background-color: #f4f4f4;
                    margin: 0;
                    padding: 20px;
                    display: flex;
                    justify-content: center;
                    align-items: center;
                    height: 100vh;
                }
                .upload-form {
                    background: #ffffff;
                    padding: 20px;
                    border-radius: 8px;
                    box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
                    width: 80%; /* 設定寬度佔80% */
                    max-width: 400px; /* 最大寬度限制 */
                    box-sizing: border-box;
                }
                .upload-form h1 {
                    font-size: 20px;
                    text-align: center;
                    color: #333333;
                    margin-bottom: 20px;
                }
                .upload-form label {
                    display: block;
                    margin-bottom: 8px;
                    font-weight: bold;
                    color: #555555;
                }
                .upload-form input[type="text"], 
                .upload-form select,
                .upload-form input[type="file"] {
                    width: 100%;
                    padding: 10px;
                    margin-bottom: 15px;
                    border: 1px solid #cccccc;
                    border-radius: 4px;
                    box-sizing: border-box;
                }
                .upload-form button {
                    background-color: #4CAF50;
                    color: white;
                    padding: 10px 15px;
                    border: none;
                    border-radius: 4px;
                    cursor: pointer;
                    font-size: 16px;
                    width: 100%;
                }
                .upload-form button:hover {
                    background-color: #45a049;
                }
            </style>
            <script>
            // 上傳成功後自動跳轉回 LINE
            function handleUploadResponse(response) {
                if (response.status === 'success') {
                    alert('檔案上傳成功！即將返回 LINE');
                    setTimeout(() => {
                        window.location.href = "line://nv/chat"; // 跳回 LINE 聊天
                    }, 2000);
                } else {
                    alert(response.message || '上傳失敗，請重試！');
                }
            }

            async function submitForm(event) {
                event.preventDefault();
                const form = event.target;
                const formData = new FormData(form);

                const response = await fetch(form.action, {
                    method: form.method,
                    body: formData,
                });
                const jsonResponse = await response.json();
                handleUploadResponse(jsonResponse);
            }
        </script>
        </head>
        <body>
            <form class="upload-form" method="post" enctype="multipart/form-data">
                <h1>檔案上傳</h1>
                <label for="subject">科目名稱</label>
                <input type="text" id="subject" name="subject" placeholder="例如：數學" required>
                
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
        </body>
        </html>
        '''

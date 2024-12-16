class UploadHandler:
    def __init__(self, app, upload_folder="uploads"):
        self.app = app
        self.upload_folder = upload_folder
        os.makedirs(self.upload_folder, exist_ok=True)

        # 註冊路由
        self.setup_routes()

    def setup_routes(self):
        @self.app.route('/upload', methods=['GET', 'POST'])
        def upload():
            if request.method == 'POST':
                file = request.files.get('file')
                if file and self.allowed_file(file.filename):
                    file_path = os.path.join(self.upload_folder, file.filename)
                    file.save(file_path)
                    # 回傳檔案連結
                    return jsonify({
                        "status": "success",
                        "url": f"https://{request.host}/{file_path}"
                    })
                return jsonify({"status": "error", "message": "未接收到有效檔案"})
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

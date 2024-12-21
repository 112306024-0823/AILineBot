from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload
import os
import json

def check_environment_variables():
    """檢查必要的環境變數是否已設置"""
    required_env_vars = ["GOOGLE_DRIVE_CREDENTIALS", "FIREBASE_CREDENTIALS", "CHANNEL_ACCESS_TOKEN", "CHANNEL_SECRET"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        raise EnvironmentError(f"缺少以下環境變數：{', '.join(missing_vars)}")

def upload_file_to_google_drive(file_path, file_name, folder_id):
    """將檔案上傳到 Google Drive，並返回下載連結"""
    try:
        credentials_info = json.loads(os.getenv("GOOGLE_DRIVE_CREDENTIALS"))
        creds = service_account.Credentials.from_service_account_info(credentials_info)
        service = build("drive", "v3", credentials=creds)

        file_metadata = {"name": file_name, "parents": [folder_id]}
        media = MediaFileUpload(file_path, resumable=True)
        file = service.files().create(body=file_metadata, media_body=media, fields="id").execute()
        file_id = file.get("id")

        service.permissions().create(fileId=file_id, body={"type": "anyone", "role": "reader"}).execute()

        return f"https://drive.google.com/uc?id={file_id}&export=download"
    except Exception as e:
        raise Exception(f"Google Drive 上傳失敗：{e}")

def save_file_metadata(user_id, file_name, file_url, subject="", grade=""):
    """儲存文件元數據到 Firestore"""
    try:
        from firebase_admin import firestore
        db = firestore.client()
        db.collection("notes").add({
            "user_id": user_id,
            "file_name": file_name,
            "file_url": file_url,
            "subject": subject,
            "grade": grade,
            "status": "審核中"
        })
    except Exception as e:
        raise Exception(f"儲存文件元數據失敗：{e}")

# firebase_utils.py
import firebase_admin
from firebase_admin import credentials, firestore
import os
import json

# 初始化 Firebase
def initialize_firebase():
    if not firebase_admin._apps:  # 確保只初始化一次
        try:
            firebase_info = json.loads(os.getenv("FIREBASE_CREDENTIALS", "{}"))
            if not firebase_info:
                raise ValueError("FIREBASE_CREDENTIALS 環境變數未設置或無效。")
            cred = credentials.Certificate(firebase_info)
            firebase_admin.initialize_app(cred)
            print("Firebase 初始化成功")
        except Exception as e:
            print(f"Firebase 初始化失敗：{e}")
            raise

# 確保 Firebase 已初始化並返回 Firestore 客戶端
initialize_firebase()
db = firestore.client()

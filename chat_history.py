from firebase_admin import firestore
from datetime import datetime
from firebase_utils import db  # 引入 Firestore 客戶端


MAX_HISTORY_LENGTH = 10  # 最大對話歷史長度

def save_chat_history(user_id, role, content):
    """將對話存入 Firebase"""
    try:
        doc_ref = db.collection('chat_history').document(user_id)
        doc = doc_ref.get()
        if doc.exists:
            # 如果有歷史對話，追加到陣列
            conversations = doc.to_dict().get('conversations', [])
            conversations.append({"role": role, "content": content})
            conversations = trim_chat_history(conversations)  # 修剪歷史
            doc_ref.update({
                "conversations": conversations,
                "last_updated": datetime.utcnow()
            })
        else:
            # 如果是新用戶，創建新的對話記錄
            doc_ref.set({
                "conversations": [{"role": role, "content": content}],
                "last_updated": datetime.utcnow()
            })
        return True
    except Exception as e:
        print(f"Error saving chat history: {e}")
        return False

def load_chat_history(user_id):
    """從 Firebase 加載用戶對話歷史"""
    try:
        doc_ref = db.collection('chat_history').document(user_id)
        doc = doc_ref.get()
        if doc.exists:
            return doc.to_dict().get('conversations', [])
        return []
    except Exception as e:
        print(f"Error loading chat history: {e}")
        return []

def trim_chat_history(conversations):
    """修剪對話歷史，保留最近的對話"""
    if len(conversations) > MAX_HISTORY_LENGTH:
        return conversations[-MAX_HISTORY_LENGTH:]
    return conversations

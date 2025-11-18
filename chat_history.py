from collections import deque
from threading import Lock

MAX_HISTORY_LENGTH = 10  # 最大對話歷史長度

# 使用記憶體儲存對話歷史
_chat_history_store = {}
_store_lock = Lock()

def save_chat_history(user_id, role, content):
    """將對話存入記憶體"""
    try:
        with _store_lock:
            if user_id not in _chat_history_store:
                _chat_history_store[user_id] = deque(maxlen=MAX_HISTORY_LENGTH)
            _chat_history_store[user_id].append({"role": role, "content": content})
        return True
    except Exception as e:
        print(f"Error saving chat history: {e}")
        return False

def load_chat_history(user_id):
    """從記憶體加載用戶對話歷史"""
    try:
        with _store_lock:
            history = _chat_history_store.get(user_id, deque())
            return list(history)
    except Exception as e:
        print(f"Error loading chat history: {e}")
        return []

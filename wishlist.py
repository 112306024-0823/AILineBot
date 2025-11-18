from datetime import datetime
from threading import Lock

# 使用記憶體儲存許願清單
_wishlist_entries = []
_wishlist_lock = Lock()

def submit_wishlist(user_id, course, description):
    """用戶提交筆記許願（儲存在記憶體）"""
    try:
        with _wishlist_lock:
            _wishlist_entries.append({
                'user_id': user_id,
                'course': course,
                'description': description,
                'created_at': datetime.utcnow()
            })
        return True
    except Exception as e:
        print(f"Error submitting wishlist: {e}")
        return False

def get_wishlist(limit=5):
    """從記憶體獲取最近的許願"""
    try:
        with _wishlist_lock:
            sorted_entries = sorted(_wishlist_entries, key=lambda x: x.get('created_at', datetime.min), reverse=True)
            return [
                {"course": entry.get("course"), "description": entry.get("description")}
                for entry in sorted_entries[:limit]
            ]
    except Exception as e:
        print(f"Error fetching wishlist: {e}")
        return []

def delete_user_wishlist(user_id, course):
    """刪除用戶的特定許願"""
    try:
        with _wishlist_lock:
            original_length = len(_wishlist_entries)
            _wishlist_entries[:] = [
                entry for entry in _wishlist_entries
                if not (entry.get('user_id') == user_id and entry.get('course') == course)
            ]
            return len(_wishlist_entries) != original_length
    except Exception as e:
        print(f"Error deleting wishlist: {e}")
        return False

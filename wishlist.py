from flask import request
from datetime import datetime
from firebase_admin import firestore

# 初始化 Firebase
db = firestore.client()

def submit_wishlist(user_id, course, description):
    """用戶提交筆記許願"""
    try:
        db.collection('note_wishlist').add({
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
    """從 Firebase 獲取最近的許願"""
    try:
        wishes = db.collection('note_wishlist').order_by('created_at', direction=firestore.Query.DESCENDING).limit(limit).stream()
        return [{"course": w.to_dict().get("course"), "description": w.to_dict().get("description")} for w in wishes]
    except Exception as e:
        print(f"Error fetching wishlist: {e}")
        return []

def delete_user_wishlist(user_id, course):
    """刪除用戶的特定許願"""
    try:
        wishes = db.collection('note_wishlist').where('user_id', '==', user_id).where('course', '==', course).stream()
        for wish in wishes:
            db.collection('note_wishlist').document(wish.id).delete()
        return True
    except Exception as e:
        print(f"Error deleting wishlist: {e}")
        return False

from firebase_admin import firestore
from linebot.models import FlexSendMessage
from notifications import send_review_failure_notification,send_review_success_notification

def monitor_review_status(line_bot_api):
    """監聽 Firebase 中的筆記審核狀態變更"""
    db = firestore.client()
    notes_ref = db.collection("notes")

    # 設置監聽器
    def on_snapshot(docs, changes, read_time):
        for change in changes:
            if change.type.name == "MODIFIED":  # 當資料被修改時觸發
                note = change.document.to_dict()
                print(f"更新的文件內容：{note}")

                user_id = note.get("user_id")
                file_name = note.get("file_name")
                subject = note.get("subject", "未知科目")
                grade = note.get("grade", "未知年級")
                status = note.get("status")
                print(f"更新的文件內容：{note}")

                reason = note.get("reason", "未提供原因")


                if status == "上架成功":
                    send_review_success_notification(line_bot_api, user_id, file_name, subject, grade, note.get("file_url"))
                    notes_ref.document(change.document.id).update({"status": "已通知"})
                elif status == "審核失敗":
                    send_review_failure_notification(line_bot_api, user_id, file_name, reason)
                    notes_ref.document(change.document.id).update({"status": "已通知"})

    # 啟用監聽器
    notes_ref.on_snapshot(on_snapshot)

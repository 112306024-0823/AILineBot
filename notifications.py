class NotificationHandler:
    """用於處理審核通知的類別"""

    @staticmethod
    def send_review_success_notification(line_bot_api, user_id, file_name, subject, grade, file_url):
        """發送審核成功通知"""
        flex_message = NotificationHandler.create_review_success_flex(file_name, subject, grade, file_url)
        try:
            line_bot_api.push_message(user_id, flex_message)
            print(f"審核成功通知已發送給用戶 {user_id}，檔案: {file_name}")
        except Exception as e:
            print(f"通知發送失敗: {e}")

    @staticmethod
    def send_review_failure_notification(line_bot_api, user_id, file_name, reason):
        """發送審核失敗通知"""
        flex_message = NotificationHandler.create_review_failure_flex(file_name, reason)
        try:
            line_bot_api.push_message(user_id, flex_message)
            print(f"審核失敗通知已發送給用戶 {user_id}，檔案: {file_name}")
        except Exception as e:
            print(f"通知發送失敗: {e}")

    @staticmethod
    def create_review_success_flex(file_name, subject, grade, file_url):
        """建立審核成功的 Flex Message"""
        return FlexSendMessage(
            alt_text="審核成功通知",
            contents={
                "type": "bubble",
                "hero": {"type": "image", "url": "https://yourdomain.com/static/images/review_success.png", "size": "full", "aspectRatio": "20:10", "aspectMode": "cover"},
                "body": {"type": "box", "layout": "vertical", "contents": [
                    {"type": "text", "text": "審核成功！", "weight": "bold", "size": "xl", "align": "center", "color": "#1DB446"},
                    {"type": "text", "text": "您的筆記已成功上架，感謝您的分享！", "wrap": True, "size": "md", "margin": "md", "color": "#666666"},
                    {"type": "separator", "margin": "md"},
                    {"type": "text", "text": f"檔案名稱: {file_name}", "wrap": True, "size": "sm", "color": "#666666"},
                    {"type": "text", "text": f"科目名稱: {subject}", "wrap": True, "size": "sm", "color": "#666666"},
                    {"type": "text", "text": f"年級: {grade}", "wrap": True, "size": "sm", "color": "#666666"},
                    {"type": "button", "style": "primary", "action": {"type": "uri", "label": "查看筆記", "uri": file_url}}
                ]}
            }
        )

    @staticmethod
    def create_review_failure_flex(file_name, reason):
        """建立審核失敗的 Flex Message"""
        return FlexSendMessage(
            alt_text="審核失敗通知",
            contents={
                "type": "bubble",
                "hero": {"type": "image", "url": "https://yourdomain.com/static/images/review_failed.png", "size": "full", "aspectRatio": "20:10", "aspectMode": "cover"},
                "body": {"type": "box", "layout": "vertical", "contents": [
                    {"type": "text", "text": "審核失敗", "weight": "bold", "size": "xl", "align": "center", "color": "#FF6B6E"},
                    {"type": "text", "text": "很抱歉，您的筆記未能通過審核。", "wrap": True, "size": "md", "margin": "md", "color": "#666666"},
                    {"type": "separator", "margin": "md"},
                    {"type": "text", "text": f"檔案名稱: {file_name}", "wrap": True, "size": "sm", "color": "#666666"},
                    {"type": "text", "text": f"失敗原因: {reason}", "wrap": True, "size": "sm", "color": "#FF6B6E"}
                ]}
            }
        )

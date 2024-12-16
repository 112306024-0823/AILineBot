from linebot.models import FlexSendMessage

def create_upload_success_flex(file_name, subject, grade):
    """建立 Flex Message 用於通知檔案上傳成功"""
    return FlexSendMessage(
        alt_text="檔案上傳成功通知",
        contents={
            "type": "bubble",
            "hero": {
                "type": "image",
                "url": "https://via.placeholder.com/1024x512.png?text=檔案上傳成功",
                "size": "full",
                "aspectRatio": "20:10",
                "aspectMode": "cover"
            },
            "body": {
                "type": "box",
                "layout": "vertical",
                "contents": [
                    {
                        "type": "text",
                        "text": "檔案上傳成功！",
                        "weight": "bold",
                        "size": "xl",
                        "margin": "md",
                        "align": "center"
                    },
                    {
                        "type": "separator",
                        "margin": "md"
                    },
                    {
                        "type": "box",
                        "layout": "vertical",
                        "margin": "lg",
                        "spacing": "sm",
                        "contents": [
                            {
                                "type": "box",
                                "layout": "baseline",
                                "contents": [
                                    {"type": "text", "text": "檔案名稱", "color": "#aaaaaa", "size": "sm", "flex": 2},
                                    {"type": "text", "text": file_name, "wrap": True, "color": "#666666", "size": "sm", "flex": 4}
                                ]
                            },
                            {
                                "type": "box",
                                "layout": "baseline",
                                "contents": [
                                    {"type": "text", "text": "科目名稱", "color": "#aaaaaa", "size": "sm", "flex": 2},
                                    {"type": "text", "text": subject, "wrap": True, "color": "#666666", "size": "sm", "flex": 4}
                                ]
                            },
                            {
                                "type": "box",
                                "layout": "baseline",
                                "contents": [
                                    {"type": "text", "text": "年級", "color": "#aaaaaa", "size": "sm", "flex": 2},
                                    {"type": "text", "text": grade, "wrap": True, "color": "#666666", "size": "sm", "flex": 4}
                                ]
                            },
                            {
                                "type": "box",
                                "layout": "baseline",
                                "contents": [
                                    {"type": "text", "text": "目前狀態", "color": "#aaaaaa", "size": "sm", "flex": 2},
                                    {"type": "text", "text": "審核中", "wrap": True, "color": "#FF6B6E", "size": "sm", "flex": 4}
                                ]
                            }
                        ]
                    }
                ]
            }
        }
    )

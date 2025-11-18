from flask import Flask, request, abort, jsonify
import json
from chat_history import save_chat_history, load_chat_history

from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, QuickReply, QuickReplyButton,
    URIAction, ImageSendMessage, MessageAction, ImageMessage
)
from Upload_Handler import UploadHandler
from utils import check_environment_variables
import os
import random
from threading import Lock

# 初始化環境變數檢查
check_environment_variables()

NOTES_PRICING = {
    "A01": 150,
    "A02": 150,
    "A03": 150,
    "A04": 30,
    "A05": 150,
    "A06": 150,
    "A07": 150,
    "A08": 150,
    "A09": 150,
    "A10": 100,
    "A11": 150,
    "A12": 150
}


# 初始化 Flask 和 LINE API
app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

ECHO_MODE_ENABLED = os.getenv("ECHO_MODE_ENABLED", "true").lower() == "true"

# 用戶狀態管理（使用記憶體儲存）
_user_states = {}
_user_states_lock = Lock()

def get_user_state(user_id):
    """獲取用戶狀態"""
    with _user_states_lock:
        return _user_states.get(user_id, "default")

def set_user_state(user_id, state):
    """設定用戶狀態"""
    with _user_states_lock:
        _user_states[user_id] = state

# 簡化的回應函數（暫時使用 echo，之後可整合 AI）
def generate_E_response(user_id, user_message):
    """生成回應（暫時簡化版本）"""
    # 儲存對話歷史
    save_chat_history(user_id, "user", user_message)
    # 暫時回傳簡單回應，之後可整合 AI 或查詢商品功能
    response = f"收到您的訊息：{user_message}"
    save_chat_history(user_id, "assistant", response)
    return response

# 檢查是否為問候語
def is_greeting(message: str) -> bool:
    """檢查訊息是否為常見問候語"""
    greetings = [
        "你好", "您好", "hi", "hello", "嗨", "哈囉", "哈囉", "hey",
        "早安", "午安", "晚安", "早上好", "下午好", "晚上好",
        "你好嗎", "您好嗎", "how are you", "how are you doing"
    ]
    message_lower = message.lower().strip()
    return message_lower in [g.lower() for g in greetings]

# 生成問候語回應
def generate_greeting_response() -> str:
    """生成問候語回應"""
    responses = [
        "你好！我是 Enote 的學霸小E，很高興認識你！😊\n\n我可以幫你：\n📚 上傳和分享筆記\n🔍 尋找需要的筆記\n💝 許願想要的筆記內容\n\n點擊下方按鈕開始使用吧！",
        "您好！歡迎使用 Enote！我是學霸小E 👋\n\n這裡是筆記分享平台，你可以：\n✨ 上傳自己的筆記\n🔎 搜尋需要的筆記\n🎯 許願想要的筆記\n\n需要什麼協助嗎？",
        "嗨！很高興見到你！我是學霸小E 📖\n\nEnote 是一個筆記分享平台，讓學習資源更容易取得！\n\n你可以透過下方按鈕來：\n📤 上傳筆記\n🔍 找筆記\n💭 許願筆記\n\n有什麼需要幫忙的嗎？"
    ]
    return random.choice(responses)

# 註冊 UploadHandler
upload_handler = UploadHandler(upload_folder="uploads", line_bot_api=line_bot_api)
app.register_blueprint(upload_handler.blueprint)

@app.route("/", methods=['GET'])
def index():
    """根路由，返回服務狀態"""
    return jsonify({
        "status": "running",
        "service": "Enote LINE Bot",
        "version": "1.0.0"
    }), 200

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature', None)
    body = request.get_data(as_text=True)

    app.logger.info(f"Request body: {body}")
    if not signature:
        app.logger.error("缺少 X-Line-Signature")
        abort(400)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.error("簽名驗證失敗")
        abort(400)
    return 'OK'

# 快速回覆選項生成
def get_quick_reply(user_state):
    default_quick_reply = [
        QuickReplyButton(action=MessageAction(label="找學霸小E談談心！", text="跟小E對話")),
        QuickReplyButton(action=MessageAction(label="上傳筆記", text="我要上傳筆記")),
        QuickReplyButton(action=MessageAction(label="找筆記", text="找筆記")),
        QuickReplyButton(action=MessageAction(label="許願池", text="筆記許願池")),
        QuickReplyButton(action=MessageAction(label="了解Enote", text="介紹Enote"))
    ]
    chat_quick_reply = [
        QuickReplyButton(action=MessageAction(label="告訴我期末如何歐趴", text="告訴我期末如何歐趴")),
        QuickReplyButton(action=MessageAction(label="給我一點學習建議", text="給我一點學習建議")),
        QuickReplyButton(action=MessageAction(label="吐槽我為甚麼還沒開始讀書", text="吐槽我為甚麼還沒開始讀書")),
        QuickReplyButton(action=MessageAction(label="許願池", text="筆記許願池")),
        QuickReplyButton(action=MessageAction(label="退出小E談話模式", text="退出小E模式"))
    ]
    return QuickReply(items=chat_quick_reply if user_state == "chat_with_xiaoE" else default_quick_reply)

# 處理用戶訊息邏輯
@handler.add(MessageEvent, message=TextMessage)
def handle_text_message(event):
    user_id = getattr(event.source, 'user_id', None)
    if not user_id:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="無法獲取用戶 ID，請確保您已添加好友。")
        )
        return

    message_text = event.message.text.strip()
    if ECHO_MODE_ENABLED:
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=message_text)
        )
        return

    user_state = get_user_state(user_id)

    if user_state == "default":
        # 檢查是否為問候語
        if is_greeting(message_text):
            reply_message = TextSendMessage(
                text=generate_greeting_response(),
                quick_reply=get_quick_reply("default")
            )
        elif message_text == "跟小E對話":
            set_user_state(user_id, "chat_with_xiaoE")
            reply_message = TextSendMessage(
                text="你好，我是學霸小E，歡迎跟我聊天！",
                quick_reply=get_quick_reply("chat_with_xiaoE")
            )

        elif message_text == "我要上傳筆記":
            quick_reply = QuickReply(items=[
                QuickReplyButton(action=URIAction(label="點擊上傳檔案", uri=f"https://{request.host}/upload?user_id={user_id}")),
                QuickReplyButton(action=MessageAction(label="找筆記", text="找筆記"))

            ])
            reply_message = TextSendMessage(
                text="請點擊下方按鈕上傳檔案：", quick_reply=quick_reply
            )
        elif message_text.startswith("購買筆記"):
            import re
            match = re.match(r"購買筆記\s*(A\d{2})", message_text)
            if match:
                note_code = match.group(1)
                if note_code in NOTES_PRICING:
                    price = NOTES_PRICING[note_code]
                    quick_reply = QuickReply(items=[
                        QuickReplyButton(action=MessageAction(label="LINE Pay", text="選擇 LINE Pay")),
                        QuickReplyButton(action=MessageAction(label="郵局匯款", text="選擇 郵局匯款"))
                    ])
                    reply_message = TextSendMessage(
                        text=f"您選擇購買筆記 {note_code}，價格為 {price} 元。請選擇您的付款方式：",
                        quick_reply=quick_reply
                    )
                else:
                    reply_message = TextSendMessage(
                        text="🌟 未找到該筆記編號，請確認後重新輸入。"
                    )
            else:
                reply_message = TextSendMessage(
                    text="🌟 請提供有效的筆記編號，例如：購買筆記 A01。"
                )
        elif message_text == "選擇 LINE Pay":
            linepay_image_url = f"https://{request.host}/static/images/linepay_qrcode.jpg"
            text_message = TextSendMessage(
                text=("✨ 感謝您的支持！\n\n"
                      "📷 請掃描以下的 QR Code 完成付款：\n\n"
                      "📤 完成付款後，請回傳付款截圖，我們將在確認款項後提供限時有效的下載連結給您！\n\n"
                      "🌟 感謝您的支持與信任，期待您的購買！ 🛍️"),
                quick_reply=get_quick_reply(user_state)
            )
            image_message = ImageSendMessage(
                original_content_url=linepay_image_url,
                preview_image_url=linepay_image_url
            )
            line_bot_api.reply_message(event.reply_token, [text_message, image_message])
            return
        elif message_text == "選擇 郵局匯款":
            reply_message = TextSendMessage(
                text=("✨ 感謝您的支持！\n\n"
                      "🏦郵局匯款\n\n"
                      "銀行代碼：700\n"
                      "帳號：0000023980362050\n\n"
                      "📤 完成匯款後，請回傳付款截圖，我們將在確認款項後提供限時有效的下載連結給您！\n\n"
                      "🌟 感謝您的支持，祝期末HIGH PASS！ 🎉"),
                quick_reply=get_quick_reply(user_state)
            )
        else:
            reply_message = TextSendMessage(
                text=" ",
                quick_reply=get_quick_reply("default")
            )
        line_bot_api.reply_message(event.reply_token, reply_message)

    

    elif user_state == "chat_with_xiaoE":
        if message_text == "退出小E模式":
            set_user_state(user_id, "default")
            reply_message = TextSendMessage(
                text="已退出學霸小E模式，趕快去讀書啦！",
                quick_reply=get_quick_reply("default")
            )

        elif message_text == "找筆記":
            set_user_state(user_id, "default")
            quick_reply=get_quick_reply("default")

        elif message_text == "筆記許願池":
            set_user_state(user_id, "default")
            quick_reply=get_quick_reply("default")

 
        elif "購買筆記" in message_text:
            set_user_state(user_id, "default")
            quick_reply=get_quick_reply("default")

        elif "上傳筆記" in message_text:
            set_user_state(user_id, "default")
            quick_reply=get_quick_reply("default")

        else:
            reply_content = generate_E_response(user_id, message_text)
            reply_message = TextSendMessage(
                text=reply_content, quick_reply=get_quick_reply("chat_with_xiaoE")
            )
        line_bot_api.reply_message(event.reply_token, reply_message)

@handler.add(MessageEvent, message=ImageMessage) 
def handle_image_message(event):
    reply_token = event.reply_token
    confirmation_message = TextSendMessage(
        text="✅ 已收到您的付款證明。我們將在確認款項後提供下載連結！"
    )
    line_bot_api.reply_message(reply_token, confirmation_message)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    # 啟動 Flask 應用
    app.run(host='0.0.0.0', port=port)

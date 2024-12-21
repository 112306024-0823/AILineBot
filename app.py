from flask import Flask, request, abort, jsonify
import json
import openai
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import (
    MessageEvent, TextMessage, TextSendMessage, QuickReply, QuickReplyButton,
    URIAction, ImageSendMessage, MessageAction, ImageMessage
)
from Upload_Handler import UploadHandler
from utils import check_environment_variables
import os
import firebase_admin
from firebase_admin import credentials, firestore
from threading import Thread
from review_monitor import monitor_review_status  # 假設監聽邏輯放在 review_monitor.py

# 初始化環境變數檢查
check_environment_variables()

NOTES_PRICING = {
    "A01": 150,
    "A02": 150,
    "A03": 150,
    "A04": 50,
    "A05": 50
}

# 初始化 Firebase
try:
    firebase_info = json.loads(os.getenv("FIREBASE_CREDENTIALS"))
    cred = credentials.Certificate(firebase_info)
    firebase_admin.initialize_app(cred)
    db = firestore.client()
    print("Firebase 初始化成功")
except Exception as e:
    print(f"Firebase 初始化失敗：{e}")
    raise

# 初始化 Flask 和 LINE API
app = Flask(__name__)
line_bot_api = LineBotApi(os.getenv('CHANNEL_ACCESS_TOKEN'))
handler = WebhookHandler(os.getenv('CHANNEL_SECRET'))

# 從環境變數中獲取 OpenAI API 金鑰
openai.api_key = os.getenv("OPENAI_API_KEY")
# 用戶狀態管理
user_states = {}  # 用來存儲用戶的狀態

# 更新生成學霸小E回應的函數
def generate_E_response(user_message):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",  # 可以使用 "gpt-4" 來提高創意和多樣性
            messages=[
                {"role": "system", "content": 
                    "你是學霸小E，你是幽默風趣且毒舌的勸學專家、喜歡吐槽跟聊天，最近期末將至，你專治那些臨時抱佛腳、偷懶或不想讀書的學生。每次回應不超過130字，並且能夠以充滿挑戰、幽默的語氣進行反擊。另外你也是ENOTE讀書會的代言人，ENOTE 的相關提及可以偶爾自然融入不需要常常提及，例如推薦用戶貢獻、成為Enote的筆記供給者賺錢，或追蹤ENOTE"},
                
                {"role": "user", "content": user_message}  # 用戶的輸入
            ],
            max_tokens=150,  # 設定最大 tokens 數量
            temperature=0.85,  # 增加隨機性，讓回應更具多樣性
            top_p=0.9  # 增加多樣性，讓回應更有創意
        )
        return response.choices[0].message['content'].strip()  # 提取生成的回應
    except Exception as e:
        print(f"Error: {e}")
        return "抱歉，我無法理解您的問題，請稍後再試。"

# 註冊 UploadHandler
FOLDER_ID = "1h7DL1gRlB96Dpxmad0-gMvSDdVjm57vn"
upload_handler = UploadHandler(upload_folder="uploads", line_bot_api=line_bot_api, folder_id=FOLDER_ID)
app.register_blueprint(upload_handler.blueprint)


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


# 處理用戶訊息的邏輯
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

    # 設置用戶的初始狀態，如果尚未存在
    if user_id not in user_states:
        user_states[user_id] = "default"  # 設置初始狀態為 'default'

    # 快速回覆選項的邏輯
    def get_quick_reply():
        # 默認顯示這些選項，不管是處於哪個模式
        default_quick_reply = [
            QuickReplyButton(action=MessageAction(label="學霸小E等你！", text="跟小E對話")),
            QuickReplyButton(action=MessageAction(label="上傳筆記", text="我要上傳筆記")),
            QuickReplyButton(action=MessageAction(label="快來找筆記！", text="找筆記"))
        ]

        if user_states[user_id] == "chat_with_xiaoE":
            # 在學霸小E對話模式下，顯示「退出小E對話」選項
            return QuickReply(items=[
                QuickReplyButton(action=MessageAction(label="小E，別再打擊我了掰", text="退出小E模式"))
            ] + default_quick_reply)

        elif user_states[user_id] == "buy_note":
            # 購買筆記模式，顯示付款方式選項（LINE Pay 或郵局匯款）
            return QuickReply(items=[
                QuickReplyButton(action=MessageAction(label="LINE Pay", text="選擇 LINE Pay")),
                QuickReplyButton(action=MessageAction(label="郵局匯款", text="選擇 郵局匯款"))
            ] + default_quick_reply)

        # 默認返回基本選項（即不跟小E對話的模式）
        return QuickReply(items=default_quick_reply)

    # 進入小E對話模式
    if message_text == "跟小E對話":
        user_states[user_id] = "chat_with_xiaoE"
        reply_message = TextSendMessage(
            text="學霸小E已經啟動！請問，你準備好期末了嗎？",
            quick_reply=get_quick_reply()
        )
        line_bot_api.reply_message(event.reply_token, reply_message)

    # 退出小E對話模式
    elif message_text == "退出小E模式":
        user_states[user_id] = "default"
        reply_message = TextSendMessage(
            text="已退出學霸小E模式，學霸要來偷卷了",
            quick_reply=get_quick_reply()
        )
        line_bot_api.reply_message(event.reply_token, reply_message)

    # 學霸小E對話模式
    elif user_states[user_id] == "chat_with_xiaoE":
        reply_content = generate_E_response(message_text)  # 調用生成學霸小E回應的函數
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text=reply_content, quick_reply=get_quick_reply())  # 保持快速回覆按鈕
        )

    # 處理其他指令
    elif message_text == "我要上傳筆記":
        quick_reply = QuickReply(items=[QuickReplyButton(action=URIAction(label="點擊上傳檔案", uri=f"https://{request.host}/upload?user_id={user_id}"))])
        reply_message = TextSendMessage(
            text="請點擊下方按鈕上傳檔案：", quick_reply=quick_reply
        )
        line_bot_api.reply_message(event.reply_token, reply_message)

    elif message_text.startswith("購買筆記"):
        import re
        match = re.match(r"購買筆記\s*(A\d{2})", message_text)
        if not match:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="❌ 請提供有效的筆記編號，例如：購買筆記 A01。")
            )
            return

        note_code = match.group(1)
        if note_code in NOTES_PRICING:
            price = NOTES_PRICING[note_code]
            quick_reply = QuickReply(items=[
                QuickReplyButton(action=MessageAction(label="LINE Pay", text="選擇 LINE Pay")),
                QuickReplyButton(action=MessageAction(label="郵局匯款", text="選擇 郵局匯款"))
            ])
            reply_message = TextSendMessage(
                text=f"您選擇購買筆記 {note_code}，價格為 {price} 元。\n請選擇您的付款方式：",
                quick_reply=quick_reply
            )
            line_bot_api.reply_message(event.reply_token, reply_message)
        else:
            line_bot_api.reply_message(
                event.reply_token,
                TextSendMessage(text="❌ 未找到該筆記編號，請確認後重新輸入。")
            )

    elif message_text == "選擇 LINE Pay":
        linepay_image_url = f"https://{request.host}/static/images/linepay_qrcode.jpg"
        text_message = TextSendMessage(
            text=("✨ 感謝您的支持！\n\n"
                  "📷 請掃描以下的 QR Code 完成付款：\n\n"
                  "📤 完成付款後，請回傳付款截圖，我們將在確認款項後提供限時有效的下載連結給您！\n\n"
                  "🌟 感謝您的支持與信任，期待您的購買！ 🛍️"),quick_reply=quick_reply)

        
        image_message = ImageSendMessage(
            original_content_url=linepay_image_url,
            preview_image_url=linepay_image_url
        )
        line_bot_api.reply_message(event.reply_token, [text_message, image_message])
        

    elif message_text == "選擇 郵局匯款":
        reply_message = TextSendMessage(
            text=("✨ 感謝您的支持！\n\n"
                  "🏦郵局匯款\n\n"
                  "銀行代碼：700\n"
                  "帳號：0000023980362050\n\n"
                  "📤 完成匯款後，請回傳付款截圖，我們將在確認款項後提供限時有效的下載連結給您！\n\n"
                  "🌟 感謝您的支持，祝期末HIGH PASS！ 🎉"),quick_reply=quick_reply)
            
        
        line_bot_api.reply_message(event.reply_token, reply_message)



@handler.add(MessageEvent, message=ImageMessage)
def handle_image_message(event):
    reply_token = event.reply_token
    confirmation_message = TextSendMessage(
        text="✅ 已收到您的付款證明。我們將盡快處理並提供下載連結！"
    )
    line_bot_api.reply_message(reply_token, confirmation_message)


if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    
    # 啟動 Firebase 監聽器
    Thread(target=monitor_review_status, args=(line_bot_api,)).start()
    
    # 啟動 Flask 應用
    app.run(host='0.0.0.0', port=port)

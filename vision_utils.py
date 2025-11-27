import base64
import google.generativeai as genai
import os

# 設定 API Key
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))

def extract_keywords_from_image_gemini(image_bytes: bytes):
    """
    使用 Gemini 進行圖片理解（OCR + 商品辨識）
    回傳： keywords(list), full_text(str)
    """
    model = genai.GenerativeModel("gemini-2.5-flash")

    # 將圖片轉 base64
    b64 = base64.b64encode(image_bytes).decode()

    # Gemini 提示
    prompt = """
    請分析這張圖片內容，並輸出：
    1. 圖中出現的可能商品名稱
    2. 品牌
    3. 任何可用來搜尋商品的關鍵字（例如：可口可樂、麥香奶茶、乖乖、洗髮乳、牙膏...）
    4. 如果有文字（包裝上的OCR），請一起輸出。
    
    請輸出純文字，不要解釋。
    """

    response = model.generate_content(
        [
            {"mime_type": "image/jpeg", "data": image_bytes},
            prompt
        ]
    )

    full_text = response.text
    # 取出關鍵字（簡單切割，你可再優化）
    keywords = [w.strip() for w in full_text.split() if len(w.strip()) >= 2]

    return keywords[:10], full_text

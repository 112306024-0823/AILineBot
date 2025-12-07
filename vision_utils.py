import base64
import google.generativeai as genai
import os
import logging
from api_key_manager import get_api_key_manager

logger = logging.getLogger(__name__)

def extract_keywords_from_image_gemini(image_bytes: bytes):
    """
    使用 Gemini 進行圖片理解（OCR + 商品辨識）
    回傳： keywords(list), full_text(str)
    """
    api_manager = get_api_key_manager()
    model = api_manager.get_model("gemini-2.5-flash")

    # 將圖片轉 base64
    b64 = base64.b64encode(image_bytes).decode()

    # Gemini 提示 - 只辨識商品名稱和品牌
    prompt = """
    請分析這張圖片，只輸出商品名稱和品牌。

    輸出格式：
    商品名稱 品牌
    
    例如：
    可口可樂 Coca-Cola
    麥香奶茶 統一
    養樂多 養樂多
    
    如果只有商品名稱沒有品牌，只輸出商品名稱。
    如果只有品牌沒有商品名稱，只輸出品牌。
    
    只輸出商品名稱和品牌，不要其他文字或解釋。
    """

    # 使用 API key 管理器的重試機制
    response = api_manager.generate_content_with_retry(
        model,
        [
            {"mime_type": "image/jpeg", "data": image_bytes},
            prompt
        ]
    )

    full_text = response.text.strip()
    
    # 提取關鍵字：商品名稱和品牌
    keywords = []
    lines = full_text.split('\n')
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # 分割商品名稱和品牌
        parts = line.split()
        for part in parts:
            # 移除可能的標點符號
            part = part.strip('.,;:!?()[]{}')
            if len(part) >= 2 and part not in keywords:
                keywords.append(part)
    
    # 如果沒有提取到關鍵字，使用原始文字分割
    if not keywords:
        keywords = [w.strip() for w in full_text.split() if len(w.strip()) >= 2]
    
    # 限制關鍵字數量，優先保留較長的詞（通常是商品名稱）
    keywords = sorted(keywords, key=lambda x: len(x), reverse=True)[:5]
    
    logger.info(f"提取的關鍵字：{keywords}")
    
    return keywords, full_text

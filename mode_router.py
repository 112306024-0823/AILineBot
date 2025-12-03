"""
模式判斷與路由模組
負責判斷用戶訊息應該進入哪個模式
"""
from typing import Dict

# 用戶模式狀態管理（記憶體儲存）
# key: user_id, value: 'qa' (智能問答模式) 或 None (預設商品搜尋模式)
user_modes: Dict[str, str] = {}


def determine_mode(message_text: str, user_id: str = None) -> str:
    """
    判斷訊息應該進入哪個模式
    
    Args:
        message_text: 用戶訊息
        user_id: 用戶 ID（用於檢查用戶當前模式）
    
    Returns:
        'qa': 智能問答模式
        'search': 商品搜尋模式
        'favorite': 收藏功能
        'help': 使用說明
        'area': 區域查詢模式
        'search': 預設為商品搜尋模式
    """
    message_text = message_text.strip()
    
    # 檢查用戶當前模式（如果用戶在智能問答模式中）
    if user_id and user_id in user_modes and user_modes[user_id] == 'qa':
        # 檢查是否要退出智能問答模式
        exit_keywords = ["退出", "返回", "結束", "取消", "搜尋商品", "商品搜尋"]
        if any(keyword in message_text for keyword in exit_keywords):
            # 清除模式狀態
            user_modes.pop(user_id, None)
            return 'search' if "搜尋" in message_text else 'help'
        # 否則保持在智能問答模式
        return 'qa'
    
    # 使用說明關鍵字
    help_keywords = ["使用說明", "說明", "幫助", "help", "如何使用", "功能"]
    if any(keyword in message_text for keyword in help_keywords):
        return 'help'
    
    # 收藏功能關鍵字（已在 handle_favorite_commands 中處理，這裡只是標記）
    favorite_keywords = ["我的收藏", "收藏列表", "收藏"]
    if message_text in favorite_keywords:
        return 'favorite'
    
    # 區域查詢關鍵字
    area_keywords = ["區在哪", "專區在哪", "在哪裡", "在哪", "位置", "樓層", "幾樓"]
    area_names = ["飲料區", "零食專區", "泡麵專區", "調味料區", "乳製品專區", "罐頭專區", "冷凍食品專區"]
    if any(keyword in message_text for keyword in area_keywords) or \
       any(area_name in message_text for area_name in area_names):
        return 'area'
    
    # 商品搜尋模式觸發詞（用於顯示提示）
    search_trigger_keywords = ["搜尋商品", "商品搜尋", "搜尋", "找商品"]
    if any(keyword == message_text for keyword in search_trigger_keywords):
        # 清除智能問答模式（如果有的話）
        if user_id:
            user_modes.pop(user_id, None)
        return 'search_help'  # 特殊標記，用於顯示搜尋提示
    
    # 明確的智能問答觸發詞
    qa_trigger_keywords = ["智能問答", "問答", "問你", "請問"]
    if any(keyword in message_text for keyword in qa_trigger_keywords):
        # 設定用戶為智能問答模式
        if user_id:
            user_modes[user_id] = 'qa'
        return 'qa'
    
    # 智能問答模式關鍵字（如果包含疑問詞，進入智能問答模式）
    qa_keywords = ["什麼", "哪些", "哪裡", "多少", "最", "比較", "推薦", "便宜", "貴", "價格", "位置", "區"]
    is_question = any(keyword in message_text for keyword in qa_keywords) or \
                 message_text.endswith("?") or message_text.endswith("？")
    
    if is_question:
        return 'qa'
    
    # 預設為商品搜尋模式
    return 'search'


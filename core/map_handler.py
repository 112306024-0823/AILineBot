"""
地圖處理模組
負責處理位置查詢時的地圖生成和顯示
"""
import os
import sys
import uuid
import logging
from typing import Optional, List, Dict, Any, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from linebot.models import (
    ImageSendMessage, FlexSendMessage, TextSendMessage,
    BubbleContainer, BoxComponent, TextComponent, ImageComponent, ButtonComponent,
    MessageAction, PostbackAction
)

logger = logging.getLogger(__name__)

# 靜態地圖目錄
STATIC_MAP_DIR = os.path.join(os.path.dirname(__file__), '..', 'static', 'maps')
GENERATED_MAP_DIR = os.path.join(os.path.dirname(__file__), '..', 'static', 'generated_maps')

# 確保生成地圖目錄存在
os.makedirs(GENERATED_MAP_DIR, exist_ok=True)


def generate_and_save_map(
    floor: int,
    products: List[Dict[str, Any]],
    highlight_product_id: str = None,
    product_name: str = None,
    area: str = None,
    base_url: str = None
) -> Optional[str]:
    """
    生成地圖並保存到本地靜態目錄
    
    Args:
        floor: 樓層
        products: 商品列表
        highlight_product_id: 要高亮的商品 ID
        product_name: 商品名稱（用於簡單地圖）
        area: 區域名稱（用於簡單地圖）
        base_url: 伺服器基礎 URL（例如 https://xxx.ngrok.io）
    
    Returns:
        圖片完整 URL 或 None
    """
    try:
        from core.map_generator import generate_location_map, generate_simple_location_map
        
        # 決定使用哪種地圖生成方式
        if products and len(products) > 0:
            map_bytes = generate_location_map(
                floor=floor,
                products=products,
                highlight_product_id=highlight_product_id
            )
        elif area:
            map_bytes = generate_simple_location_map(
                floor=floor,
                area=area,
                product_name=product_name
            )
        else:
            logger.warning("沒有足夠的資訊生成地圖")
            return None
        
        if not map_bytes:
            logger.warning("地圖生成失敗")
            return None
        
        # 保存到本地靜態目錄
        filename = f"map_{floor}F_{uuid.uuid4().hex[:8]}.png"
        filepath = os.path.join(GENERATED_MAP_DIR, filename)
        
        with open(filepath, 'wb') as f:
            f.write(map_bytes)
        
        logger.info(f"地圖已保存：{filepath}")
        
        # 構建完整 URL
        if base_url:
            # 移除尾部斜線
            base_url = base_url.rstrip('/')
            image_url = f"{base_url}/static/generated_maps/{filename}"
            logger.info(f"地圖 URL：{image_url}")
            return image_url
        else:
            # 返回相對路徑（需要在外部組合 base_url）
            return f"/static/generated_maps/{filename}"
            
    except Exception as e:
        logger.error(f"生成並保存地圖失敗：{e}", exc_info=True)
        return None


def get_static_map_url(floor: int, base_url: str = None) -> Optional[str]:
    """
    取得靜態地圖的 URL（不標記商品位置）
    
    Args:
        floor: 樓層
        base_url: 伺服器基礎 URL
    
    Returns:
        地圖 URL 或 None
    """
    filename = f"F{floor}.png"
    filepath = os.path.join(STATIC_MAP_DIR, filename)
    
    if not os.path.exists(filepath):
        logger.warning(f"找不到靜態地圖：{filepath}")
        return None
    
    if base_url:
        base_url = base_url.rstrip('/')
        return f"{base_url}/static/maps/{filename}"
    else:
        return f"/static/maps/{filename}"


def create_location_flex_message(
    product: Dict[str, Any],
    map_image_url: str,
    floor: int,
    area: str
) -> FlexSendMessage:
    """
    建立包含地圖的 Flex Message
    
    Args:
        product: 商品資訊
        map_image_url: 地圖圖片 URL
        floor: 樓層
        area: 區域
    
    Returns:
        FlexSendMessage
    """
    name = product.get('name', '未知商品')
    price = float(product.get('price', 0))
    product_id = product.get('id')
    
    # 取得位置詳情
    locations = product.get('locations', [])
    shelf = ''
    notes = ''
    if locations:
        loc = locations[0]
        shelf = loc.get('shelf', '')
        notes = loc.get('notes', '')
    
    # 位置文字
    location_text = f"📍 {floor}F {area}"
    if shelf:
        location_text += f" {shelf}"
    
    bubble = BubbleContainer(
        hero=ImageComponent(
            url=map_image_url,
            size="full",
            aspect_ratio="4:3",
            aspect_mode="fit"
        ),
        body=BoxComponent(
            layout="vertical",
            spacing="sm",
            contents=[
                TextComponent(
                    text=name[:40],
                    weight="bold",
                    size="lg",
                    wrap=True
                ),
                TextComponent(
                    text=location_text,
                    size="md",
                    color="#FF6B9D",
                    margin="md"
                ),
                TextComponent(
                    text=f"💰 ${price:.0f}",
                    size="sm",
                    color="#666666",
                    margin="sm"
                )
            ]
        ),
        footer=BoxComponent(
            layout="horizontal",
            spacing="sm",
            contents=[
                ButtonComponent(
                    style="primary",
                    color="#FF6B9D",
                    height="sm",
                    action=MessageAction(
                        label="查看詳情",
                        text=f"詳情：{name}"
                    )
                ),
                ButtonComponent(
                    style="secondary",
                    height="sm",
                    action=PostbackAction(
                        label="收藏",
                        data=f"action=favorite&product_id={product_id}"
                    )
                ) if product_id else ButtonComponent(
                    style="secondary",
                    height="sm",
                    action=MessageAction(
                        label="更多商品",
                        text=f"搜尋 {area}"
                    )
                )
            ]
        )
    )
    
    return FlexSendMessage(
        alt_text=f"📍 {name} 位置：{floor}F {area}",
        contents=bubble
    )


def create_location_image_message(map_image_url: str, product_name: str = None) -> ImageSendMessage:
    """
    建立純圖片訊息
    
    Args:
        map_image_url: 地圖圖片 URL
        product_name: 商品名稱
    
    Returns:
        ImageSendMessage
    """
    return ImageSendMessage(
        original_content_url=map_image_url,
        preview_image_url=map_image_url
    )


def handle_location_query_with_map(
    products: List[Dict[str, Any]],
    search_term: str,
    line_bot_api,
    app
) -> Tuple[Optional[List], Optional[str]]:
    """
    處理位置查詢並生成地圖訊息
    
    Args:
        products: 商品列表
        search_term: 搜尋關鍵字
        line_bot_api: LINE Bot API
        app: Flask app
    
    Returns:
        (訊息列表, 地圖URL) 或 (None, None)
    """
    try:
        if not products:
            return None, None
        
        # 取得第一個商品的位置資訊
        product = products[0]
        locations = product.get('locations', [])
        
        if not locations:
            app.logger.info(f"商品 {product.get('name')} 沒有位置資訊")
            return None, None
        
        loc = locations[0]
        floor = loc.get('floor', 1)
        area = loc.get('area', '')
        
        # 取得伺服器 base URL（從環境變數或 app config）
        base_url = os.getenv('BASE_URL') or app.config.get('BASE_URL')
        
        if not base_url:
            app.logger.warning("未設定 BASE_URL，無法生成地圖 URL")
            return None, None
        
        # 生成並保存地圖
        map_url = generate_and_save_map(
            floor=floor,
            products=products[:5],  # 最多顯示 5 個商品
            highlight_product_id=product.get('id'),
            product_name=product.get('name'),
            area=area,
            base_url=base_url
        )
        
        if not map_url:
            app.logger.warning("地圖生成失敗，返回文字訊息")
            return None, None
        
        # 建立訊息列表
        messages = []
        
        # 地圖圖片
        image_message = create_location_image_message(map_url, product.get('name'))
        messages.append(image_message)
        
        # 取得商品名稱（用於回應）
        product_name = product.get('name', search_term)
        
        # 位置說明文字
        location_text = f"找到{product_name}的位置囉！\n\n"
        location_text += f"🏬 樓層：{floor}F\n"
        location_text += f"📍 區域：{area}\n"
        
        shelf = loc.get('shelf', '')
        if shelf:
            location_text += f"🗄️ 貨架：{shelf}\n"
        
        # 生成詳細位置描述
        detailed_location = generate_detailed_location_description(area, floor, shelf)
        if detailed_location:
            location_text += f"📍 {detailed_location}\n"
        
        notes = loc.get('notes', '')
        if notes:
            location_text += f"💡 備註：{notes}\n"
        
        location_text += f"\n💰 價格：${float(product.get('price', 0)):.0f}"
        
        if len(products) > 1:
            location_text += f"\n\n📦 還找到其他 {len(products) - 1} 個相關商品"
        
        text_message = TextSendMessage(text=location_text)
        messages.append(text_message)
        
        return messages, map_url
        
    except Exception as e:
        app.logger.error(f"處理位置查詢地圖失敗：{e}", exc_info=True)
        return None, None


def generate_detailed_location_description(area: str, floor: int, shelf: str = '') -> str:
    """
    使用友善的語氣，根據區域名稱和樓層生成詳細的位置描述
    
    Args:
        area: 區域名稱
        floor: 樓層
        shelf: 貨架編號
    
    Returns:
        詳細位置描述文字
    """
    descriptions = []
    
    # 根據區域名稱判斷相對位置
    area_lower = area.lower()
    
    # 收銀台相關
    if '收銀' in area or 'checkout' in area_lower or 'C區' in area:
        descriptions.append("就在收銀台旁邊")
    elif '入口' in area or 'entrance' in area_lower:
        descriptions.append("靠近入口處")
    elif '電梯' in area or 'elevator' in area_lower:
        descriptions.append("在電梯附近")
    elif '樓梯' in area or 'stair' in area_lower:
        descriptions.append("在樓梯旁邊")
    
    # 根據樓層和區域推斷
    if floor == 1:
        if '飲料' in area or 'A區' in area or 'drinks' in area_lower:
            descriptions.append("離入口不遠")
        elif '零食' in area or 'B區' in area or 'snacks' in area_lower:
            descriptions.append("在入口附近")
        elif '生鮮' in area or 'L區' in area or 'produce' in area_lower:
            descriptions.append("靠近收銀台")
        elif '熟食' in area or 'N區' in area or 'deli' in area_lower:
            descriptions.append("在賣場中央")
        elif '麵包' in area or 'M區' in area or 'bakery' in area_lower:
            descriptions.append("在賣場中段")
        elif '生活' in area or 'U區' in area or 'home' in area_lower:
            descriptions.append("在賣場後段，靠近收銀台")
    elif floor == 2:
        if '調味' in area or 'E區' in area or 'sauces' in area_lower:
            descriptions.append("在賣場前段")
        elif '泡麵' in area or 'D區' in area or 'noodles' in area_lower:
            descriptions.append("在賣場中段")
        elif '米類' in area or 'F區' in area or 'rice' in area_lower:
            descriptions.append("在賣場後段")
        elif '穀物' in area or 'O區' in area or 'cereals' in area_lower:
            descriptions.append("在賣場中後段")
        elif '油品' in area or 'P區' in area or 'oil' in area_lower:
            descriptions.append("靠近收銀台")
    elif floor == 3:
        if '乳製品' in area or 'G區' in area or 'dairy' in area_lower:
            descriptions.append("在賣場前段，靠近電梯")
        elif '罐頭' in area or 'H區' in area or 'canned' in area_lower:
            descriptions.append("在賣場中段")
        elif '冷藏飲料' in area or 'I區' in area or 'chilled' in area_lower:
            descriptions.append("在賣場後段，靠近電梯")
        elif '咖啡' in area or 'R區' in area or 'coffee' in area_lower:
            descriptions.append("在賣場前段")
        elif '果汁' in area or 'Q區' in area or 'juice' in area_lower:
            descriptions.append("在賣場中段")
    elif floor == 4:
        if '冷凍食品' in area or 'J區' in area or 'frozen' in area_lower:
            descriptions.append("在賣場前段，靠近電梯")
        elif '冰淇淋' in area or 'S區' in area or 'ice cream' in area_lower:
            descriptions.append("在賣場中段")
        elif '冷凍肉品' in area or 'K區' in area or 'meat' in area_lower:
            descriptions.append("在賣場後段，靠近電梯")
        elif '冷凍海鮮' in area or 'T區' in area or 'seafood' in area_lower:
            descriptions.append("在賣場後段")
    
    # 如果沒有特定描述，使用通用描述
    if not descriptions:
        if floor == 1:
            descriptions.append("在1樓賣場")
        elif floor == 2:
            descriptions.append("在2樓賣場")
        elif floor == 3:
            descriptions.append("在3樓賣場")
        elif floor == 4:
            descriptions.append("在4樓賣場")
    
    # 如果有貨架資訊，可以加入更精確的描述
    if shelf:
        if 'A' in shelf or 'B' in shelf or 'C' in shelf:
            if not any('收銀' in d or '入口' in d for d in descriptions):
                descriptions.append("在該區域的中段")
    
    return "，".join(descriptions) if descriptions else ""


def is_location_query(question: str, analysis: Dict[str, Any] = None) -> bool:
    """
    判斷是否為位置查詢
    
    Args:
        question: 用戶問題
        analysis: 問題分析結果
    
    Returns:
        是否為位置查詢
    """
    # 從分析結果判斷
    if analysis:
        intent = analysis.get('intent', '')
        if intent == 'search_by_location':
            return True
    
    # 從問題文字判斷
    location_keywords = ['在哪', '哪裡', '位置', '怎麼走', '怎麼去', '哪一區', '幾樓', '哪個區']
    return any(keyword in question for keyword in location_keywords)


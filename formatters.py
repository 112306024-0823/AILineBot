"""
格式化函數模組
負責將資料格式化為 LINE 訊息格式（文字、Carousel、Flex Message）
"""
from typing import Dict, Any, List, Optional
from linebot.models import (
    TemplateSendMessage, CarouselTemplate, CarouselColumn,
    MessageAction, PostbackAction, TextSendMessage,
    FlexSendMessage, BubbleContainer, BoxComponent, TextComponent, ImageComponent, ButtonComponent
)
import logging

logger = logging.getLogger(__name__)

# 預設圖片 URL（如果商品沒有圖片時使用）
DEFAULT_PRODUCT_IMAGE_URL = "https://images.unsplash.com/photo-1556742049-0cfed4f6a45d?w=300&h=300&fit=crop"


def format_product_search_result(products: list, search_term: str) -> str:
    """
    格式化產品搜尋結果轉為 LINE 訊息
    
    Args:
        products: 產品列表（包含位置資訊）
        search_term: 搜尋關鍵字
    
    Returns:
        格式化後的字串
    """
    if not products:
        return f"🔍 找不到包含「{search_term}」的產品"
    
    result_text = f"🔍 找到 {len(products)} 個包含「{search_term}」的產品：\n\n"
    result_text += "=" * 30 + "\n\n"
    
    for idx, product in enumerate(products, 1):
        result_text += f"【{idx}】{product.get('name', '未知產品')}\n"
        result_text += f"💰 價格：${float(product.get('price', 0)):.0f}\n"
        
        # 存貨狀態
        stock = product.get('stock', 0)
        if stock is None:
            stock = 0
        else:
            try:
                stock = int(stock)
            except (ValueError, TypeError):
                stock = 0
        
        if stock > 0:
            result_text += f"✅ 有存貨\n"
        else:
            result_text += f"❌ 【缺貨中】\n"
        
        if product.get('brand'):
            result_text += f"🏷️ 品牌：{product['brand']}\n"
        
        if product.get('category'):
            result_text += f"📦 分類：{product['category']}\n"
        
        # 位置資訊
        locations = product.get('locations', [])
        if locations:
            result_text += f"📍 位置資訊：\n"
            for loc in locations:
                area = loc.get('area', '未知區域')
                shelf = loc.get('shelf', '')
                floor = loc.get('floor', '')
                location_str = f"   • {area}"
                if shelf:
                    location_str += f" - {shelf}"
                if floor:
                    location_str += f" (樓層 {floor})"
                result_text += location_str + "\n"
        else:
            result_text += "📍 位置：暫無位置資訊\n"
        
        if product.get('description'):
            desc = product['description'][:50]
            if len(product['description']) > 50:
                desc += "..."
            result_text += f"📝 {desc}\n"
        
        result_text += "\n" + "-" * 30 + "\n\n"
    
    return result_text


def format_product_carousel(products: list, search_term: str, line_bot_api=None, app=None):
    """
    格式化產品搜尋結果為 LINE Carousel Template（圖片+文字）
    
    Args:
        products: 產品列表（包含位置資訊和 image_url）
        search_term: 搜尋關鍵字
        line_bot_api: LINE Bot API 實例（用於日誌，可選）
        app: Flask app 實例（用於日誌，可選）
    
    Returns:
        TemplateSendMessage 或 None（如果沒有商品）
    """
    if not products:
        return None
    
    # 處理所有產品（最多 10 個，LINE Carousel 限制）
    products_to_show = []
    for product in products[:10]:
        image_url = product.get('image_url')
        # 檢查圖片 URL 是否有效（必須是 HTTPS）
        if image_url and image_url.startswith('https://') and not image_url.startswith('https://example.com'):
            product['display_image_url'] = image_url
        else:
            product['display_image_url'] = DEFAULT_PRODUCT_IMAGE_URL
            if app:
                app.logger.info(f"商品 {product.get('name')} 沒有有效圖片，使用預設圖片")
        
        products_to_show.append(product)
    
    # 如果沒有商品，返回 None
    if not products_to_show:
        if app:
            app.logger.info("沒有商品可顯示")
        return None
    
    # 建立 Carousel Columns
    columns = []
    for product in products_to_show:
        name = product.get('name', '未知產品')
        price = float(product.get('price', 0))
        stock = product.get('stock', 0)
        
        # 處理存貨狀態
        if stock is None:
            stock = 0
        else:
            try:
                stock = int(stock)
            except (ValueError, TypeError):
                stock = 0
        
        # 建立文字內容
        text = f"💰 ${price:.0f}\n"
        if stock > 0:
            text += f"✅ 有存貨（{stock} 個）\n"
        else:
            text += "❌ 【缺貨中】\n"
        
        if product.get('brand'):
            text += f"🏷️ {product['brand']}\n"
        
        # 位置資訊（只顯示第一個位置）
        locations = product.get('locations', [])
        if locations:
            loc = locations[0]
            area = loc.get('area', '未知區域')
            shelf = loc.get('shelf', '')
            location_str = area
            if shelf:
                location_str += f" - {shelf}"
            text += f"📍 {location_str}\n"
        
        # 描述（限制長度）
        if product.get('description'):
            desc = product['description'][:50]
            if len(product['description']) > 50:
                desc += "..."
            text += f"\n📝 {desc}"
        
        # 建立 CarouselColumn
        title = name[:40] if len(name) <= 40 else name[:37] + "..."
        text = text[:120] if len(text) <= 120 else text[:117] + "..."
        
        # 建立按鈕動作
        product_id = product.get('id')
        actions = [
            MessageAction(
                label='查看詳情',
                text=f"詳情：{name}"
            )
        ]
        
        # 添加收藏按鈕（如果有 product_id）
        if product_id:
            actions.append(
                PostbackAction(
                    label='收藏商品',
                    data=f"action=favorite&product_id={product_id}&source=search"
                )
            )
        
        column = CarouselColumn(
            thumbnail_image_url=product.get('display_image_url', DEFAULT_PRODUCT_IMAGE_URL),
            title=title,
            text=text,
            actions=actions
        )
        columns.append(column)
    
    if not columns:
        return None
    
    # 建立 Carousel Template
    carousel_template = CarouselTemplate(columns=columns)
    
    # 建立 TemplateSendMessage
    template_message = TemplateSendMessage(
        alt_text=f"找到 {len(columns)} 個包含「{search_term}」的產品",
        template=carousel_template
    )
    
    return template_message


def format_area_info(area: Dict[str, Any]) -> str:
    """格式化單個區域資訊"""
    area_name = area.get("area_name", "未知區域")
    floor = area.get("floor", 0)
    area_code = area.get("area_code", "")
    description = area.get("description", "")
    notes = area.get("notes", "")
    
    text = f"📍 {area_name}\n\n"
    text += f"🏢 {floor}樓\n"
    if area_code:
        text += f"📍 {area_code}\n"
    if description:
        text += f"📝 {description}\n"
    if notes:
        text += f"💡 {notes}\n"
    
    return text


def format_areas_list(areas: List[Dict[str, Any]], area_type: str) -> str:
    """格式化區域列表"""
    if not areas:
        return f"找不到{area_type}相關區域"
    
    text = f"📍 {area_type}相關區域：\n\n"
    for area in areas:
        area_name = area.get("area_name", "未知區域")
        floor = area.get("floor", 0)
        area_code = area.get("area_code", "")
        text += f"• {area_name} - {floor}樓 {area_code}\n"
    
    return text


def format_areas_by_floor(areas: List[Dict[str, Any]], floor: int) -> str:
    """格式化樓層區域資訊"""
    if not areas:
        return f"{floor}樓沒有區域資訊"
    
    text = f"🏢 {floor}樓區域資訊：\n\n"
    for area in areas:
        area_name = area.get("area_name", "未知區域")
        area_code = area.get("area_code", "")
        description = area.get("description", "")
        text += f"📍 {area_name} ({area_code})\n"
        if description:
            text += f"   {description}\n"
        text += "\n"
    
    return text


def format_all_areas(areas: List[Dict[str, Any]]) -> str:
    """格式化所有區域資訊（按樓層分組）"""
    if not areas:
        return "目前沒有區域資訊"
    
    # 按樓層分組
    floors = {}
    for area in areas:
        floor = area.get("floor", 0)
        if floor not in floors:
            floors[floor] = []
        floors[floor].append(area)
    
    text = "📍 賣場區域資訊：\n\n"
    for floor in sorted(floors.keys()):
        text += f"🏢 {floor}樓：\n"
        for area in floors[floor]:
            area_name = area.get("area_name", "未知區域")
            area_code = area.get("area_code", "")
            text += f"  • {area_name} ({area_code})\n"
        text += "\n"
    
    text += "💡 提示：可以詢問「飲料區在哪裡？」或「1樓有哪些區域？」"
    
    return text


def format_favorites_carousel(favorites: list) -> Optional[TemplateSendMessage]:
    """
    格式化收藏列表為 LINE Carousel Template
    
    Args:
        favorites: 收藏的商品列表（包含位置資訊和 image_url）
    
    Returns:
        TemplateSendMessage 或 None（如果沒有商品）
    """
    if not favorites:
        return None
    
    # 處理所有收藏商品（最多 10 個，LINE Carousel 限制）
    products_to_show = []
    for product in favorites[:10]:
        image_url = product.get('image_url')
        if image_url and image_url.startswith('https://') and not image_url.startswith('https://example.com'):
            product['display_image_url'] = image_url
        else:
            product['display_image_url'] = DEFAULT_PRODUCT_IMAGE_URL
        
        products_to_show.append(product)
    
    if not products_to_show:
        return None
    
    # 建立 Carousel Columns
    columns = []
    for product in products_to_show:
        name = product.get('name', '未知產品')
        price = float(product.get('price', 0))
        stock = product.get('stock', 0)
        product_id = product.get('id')
        
        # 處理存貨狀態
        if stock is None:
            stock = 0
        else:
            try:
                stock = int(stock)
            except (ValueError, TypeError):
                stock = 0
        
        # 建立文字內容
        text = f"💰 ${price:.0f}\n"
        if stock > 0:
            text += f"✅ 有存貨（{stock} 個）\n"
        else:
            text += "❌ 【缺貨中】\n"
        
        if product.get('brand'):
            text += f"🏷️ {product['brand']}\n"
        
        # 位置資訊（只顯示第一個位置）
        locations = product.get('locations', [])
        if locations:
            loc = locations[0]
            area = loc.get('area', '未知區域')
            shelf = loc.get('shelf', '')
            location_str = area
            if shelf:
                location_str += f" - {shelf}"
            text += f"📍 {location_str}\n"
        
        # 描述（限制長度）
        if product.get('description'):
            desc = product['description'][:40]
            if len(product['description']) > 40:
                desc += "..."
            text += f"\n📝 {desc}"
        
        # 建立 CarouselColumn
        title = name[:40] if len(name) <= 40 else name[:37] + "..."
        text = text[:120] if len(text) <= 120 else text[:117] + "..."
        
        # 建立按鈕動作
        actions = [
            MessageAction(
                label='查看詳情',
                text=f"詳情：{name}"
            )
        ]
        
        # 添加取消收藏按鈕（因為在收藏列表中，所以顯示取消收藏）
        if product_id:
            actions.append(
                PostbackAction(
                    label='取消收藏',
                    data=f"action=favorite&product_id={product_id}&source=favorites"
                )
            )
        
        column = CarouselColumn(
            thumbnail_image_url=product.get('display_image_url', DEFAULT_PRODUCT_IMAGE_URL),
            title=title,
            text=text,
            actions=actions
        )
        columns.append(column)
    
    if not columns:
        return None
    
    # 建立 Carousel Template
    carousel_template = CarouselTemplate(columns=columns)
    
    # 建立 TemplateSendMessage
    template_message = TemplateSendMessage(
        alt_text=f"我的收藏（共 {len(columns)} 個商品）",
        template=carousel_template
    )
    
    return template_message


def format_favorites_flex(favorites: list, app=None) -> Optional[List[FlexSendMessage]]:
    """
    格式化收藏列表為 LINE Flex Message（更美觀的卡片式呈現）
    
    Args:
        favorites: 收藏的商品列表（包含位置資訊和 image_url）
        app: Flask app 實例（用於日誌，可選）
    
    Returns:
        FlexSendMessage 列表或 None
    """
    if not favorites:
        return None
    
    try:
        flex_messages = []
        
        # 為每個收藏商品建立一個 Flex Bubble
        for product in favorites[:12]:  # Flex Message 可以顯示更多商品
            name = product.get('name', '未知產品')
            price = float(product.get('price', 0))
            stock = product.get('stock', 0)
            product_id = product.get('id')
            image_url = product.get('image_url') or DEFAULT_PRODUCT_IMAGE_URL
            brand = product.get('brand', '')
            
            # 處理存貨狀態
            if stock is None:
                stock = 0
            else:
                try:
                    stock = int(stock)
                except (ValueError, TypeError):
                    stock = 0
            
            # 位置資訊
            locations = product.get('locations', [])
            location_text = "📍 位置：暫無"
            if locations:
                loc = locations[0]
                area = loc.get('area', '未知區域')
                shelf = loc.get('shelf', '')
                location_text = f"📍 {area}"
                if shelf:
                    location_text += f" - {shelf}"
            
            # 建立 Flex Bubble
            bubble = BubbleContainer(
                hero=ImageComponent(
                    url=image_url if image_url.startswith('https://') else DEFAULT_PRODUCT_IMAGE_URL,
                    size="full",
                    aspect_ratio="20:13",
                    aspect_mode="cover"
                ),
                body=BoxComponent(
                    layout="vertical",
                    spacing="sm",
                    contents=[
                        TextComponent(
                            text=name[:40] if len(name) <= 40 else name[:37] + "...",
                            weight="bold",
                            size="xl",
                            wrap=True
                        ),
                        BoxComponent(
                            layout="vertical",
                            margin="md",
                            spacing="xs",
                            contents=[
                                BoxComponent(
                                    layout="baseline",
                                    spacing="sm",
                                    contents=[
                                        TextComponent(
                                            text="價格",
                                            color="#aaaaaa",
                                            size="sm",
                                            flex=1
                                        ),
                                        TextComponent(
                                            text=f"${price:.0f}",
                                            wrap=True,
                                            color="#666666",
                                            size="sm",
                                            flex=5
                                        )
                                    ]
                                ),
                                BoxComponent(
                                    layout="baseline",
                                    spacing="sm",
                                    contents=[
                                        TextComponent(
                                            text="存貨",
                                            color="#aaaaaa",
                                            size="sm",
                                            flex=1
                                        ),
                                        TextComponent(
                                            text="✅ 有存貨" if stock > 0 else "❌ 缺貨中",
                                            wrap=True,
                                            color="#666666",
                                            size="sm",
                                            flex=5
                                        )
                                    ]
                                ),
                                BoxComponent(
                                    layout="baseline",
                                    spacing="sm",
                                    contents=[
                                        TextComponent(
                                            text="位置",
                                            color="#aaaaaa",
                                            size="sm",
                                            flex=1
                                        ),
                                        TextComponent(
                                            text=location_text,
                                            wrap=True,
                                            color="#666666",
                                            size="sm",
                                            flex=5
                                        )
                                    ]
                                )
                            ]
                        )
                    ]
                ),
                footer=BoxComponent(
                    layout="vertical",
                    spacing="sm",
                    contents=[
                        ButtonComponent(
                            style="primary",
                            color="#FF6B9D",
                            action=MessageAction(
                                label="查看詳情",
                                text=f"詳情：{name}"
                            )
                        ),
                        ButtonComponent(
                            style="secondary",
                            action=PostbackAction(
                                label="取消收藏",
                                data=f"action=favorite&product_id={product_id}&source=favorites"
                            )
                        )
                    ]
                )
            )
            
            flex_messages.append(FlexSendMessage(alt_text=f"收藏商品：{name}", contents=bubble))
        
        return flex_messages if flex_messages else None

    except Exception as e:
        if app:
            app.logger.error(f"建立 Flex Message 失敗：{e}", exc_info=True)
        logger.error(f"建立 Flex Message 失敗：{e}", exc_info=True)
        return None


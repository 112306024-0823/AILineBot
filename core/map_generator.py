"""
賣場地圖生成模組
動態在平面圖上標記商品位置
"""
from PIL import Image, ImageDraw, ImageFont
import io
import os
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)

# 地圖設定
MAP_DIR = os.path.join(os.path.dirname(__file__), '..', 'static', 'maps')

# 嘗試載入中文字體
FONT_PATH = None
POSSIBLE_FONT_PATHS = [
    os.path.join(os.path.dirname(__file__), '..', 'fonts', 'NotoSansTC-Regular.otf'),
    os.path.join(os.path.dirname(__file__), '..', 'fonts', 'NotoSansTC-Regular.ttf'),
    'C:/Windows/Fonts/msjh.ttc',  # Windows 微軟正黑體
    'C:/Windows/Fonts/mingliu.ttc',  # Windows 細明體
    '/System/Library/Fonts/PingFang.ttc',  # macOS
    '/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc',  # Linux
]

for path in POSSIBLE_FONT_PATHS:
    if os.path.exists(path):
        FONT_PATH = path
        break

# 顏色設定
COLORS = {
    'highlight': '#FF6B9D',      # 主要商品（粉紅色）
    'highlight_border': '#E91E63',
    'related': '#3B82F6',        # 相關商品（藍色）
    'related_border': '#1E40AF',
    'text': '#1F2937',           # 文字（深灰）
    'text_bg': '#FFFFFF',        # 文字背景（白色）
    'label_bg': '#FFFFFFEE',     # 標籤背景（半透明白）
}

# 區域座標對應（根據實際地圖位置，地圖尺寸約 1024x1024）
# 格式：area_name -> (center_x, center_y)
AREA_COORDINATES = {
    # 1樓
    '飲料區': (170, 160),
    'A區': (170, 160),
    '零食專區': (460, 160),
    'B區': (460, 160),
    '生鮮蔬果區': (760, 160),
    'L區': (760, 160),
    '熟食區': (170, 420),
    'N區': (170, 420),
    '麵包烘焙區': (400, 420),
    'M區': (400, 420),
    '生活用品區': (280, 680),
    'U區': (280, 680),
    '收銀台': (680, 680),
    'C區': (680, 680),
    # 1樓其他區域
    '冷凍區': (280, 680),
    '冷藏區': (170, 420),
    '零食區': (460, 160),
    
    # 2樓
    '調味料區': (170, 160),
    'E區': (170, 160),
    '泡麵專區': (460, 160),
    'D區': (460, 160),
    '米類專區': (760, 160),
    'F區': (760, 160),
    '穀物早餐區': (400, 420),
    'O區': (400, 420),
    '油品專區': (680, 420),
    'P區': (680, 420),
    '食品區': (460, 160),
    '罐頭區': (460, 420),
    
    # 3樓
    '乳製品專區': (200, 200),
    'G區': (200, 200),
    '罐頭專區': (480, 200),
    'H區': (480, 200),
    '冷藏飲料區': (720, 200),
    'I區': (720, 200),
    '咖啡茶飲區': (170, 550),
    'R區': (170, 550),
    '果汁專區': (400, 550),
    'Q區': (400, 550),
    
    # 4樓
    '冷凍食品專區': (200, 230),
    'J區': (200, 230),
    '冰淇淋區': (450, 230),
    'S區': (450, 230),
    '冷凍肉品區': (680, 230),
    'K區': (680, 230),
    '冷凍海鮮區': (600, 500),
    'T區': (600, 500),
}


def get_map_filename(floor: int) -> str:
    """取得地圖檔名"""
    return f"F{floor}.png"


def hex_to_rgb(hex_color: str) -> tuple:
    """將 HEX 顏色轉換為 RGB"""
    hex_color = hex_color.lstrip('#')
    if len(hex_color) == 8:  # RGBA
        return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4, 6))
    return tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))


def get_area_center(area: str, floor: int) -> Optional[tuple]:
    """
    取得區域的中心座標
    
    Args:
        area: 區域名稱
        floor: 樓層
    
    Returns:
        (x, y) 座標或 None
    """
    # 先嘗試直接匹配
    if area in AREA_COORDINATES:
        return AREA_COORDINATES[area]
    
    # 嘗試部分匹配
    for key, coords in AREA_COORDINATES.items():
        if area in key or key in area:
            return coords
    
    # 預設位置（根據樓層）
    default_positions = {
        1: (400, 400),
        2: (400, 300),
        3: (400, 350),
        4: (400, 350),
    }
    return default_positions.get(floor, (400, 400))


def generate_location_map(
    floor: int,
    products: List[Dict[str, Any]],
    highlight_product_id: str = None,
    map_width: int = 800
) -> Optional[bytes]:
    """
    生成帶有商品標記的地圖
    
    Args:
        floor: 樓層
        products: 商品列表（需包含 locations）
        highlight_product_id: 要突出顯示的商品 ID
        map_width: 輸出地圖寬度
    
    Returns:
        PNG 圖片的 bytes 資料，失敗時返回 None
    """
    try:
        # 載入底圖
        map_filename = get_map_filename(floor)
        map_path = os.path.join(MAP_DIR, map_filename)
        
        if not os.path.exists(map_path):
            logger.warning(f"找不到地圖檔案：{map_path}")
            return None
        
        base_map = Image.open(map_path).convert('RGBA')
        original_width = base_map.width
        original_height = base_map.height
        
        # 調整大小
        ratio = map_width / original_width
        new_height = int(original_height * ratio)
        base_map = base_map.resize((map_width, new_height), Image.Resampling.LANCZOS)
        
        # 建立繪圖物件
        draw = ImageDraw.Draw(base_map)
        
        # 載入字體
        try:
            if FONT_PATH:
                font = ImageFont.truetype(FONT_PATH, 14)
                font_bold = ImageFont.truetype(FONT_PATH, 16)
            else:
                font = ImageFont.load_default()
                font_bold = font
        except Exception as e:
            logger.warning(f"載入字體失敗：{e}")
            font = ImageFont.load_default()
            font_bold = font
        
        # 收集要標記的商品
        markers = []
        for product in products:
            locations = product.get('locations', [])
            if not locations:
                continue
            
            loc = locations[0]
            loc_floor = loc.get('floor', 1)
            
            # 只標記同一樓層的商品
            if loc_floor != floor:
                continue
            
            area = loc.get('area', '')
            
            # 取得座標
            # 優先使用資料庫中的座標
            x = loc.get('position_x')
            y = loc.get('position_y')
            
            if x is None or y is None:
                # 使用區域中心座標
                center = get_area_center(area, floor)
                if center:
                    x, y = center
                else:
                    continue
            else:
                x = float(x)
                y = float(y)
            
            # 調整座標比例
            x = int(x * ratio)
            y = int(y * ratio)
            
            markers.append({
                'product': product,
                'x': x,
                'y': y,
                'is_highlight': product.get('id') == highlight_product_id
            })
        
        # 先繪製非高亮標記
        for marker in markers:
            if not marker['is_highlight']:
                draw_marker(draw, marker, font, is_highlight=False)
        
        # 再繪製高亮標記（確保在最上層）
        for marker in markers:
            if marker['is_highlight']:
                draw_marker(draw, marker, font_bold, is_highlight=True)
        
        # 轉換為 bytes
        output = io.BytesIO()
        
        # 轉換為 RGB（LINE 不支援透明 PNG）
        rgb_map = Image.new('RGB', base_map.size, (255, 255, 255))
        rgb_map.paste(base_map, mask=base_map.split()[3] if base_map.mode == 'RGBA' else None)
        
        rgb_map.save(output, format='PNG', optimize=True)
        return output.getvalue()
        
    except Exception as e:
        logger.error(f"生成地圖失敗：{e}", exc_info=True)
        return None


def draw_marker(draw: ImageDraw, marker: Dict, font: ImageFont, is_highlight: bool = False):
    """繪製單個標記"""
    x = marker['x']
    y = marker['y']
    product = marker['product']
    name = product.get('name', '')[:15]  # 限制名稱長度
    
    if is_highlight:
        # 主要商品：大標記
        color = COLORS['highlight']
        border_color = COLORS['highlight_border']
        radius = 18
        
        # 繪製外圈光暈效果
        for i in range(3):
            alpha = 80 - i * 25
            outer_radius = radius + 5 + i * 4
            # 繪製半透明圓
            draw.ellipse(
                [x - outer_radius, y - outer_radius, 
                 x + outer_radius, y + outer_radius],
                outline=color,
                width=2
            )
    else:
        # 相關商品：小標記
        color = COLORS['related']
        border_color = COLORS['related_border']
        radius = 12
    
    # 繪製主標記（實心圓）
    draw.ellipse(
        [x - radius, y - radius, x + radius, y + radius],
        fill=color,
        outline='white',
        width=3
    )
    
    # 繪製內部圖示（定位點）
    inner_radius = radius // 3
    draw.ellipse(
        [x - inner_radius, y - inner_radius, x + inner_radius, y + inner_radius],
        fill='white'
    )
    
    # 只為高亮商品繪製名稱標籤
    if is_highlight and name:
        try:
            # 計算文字大小
            text_bbox = draw.textbbox((0, 0), name, font=font)
            text_width = text_bbox[2] - text_bbox[0]
            text_height = text_bbox[3] - text_bbox[1]
            
            # 標籤位置（在標記上方）
            label_x = x - text_width // 2
            label_y = y - radius - text_height - 15
            padding = 6
            
            # 確保標籤不超出邊界
            if label_x < 5:
                label_x = 5
            if label_y < 5:
                label_y = y + radius + 10  # 改到下方
            
            # 繪製標籤背景（圓角矩形）
            draw.rounded_rectangle(
                [label_x - padding, label_y - padding,
                 label_x + text_width + padding, label_y + text_height + padding],
                radius=8,
                fill=COLORS['label_bg'],
                outline=color,
                width=2
            )
            
            # 繪製文字
            draw.text((label_x, label_y), name, fill=COLORS['text'], font=font)
            
        except Exception as e:
            logger.warning(f"繪製標籤失敗：{e}")


def generate_simple_location_map(
    floor: int,
    area: str,
    product_name: str = None
) -> Optional[bytes]:
    """
    生成簡單的位置標記地圖（只標記一個區域）
    
    Args:
        floor: 樓層
        area: 區域名稱
        product_name: 商品名稱（可選）
    
    Returns:
        PNG 圖片的 bytes 資料
    """
    try:
        # 載入底圖
        map_filename = get_map_filename(floor)
        map_path = os.path.join(MAP_DIR, map_filename)
        
        if not os.path.exists(map_path):
            logger.warning(f"找不到地圖檔案：{map_path}")
            return None
        
        base_map = Image.open(map_path).convert('RGBA')
        
        # 調整大小
        map_width = 800
        ratio = map_width / base_map.width
        new_height = int(base_map.height * ratio)
        base_map = base_map.resize((map_width, new_height), Image.Resampling.LANCZOS)
        
        draw = ImageDraw.Draw(base_map)
        
        # 載入字體
        try:
            if FONT_PATH:
                font = ImageFont.truetype(FONT_PATH, 16)
            else:
                font = ImageFont.load_default()
        except:
            font = ImageFont.load_default()
        
        # 取得區域座標
        center = get_area_center(area, floor)
        if center:
            x, y = int(center[0] * ratio), int(center[1] * ratio)
            
            # 繪製大標記
            color = COLORS['highlight']
            radius = 25
            
            # 外圈動畫效果
            for i in range(4):
                outer_radius = radius + 8 + i * 6
                draw.ellipse(
                    [x - outer_radius, y - outer_radius,
                     x + outer_radius, y + outer_radius],
                    outline=color,
                    width=2
                )
            
            # 主標記
            draw.ellipse(
                [x - radius, y - radius, x + radius, y + radius],
                fill=color,
                outline='white',
                width=4
            )
            
            # 內部白點
            inner_radius = 8
            draw.ellipse(
                [x - inner_radius, y - inner_radius,
                 x + inner_radius, y + inner_radius],
                fill='white'
            )
            
            # 標籤
            if product_name:
                label = product_name[:20]
                text_bbox = draw.textbbox((0, 0), label, font=font)
                text_width = text_bbox[2] - text_bbox[0]
                text_height = text_bbox[3] - text_bbox[1]
                
                label_x = x - text_width // 2
                label_y = y - radius - text_height - 20
                padding = 8
                
                if label_y < 10:
                    label_y = y + radius + 15
                
                draw.rounded_rectangle(
                    [label_x - padding, label_y - padding,
                     label_x + text_width + padding, label_y + text_height + padding],
                    radius=10,
                    fill='#FFFFFFEE',
                    outline=color,
                    width=2
                )
                
                draw.text((label_x, label_y), label, fill=COLORS['text'], font=font)
        
        # 轉換為 bytes
        output = io.BytesIO()
        rgb_map = Image.new('RGB', base_map.size, (255, 255, 255))
        rgb_map.paste(base_map, mask=base_map.split()[3] if base_map.mode == 'RGBA' else None)
        rgb_map.save(output, format='PNG', optimize=True)
        
        return output.getvalue()
        
    except Exception as e:
        logger.error(f"生成簡單地圖失敗：{e}", exc_info=True)
        return None


# 測試用
if __name__ == "__main__":
    # 測試生成地圖
    test_products = [
        {
            'id': '1',
            'name': '林鳳營鮮乳 1000ml',
            'locations': [{'area': '乳製品專區', 'floor': 3, 'position_x': 200, 'position_y': 200}]
        }
    ]
    
    result = generate_location_map(floor=3, products=test_products, highlight_product_id='1')
    if result:
        with open('test_map.png', 'wb') as f:
            f.write(result)
        print("地圖已生成：test_map.png")
    else:
        print("地圖生成失敗")


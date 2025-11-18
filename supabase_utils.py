"""
Supabase 連線和資料操作模組
用於管理商品資料和位置資訊
"""
import os
from supabase import create_client, Client
from typing import Optional, List, Dict, Any, BinaryIO
import logging
from datetime import datetime
import uuid
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

logger = logging.getLogger(__name__)

# 初始化 Supabase 客戶端
supabase_url = os.getenv("SUPABASE_URL")
supabase_key = os.getenv("SUPABASE_KEY")

if not supabase_url or not supabase_key:
    logger.warning("Supabase 環境變數未設置，部分功能可能無法使用")
    supabase: Optional[Client] = None
else:
    try:
        supabase: Optional[Client] = create_client(supabase_url, supabase_key)
        # 測試連線
        test_result = supabase.table("products").select("id").limit(1).execute()
        logger.info("Supabase 連線成功")
    except Exception as e:
        logger.error(f"Supabase 連線失敗：{e}")
        logger.warning("Supabase 功能將無法使用，請檢查環境變數和網路連線")
        supabase: Optional[Client] = None

# Storage bucket 名稱（可在環境變數中設定）
STORAGE_BUCKET = os.getenv("SUPABASE_STORAGE_BUCKET", "product-images")


# ==================== 商品資料操作 ====================

def create_product(
    name: str,
    price: float,
    description: Optional[str] = None,
    category: Optional[str] = None,
    image_url: Optional[str] = None,
    ingredients: Optional[str] = None,
    **kwargs
) -> Optional[Dict[str, Any]]:
    """
    建立新商品
    
    Args:
        name: 商品名稱
        price: 價格
        description: 商品描述
        category: 商品分類
        image_url: 商品圖片 URL（存在 Supabase Storage）
        ingredients: 成分/規格說明
        **kwargs: 其他自訂欄位
    
    Returns:
        建立的商品資料，失敗則返回 None
    """
    if not supabase:
        logger.error("Supabase 未初始化")
        return None
    
    try:
        data = {
            "name": name,
            "price": price,
            "description": description,
            "category": category,
            "image_url": image_url,
            "ingredients": ingredients,
            **kwargs
        }
        # 移除 None 值
        data = {k: v for k, v in data.items() if v is not None}
        
        result = supabase.table("products").insert(data).execute()
        if result.data:
            logger.info(f"商品建立成功：{name}")
            return result.data[0]
        return None
    except Exception as e:
        logger.error(f"建立商品失敗：{e}")
        return None


def get_product_by_id(product_id: str) -> Optional[Dict[str, Any]]:
    """根據 ID 獲取商品"""
    if not supabase:
        return None
    
    try:
        result = supabase.table("products").select("*").eq("id", product_id).execute()
        if result.data:
            return result.data[0]
        return None
    except Exception as e:
        logger.error(f"獲取商品失敗：{e}")
        return None


def search_products(
    name: Optional[str] = None,
    category: Optional[str] = None,
    limit: int = 20
) -> List[Dict[str, Any]]:
    """
    搜尋商品
    
    Args:
        name: 商品名稱（模糊搜尋）
        category: 商品分類
        limit: 回傳數量上限
    
    Returns:
        商品列表
    """
    if not supabase:
        return []
    
    try:
        query = supabase.table("products").select("*")
        
        if name:
            query = query.ilike("name", f"%{name}%")
        if category:
            query = query.eq("category", category)
        
        result = query.limit(limit).execute()
        return result.data if result.data else []
    except Exception as e:
        logger.error(f"搜尋商品失敗：{e}")
        return []


def search_products_with_locations(
    search_term: str,
    limit: int = 10
) -> List[Dict[str, Any]]:
    """
    搜尋商品並包含位置資訊
    
    Args:
        search_term: 搜尋關鍵字（會在商品名稱、描述、品牌中搜尋）
        limit: 回傳數量上限
    
    Returns:
        商品列表（每個商品包含 locations 欄位）
    """
    if not supabase:
        logger.warning("Supabase 未初始化，無法搜尋產品")
        return []
    
    try:
        logger.info(f"開始搜尋產品：{search_term}")
        
        # 先搜尋產品（使用名稱模糊搜尋）
        products = search_products(name=search_term, limit=limit)
        logger.info(f"名稱搜尋結果：{len(products)} 個產品")
        
        if not products:
            # 如果名稱搜尋沒結果，嘗試搜尋品牌
            try:
                logger.info(f"嘗試品牌搜尋：{search_term}")
                query = supabase.table("products").select("*")
                query = query.ilike("brand", f"%{search_term}%")
                result = query.limit(limit).execute()
                if result.data:
                    products = result.data
                    logger.info(f"品牌搜尋結果：{len(products)} 個產品")
            except Exception as e:
                logger.error(f"品牌搜尋失敗：{e}")
        
        if not products:
            # 如果還是沒結果，嘗試搜尋描述
            try:
                logger.info(f"嘗試描述搜尋：{search_term}")
                query = supabase.table("products").select("*")
                query = query.ilike("description", f"%{search_term}%")
                result = query.limit(limit).execute()
                if result.data:
                    products = result.data
                    logger.info(f"描述搜尋結果：{len(products)} 個產品")
            except Exception as e:
                logger.error(f"描述搜尋失敗：{e}")
        
        # 為每個產品添加位置資訊
        for product in products:
            try:
                locations = get_product_locations(product['id'])
                product['locations'] = locations
            except Exception as e:
                logger.error(f"獲取產品位置失敗（產品ID: {product.get('id')}）：{e}")
                product['locations'] = []
        
        logger.info(f"最終搜尋結果：{len(products)} 個產品（含位置資訊）")
        return products
    except Exception as e:
        logger.error(f"搜尋商品及位置失敗：{e}", exc_info=True)
        return []


def update_product(product_id: str, **kwargs) -> Optional[Dict[str, Any]]:
    """更新商品資訊"""
    if not supabase:
        return None
    
    try:
        # 移除 None 值
        data = {k: v for k, v in kwargs.items() if v is not None}
        result = supabase.table("products").update(data).eq("id", product_id).execute()
        if result.data:
            return result.data[0]
        return None
    except Exception as e:
        logger.error(f"更新商品失敗：{e}")
        return None


# ==================== 商品位置操作 ====================

def add_product_location(
    product_id: str,
    area: str,
    shelf: Optional[str] = None,
    position_x: Optional[float] = None,
    position_y: Optional[float] = None,
    floor: Optional[int] = None,
    notes: Optional[str] = None
) -> Optional[Dict[str, Any]]:
    """
    新增商品位置
    
    Args:
        product_id: 商品 ID
        area: 區域（例如：A區、B區）
        shelf: 貨架編號（例如：3號貨架）
        position_x: X 座標（可選，用於地圖定位）
        position_y: Y 座標（可選，用於地圖定位）
        floor: 樓層（可選）
        notes: 備註
    
    Returns:
        建立的位置資料，失敗則返回 None
    """
    if not supabase:
        return None
    
    try:
        data = {
            "product_id": product_id,
            "area": area,
            "shelf": shelf,
            "position_x": position_x,
            "position_y": position_y,
            "floor": floor,
            "notes": notes
        }
        # 移除 None 值
        data = {k: v for k, v in data.items() if v is not None}
        
        result = supabase.table("product_locations").insert(data).execute()
        if result.data:
            logger.info(f"商品位置新增成功：商品 {product_id} 在 {area}")
            return result.data[0]
        return None
    except Exception as e:
        logger.error(f"新增商品位置失敗：{e}")
        return None


def get_product_locations(product_id: str) -> List[Dict[str, Any]]:
    """獲取商品的所有位置"""
    if not supabase:
        return []
    
    try:
        result = supabase.table("product_locations").select("*").eq("product_id", product_id).execute()
        return result.data if result.data else []
    except Exception as e:
        logger.error(f"獲取商品位置失敗：{e}")
        return []


def search_products_by_location(
    area: Optional[str] = None,
    shelf: Optional[str] = None,
    floor: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    根據位置搜尋商品
    
    Args:
        area: 區域
        shelf: 貨架
        floor: 樓層
    
    Returns:
        商品位置列表（包含商品資訊）
    """
    if not supabase:
        return []
    
    try:
        query = supabase.table("product_locations").select("*, products(*)")
        
        if area:
            query = query.eq("area", area)
        if shelf:
            query = query.eq("shelf", shelf)
        if floor:
            query = query.eq("floor", floor)
        
        result = query.execute()
        return result.data if result.data else []
    except Exception as e:
        logger.error(f"根據位置搜尋商品失敗：{e}")
        return []


def get_product_with_location(product_id: str) -> Optional[Dict[str, Any]]:
    """獲取商品及其所有位置資訊"""
    if not supabase:
        return None
    
    try:
        # 獲取商品資訊
        product = get_product_by_id(product_id)
        if not product:
            return None
        
        # 獲取位置資訊
        locations = get_product_locations(product_id)
        product["locations"] = locations
        
        return product
    except Exception as e:
        logger.error(f"獲取商品及位置失敗：{e}")
        return None


# ==================== 圖片上傳功能 ====================

def upload_product_image(
    file_path: str,
    product_name: Optional[str] = None,
    file_content: Optional[bytes] = None
) -> Optional[str]:
    """
    上傳商品圖片到 Supabase Storage
    
    Args:
        file_path: 本地檔案路徑，或要儲存的檔案名稱（例如：'products/coke.jpg'）
        product_name: 商品名稱（用於生成檔案名稱，選填）
        file_content: 檔案內容（bytes），如果提供則使用此內容而非讀取 file_path
    
    Returns:
        圖片的公開 URL，失敗則返回 None
    
    範例：
        # 方式 1: 從本地檔案上傳
        image_url = upload_product_image('/path/to/image.jpg', product_name='可口可樂')
        
        # 方式 2: 從 bytes 上傳（例如從 LINE Bot 接收的圖片）
        with open('image.jpg', 'rb') as f:
            image_url = upload_product_image('products/coke.jpg', file_content=f.read())
    """
    if not supabase:
        logger.error("Supabase 未初始化")
        return None
    
    try:
        # 生成唯一的檔案名稱
        if product_name:
            # 使用商品名稱和時間戳生成檔案名
            safe_name = "".join(c for c in product_name if c.isalnum() or c in (' ', '-', '_')).strip()
            safe_name = safe_name.replace(' ', '_')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            file_name = f"products/{safe_name}_{timestamp}_{uuid.uuid4().hex[:8]}.jpg"
        else:
            # 使用原始檔案名稱或生成 UUID
            if '/' in file_path or '\\' in file_path:
                # 如果 file_path 已經是完整路徑，提取檔名
                file_name = os.path.basename(file_path)
            else:
                file_name = file_path
            # 確保在 products 資料夾下
            if not file_name.startswith('products/'):
                file_name = f"products/{file_name}"
        
        # 讀取檔案內容
        if file_content:
            file_data = file_content
        else:
            with open(file_path, 'rb') as f:
                file_data = f.read()
        
        # 上傳到 Supabase Storage
        result = supabase.storage.from_(STORAGE_BUCKET).upload(
            file_name,
            file_data,
            file_options={"content-type": "image/jpeg", "upsert": "false"}
        )
        
        if result:
            # 取得公開 URL
            public_url = supabase.storage.from_(STORAGE_BUCKET).get_public_url(file_name)
            logger.info(f"圖片上傳成功：{file_name}")
            return public_url
        else:
            logger.error("圖片上傳失敗：未返回結果")
            return None
            
    except Exception as e:
        logger.error(f"圖片上傳失敗：{e}")
        return None


def upload_product_image_from_bytes(
    file_content: bytes,
    file_extension: str = "jpg",
    product_name: Optional[str] = None
) -> Optional[str]:
    """
    從 bytes 上傳商品圖片（適用於從 LINE Bot 或其他來源接收的圖片）
    
    Args:
        file_content: 圖片的 bytes 內容
        file_extension: 檔案副檔名（預設：jpg）
        product_name: 商品名稱（用於生成檔案名稱，選填）
    
    Returns:
        圖片的公開 URL，失敗則返回 None
    """
    if not file_content:
        logger.error("檔案內容為空")
        return None
    
    # 生成檔案名稱
    if product_name:
        safe_name = "".join(c for c in product_name if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_name = safe_name.replace(' ', '_')
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"products/{safe_name}_{timestamp}_{uuid.uuid4().hex[:8]}.{file_extension}"
    else:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_name = f"products/{timestamp}_{uuid.uuid4().hex[:8]}.{file_extension}"
    
    try:
        # 上傳到 Supabase Storage
        result = supabase.storage.from_(STORAGE_BUCKET).upload(
            file_name,
            file_content,
            file_options={"content-type": f"image/{file_extension}", "upsert": "false"}
        )
        
        if result:
            # 取得公開 URL
            public_url = supabase.storage.from_(STORAGE_BUCKET).get_public_url(file_name)
            logger.info(f"圖片上傳成功：{file_name}")
            return public_url
        else:
            logger.error("圖片上傳失敗：未返回結果")
            return None
            
    except Exception as e:
        logger.error(f"圖片上傳失敗：{e}")
        return None


def delete_product_image(image_url: str) -> bool:
    """
    刪除 Supabase Storage 中的圖片
    
    Args:
        image_url: 圖片的公開 URL
    
    Returns:
        成功返回 True，失敗返回 False
    """
    if not supabase:
        logger.error("Supabase 未初始化")
        return False
    
    try:
        # 從 URL 中提取檔案路徑
        # URL 格式：https://xxx.supabase.co/storage/v1/object/public/product-images/products/xxx.jpg
        if '/object/public/' in image_url:
            file_path = image_url.split('/object/public/')[-1]
            # 移除 bucket 名稱（如果包含）
            if file_path.startswith(f"{STORAGE_BUCKET}/"):
                file_path = file_path[len(f"{STORAGE_BUCKET}/"):]
        else:
            logger.error(f"無法解析圖片 URL：{image_url}")
            return False
        
        # 刪除檔案
        result = supabase.storage.from_(STORAGE_BUCKET).remove([file_path])
        logger.info(f"圖片刪除成功：{file_path}")
        return True
        
    except Exception as e:
        logger.error(f"圖片刪除失敗：{e}")
        return False


def create_product_with_image(
    name: str,
    price: float,
    image_path: Optional[str] = None,
    image_content: Optional[bytes] = None,
    description: Optional[str] = None,
    category: Optional[str] = None,
    ingredients: Optional[str] = None,
    **kwargs
) -> Optional[Dict[str, Any]]:
    """
    建立商品並同時上傳圖片（便利函數）
    
    Args:
        name: 商品名稱
        price: 價格
        image_path: 本地圖片路徑
        image_content: 圖片內容（bytes），如果提供則優先使用
        description: 商品描述
        category: 商品分類
        ingredients: 成分/規格說明
        **kwargs: 其他商品欄位
    
    Returns:
        建立的商品資料（包含 image_url），失敗則返回 None
    """
    image_url = None
    
    # 上傳圖片
    if image_content:
        image_url = upload_product_image_from_bytes(image_content, product_name=name)
    elif image_path:
        image_url = upload_product_image(image_path, product_name=name)
    
    # 建立商品
    return create_product(
        name=name,
        price=price,
        description=description,
        category=category,
        image_url=image_url,
        ingredients=ingredients,
        **kwargs
    )


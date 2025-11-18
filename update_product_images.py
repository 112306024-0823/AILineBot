"""
產品圖片上傳與更新腳本

此腳本用於：
1. 上傳圖片到 Supabase Storage
2. 更新 products 表的 image_url 欄位

使用方法：
    python update_product_images.py --product-id <UUID> --image-path <路徑>
    或
    python update_product_images.py --product-name <名稱> --image-path <路徑>
    或
    python update_product_images.py --batch-folder <資料夾路徑>
"""

import os
import sys
import argparse
from typing import Optional, List, Dict, Any
from dotenv import load_dotenv

# 載入環境變數
load_dotenv()

from supabase_utils import (
    upload_product_image,
    upload_product_image_from_bytes,
    update_product,
    get_product_by_id,
    search_products,
    supabase
)


def update_single_product_image(
    product_id: Optional[str] = None,
    product_name: Optional[str] = None,
    image_path: Optional[str] = None,
    image_url: Optional[str] = None
) -> bool:
    """
    更新單一產品的圖片
    
    Args:
        product_id: 產品 ID（UUID）
        product_name: 產品名稱（如果沒有提供 product_id）
        image_path: 本地圖片檔案路徑
        image_url: 已上傳的圖片 URL（如果已經上傳）
    
    Returns:
        是否成功
    """
    # 1. 取得產品資訊
    if product_id:
        product = get_product_by_id(product_id)
    elif product_name:
        products = search_products(name=product_name, limit=1)
        if not products:
            print(f"❌ 找不到產品：{product_name}")
            return False
        product = products[0]
        product_id = product['id']
    else:
        print("❌ 請提供 product_id 或 product_name")
        return False
    
    if not product:
        print(f"❌ 找不到產品")
        return False
    
    print(f"📦 找到產品：{product['name']} (ID: {product_id})")
    
    # 2. 上傳圖片或使用現有 URL
    if image_url:
        final_image_url = image_url
        print(f"✅ 使用提供的圖片 URL")
    elif image_path:
        if not os.path.exists(image_path):
            print(f"❌ 圖片檔案不存在：{image_path}")
            return False
        
        print(f"📤 上傳圖片：{image_path}")
        final_image_url = upload_product_image(
            file_path=image_path,
            product_name=product['name']
        )
        
        if not final_image_url:
            print(f"❌ 圖片上傳失敗")
            return False
    else:
        print("❌ 請提供 image_path 或 image_url")
        return False
    
    # 3. 更新資料表
    print(f"🔄 更新產品圖片 URL...")
    try:
        updated_product = update_product(
            product_id=product_id,
            image_url=final_image_url
        )
        
        if updated_product:
            print(f"✅ 更新成功！")
            print(f"   產品：{updated_product['name']}")
            print(f"   圖片 URL：{final_image_url}")
            return True
        else:
            print(f"❌ 更新失敗")
            return False
    except Exception as e:
        print(f"❌ 更新時發生錯誤：{e}")
        return False


def batch_update_from_folder(folder_path: str) -> Dict[str, Any]:
    """
    從資料夾批次更新產品圖片
    
    假設圖片檔名與產品名稱相同（不包含副檔名）
    
    Args:
        folder_path: 圖片資料夾路徑
    
    Returns:
        更新結果統計
    """
    if not os.path.exists(folder_path):
        print(f"❌ 資料夾不存在：{folder_path}")
        return {"success": 0, "failed": 0, "not_found": 0}
    
    # 取得所有圖片檔案
    image_files = []
    for ext in ['jpg', 'jpeg', 'png', 'webp', 'gif']:
        image_files.extend([
            f for f in os.listdir(folder_path)
            if f.lower().endswith(f'.{ext}')
        ])
    
    if not image_files:
        print(f"⚠️ 資料夾中沒有找到圖片檔案")
        return {"success": 0, "failed": 0, "not_found": 0}
    
    print(f"📁 找到 {len(image_files)} 個圖片檔案")
    
    results = {"success": 0, "failed": 0, "not_found": 0}
    
    for image_file in image_files:
        image_path = os.path.join(folder_path, image_file)
        # 從檔名取得產品名稱（移除副檔名）
        product_name = os.path.splitext(image_file)[0]
        
        print(f"\n處理：{image_file} -> 產品：{product_name}")
        
        success = update_single_product_image(
            product_name=product_name,
            image_path=image_path
        )
        
        if success:
            results["success"] += 1
        else:
            # 檢查是找不到產品還是上傳失敗
            products = search_products(name=product_name, limit=1)
            if not products:
                results["not_found"] += 1
            else:
                results["failed"] += 1
    
    return results


def list_products_without_images(limit: int = 20) -> List[Dict[str, Any]]:
    """
    列出沒有圖片的產品
    
    Args:
        limit: 回傳數量上限
    
    Returns:
        產品列表
    """
    if not supabase:
        print("❌ Supabase 未初始化")
        return []
    
    try:
        # 查詢沒有 image_url 或 image_url 為空的產品
        result = supabase.table('products').select('id, name, image_url').or_(
            'image_url.is.null,image_url.eq.'
        ).limit(limit).execute()
        
        products = result.data
        print(f"📋 找到 {len(products)} 個沒有圖片的產品：")
        for product in products:
            print(f"   - {product['name']} (ID: {product['id']})")
        
        return products
    except Exception as e:
        print(f"❌ 查詢失敗：{e}")
        return []


def main():
    """主函數"""
    parser = argparse.ArgumentParser(
        description='更新產品圖片到 Supabase Storage 並更新資料表'
    )
    
    parser.add_argument(
        '--product-id',
        type=str,
        help='產品 ID (UUID)'
    )
    parser.add_argument(
        '--product-name',
        type=str,
        help='產品名稱'
    )
    parser.add_argument(
        '--image-path',
        type=str,
        help='本地圖片檔案路徑'
    )
    parser.add_argument(
        '--image-url',
        type=str,
        help='已上傳的圖片 URL（如果已經上傳）'
    )
    parser.add_argument(
        '--batch-folder',
        type=str,
        help='批次處理：從資料夾更新多個產品圖片'
    )
    parser.add_argument(
        '--list-no-image',
        action='store_true',
        help='列出沒有圖片的產品'
    )
    
    args = parser.parse_args()
    
    # 列出沒有圖片的產品
    if args.list_no_image:
        list_products_without_images()
        return
    
    # 批次處理
    if args.batch_folder:
        print(f"📁 批次處理資料夾：{args.batch_folder}")
        results = batch_update_from_folder(args.batch_folder)
        print(f"\n📊 處理結果：")
        print(f"   ✅ 成功：{results['success']}")
        print(f"   ❌ 失敗：{results['failed']}")
        print(f"   ⚠️ 找不到產品：{results['not_found']}")
        return
    
    # 單一產品更新
    if not (args.product_id or args.product_name):
        print("❌ 請提供 --product-id 或 --product-name")
        parser.print_help()
        return
    
    if not (args.image_path or args.image_url):
        print("❌ 請提供 --image-path 或 --image-url")
        parser.print_help()
        return
    
    success = update_single_product_image(
        product_id=args.product_id,
        product_name=args.product_name,
        image_path=args.image_path,
        image_url=args.image_url
    )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()


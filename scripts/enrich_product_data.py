"""
補充商品缺失資料腳本
使用 Gemini AI 生成缺失的 ingredients、description、barcode 等資訊
"""

import os
import sys
import io
import time
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
import google.generativeai as genai
import re

# 設定 UTF-8 編碼
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

load_dotenv()

# 加入父目錄到 path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from supabase_utils import supabase

# 設定 Gemini API
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel('gemini-pro')


def generate_product_info(product: Dict[str, Any]) -> Dict[str, Any]:
    """
    使用 Gemini AI 生成商品資訊
    
    Args:
        product: 商品資料字典
    
    Returns:
        包含生成資訊的字典（ingredients, description, barcode）
    """
    name = product.get('name', '')
    brand = product.get('brand', '')
    category = product.get('category', '')
    existing_desc = product.get('description', '')
    
    prompt = f"""你是一位商品資訊專家。請根據以下商品資訊，生成詳細的商品描述、成分和可能的條碼格式。

商品名稱：{name}
品牌：{brand or '未知'}
分類：{category}

請提供以下資訊（用繁體中文回答）：
1. **商品描述**：簡短但詳細的商品描述（50-100字），說明商品特色、用途、口感等
2. **成分**：列出主要成分（如果已知），格式為「成分1、成分2、成分3...」
3. **條碼**：如果無法確定真實條碼，請生成一個符合台灣商品條碼格式的13位數字（471開頭）

請用以下格式回答：
描述：[商品描述]
成分：[成分列表]
條碼：[13位數字條碼]

如果某項資訊無法確定，請標註「無法確定」。
"""
    
    try:
        response = model.generate_content(prompt)
        text = response.text
        
        result = {}
        
        # 解析描述
        desc_match = re.search(r'描述[：:]\s*(.+?)(?=\n|成分|條碼|$)', text, re.DOTALL)
        if desc_match:
            desc = desc_match.group(1).strip()
            if desc and '無法確定' not in desc:
                result['description'] = desc
        
        # 解析成分
        ing_match = re.search(r'成分[：:]\s*(.+?)(?=\n|條碼|$)', text, re.DOTALL)
        if ing_match:
            ingredients = ing_match.group(1).strip()
            if ingredients and '無法確定' not in ingredients:
                result['ingredients'] = ingredients
        
        # 解析條碼
        barcode_match = re.search(r'條碼[：:]\s*(\d{13})', text)
        if barcode_match:
            result['barcode'] = barcode_match.group(1)
        
        return result
    
    except Exception as e:
        print(f"    [錯誤] 生成商品資訊失敗: {e}")
        return {}


def update_product_data(product_id: str, updates: Dict[str, Any]) -> bool:
    """
    更新商品資料
    
    Args:
        product_id: 商品 ID
        updates: 要更新的資料
    
    Returns:
        是否成功
    """
    if not supabase:
        return False
    
    try:
        # 移除 None 值和空字串
        updates = {k: v for k, v in updates.items() if v is not None and v != ''}
        
        if not updates:
            return False
        
        result = supabase.table('products').update(updates).eq('id', product_id).execute()
        
        if result.data:
            print(f"    [✓] 更新成功: {', '.join(updates.keys())}")
            return True
        else:
            print(f"    [✗] 更新失敗")
            return False
    
    except Exception as e:
        print(f"    [✗] 更新時發生錯誤: {e}")
        return False


def get_products_missing_data() -> List[Dict[str, Any]]:
    """
    獲取缺少資料的商品列表
    
    Returns:
        商品列表
    """
    if not supabase:
        return []
    
    try:
        # 獲取所有商品
        result = supabase.table('products').select('*').execute()
        
        if not result.data:
            return []
        
        # 篩選出缺少資料的商品
        missing_data_products = []
        for product in result.data:
            needs_update = False
            missing_fields = []
            
            if not product.get('ingredients'):
                needs_update = True
                missing_fields.append('ingredients')
            
            if not product.get('barcode'):
                needs_update = True
                missing_fields.append('barcode')
            
            if not product.get('description') or product.get('description', '').strip() == '':
                needs_update = True
                missing_fields.append('description')
            
            if needs_update:
                product['_missing_fields'] = missing_fields
                missing_data_products.append(product)
        
        return missing_data_products
    
    except Exception as e:
        print(f"[錯誤] 獲取商品列表失敗: {e}")
        return []


def enrich_products(batch_size: int = 10, max_products: Optional[int] = None):
    """
    補充商品缺失資料
    
    Args:
        batch_size: 每批處理的商品數量
        max_products: 最多處理幾個商品（None 表示全部）
    """
    print("\n" + "="*60)
    print("商品資料補充腳本")
    print("="*60 + "\n")
    
    if not supabase:
        print("[錯誤] Supabase 未連線，請檢查環境變數設定")
        return
    
    if not os.getenv("GEMINI_API_KEY"):
        print("[錯誤] GEMINI_API_KEY 未設定")
        return
    
    print("[✓] Supabase 已連線")
    print("[✓] Gemini API 已設定\n")
    
    # 獲取缺少資料的商品
    print("[1/3] 正在獲取缺少資料的商品...")
    products = get_products_missing_data()
    
    if not products:
        print("✓ 所有商品資料完整，無需補充")
        return
    
    print(f"✓ 找到 {len(products)} 個需要補充資料的商品\n")
    
    # 限制處理數量
    if max_products:
        products = products[:max_products]
        print(f"[INFO] 限制處理數量為 {max_products} 個\n")
    
    # 處理商品
    print(f"[2/3] 開始補充商品資料（每批 {batch_size} 個）...\n")
    
    success_count = 0
    for i, product in enumerate(products, 1):
        print(f"[{i}/{len(products)}] 處理商品: {product['name']}")
        print(f"    缺少欄位: {', '.join(product.get('_missing_fields', []))}")
        
        # 使用 AI 生成資訊
        generated_info = generate_product_info(product)
        
        if generated_info:
            # 只更新缺少的欄位
            updates = {}
            missing_fields = product.get('_missing_fields', [])
            
            if 'description' in missing_fields and 'description' in generated_info:
                updates['description'] = generated_info['description']
            
            if 'ingredients' in missing_fields and 'ingredients' in generated_info:
                updates['ingredients'] = generated_info['ingredients']
            
            if 'barcode' in missing_fields and 'barcode' in generated_info:
                updates['barcode'] = generated_info['barcode']
            
            # 更新資料庫
            if updates:
                if update_product_data(product['id'], updates):
                    success_count += 1
                    print(f"    [✓] 已補充: {', '.join(updates.keys())}")
                else:
                    print(f"    [✗] 更新失敗")
            else:
                print(f"    [跳過] 無法生成所需資訊")
        else:
            print(f"    [跳過] AI 無法生成資訊")
        
        # 避免 API 請求過快
        if i % batch_size == 0:
            print(f"\n[INFO] 已處理 {i} 個商品，暫停 2 秒...\n")
            time.sleep(2)
        else:
            time.sleep(0.5)
    
    print(f"\n{'='*60}")
    print(f"[3/3] 完成！")
    print(f"成功補充: {success_count}/{len(products)} 個商品")
    print(f"{'='*60}\n")


def main():
    """主函數"""
    print("\n選擇模式：")
    print("1. 補充所有缺少資料的商品（分批處理）")
    print("2. 只補充前 20 個商品（測試用）")
    print("3. 只補充前 50 個商品")
    
    choice = input("\n請輸入選項 (1-3): ").strip()
    
    if choice == '1':
        enrich_products(batch_size=10, max_products=None)
    elif choice == '2':
        enrich_products(batch_size=5, max_products=20)
    elif choice == '3':
        enrich_products(batch_size=10, max_products=50)
    else:
        print("[錯誤] 無效的選項")


if __name__ == "__main__":
    main()


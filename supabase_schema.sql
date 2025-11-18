-- ============================================
-- Supabase 資料庫結構設計
-- 賣場線上線下智慧系統
-- ============================================

-- 1. 商品資料表 (products)
-- 儲存商品的基本資訊、規格和照片
CREATE TABLE IF NOT EXISTS products (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name TEXT NOT NULL,
    price DECIMAL(10, 2) NOT NULL,
    description TEXT,
    category TEXT,
    image_url TEXT,  -- Supabase Storage 的圖片 URL
    ingredients TEXT,  -- 成分/規格說明
    brand TEXT,  -- 品牌（選填）
    barcode TEXT UNIQUE,  -- 條碼（選填，用於掃描辨識）
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- 建立索引以加速搜尋
CREATE INDEX IF NOT EXISTS idx_products_name ON products(name);
CREATE INDEX IF NOT EXISTS idx_products_category ON products(category);
CREATE INDEX IF NOT EXISTS idx_products_barcode ON products(barcode);

-- 2. 商品位置表 (product_locations)
-- 儲存商品在實體賣場的位置資訊
CREATE TABLE IF NOT EXISTS product_locations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_id UUID NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    area TEXT NOT NULL,  -- 區域（例如：A區、B區、生鮮區）
    shelf TEXT,  -- 貨架編號（例如：3號貨架、A-3）
    floor INTEGER,  -- 樓層（例如：1樓、2樓）
    position_x DECIMAL(10, 2),  -- X 座標（用於地圖定位，可選）
    position_y DECIMAL(10, 2),  -- Y 座標（用於地圖定位，可選）
    notes TEXT,  -- 備註（例如：靠近入口、冷藏區）
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    UNIQUE(product_id, area, shelf)  -- 同一商品在同一區域的同一貨架只能有一個位置
);

-- 建立索引以加速位置查詢
CREATE INDEX IF NOT EXISTS idx_product_locations_product_id ON product_locations(product_id);
CREATE INDEX IF NOT EXISTS idx_product_locations_area ON product_locations(area);
CREATE INDEX IF NOT EXISTS idx_product_locations_shelf ON product_locations(shelf);
CREATE INDEX IF NOT EXISTS idx_product_locations_floor ON product_locations(floor);

-- 3. 自動更新 updated_at 的觸發器函數
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ language 'plpgsql';

-- 為 products 表建立觸發器
CREATE TRIGGER update_products_updated_at BEFORE UPDATE ON products
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 為 product_locations 表建立觸發器
CREATE TRIGGER update_product_locations_updated_at BEFORE UPDATE ON product_locations
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ============================================
-- 範例資料（可選）
-- ============================================

-- 插入範例商品
-- INSERT INTO products (name, price, description, category, ingredients) VALUES
-- ('可口可樂 330ml', 25.00, '經典碳酸飲料', '飲料', '水、糖、二氧化碳、焦糖色素'),
-- ('統一泡麵 肉燥風味', 35.00, '經典泡麵', '食品', '麵粉、棕櫚油、調味料'),
-- ('鮮奶 1000ml', 89.00, '新鮮牛奶', '乳製品', '生乳');

-- 插入範例位置
-- INSERT INTO product_locations (product_id, area, shelf, floor, notes) VALUES
-- ((SELECT id FROM products WHERE name = '可口可樂 330ml'), 'A區', '3號貨架', 1, '靠近入口'),
-- ((SELECT id FROM products WHERE name = '統一泡麵 肉燥風味'), 'B區', '5號貨架', 1, '泡麵專區'),
-- ((SELECT id FROM products WHERE name = '鮮奶 1000ml'), 'C區', '冷藏櫃-2', 1, '需冷藏');

-- ============================================
-- 查詢範例
-- ============================================

-- 查詢商品及其位置
-- SELECT 
--     p.*,
--     json_agg(
--         json_build_object(
--             'area', pl.area,
--             'shelf', pl.shelf,
--             'floor', pl.floor,
--             'notes', pl.notes
--         )
--     ) as locations
-- FROM products p
-- LEFT JOIN product_locations pl ON p.id = pl.product_id
-- WHERE p.name ILIKE '%可樂%'
-- GROUP BY p.id;

-- 根據位置查詢商品
-- SELECT 
--     p.*,
--     pl.area,
--     pl.shelf,
--     pl.floor
-- FROM products p
-- INNER JOIN product_locations pl ON p.id = pl.product_id
-- WHERE pl.area = 'A區' AND pl.shelf = '3號貨架';


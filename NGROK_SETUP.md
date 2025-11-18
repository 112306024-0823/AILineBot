# ngrok 使用指南

## 為什麼使用 ngrok？

✅ **優點：**
- 本地開發時響應速度快（無需部署）
- 修改代碼立即生效，無需等待部署
- 適合快速測試和調試
- 免費版足夠開發使用

⚠️ **缺點：**
- 免費版 URL 每次重啟都會變化
- 需要保持本地電腦和網路連接
- 免費版有連接數限制

---

## 安裝 ngrok

### Windows 方法 1：直接下載
1. 訪問 https://ngrok.com/download
2. 下載 Windows 版本
3. 解壓縮到任意資料夾（例如：`C:\ngrok`）
4. 將 ngrok.exe 的路徑添加到系統環境變數 PATH

### Windows 方法 2：使用 Chocolatey
```powershell
choco install ngrok
```

### Windows 方法 3：使用 Scoop
```powershell
scoop install ngrok
```

---

## 註冊 ngrok 帳號（推薦）

1. 訪問 https://dashboard.ngrok.com/signup
2. 註冊免費帳號
3. 獲取 authtoken（在 Dashboard > Your Authtoken）
4. 配置 authtoken：
```bash
ngrok config add-authtoken YOUR_AUTHTOKEN
```

**為什麼要註冊？**
- 免費版可以獲得固定域名（需要付費）
- 可以查看請求日誌和統計
- 更好的穩定性

---

## 使用步驟

### 1. 啟動本地 Flask 應用

在專案目錄下運行：
```bash
python app.py
```

應該會看到：
```
 * Running on http://0.0.0.0:5000
```

### 2. 啟動 ngrok（新開一個終端）

```bash
ngrok http 5000
```

**輸出範例：**
```
ngrok                                                                              
                                                                                   
Session Status                online                                               
Account                       Your Name (Plan: Free)                               
Version                       3.x.x                                                
Region                        Asia Pacific (ap)                                    
Latency                       45ms                                                 
Web Interface                 http://127.0.0.1:4040                                
Forwarding                    https://xxxx-xx-xx-xx-xx.ngrok-free.app -> http://localhost:5000
                                                                                   
Connections                   ttl     opn     rt1     rt5     p50     p90          
                              0       0       0.00    0.00    0.00    0.00        
```

**重要資訊：**
- `Forwarding` 後面的 URL 就是你的公開 URL
- 例如：`https://xxxx-xx-xx-xx-xx.ngrok-free.app`
- Web Interface：`http://127.0.0.1:4040` 可以查看所有請求

### 3. 配置 LINE Webhook

1. 訪問 LINE Developers Console：https://developers.line.biz/console/
2. 選擇你的 Channel
3. 進入 **Messaging API** 設定
4. 找到 **Webhook URL** 設定
5. 輸入：`https://xxxx-xx-xx-xx-xx.ngrok-free.app/callback`
   （替換成你的 ngrok URL）
6. 點擊 **Verify** 驗證連接
7. 啟用 **Use webhook**

### 4. 測試

1. 在 LINE 中發送訊息給你的 Bot
2. 在終端查看 Flask 的日誌輸出
3. 在 ngrok Web Interface (`http://127.0.0.1:4040`) 查看請求詳情

---

## 常用 ngrok 命令

### 基本使用
```bash
# 轉發本地 5000 端口
ngrok http 5000

# 指定區域（可選，可能更快）
ngrok http 5000 --region ap  # Asia Pacific
ngrok http 5000 --region us  # United States
ngrok http 5000 --region eu  # Europe
```

### 查看請求（Web Interface）
訪問 `http://127.0.0.1:4040` 可以：
- 查看所有 HTTP 請求
- 查看請求/回應內容
- 重放請求（Replay）

### 使用固定域名（需要付費）
```bash
ngrok http 5000 --domain=your-fixed-domain.ngrok.app
```

---

## 開發工作流程

### 推薦流程：

1. **開發階段**（使用 ngrok）
   ```bash
   # 終端 1：啟動 Flask
   python app.py
   
   # 終端 2：啟動 ngrok
   ngrok http 5000
   ```
   - LINE webhook 指向 ngrok URL
   - 修改代碼後重啟 Flask 即可，無需重新部署

2. **測試完成後**（切換到 Render）
   - 將代碼推送到 Git
   - Render 自動部署
   - LINE webhook 改為 Render URL

---

## 故障排除

### 問題 1：ngrok 連接失敗
**解決方案：**
- 檢查防火牆設定
- 確認 Flask 正在運行
- 確認端口號正確（預設 5000）

### 問題 2：LINE Webhook 驗證失敗
**解決方案：**
- 確認 ngrok URL 正確（包含 `/callback`）
- 確認 Flask 的 `/callback` 路由正常
- 檢查 LINE Developers Console 的錯誤訊息

### 問題 3：ngrok URL 每次重啟都變
**解決方案：**
- 這是免費版的限制
- 每次重啟 ngrok 後，記得更新 LINE webhook URL
- 或考慮付費版獲得固定域名

### 問題 4：請求超時
**解決方案：**
- 檢查本地網路連接
- 嘗試更換 ngrok 區域（`--region` 參數）

---

## 進階技巧

### 1. 使用 ngrok 配置文件

創建 `ngrok.yml`：
```yaml
version: "2"
authtoken: YOUR_AUTHTOKEN
tunnels:
  flask:
    addr: 5000
    proto: http
```

然後運行：
```bash
ngrok start flask
```

### 2. 查看日誌
```bash
# 查看 ngrok 日誌
ngrok http 5000 --log=stdout

# 保存日誌到文件
ngrok http 5000 --log=ngrok.log
```

### 3. 同時監聽多個端口
```bash
# 需要配置文件
ngrok start flask api
```

---

## 與 Render 的比較

| 特性 | ngrok | Render |
|------|-------|--------|
| 速度 | ⚡ 快（本地運行） | 🐢 較慢（需要部署） |
| 穩定性 | ⚠️ 需要保持本地運行 | ✅ 24/7 運行 |
| 修改代碼 | ✅ 立即生效 | ❌ 需要重新部署 |
| URL | ❌ 免費版會變 | ✅ 固定 URL |
| 成本 | ✅ 免費 | ✅ 免費（有限制） |
| 用途 | 開發/測試 | 生產環境 |

---

## 總結

**使用 ngrok 當：**
- ✅ 正在開發和測試
- ✅ 需要快速迭代
- ✅ 本地調試

**使用 Render 當：**
- ✅ 開發完成
- ✅ 需要 24/7 運行
- ✅ 生產環境部署

**最佳實踐：**
開發時用 ngrok，完成後部署到 Render！


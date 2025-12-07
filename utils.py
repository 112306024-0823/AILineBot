import os

def check_environment_variables():
    required_vars = [
        "CHANNEL_ACCESS_TOKEN",
        "CHANNEL_SECRET",
        "SUPABASE_URL",
        "SUPABASE_KEY",
    ]

    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)

    # 檢查至少有一個 GEMINI_API_KEY
    has_gemini_key = bool(os.getenv("GEMINI_API_KEY"))
    if not has_gemini_key:
        missing.append("GEMINI_API_KEY (至少需要一個)")

    if missing:
        raise EnvironmentError(
            f"❌ 缺少必要環境變數：{', '.join(missing)}\n"
            "請確認 .env 設定完整後再啟動程式。\n"
            "提示：可以設定多個 GEMINI_API_KEY（GEMINI_API_KEY, GEMINI_API_KEY_2, GEMINI_API_KEY_3, GEMINI_API_KEY_4, GEMINI_API_KEY_5）"
        )
    else:
        # 統計有多少個 API key
        api_key_count = sum(1 for i in range(1, 6) if os.getenv(f"GEMINI_API_KEY_{i}" if i > 1 else "GEMINI_API_KEY"))
        print("✅ 所有必要環境變數皆已設定完成！")
        if api_key_count > 1:
            print(f"✅ 已載入 {api_key_count} 個 Gemini API Key（支援自動切換）")

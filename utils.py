import os

def check_environment_variables():
    required_vars = [
        "CHANNEL_ACCESS_TOKEN",
        "CHANNEL_SECRET",
        "SUPABASE_URL",
        "SUPABASE_KEY",
        "GEMINI_API_KEY"  
    ]

    missing = []
    for var in required_vars:
        if not os.getenv(var):
            missing.append(var)

    if missing:
        raise EnvironmentError(
            f"❌ 缺少必要環境變數：{', '.join(missing)}\n"
            "請確認 .env 設定完整後再啟動程式。"
        )
    else:
        print("✅ 所有必要環境變數皆已設定完成！")

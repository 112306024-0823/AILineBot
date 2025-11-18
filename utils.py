import os
import logging

# 設定日誌
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def check_environment_variables():
    """檢查必要的環境變數是否已設置"""
    required_env_vars = ["CHANNEL_ACCESS_TOKEN", "CHANNEL_SECRET"]
    missing_vars = [var for var in required_env_vars if not os.getenv(var)]
    if missing_vars:
        raise EnvironmentError(f"缺少以下環境變數：{', '.join(missing_vars)}")
    logger.info("所有必要的環境變數已正確設置。")


def save_file_locally(user_id, file_name, file_path, subject="", grade="", year="", price=""):
    """將檔案資訊記錄到本地（簡化版本，僅記錄日誌）"""
    try:
        logger.info(f"檔案已接收：{file_name}，用戶：{user_id}，科目：{subject}，年級：{grade}，年份：{year}，價格：{price}")
        # 檔案已儲存在本地 uploads 資料夾，這裡僅記錄日誌
        return True
    except Exception as e:
        logger.error(f"記錄檔案資訊失敗：{e}")
        return False

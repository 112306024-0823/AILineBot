"""
API Key 管理器
管理多個 Gemini API Key，當一個用盡時自動切換到下一個
"""
import os
import logging
from typing import List, Optional
import google.generativeai as genai
from google.api_core import exceptions as google_exceptions

logger = logging.getLogger(__name__)


class GeminiAPIKeyManager:
    """
    Gemini API Key 管理器
    
    管理多個 API key，當一個配額用盡時自動切換到下一個可用的 key
    """
    
    def __init__(self, api_keys: Optional[List[str]] = None):
        """
        初始化 API Key 管理器
        
        Args:
            api_keys: API key 列表，如果為 None 則從環境變數讀取
                     支援 GEMINI_API_KEY, GEMINI_API_KEY_2, GEMINI_API_KEY_3, GEMINI_API_KEY_4, GEMINI_API_KEY_5
        """
        if api_keys is None:
            api_keys = self._load_api_keys_from_env()
        
        # 過濾掉空值
        self.api_keys = [key for key in api_keys if key]
        
        if not self.api_keys:
            raise ValueError("至少需要一個有效的 API key")
        
        self.current_key_index = 0
        self.failed_keys = set()  # 記錄已失敗的 key 索引
        
        # 初始化第一個 API key
        self._configure_current_key()
        
        logger.info(f"API Key 管理器初始化完成，共有 {len(self.api_keys)} 個 API key")
    
    def _load_api_keys_from_env(self) -> List[str]:
        """
        從環境變數載入 API keys
        
        Returns:
            API key 列表
        """
        keys = []
        
        # 優先讀取 GEMINI_API_KEY（向後兼容）
        primary_key = os.getenv("GEMINI_API_KEY")
        if primary_key:
            keys.append(primary_key)
        
        # 讀取其他備用 keys
        for i in range(2, 6):  # GEMINI_API_KEY_2, GEMINI_API_KEY_3, GEMINI_API_KEY_4, GEMINI_API_KEY_5
            key = os.getenv(f"GEMINI_API_KEY_{i}")
            if key:
                keys.append(key)
        
        return keys
    
    def _configure_current_key(self) -> None:
        """配置當前使用的 API key"""
        if self.current_key_index < len(self.api_keys):
            current_key = self.api_keys[self.current_key_index]
            genai.configure(api_key=current_key)
            logger.info(f"已切換到 API key #{self.current_key_index + 1}")
    
    def _is_quota_exceeded_error(self, error: Exception) -> bool:
        """
        判斷是否為配額用盡錯誤
        
        Args:
            error: 異常物件
            
        Returns:
            是否為配額用盡錯誤
        """
        error_str = str(error).lower()
        error_type = type(error).__name__
        
        # 檢查常見的配額用盡錯誤訊息
        quota_keywords = [
            "quota",
            "resource exhausted",
            "rate limit",
            "429",
            "insufficient quota",
            "quota exceeded",
            "billing",
            "permission denied",
            "api key not valid",
        ]
        
        # 檢查錯誤類型
        if isinstance(error, google_exceptions.ResourceExhausted):
            return True
        
        # 檢查錯誤訊息
        if any(keyword in error_str for keyword in quota_keywords):
            return True
        
        # 檢查錯誤類型名稱
        if "ResourceExhausted" in error_type or "QuotaExceeded" in error_type:
            return True
        
        return False
    
    def get_current_key(self) -> str:
        """
        獲取當前使用的 API key
        
        Returns:
            當前 API key
        """
        return self.api_keys[self.current_key_index]
    
    def switch_to_next_key(self) -> bool:
        """
        切換到下一個可用的 API key
        
        Returns:
            是否成功切換
        """
        # 標記當前 key 為失敗
        self.failed_keys.add(self.current_key_index)
        
        # 尋找下一個可用的 key
        for i in range(len(self.api_keys)):
            next_index = (self.current_key_index + i + 1) % len(self.api_keys)
            
            # 如果所有 key 都失敗了，重置失敗記錄
            if len(self.failed_keys) >= len(self.api_keys):
                logger.warning("所有 API key 都已失敗，重置失敗記錄")
                self.failed_keys.clear()
            
            if next_index not in self.failed_keys:
                self.current_key_index = next_index
                self._configure_current_key()
                logger.info(f"已切換到 API key #{self.current_key_index + 1}")
                return True
        
        logger.error("沒有可用的 API key")
        return False
    
    def handle_api_error(self, error: Exception) -> bool:
        """
        處理 API 錯誤，如果是配額用盡則自動切換
        
        Args:
            error: 異常物件
            
        Returns:
            是否已處理並切換到新的 key
        """
        if self._is_quota_exceeded_error(error):
            logger.warning(f"檢測到 API key 配額用盡錯誤：{error}")
            return self.switch_to_next_key()
        return False
    
    def get_model(self, model_name: str = "gemini-2.5-flash"):
        """
        獲取 GenerativeModel 實例，如果發生配額錯誤會自動重試
        
        Args:
            model_name: 模型名稱
            
        Returns:
            GenerativeModel 實例
        """
        return genai.GenerativeModel(model_name)
    
    def generate_content_with_retry(self, model, *args, **kwargs):
        """
        使用當前 API key 生成內容，如果失敗會自動切換並重試
        
        Args:
            model: GenerativeModel 實例
            *args: 傳遞給 generate_content 的參數
            **kwargs: 傳遞給 generate_content 的關鍵字參數
            
        Returns:
            generate_content 的回應
            
        Raises:
            如果所有 key 都失敗，會拋出最後一個錯誤
        """
        max_retries = len(self.api_keys)
        last_error = None
        
        # 嘗試獲取模型名稱（用於切換 key 時重新創建模型）
        model_name = "gemini-2.5-flash"  # 預設值
        if hasattr(model, '_model_name'):
            model_name = model._model_name
        elif hasattr(model, 'model_name'):
            model_name = model.model_name
        
        for attempt in range(max_retries):
            try:
                return model.generate_content(*args, **kwargs)
            except Exception as e:
                last_error = e
                
                # 如果是配額錯誤，嘗試切換 key
                if self.handle_api_error(e):
                    # 重新創建模型（使用新的 API key）
                    model = self.get_model(model_name)
                    logger.info(f"重試請求（使用新的 API key，嘗試 {attempt + 1}/{max_retries}）")
                    continue
                else:
                    # 不是配額錯誤，直接拋出
                    raise
        
        # 所有重試都失敗
        logger.error(f"所有 API key 都無法使用，最後錯誤：{last_error}")
        raise last_error


# 全域 API Key 管理器實例
_api_key_manager: Optional[GeminiAPIKeyManager] = None


def get_api_key_manager() -> GeminiAPIKeyManager:
    """
    獲取全域 API Key 管理器實例（單例模式）
    
    Returns:
        GeminiAPIKeyManager 實例
    """
    global _api_key_manager
    if _api_key_manager is None:
        _api_key_manager = GeminiAPIKeyManager()
    return _api_key_manager


def reset_api_key_manager():
    """重置 API Key 管理器（用於測試）"""
    global _api_key_manager
    _api_key_manager = None


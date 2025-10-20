from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List, Dict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra="ignore"
    )

    APP_NAME: str = "imagetoprompt-2api"
    APP_VERSION: str = "1.1.0" # 版本升级
    DESCRIPTION: str = "一个将 imagetoprompt.app 转换为兼容 OpenAI 格式 API 的高性能代理，支持多语言和结构化提示。"

    API_MASTER_KEY: Optional[str] = None
    NGINX_PORT: int = 8088

    API_REQUEST_TIMEOUT: int = 180

    DEFAULT_MODEL: str = "image-to-prompt-v1"
    KNOWN_MODELS: List[str] = ["image-to-prompt-v1"]

    # 新增：支持的语言列表，键为显示名称，值为 API 参数
    SUPPORTED_LANGUAGES: Dict[str, str] = {
        "English": "en",
        "Español": "es",
        "Deutsch": "de",
        "Français": "fr",
        "Português": "pt",
        "简体中文": "zh-CN",
        "繁體中文": "zh-TW",
        "العربية": "ar",
        "Русский": "ru",
        "日本語": "ja",
        "한국어": "ko"
    }

settings = Settings()

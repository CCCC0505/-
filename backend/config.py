import os
from functools import lru_cache
from typing import List

from dotenv import load_dotenv


load_dotenv()


class Settings:
    def __init__(self) -> None:
        self.database_url = os.getenv(
            "DATABASE_URL",
            "mysql+pymysql://root:root@127.0.0.1:3306/grade8_ai_demo?charset=utf8mb4",
        )
        self.dashscope_api_key = os.getenv("DASHSCOPE_API_KEY", "")
        self.dashscope_base_url = os.getenv(
            "DASHSCOPE_BASE_URL",
            "https://dashscope.aliyuncs.com/compatible-mode/v1",
        )
        self.qwen_model = os.getenv("QWEN_MODEL", "qwen-plus")
        self.qwen_timeout_seconds = float(os.getenv("QWEN_TIMEOUT_SECONDS", "25"))
        self.app_seed_demo_data = os.getenv("APP_SEED_DEMO_DATA", "true").lower() == "true"

    @property
    def cors_origins(self) -> List[str]:
        return ["*"]

    @property
    def qwen_enabled(self) -> bool:
        return bool(self.dashscope_api_key.strip())


@lru_cache()
def get_settings() -> Settings:
    return Settings()

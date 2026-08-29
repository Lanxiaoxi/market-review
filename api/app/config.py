"""环境变量配置（TUSHARE_TOKEN 等）—— 自动从 .env 加载，惰性读取"""

import os
from functools import lru_cache
from pathlib import Path
from zoneinfo import ZoneInfo

# A 股市场统一使用上海时区（快照任务、收盘判断、日期展示）
SHANGHAI_TZ = ZoneInfo("Asia/Shanghai")


def _load_dotenv():
    """手动加载 .env（不依赖 python-dotenv 的命令行入口）"""
    # python-dotenv 已被 tushare 间接安装
    try:
        from dotenv import load_dotenv

        env_path = Path(__file__).resolve().parent.parent / ".env"
        load_dotenv(env_path)
    except ImportError:
        pass


_load_dotenv()

# 项目根目录（api/）
BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


class Settings:
    """应用配置。

    注意：字段在 __init__ 中惰性读取 env，因此 get_settings() 的
    lru_cache 缓存的是「首次调用时」的环境快照；测试可通过
    `get_settings.cache_clear()` 后重设环境变量注入配置。
    """

    def __init__(self) -> None:
        self.app_env: str = os.getenv("APP_ENV", "development")
        self.tushare_token: str = os.getenv("TUSHARE_TOKEN", "")
        self.ths_api_key: str = os.getenv("THS_API_KEY", "")  # 同花顺金融数据 API Key
        self.api_token: str = os.getenv("API_TOKEN", "")  # 可选写接口鉴权
        self.cors_origins: str = os.getenv("CORS_ORIGINS", "")  # 生产白名单，逗号分隔
        self.database_url: str = os.getenv(
            "DATABASE_URL",
            f"sqlite+aiosqlite:///{(DATA_DIR / 'app.db').as_posix()}",
        )
        # 启动时自动回填的交易日数（0 = 关闭）。首次部署建议设 250，
        # 回填完成后改回 0 —— 已回填的日期会被 fetch_log 跳过，不会重复拉取。
        self.backfill_on_startup_days: int = int(
            os.getenv("BACKFILL_ON_STARTUP_DAYS", "0")
        )

    @property
    def is_dev(self) -> bool:
        return self.app_env == "development"

    @property
    def has_tushare(self) -> bool:
        return bool(self.tushare_token)

    @property
    def has_ths(self) -> bool:
        """配置了 THS_API_KEY 时，同花顺数据源可用（板块/涨停/指数等）"""
        return bool(self.ths_api_key)

    @property
    def has_api_token(self) -> bool:
        """配置了 API_TOKEN 时，写接口需要携带该 token"""
        return bool(self.api_token)


@lru_cache()
def get_settings() -> Settings:
    return Settings()

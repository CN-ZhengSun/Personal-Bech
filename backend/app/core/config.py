from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """应用配置，可通过环境变量或 backend/.env 覆盖。"""

    APP_NAME: str = "测试工作台 Test Workbench"
    APP_VERSION: str = "0.1.0"
    DEBUG: bool = True

    # 本机单用户部署
    LOCAL_ONLY: bool = True
    APP_SECRET_KEY: str = ""
    SESSION_COOKIE_NAME: str = "twb_session"
    SESSION_DAYS: int = 90
    ALLOWED_HOSTS: list[str] = ["localhost", "127.0.0.1", "testserver"]

    # 数据库
    DB_HOST: str = "127.0.0.1"
    DB_PORT: int = 3306
    DB_USER: str = "admin"
    DB_PASSWORD: str = "123456"
    DB_NAME: str = "testworkbench"
    DATABASE_URL: str = ""  # 显式指定时优先使用

    # CORS
    CORS_ORIGINS: list[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    def get_database_url(self) -> str:
        if self.DATABASE_URL:
            return self.DATABASE_URL
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}?charset=utf8mb4"
        )


settings = Settings()
